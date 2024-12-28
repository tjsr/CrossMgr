import socket
import sys
import time
import datetime
from typing import List, Union

from ByteUtils import ISO_ENCODING, EOL
from SocketUtils import socketReadDelimited, socketSend, socketSendMessage
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
import traceback

ChipReaderEvent, EVT_CHIP_READER = JChip.ChipReaderEvent, JChip.EVT_CHIP_READER

readerEventWindow = None
def sendReaderEvent( tagTimes ):
	if tagTimes and readerEventWindow:
		wx.PostEvent( readerEventWindow, ChipReaderEvent(tagTimes = tagTimes) )

len_EOL = len(EOL)
EPOCH_TIME = datetime.datetime(1980, 1, 1)
CONNECT_INFO_FORMAT = r'^\d{1,2}:\d{1,2}:\d{1,2} \d{1,2}-\d{1,2}-\d{4} \(-?\d+\)$'

class UltraDecoderMessage:
	def is_connect_info_message( message: str ) -> bool:
		return re.match( CONNECT_INFO_FORMAT, message ) != None
	
	def __init__( self, ultraId: int ):
		return

# Definitions from https://rfidtiming.com/Software/UltraManual.pdf Pg41
class UltraChipReadMessage(UltraDecoderMessage):
  # Retain this field order
	Zero: int # Zero (unused at present) 
	ChipCode: int # Could be the chip code decimal or hexadecimal value, depending on current setting in Ultra (see section 3.8) 
	Seconds: int # Integer value representing the number of seconds after 01/01/1980 
	Milliseconds: int # Integer value representing the millisecond portion of the time.
	RSSI: int # Negative integer value. This is the signal strength for the chip
	IsRewind: int # 0 or 1. A value of 1 means the data is being transmitted from a rewind command,
  # in other words it is not a ‘live’ read. Live and rewound data will be mixed up in between
  # each other if you do a ‘rewind while reading’. 
	ReaderNo: int # Integer value of from 1 to 3 representing the reader number. There are 2 
  # readers in an Ultra. A reader number of 3 is used for MTB downhill start times.
	UltraId: int # Integer value. See section 3.1 
	ReaderTime: str # 8 characters representing the 64-bit time recorded by the UHF readers. Not
 	# available for some Ultra models – please speak to your supplier for more information. 
	StartTime: int # For MTB downhill racing. Integer value representing the number of seconds after 01/01/1980
	LogId: int # Integer value representing the record’s position in the log (starting at one) 
 
	# Derived fields
	ChipCodeAsHexValue: bool
 
	def __init__( self, ultraId: int, chipCode: int ):
		return

def parseTagTime( crossingData: str ):
	Zero, ChipCode, Seconds, Milliseconds, Extra =  crossingData.split(',', 4)
	# AntennaNo, RSSI, IsRewind, ReaderNo, UltraID, ReaderTime, StartTime, LogID
	ExtraValues = Extra.split(',', 7)
	t = EPOCH_TIME + datetime.timedelta( seconds=int(Seconds), milliseconds=int(Milliseconds) )
	return ChipCode, t

DEFAULT_PORT = 23
#DEFAULT_PORT = 8642
DEFAULT_HOST = '127.0.0.1'		# Port to connect to the Ultra receiver.

q = None
shutdownQ = None
listener = None

def iterAdjacentIPs():
	''' Return ip addresses adjacent to the computer in an attempt to find the reader. '''
	ip = [int(i) for i in Utils.GetDefaultHost().split('.')]
	ipPrefix = '.'.join( '{}'.format(v) for v in ip[:-1] )
	ipLast = ip[-1]
	
	count = 0
	j = 0
	while 1:
		j = -j if j > 0 else -j + 1
		
		ipTest = ipLast + j
		if 0 <= ipTest < 256:
			yield '{}.{}'.format(ipPrefix, ipTest)
			count += 1
			if count >= 8:
				break

def AutoDetect( ultraPort=DEFAULT_PORT, callback=None ):
	for ultraHost in iterAdjacentIPs():
		if callback:
			if not callback( '{}:{}'.format(ultraHost,ultraPort) ):
				return None
		
		try:
			s: socket.socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
			s.settimeout( 0.5 )
			s.connect( (ultraHost, ultraPort) )
		except Exception:
			continue

		try:
			buffer: str = socketReadDelimited( s )
		except Exception:
			continue
			
		try:
			s.close()
		except Exception:
			pass
		
		if buffer.startswith('Connected'):
			return ultraHost
			
	return None

# if we get the same time, make sure we give it a small offset to make it unique, but preserve the order.
tSmall = datetime.timedelta( seconds = 0.000001 )

reNonDigit = re.compile( '[^0-9]+' )
def Server( q: Queue, shutdownQ: Queue, HOST: str, PORT: int, startTime ):
	global readerEventWindow
	
	if not readerEventWindow:
		readerEventWindow = Utils.mainWin
	
	timeoutSecs = 5
	delaySecs = 3
	
	readerComputerTimeDiff = None
	
	s: socket.socket = None
	
	def qLog( category: str, message: str ):
		q.put( (category, message) )
		Utils.writeLog( 'Ultra: {}: {}'.format(category, message) )
	
	def qLogError( category: str, message: str ):
		q.put( (category, message) )
		Utils.writeLog( 'ERROR (Ultra): {}: {}'.format(category, message) )
  
	def qLogException( category, e, exc_info ):
		# eType, eValue, eTraceback = exc_info
		ex = traceback.format_exception( e )
		for d in ex:
			for line in d.split( '\n' ):
				q.put( category, line )

	def keepGoing():
		try:
			shutdownQ.get_nowait()
		except Empty:
			return True
		return False
	
	def autoDetectCallback( m ):
		qLog( 'autodetect', '{} {}'.format(_('Checking'), m) )
		return keepGoing()
		
	def makeCall( s: socket.socket, message: str, getReply: bool=True, comment: str='' ) -> str|None:
		cmd = message.split(';', 1)[0]
		buffer: str|None = None
		qLog( 'command', 'sending: {}{}'.format(message, ' ({})'.format(comment) if comment else '') )
		try:
			#socketSend( s, bytes('{}{}'.format(message,EOL)) )
			socketSendMessage( s, message )
			if getReply:
				buffer = socketReadDelimited( s )
		except Exception as e:
			tb = traceback.format_exc()
			qLog( 'connection.makeCall', '{}: {}: "{}"'.format(cmd, _('Connection failed'), tb) )
			raise e
		
		return buffer

	def stopReader():
		try:
			makeCall( s, 'S', False, comment='stop reading' )
		except ValueError:
			pass
	
	def startReader():
		try:
			makeCall( s, 'R', False, comment='start reading' )
		except ValueError:
			pass

	while keepGoing():
		if s:
			try:
				s.shutdown( socket.SHUT_RDWR )
				s.close()
			except Exception:
				pass
			time.sleep( delaySecs )
		
		#-----------------------------------------------------------------------------------------------------
		qLog( 'connection', '{} {}:{}'.format(_('Attempting to connect to Ultra reader at'), HOST, PORT) )
		try:
			s:socket.socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
			s.settimeout( timeoutSecs )
			s.connect( (HOST, PORT) )
		except Exception as e:
			qLog( 'connection', '{}: {}'.format(_('Connection to Ultra reader failed'), e) )
			s = None
			
			qLog( 'connection', '{}'.format(_('Attempting AutoDetect...')) )
			HOST_AUTO = AutoDetect( callback = autoDetectCallback )
			if HOST_AUTO:
				qLog( 'connection', '{}: {}'.format(_('AutoDetect Ultra at'), HOST_AUTO) )
				HOST = HOST_AUTO
			else:
				time.sleep( delaySecs )
			continue

		qLog( 'connection', '{} {}:{}'.format(_('connect to Ultra reader SUCCEEDS on'), HOST, PORT) )
		
		#-----------------------------------------------------------------------------------------------------
		try:
			stopReader()
		except ValueError:
			continue
		
		#-----------------------------------------------------------------------------------------------------
		# Set the reader's time.
		# Wait for the boundary of a second.  This is the best synchronization we are going to get.
		time.sleep( (1000000 - now().microsecond) / 1000000.0 )
		try:
			message: str = 't {}'.format( now().strftime('%H:%M:%S %d-%m-%Y') )
			buffer = makeCall( s, message, True, comment='set reader time' )
		except ValueError as ve:
			Utils.logException( ve, sys.exc_info() )
			tb = traceback.format_exc()
			qLog( 'connection', '{}: {}: {}'.format(_('Invalid value when setting time on decoder'), ve, tb) )
			continue
		except Exception as e:
			Utils.logException( e, sys.exc_info() )
			tb = traceback.format_exc()
			qLog( 'connection', '{}: {}'.format(_('Failed to set time on decoder'), tb) )
			continue

		readerComputerTimeDiff = datetime.timedelta( seconds=0 )
		
		#-----------------------------------------------------------------------------------------------------
		try:
			startReader()
		except ValueError:
			continue
 
		qLog( 'connection', '{}'.format(_('Reading data from decoder...')) )
		
		lastVoltage = now()
		while keepGoing():
			try:
				buffer: str = socketReadDelimited( s )
				# qLog( 'reader.keepGoing', '{}: "{}"'.format(_('Parsing messages'), str(buffer, ISO_ENCODING)) )
			except socket.timeout:
				if (now() - lastVoltage).total_seconds() > 15:
					qLog( 'connection.keepGoing', _('Lost heartbeat.') )
				continue
			except Exception as e:
				Utils.logException( e, sys.exc_info() )
				qLog( 'connection.keepGoing', '{}: "{}"'.format(_('Connection failed'), e) )
				break
  
			tagTimes = []
			times = set()
			for message in buffer.splitlines(False):
				if UltraDecoderMessage.is_connect_info_message( message ):
					qLog('connect.keepGoing', '{}: "{}"'.format(_('Last data sent'), message) )
					continue

				# Check for a heartbeat.
				if message.startswith( 'V=' ):
					# qLog( 'heartbeat.keepGoing', '{}: "{}"'.format(_('heartbeat'), message) )
					lastVoltage = now()	# If so, reset the last heartbeat time.
					continue

				qLog( 'connection.keepGoing', '{}: "{}"'.format(_('data'), message) )
				# Otherwise, assume this is a chip read.
				try:
					tag, t = parseTagTime( message )
				except Exception as e:
					qLog('reader.keepGoing.parseTagTime.exception', '{}: "{}"'.format(_('Failed to parse tag time'), message) )
					qLogException( 'reader.keepGoing', e, sys.exc_info() )
					continue

				if tag is None or t is None:
					qLogError( 'command.keepGoing', '{}: "{}"'.format(_('Unexpected reader message'), message) )
					continue
				
				t += readerComputerTimeDiff
				while t in times:	# Ensure no equal times.
					t += tSmall
				
				times.add( t )
				tagTimes.append( (tag, t) )
		
			sendReaderEvent( tagTimes )
			for tag, t in tagTimes:
				q.put( ('data', tag, t) )
	
	# Final cleanup.
	try:
		s.shutdown( socket.SHUT_RDWR )
		s.close()
	except Exception:
		pass
		
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
			StartListener( HOST='127.0.0.1', PORT=DEFAULT_PORT )
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

