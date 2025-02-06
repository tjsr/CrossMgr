import datetime
import socket
import time
from typing import List, Optional

from LogQueue import LogQueue
from SocketUtils import socketReadDelimited, socketSendMessage
from TimingDevices.TimingDevice import UnrecognisedCommandException, TimingDevice, DecoderMessage, \
	UnrecognisedDecoderMessage, CrossingListenerCallableType
from TimingDevices.TCCPTimingDevice import TCPTimingDevice
from TimingDevices.TimingDeviceCommand import TimingDeviceCommand
import re

from TimingDevices.UltraAutodetect import AutoDetect

now = datetime.datetime.now
EPOCH_TIME = datetime.datetime(1980, 1, 1)

# if we get the same time, make sure we give it a small offset to make it unique, but preserve the order.
tSmall = datetime.timedelta( seconds = 0.000001 )

class UltraDecoder(TimingDevice, TCPTimingDevice):
	commands = {
		'start': TimingDeviceCommand('R', False),
		'stop': TimingDeviceCommand('S', False),
		'status': TimingDeviceCommand('?', True)
	}

	DEFAULT_PORT: int = 23
	# DEFAULT_PORT = 8642
	DEFAULT_HOST: str = '127.0.0.1'  # Port to connect to the Ultra receiver.

	_delaySecs: int = 3
	_lastVoltage: datetime.datetime | None = None
	_computerTimeDiff: datetime.timedelta | None = None
	_crossing_listener: CrossingListenerCallableType | None = None

	def __init__( self, log: LogQueue, host: str, port: int ):
		TimingDevice.__init__(self)
		TCPTimingDevice.__init__(self, host, port)
		self.logger = log

	def getDeviceType(self) -> str:
		return 'Ultra'

	@property
	def crossingListener(self) -> CrossingListenerCallableType:
		return self._crossing_listener

	@crossingListener.setter
	def crossingListener(self, listener: CrossingListenerCallableType):
		self._crossing_listener = listener

	@property
	def computerTimeDiff(self) -> datetime.timedelta:
		return self._computerTimeDiff

	@computerTimeDiff.setter
	def computerTimeDiff(self, offset: datetime.timedelta):
		self._computerTimeDiff = offset

	def on_connect(self) -> bool:
		result = False
		try:
			result = self.setTime() or result
			result = self.get_status() or result
		except Exception as e:
			self.getLog().exception('Failed while getting decoder status', e)

		return result

	def begin_reading( self ) -> None:
		try:
			self.makeCall('R', comment='start reading')
		except ValueError:
			pass

	def stop_reading(self) -> None:
		try:
			self.makeCall('S', comment='stop reading')
		except ValueError:
			pass

	def autoconnect(self, autoDetectCallback) -> bool:
		self.log('autoconnect', '{}'.format(_('Attempting AutoDetect...')))
		HOST_AUTO = AutoDetect(callback=autoDetectCallback)
		if HOST_AUTO:
			self.log('autoconnect', '{}: {}'.format(_('AutoDetect Ultra at'), HOST_AUTO))
			self._host = HOST_AUTO
		else:
			time.sleep(self._delaySecs)
		return False

	def setTime(self) -> bool:
		#-----------------------------------------------------------------------------------------------------
		# Set the reader's time.
		# Wait for the boundary of a second.  This is the best synchronization we are going to get.
		time.sleep( (1000000 - now().microsecond) / 1000000.0 )
		decoderMessage: str
		try:
			decoderMessage = 't {}'.format( now().strftime('%H:%M:%S %d-%m-%Y') )
			buffer = self.makeSyncCall( decoderMessage, comment='set reader time' )
			bufSize:int = self.process_message_buffer(buffer)
			self.log('setTime', '{}: {} ({} on queue)'.format(_('Response to set time on decoder'), buffer, bufSize))

			# We wait for the second boundary above and then set the offset to the response here so we know the round-trip offset.
			self.computerTimeDiff = datetime.timedelta(seconds=0)
		except ValueError as ve:
			self.logEx('setTime',
			           _('Invalid value when setting time on decoder'),
			           ve)
			return False
		except Exception as e:
			self.logEx('setTime', 'Failed to set time on decoder', e)
			return False
		return True

	def process_messages(self) -> bool:
		tagTimes = []
		times = set()
		message: DecoderMessage | None = self.peek_last_message()
		if message is None:
			return False

		while message := self.get_last_message():
			if isinstance(message, UltraConnectInfoMessage):
				self.log('process_messages', '{}: "{}"'.format(_('Connection info'), message))
				continue
			elif isinstance(message, UltraVoltageMessage):
				self._lastVoltage = now()  # If so, reset the last heartbeat time.
				continue
			elif isinstance(message, UltraChipReadMessage):
				chipRead: UltraChipReadMessage = message
				if not chipRead.hasValidTag():
					self.log('process_messages', '{}: "{}"'.format(_('Invalid tag in chip read message'), chipRead))
					continue
				chip = chipRead.ChipCode
				tag = '{:d}'.format(chip)

				crossingTime = chipRead.getTagTime() + self.computerTimeDiff

				while crossingTime in times:
					# Ensure no equal times.
					crossingTime += tSmall

				times.add(crossingTime)
				tagTimes.append((tag, crossingTime))

		# log.q('connection.keepGoing', '{}: "{}"'.format(_('data'), bufMessage))
		# Otherwise, assume this is a chip read.
		# try:
		# 	tag, t = parseTagTime( bufMessage )
		# except Exception as e:
		# 	log.q('reader.keepGoing.parseTagTime.exception', '{}: "{}"'.format(_('Failed to parse tag time'), bufMessage))
		# 	log.exception('reader.keepGoing', e, sys.exc_info())
		# 	continue
		#
		# if tag is None or t is None:
		# 	log.error('command.keepGoing', '{}: "{}"'.format(_('Unexpected reader message'), bufMessage))
		# 	continue

		# t += readerComputerTimeDiff
		# while t in times:	# Ensure no equal times.
		# 	t += tSmall
		#
		# times.add( t )
		# tagTimes.append( (tag, t) )

		self.process_crossings(tagTimes)

		return True

	def process_crossings(self, tagTimes: [(str, datetime.datetime)]) -> None:
		self._crossing_listener(tagTimes)

		# if msg := UltraConnectInfoMessage.parse( bufMessage ):
		# 	self.log('get_messages', '{}: "{}"'.format(_('Last data sent'), bufMessage))
		# 	messages.append(msg)
		# 	continue
		#
		# # Check for a heartbeat.
		# if msg := UltraVoltageMessage.parse( bufMessage ):
		# 	# log.q( 'heartbeat.keepGoing', '{}: "{}"'.format(_('heartbeat'), message) )
		# 	self._lastVoltage = now()	# If so, reset the last heartbeat time.
		# 	continue

	def on_socket_timeout(self, ex: socket.timeout) -> None:
		if (now() - self._lastVoltage).total_seconds() > 15:
			self.log('get_messages', _('Lost heartbeat.'))

	def get_messages(self) -> List[DecoderMessage]:
		buffer: str = TCPTimingDevice.get_message_buffer(self)

		if buffer is not None:
			self.process_message_buffer(buffer)

		msgQueue = super().get_messages()
		return msgQueue

	def get_command(self, command_type: str) -> TimingDeviceCommand:
		if command_type in UltraDecoder.commands:
			return UltraDecoder.commands[command_type]

		raise UnrecognisedCommandException(command_type)

	def parse_message(self, message: str) -> DecoderMessage:
		return UltraDecoder.parse(message)

	@staticmethod
	def parse(message: str) -> DecoderMessage|None:
		if (msg := UltraConnectConfirmationMessage.parse(message)) is not None:
			return msg
		elif (msg := UltraConnectInfoMessage.parse(message)) is not None:
			return msg
		elif (msg := UltraVoltageMessage.parse(message)) is not None:
			return msg
		elif (msg := UltraChipReadMessage.parse(message)) is not None:
			return msg
		elif len(message.strip()) > 0:
			return UnrecognisedDecoderMessage(message)

		# log.q('connection.keepGoing', '{}: "{}"'.format(_('data'), message))
		# # Otherwise, assume this is a chip read.
		# try:
		# 	tag, t = parseTagTime(message)
		# except Exception as e:
		# 	log.q('reader.keepGoing.parseTagTime.exception', '{}: "{}"'.format(_('Failed to parse tag time'), bufMessage))
		# 	log.exception('reader.keepGoing', e, sys.exc_info())
		# 	continue

		# if tag is None or t is None:
		# 	log.error('command.keepGoing', '{}: "{}"'.format(_('Unexpected reader message'), bufMessage))
		# 	continue

		return None

	def makeSyncCall(self, message, comment: str = '') -> str:
		self.makeCall(message, comment)
		callBuffer = socketReadDelimited(self._s)
		return callBuffer

	def makeCall(self, message: str, comment: str = '') -> None:
		cmd = message.split(';', 1)[0]
		self.log('makeCall', 'sending: {}{}'.format(message, ' ({})'.format(comment) if comment else ''))
		try:
			# socketSend( s, bytes('{}{}'.format(message,EOL)) )
			socketSendMessage(self._s, message)
		except Exception as e:
			self.logEx('makeCall', '{}: {}'.format(cmd, _('Connection failed')), e)
			raise e

CONNECT_INFO_FORMAT = r'^\d{1,2}:\d{1,2}:\d{1,2} \d{1,2}-\d{1,2}-\d{4} \(-?\d+\)$'

class UltraDecoderMessage(DecoderMessage):
	_UltraId: int | None # Integer value. See section 3.1

	def __init__(self, ultraId: int | None):
		super().__init__()
		self._UltraId = ultraId

	@property
	def UltraId(self) -> int | None:
		return self._UltraId

	@UltraId.setter
	def UltraId(self, value: int):
		self._UltraId = value

class UltraConnectConfirmationMessage(UltraDecoderMessage):
	def __init__(self, ultraId: int):
		super().__init__(ultraId)

	@staticmethod
	def parse(message: str) -> Optional['UltraConnectConfirmationMessage']:
		if message is not None and message.startswith('Connected'):
			try:
				Connected, UltraID, CommandCode = message.split(',', 3)
				return UltraConnectConfirmationMessage(int(UltraID))
			except ValueError:
				return None
		return None

class UltraConnectInfoMessage(UltraDecoderMessage):
	def __init__(self, ultraId: int):
		super().__init__(ultraId)

	@staticmethod
	def parse(message: str) -> Optional['UltraConnectInfoMessage']:
		if re.match(CONNECT_INFO_FORMAT, message) is not None:
			return UltraConnectInfoMessage(0)
		return None


class UltraVoltageMessage(UltraDecoderMessage):
	Voltage: float

	@staticmethod
	def parse(message: str) -> Optional['UltraVoltageMessage']:
		if message is not None and message.startswith('V='):
			return UltraVoltageMessage(0, float(message[2:]))
		return None


	def __init__(self, ultraId: int, voltage: float):
		super().__init__(ultraId)
		self._Voltage = voltage

	@property
	def Voltage(self) -> float:
		return self._Voltage

class DecoderStatusMessage(UltraDecoderMessage):
	_readStatus: bool
	_sendStatus: bool

	@property
	def readStatus(self) -> bool:
		return self._readStatus

	@property
	def sendStatus(self) -> bool:
		return self._sendStatus

	@staticmethod
	def parse(message: str) -> Optional['DecoderStatusMessage']:
		if message is not None and message.startswith('S'):
			try:
				_, Payload = message.split('=', 1)
				if len(Payload) == 2:
					statusInt = int(Payload)
					readStatus = statusInt // 10
					sendStatus = statusInt % 10
					return DecoderStatusMessage(readStatus == 1, sendStatus == 1)

			except ValueError:
				return None
		return
	def __init__(self, readStatus: bool, sendStatus: bool):
		super().__init__(None)
		self._readStatus = readStatus
		self._sendStatus = sendStatus

# Definitions from https://rfidtiming.com/Software/UltraManual.pdf Pg41
class UltraChipReadMessage(UltraDecoderMessage):
	# Retain this field order
	Zero: int  # Zero (unused at present)
	_ChipCode: int  # Could be the chip code decimal or hexadecimal value, depending on current setting in Ultra (see section 3.8)
	Seconds: int  # Integer value representing the number of seconds after 01/01/1980
	Milliseconds: int  # Integer value representing the millisecond portion of the time.
	RSSI: int  # Negative integer value. This is the signal strength for the chip
	IsRewind: int  # 0 or 1. A value of 1 means the data is being transmitted from a rewind command,
	# in other words it is not a ‘live’ read. Live and rewound data will be mixed up in between
	# each other if you do a ‘rewind while reading’.
	ReaderNo: int  # Integer value of from 1 to 3 representing the reader number. There are 2
	# readers in an Ultra. A reader number of 3 is used for MTB downhill start times.
	# UltraId: int  # Integer value. See section 3.1 - Defined in superclass
	ReaderTime: str  # 8 characters representing the 64-bit time recorded by the UHF readers. Not
	# available for some Ultra models – please speak to your supplier for more information.
	StartTime: int  # For MTB downhill racing. Integer value representing the number of seconds after 01/01/1980
	LogId: int  # Integer value representing the record’s position in the log (starting at one)

	# Derived fields
	ChipCodeAsHexValue: bool

	@staticmethod
	def chipNumberFromString(chipStr: str) -> int:
		if chipStr.startswith('0x'):
			return int(chipStr, 16)
		return int(chipStr)

	@staticmethod
	def parse(message: str) -> 'UltraChipReadMessage | None':
		output: UltraChipReadMessage
		try:
			Zero, ChipCode, Seconds, Milliseconds, Extra = message.split(',', 4)

			output = UltraChipReadMessage(0, UltraChipReadMessage.chipNumberFromString(ChipCode))
			output.Seconds = int(Seconds)
			output.Milliseconds = int(Milliseconds)
		except ValueError as e:
			raise ValueError('Invalid crossing message format parsing {}'.format(message), e)

		try:
			if Extra is not None:
				AntennaNo, RSSI, IsRewind, ReaderNo, UltraID, ReaderTime, StartTime, LogID = Extra.split(',', 7)
				output.AntennaNo = int(AntennaNo)
				output.RSSI = int(RSSI)
				output.IsRewind = int(IsRewind)
				output.ReaderNo = int(ReaderNo)
				output.UltraId = int(UltraID)
				output.ReaderTime = ReaderTime
				output.StartTime = int(StartTime)
				output.LogId = int(LogID)

		except ValueError:
			pass

		return output

	def __init__(self, ultraId: int, chipCode: int):
		super().__init__(ultraId)
		self._ChipCode = chipCode

	def getTagTime(self) -> datetime.datetime:
		return EPOCH_TIME + datetime.timedelta(seconds=self.Seconds, milliseconds=self.Milliseconds)

	@property
	def ChipCode(self) -> int:
		return self._ChipCode

	def hasValidTag(self) -> bool:
		return self._ChipCode != 0
