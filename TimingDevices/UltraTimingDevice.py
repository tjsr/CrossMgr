import datetime
import socket
import time
from typing import cast

from Log import getLogger
from LogQueue import LogQueue
from TimingDevices.TimingDevice import UnrecognisedCommandException, TimingDevice, DecoderMessage, \
	UnrecognisedDecoderMessage, CrossingListenerCallableType
from TimingDevices.TCCPTimingDevice import TCPTimingDevice
from TimingDevices.TimingDeviceCommand import TimingDeviceCommand

from TimingDevices.UltraAutodetect import AutoDetect
from TimingDevices.UltraDecoderCommands import UltraSetTimeCommand
from TimingDevices.UltraDecoderMessages import UltraConnectConfirmationMessage, UltraConnectInfoMessage, \
	UltraVoltageMessage, UltraChipReadMessage, UltraDecoderStatusMessage

now = datetime.datetime.now
EPOCH_TIME = datetime.datetime(1980, 1, 1)

# if we get the same time, make sure we give it a small offset to make it unique, but preserve the order.
tSmall = datetime.timedelta( seconds = 0.000001 )


class UltraDecoder(TimingDevice, TCPTimingDevice):
	commands = {
		TimingDeviceCommand.COMMAND_START: TimingDeviceCommand('R', response_type=None, sync=False),
		TimingDeviceCommand.COMMAND_STOP: TimingDeviceCommand('S', response_type=None, sync=False),
		TimingDeviceCommand.COMMAND_STATUS: TimingDeviceCommand('?', response_type=UltraDecoderStatusMessage, sync=True),
		TimingDeviceCommand.COMMAND_SET_TIME: UltraSetTimeCommand()
	}

	DEFAULT_PORT: int = 23
	# DEFAULT_PORT = 8642
	DEFAULT_HOST: str = '127.0.0.1'  # Port to connect to the Ultra receiver.

	_delaySecs: int = 3
	_lastVoltage: datetime.datetime | None = None
	_computerTimeDiff: datetime.timedelta | None = None
	_crossing_listener: CrossingListenerCallableType | None = None
	__on_connect_action_set_time: bool = True
	__on_connect_action_start_if_stopped: bool = True

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
		connectMessage = self.wait_for_message(timeout=5, messageType=UltraConnectConfirmationMessage)
		if connectMessage is not None:
			return self.on_connect_confirmed()
		else:
			self.getLog().warning('Connected to decode but didn\'t get confirmation after waiting.')
			return False

	def on_connect_confirmed(self) -> bool:
		result = True
		try:
			if self.__on_connect_action_set_time:
				setTimeCommand = self.set_time()

			if self.__on_connect_action_start_if_stopped:
				getStatusCommand = self.get_status()

		except Exception as e:
			self.getLog().exception('Failed while getting decoder status', e)

		return result


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
			set_time_command: UltraSetTimeCommand = cast(UltraSetTimeCommand, self.get_command(TimingDeviceCommand.COMMAND_SET_TIME))
			self.send_command(set_time_command)
			response = set_time_command.response
			self.log('setTime', '{}: {}'.format(_('Response to set time on decoder'), response))

			# decoderMessage = set_time_command.get_command_string()
			# self.makeCommandCall(set_time_command)
			# buffer = self.makeSyncCall( decoderMessage, comment='set reader time' )
			# bufSize:int = self.process_message_buffer(buffer)
			# self.log('setTime', '{}: {} ({} on queue)'.format(_('Response to set time on decoder'), buffer, bufSize))
			# self.wait_for_response(timeout=5, command=set_time_command)

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
				tag = f'{chip}'

				crossingTime = chipRead.getTagTime()
				if self.computerTimeDiff:
					crossingTime += self.computerTimeDiff

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

	def get_message_buffer(self) -> str:
		return TCPTimingDevice.get_message_buffer(self)

	def get_command(self, command_type: str, *args, **kwargs) -> TimingDeviceCommand:
		if command_type in UltraDecoder.commands:
			return UltraDecoder.commands[command_type]

		raise UnrecognisedCommandException(command_type)

	def parse_message(self, message: str) -> DecoderMessage:
		self.getLog().debug('parse_message')
		return UltraDecoder.parse(message)

	@staticmethod
	def parse(message: str) -> DecoderMessage|None:
		log = getLogger('UltraDecoder.parse')
		log.debug('<< {}'.format(message))

		if (msg := UltraConnectConfirmationMessage.parse(message)) is not None:
			return msg
		elif (msg := UltraConnectInfoMessage.parse(message)) is not None:
			return msg
		elif (msg := UltraVoltageMessage.parse(message)) is not None:
			return msg
		elif (msg := UltraDecoderStatusMessage.parse(message)) is not None:
			return msg
		elif (msg := UltraChipReadMessage.parse(message)) is not None:
			log.debug('Parsed chip read message: {}'.format(msg))
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

	def stop_reading(self):
		TimingDevice.stop_reading(self)

	def send_data(self, payload: str):
		TCPTimingDevice.send_data(self, payload)

