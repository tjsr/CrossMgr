import asyncio
import logging
import time
import datetime
from typing import List, Union, Optional, Callable, Coroutine, Any

import Log
from ByteUtils import EOL
from LogQueue import LogQueue
from TimingDevices.DecoderMessages import DecoderCrossingMessage
from TimingDevices.TCPTimingDevice import TCPTimingDevice
from TimingDevices.TimingDeviceWXEvents import TimingDeviceTransponderEvent

from TimingDevices.UltraTimingDevice import UltraDecoder

now = datetime.datetime.now
import atexit
import threading
import wx
import wx.lib.newevent
import Utils
import Model
from queue import Queue, Empty
import JChip

ChipReaderEvent, EVT_CHIP_READER = JChip.ChipReaderEvent, JChip.EVT_CHIP_READER
DecoderThreadEndedEvent, EVT_DECODER_THREAD_ENDED = wx.lib.newevent.NewEvent()

ultraDecoder: Optional[UltraDecoder] = None

len_EOL = len(EOL)
lock: threading.Lock = threading.Lock()

q: Queue|None = None
shutdownQ: Queue|None = None

# if we get the same time, make sure we give it a small offset to make it unique, but preserve the order.
tSmall = datetime.timedelta( seconds = 0.000001 )

class TDFListenerThread(threading.Thread):
	_decoder: TCPTimingDevice
	_log: logging.Logger
	_test_mode: bool = False

	def __init__(self, decoder: TCPTimingDevice = None):
		listener_thread_name = f'{decoder.description} Ultra Listener'

		threading.Thread.__init__(self, target=asyncio.run, args=(self._main_loop(),), daemon=True, name=listener_thread_name)

		if decoder is None:
			raise ValueError('decoder is required.')

		self._decoder = decoder
		self._log = Log.getLogger('TDFListenerThread')

	@property
	def Decoder(self):
		return self._decoder

	@property
	def log(self) -> logging.Logger:
		return self._log

	@property
	def IsTestMode(self) -> bool:
		return self._test_mode

	async def sync_disconnect(self, reason: str = None):
		if self._decoder.connected():
			await self._decoder.disconnect(reason=reason)

	async def init(self) -> None:
		pass

	def start(self, *args, **kwargs) -> None:
		self.log.info('Starting Ultra decoder thread.')
		return threading.Thread.start(self)

	def run(self) -> None:
		return threading.Thread.run(self)

	async def _main_loop(self) -> bool:
		while self._decoder.ShouldReconnect:
			if self._decoder.WaitForReconnect:
				time.sleep(0.500)
				continue
			if not self._decoder.connect():
				retries = f'{self._decoder.ReconnectAttemptCount}/{self._decoder.MaximumReconnectionAttempts}'
				if self._decoder.ShouldReconnect:
					Log.getLogger(name='Ultra').warning(
						f'Waiting until {ultraDecoder.NextReconnectTime} before trying again ({retries}).')
				else:
					Log.getLogger(name='Ultra').warning(f'Maximum connection retries ({retries}) reached - not reconnecting.')
				continue

			while ultraDecoder.connected():
				if not ultraDecoder.process():
					return False

		await listener.sync_disconnect(reason='Server thread condition to continue is False.')

		return False

	def sendReaderEvent(self, tagTimes: List[Union[str, datetime.datetime]]) -> None:
		pass

	def on_chip_read(self, tagTimes: List[Union[str, datetime.datetime]] ) -> None:
		if self.IsTestMode is not True:
			self.sendReaderEvent(tagTimes)
		elif not hasattr(ultraDecoder, 'sendReaderEvent') and self.IsTestMode is not True:
			Log.getLogger('on_chip_read').error('sendReaderEvent is None.')
		else:
			pass

	def stop(self) -> None:
		if self._decoder is None:
			raise ValueError('decoder is required.')

		self._decoder.ShouldReconnect = False

		# The thread will terminate after the socket is disconnected.
		# A manual disconnect command tells it to stop attempting to reconnect and will end the main loop.
		asyncio.run(self.sync_disconnect())

		self.join()


listener: TDFListenerThread|None = None

class WXUltraDecoder(UltraDecoder):
	log: LogQueue = LogQueue(q, 'ultra')
	_readerEventWindow: wx.Window = None

	def __init__(self, host: str, port: int, eventWindow: wx.Window = None):
		super().__init__(host, port)
		self._readerEventWindow = eventWindow if eventWindow is not None else Utils.mainWin
		self.crossingListener = self._crossingListener

	def registerListener( self, windowListener: Callable[[List[Union[str, datetime.datetime]]], None] ) -> None:
		self.crossingListener = windowListener

	def transponderEvent(self, message: DecoderCrossingMessage) -> None:
		wx.PostEvent( self._readerEventWindow, TimingDeviceTransponderEvent(message=message) )

	def _crossingListener(self, tagTimes: List[Union[str, datetime.datetime]]) -> None:
		if tagTimes and self._readerEventWindow:
			wx.PostEvent(self._readerEventWindow, ChipReaderEvent(tagTimes=tagTimes))

	# def on_chip_read(self, tagTimes: List[Union[str, datetime.datetime]] ) -> None:
	# 	if self.IsTestMode is not True:
	# 		self.sendReaderEvent(tagTimes)
	# 	elif not hasattr(ultraDecoder, 'sendReaderEvent') and self.IsTestMode is not True:
	# 		Log.getLogger('on_chip_read').error('sendReaderEvent is None.')
	# 	else:
	# 		if tagTimes and self._readerEventWindow:
	# 			wx.PostEvent(self._readerEventWindow, ChipReaderEvent(tagTimes=tagTimes))


class WXUltraDecoderListenerThread(TDFListenerThread):
	_wxDecoder: WXUltraDecoder
	_eventWindow: wx.Window

	def __init__(self, host: str, port: int, eventWindow: wx.Window):
		if eventWindow is None:
			raise ValueError('eventWindow is required.')
		if host is None:
			raise ValueError('host is required.')
		if port is None:
			raise ValueError('port is required.')

		self._wxDecoder = WXUltraDecoder(host, port)
		self._wxDecoder._readerEventWindow = eventWindow
		TDFListenerThread.__init__(self, decoder=self._wxDecoder)

		self._eventWindow = eventWindow
		self._decoder.crossing_listener = self.on_chip_read

	@property
	def Decoder(self) -> WXUltraDecoder:
		return self._wxDecoder

	async def _main_loop(self) -> Any: # Coroutine[Any, Any, bool]:
		result = await TDFListenerThread._main_loop(self)
		threading.Thread(target=lambda: asyncio.run(self.signalThreadEnded())).start()
		return result

	async def signalThreadEnded(self) -> None:
		wx.PostEvent(self._eventWindow, DecoderThreadEndedEvent(
			owner=threading.current_thread(),
			should_restart_thread=self._wxDecoder.ShouldReconnect)
   )


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


def IsListening() -> bool:
	return listener is not None and listener.is_alive()

def StopListener() -> None:
	global listener

	lock.acquire(blocking=True, timeout=1.0)
	try:
		if IsListening() is True:
			listener.stop()
	finally:
		if lock.locked():
			lock.release()

def GetCurrentDecoder() -> UltraDecoder | None:
	global ultraDecoder
	return ultraDecoder


def StartListener(startTime: datetime.datetime=now(), host: str=None, port: int=None, test: bool=False) -> threading.Thread:
	global q
	global shutdownQ
	global listener
	global ultraDecoder

	Log.getLogger('Ultra').trace(msg='Starting Ultra decoder thread')

	lock.acquire(blocking=True, timeout=1.0)
	try:
		if IsListening() is True:
			listener.stop()
			listener.join(5.0)
	finally:
		if lock.locked():
			lock.release()

	if Model.race:
		host = (host or Model.race.chipReaderIpAddr)
		port = (port or Model.race.chipReaderPort)

	Log.getLogger('Ultra').info('Starting Ultra decoder thread.')
	if test is True:
		ultraDecoder = UltraDecoder(host, port)
		listener = TDFListenerThread(ultraDecoder)
	else:
		listener = WXUltraDecoderListenerThread(host, port, Utils.mainWin)
		ultraDecoder = listener.Decoder

	listener.start()
	return listener

@atexit.register
def CleanupListener() -> None:
	global shutdownQ
	global listener
	if listener and listener.is_alive():
		listener.join()
	listener = None


if __name__ == '__main__':
	def doTest() -> None:
		global listener
		# ultraTestHost = '192.168.1.148' # UltraDecoder.DEFAULT_HOST
		ultraTestHost = '192.168.1.119' # UltraDecoder.DEFAULT_HOST
		try:
			listener = StartListener(host=ultraTestHost, port=UltraDecoder.DEFAULT_PORT, test=True)
			listener.join()

		except KeyboardInterrupt:
			return
		
	t = threading.Thread( target=doTest )
	t.daemon = True
	t.run()
	
	time.sleep( 1000000 )

