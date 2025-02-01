import enum
import socket
import sys
import time
import datetime
from abc import abstractmethod
from typing import List, Union

from ByteUtils import ISO_ENCODING, EOL
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

readerEventWindow = None
def sendReaderEvent( tagTimes ):
	if tagTimes and readerEventWindow:
		wx.PostEvent( readerEventWindow, ChipReaderEvent(tagTimes = tagTimes) )

len_EOL = len(EOL)

q: Queue|None = None
shutdownQ: Queue|None = None
listener: Process|None = None

# if we get the same time, make sure we give it a small offset to make it unique, but preserve the order.
tSmall = datetime.timedelta( seconds = 0.000001 )

reNonDigit = re.compile( '[^0-9]+' )
def Server( q: Queue, shutdownQ: Queue, HOST: str, PORT: int, startTime ):
	global readerEventWindow
	log: LogQueue = LogQueue(q, 'ultra')
	ultraDecoder = UltraDecoder(log, HOST, PORT)

	def on_chip_read( tagTimes: List[Union[str, datetime.datetime]] ) -> None:
		sendReaderEvent(tagTimes)
		for tag, tagTime in tagTimes:
			q.put(('data', tag, tagTime))

	ultraDecoder.crossingListener = on_chip_read

	if not readerEventWindow:
		readerEventWindow = Utils.mainWin
	
	delaySecs = 3
	
	readerComputerTimeDiff = None

	def keepGoing():
		try:
			shutdownQ.get_nowait()
		except Empty:
			return True
		return False
	
	def autoDetectCallback( m ):
		log.q( 'autodetect', '{} {}'.format(_('Checking'), m) )
		return keepGoing()

	while keepGoing():
		if ultraDecoder.disconnect():
			time.sleep( delaySecs )

		if not ultraDecoder.connect():
			continue
		
		#-----------------------------------------------------------------------------------------------------
		try:
			ultraDecoder.stop_reading()
		except ValueError:
			continue

		if not ultraDecoder.setTime():
			continue

		ultraDecoder.computerTimeDiff = datetime.timedelta( seconds=0 )

		#-----------------------------------------------------------------------------------------------------
		try:
			time.sleep(delaySecs)
			ultraDecoder.begin_reading()
		except ValueError:
			continue
		except Exception as e:
			log.exception( 'ultra.keepGoing', e )

		log.q('ultra.keepGoing', '{}'.format(_('Reading data from decoder...')))
		
		while keepGoing():
			try:
				ultraDecoder.get_messages()
				ultraDecoder.process_messages()
			except Exception as e:
				log.exception('ultra.keepGoing', e)
				break
	
	# Final cleanup.
	ultraDecoder.disconnect()
		
def GetData():
	data = []
	while 1:
		try:
			data.append( q.get_nowait() )
		except (Empty, AttributeError):
			break
	return data

def StopListener():
	global q
	global listener
	global shutdownQ
	
	# Terminate the server process if it is running.
	# Add a number of shutdown commands as we may check a number of times.
	if listener:
		for i in range(32):
			shutdownQ.put( 'shutdown' )
		listener.join()
	listener = None
	
	# Purge the queues.
	while q:
		try:
			q.get_nowait()
		except Empty:
			q = None
			break
	
	shutdownQ = None
	
def IsListening():
	return listener is not None


def StartListener( startTime=now(), HOST=None, PORT=None, test=False ):
	global q
	global shutdownQ
	global listener
	
	StopListener()

	if Model.race:
		HOST = (HOST or Model.race.chipReaderIpAddr)
		PORT = (PORT or Model.race.chipReaderPort)

	q = Queue()
	shutdownQ = Queue()
	listener = Process( target = Server, args=(q, shutdownQ, HOST, PORT, startTime) )
	listener.name = 'Ultra Listener'
	listener.daemon = True
	listener.start()
	
@atexit.register
def CleanupListener():
	global shutdownQ
	global listener
	if listener and listener.is_alive():
		shutdownQ.put( 'shutdown' )
		listener.join()
	listener = None
	
if __name__ == '__main__':
	def doTest():
		try:
			StartListener( HOST=UltraDecoder.DEFAULT_HOST, PORT=UltraDecoder.DEFAULT_PORT )
			count = 0
			while 1:
				time.sleep( 1 )
				sys.stdout.write( '.' )
				messages = GetData()
				if messages:
					sys.stdout.write( '\n' )
				for m in messages:
					if m[0] == 'data':
						count += 1
						print( '{}: {}, {}'.format(count, m[1], m[2].time()) )
					else:
						print( 'other: {}, {}'.format(m[0], ', '.join('"{}"'.format(s) for s in m[1:])) )
				sys.stdout.flush()
		except KeyboardInterrupt:
			return
		
	t = threading.Thread( target=doTest )
	t.daemon = True
	t.run()
	
	time.sleep( 1000000 )

