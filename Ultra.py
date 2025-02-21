import sys
import time
import datetime
from typing import List, Union, Optional

import Log
from ByteUtils import EOL
from LogQueue import LogQueue

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

readerEventWindow = None
ultraDecoder: Optional[UltraDecoder] = None
def sendReaderEvent( tagTimes ):
	if tagTimes and readerEventWindow:
		wx.PostEvent( readerEventWindow, ChipReaderEvent(tagTimes = tagTimes) )

len_EOL = len(EOL)

q: Queue|None = None
shutdownQ: Queue|None = None
listener: Process|None = None

# if we get the same time, make sure we give it a small offset to make it unique, but preserve the order.
tSmall = datetime.timedelta( seconds = 0.000001 )

class WXUltraDecoder(UltraDecoder):
	log: LogQueue = LogQueue(q, 'ultra')

	def __init__(self, host: str, port: int):
		super().__init__(host, port)

	def registerListener( self, windowListener: callable ):
		self.crossingListener = windowListener


reNonDigit = re.compile( '[^0-9]+' )
def Server( HOST: str, PORT: int, _startTime ):
	global readerEventWindow
	global ultraDecoder
	reconnect:bool = True
	ultraDecoder = WXUltraDecoder(HOST, PORT)

	def on_chip_read( tagTimes: List[Union[str, datetime.datetime]] ) -> None:
		sendReaderEvent(tagTimes)
		for tag, tagTime in tagTimes:
			Log.getLogger('on_chip_read').warning("Need to reimplement this.")
			# q.put(('data', tag, tagTime))

	ultraDecoder.crossingListener = on_chip_read

	if not readerEventWindow:
		readerEventWindow = Utils.mainWin

	while ultraDecoder.ShouldReconnect:
		if ultraDecoder.WaitForReconnect:
			time.sleep(0.500)
			continue
		if not ultraDecoder.connect():
			if ultraDecoder.ShouldReconnect:
				Log.getLogger(name='Ultra').warning(
					f'Waiting until {ultraDecoder.NextReconnectTime} before trying again ({ultraDecoder.ReconnectAttemptCount}/{ultraDecoder.MaximumReconnectionAttempts}).')
			else:
				Log.getLogger(name='Ultra').warning('Maximum connection retries reached - not reconnecting.')
			continue

		while ultraDecoder.connected():
			if not ultraDecoder.process():
				break

	if ultraDecoder.connected():
		ultraDecoder.disconnect()
	Log.getLogger('Ultra').debug('Decoder read thread ended')

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

def StopListener():
	global listener

	# Terminate the server process if it is running.
	# Add a number of shutdown commands as we may check a number of times.
	if listener is not None and ultraDecoder is not None:
		ultraDecoder.disconnect()
		listener.join()
	postEvent = listener is not None
	listener = None
	
	if postEvent is True:
		wx.PostEvent( readerEventWindow, DecoderThreadEndedEvent() )
	
def IsListening() -> bool:
	return listener is not None

def GetCurrentDecoder() -> UltraDecoder | None:
	global ultraDecoder
	return ultraDecoder


def StartListener( startTime=now(), HOST=None, PORT=None, test=False ):
	global q
	global shutdownQ
	global listener
	
	StopListener()

	if Model.race:
		HOST = (HOST or Model.race.chipReaderIpAddr)
		PORT = (PORT or Model.race.chipReaderPort)

	listener = Process( target = Server, args=(HOST, PORT, startTime) )
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
			StartListener( HOST=ultraTestHost, PORT=UltraDecoder.DEFAULT_PORT )
			count = 0
			cols = 1
			while 1:
				time.sleep( 1 )
				# sys.stdout.write( '.' )
				messages = GetData()
				if messages or cols % 80 == 0:
					# sys.stdout.write( '\n' )
					cols = 1
				else:
					cols += 1
				for m in messages:
					if m[0] == 'data':
						count += 1
						# print( '{}: {}, {}'.format(count, m[1], m[2].time()) )
					else:
						print( 'other: {}, {}'.format(m[0], ', '.join('"{}"'.format(s) for s in m[1:])) )
				sys.stdout.flush()
		except KeyboardInterrupt:
			return
		
	t = threading.Thread( target=doTest )
	t.daemon = True
	t.run()
	
	time.sleep( 1000000 )

