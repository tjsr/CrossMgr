import asyncio
import sys
import time
import datetime
from typing import List, Union, Optional, Callable

import Log
from ByteUtils import EOL
from LogQueue import LogQueue
from TimingDevices.DecoderMessages import DecoderCrossingMessage
from TimingDevices.TimingDeviceWXEvents import TimingDeviceTransponderEvent

from TimingDevices.UltraTimingDevice import UltraDecoder

now = datetime.datetime.now
import atexit
import threading
import re
import wx
import wx.lib.newevent
import Utils
import Model
from threading import Thread as Process
from queue import Queue, Empty
import JChip

ChipReaderEvent, EVT_CHIP_READER = JChip.ChipReaderEvent, JChip.EVT_CHIP_READER
DecoderThreadEndedEvent, EVT_DECODER_THREAD_ENDED = wx.lib.newevent.NewEvent()

ultraDecoder: Optional[UltraDecoder] = None

len_EOL = len(EOL)

q: Queue|None = None
shutdownQ: Queue|None = None
listener: Process|None = None

# if we get the same time, make sure we give it a small offset to make it unique, but preserve the order.
tSmall = datetime.timedelta( seconds = 0.000001 )

class WXUltraDecoder(UltraDecoder):
	log: LogQueue = LogQueue(q, 'ultra')
	_readerEventWindow: wx.Window = None

	def __init__(self, host: str, port: int, eventWindow: wx.Window = None):
		super().__init__(host, port)
		self._readerEventWindow = eventWindow if eventWindow is not None else Utils.mainWin

	def registerListener( self, windowListener: Callable[[List[Union[str, datetime.datetime]]], None] ) -> None:
		self.crossingListener = windowListener

	async def signalThreadEnded(self) -> None:
		wx.PostEvent(self._readerEventWindow, DecoderThreadEndedEvent(
			owner=threading.current_thread(),
			should_restart_thread=self.ShouldReconnect)
		)

	def sendReaderEvent(self, tagTimes: List[Union[str, datetime.datetime]]) -> None:
		if tagTimes and self._readerEventWindow:
			wx.PostEvent( self._readerEventWindow, ChipReaderEvent(tagTimes = tagTimes) )

	def transponderEvent(self, message: DecoderCrossingMessage) -> None:
		wx.PostEvent( self._readerEventWindow, TimingDeviceTransponderEvent(message=message) )


reNonDigit = re.compile( '[^0-9]+' )
async def Server( HOST: str, PORT: int, _startTime, test:bool = False ):
	global ultraDecoder
	Log.getLogger('Ultra').info('Starting Ultra decoder thread.')
	if test is True:
		ultraDecoder = UltraDecoder(HOST, PORT)
	else:
		ultraDecoder = WXUltraDecoder(HOST, PORT, None)
	ultraDecoder.MaximumReconnectionAttempts = 1

	def on_chip_read( tagTimes: List[Union[str, datetime.datetime]] ) -> None:
		if test is not True:
			ultraDecoder.sendReaderEvent(tagTimes)
		elif not hasattr(ultraDecoder, 'sendReaderEvent') and test is not True:
			Log.getLogger('on_chip_read').error('sendReaderEvent is None.')

	ultraDecoder.crossingListener = on_chip_read

	while ultraDecoder.ShouldReconnect:
		if ultraDecoder.WaitForReconnect:
			time.sleep(0.500)
			continue
		if not ultraDecoder.connect():
			retries = f'{ultraDecoder.ReconnectAttemptCount}/{ultraDecoder.MaximumReconnectionAttempts}'
			if ultraDecoder.ShouldReconnect:
				Log.getLogger(name='Ultra').warning(
					f'Waiting until {ultraDecoder.NextReconnectTime} before trying again ({retries}).')
			else:
				Log.getLogger(name='Ultra').warning(f'Maximum connection retries ({retries}) reached - not reconnecting.')
			continue

		while ultraDecoder.connected():
			if not ultraDecoder.process():
				break

	if ultraDecoder.connected():
		await ultraDecoder.disconnect()

	Log.getLogger('Ultra').debug('Decoder read thread ended')
	if not test:
		threading.Thread(target=lambda: asyncio.run(ultraDecoder.signalThreadEnded())).start()
	else:
		ultraDecoder.ShouldReconnect = False


def GetData():
	data = []
	while 1:
		try:
			# data.append( q.get_nowait() )
			Log.getLogger().warning("Need to re-implement this.")
			pass
		except (Empty, AttributeError):
			break
	return data

async def sync_disconnect(decoder: UltraDecoder):
	if decoder.connected():
		await decoder.disconnect()

def StopListener():
	global listener

	# The thread will terminate after the socket is disconnected.
	# A manual disconnect command tells it to stop attempting to reconnect and will end the main loop.
	if listener is not None and ultraDecoder is not None:
		asyncio.run(sync_disconnect(ultraDecoder))
		listener.join()
	listener = None


def IsListening() -> bool:
	return listener is not None and listener.is_alive()

def GetCurrentDecoder() -> UltraDecoder | None:
	global ultraDecoder
	return ultraDecoder


def StartListener(startTime: datetime.datetime=now(), host: str=None, port: int=None, test: bool=False) -> None:
	global q
	global shutdownQ
	global listener

	if listener and listener.is_alive():
		StopListener()
		listener.join(5.0)

	if Model.race:
		host = (host or Model.race.chipReaderIpAddr)
		port = (port or Model.race.chipReaderPort)

	listener = Process(target = asyncio.run, args=(Server(host, port, startTime, test=test),))
	listener.name = 'Ultra Listener'
	listener.daemon = True
	listener.start()

@atexit.register
def CleanupListener():
	global shutdownQ
	global listener
	if listener and listener.is_alive():
		listener.join()
	listener = None


if __name__ == '__main__':
	def doTest():
		ultraTestHost = '192.168.1.148' # UltraDecoder.DEFAULT_HOST
		try:
			StartListener(host=ultraTestHost, port=UltraDecoder.DEFAULT_PORT, test=True)
			listener.join()

		except KeyboardInterrupt:
			return
		
	t = threading.Thread( target=doTest )
	t.daemon = True
	t.run()
	
	time.sleep( 1000000 )

