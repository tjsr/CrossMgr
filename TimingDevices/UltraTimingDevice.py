import datetime
import inspect
import socket
import time
from typing import cast, Callable

from TimingDevices.TimingDevice import TimingDevice, CrossingListenerCallableType
from TimingDevices.DecoderMessages import DecoderMessage, UnrecognisedDecoderMessage
from TimingDevices.TCPTimingDevice import TCPTimingDevice
from TimingDevices.TimingDeviceCommand import TimingDeviceCommand
from TimingDevices.TimingDeviceExceptions import TimingDeviceNotConnectedException, UnrecognisedCommandException

from TimingDevices.UltraAutodetect import AutoDetect
from TimingDevices.UltraDecoderCommands import UltraSetTimeCommand, UltraGetStatusCommand, UltraSendRecordsCommand, \
	UltraStopResendRecords
from TimingDevices.UltraDecoderMessages import UltraConnectConfirmationMessage, \
	UltraVoltageMessage, UltraChipReadMessage, UltraDecoderStatusMessage, UltraDecoderTimeMessage, UltraSettingsMessage

now = datetime.datetime.now

# if we get the same time, make sure we give it a small offset to make it unique, but preserve the order.
tSmall = datetime.timedelta( seconds = 0.000001 )


class UltraDecoder(TimingDevice, TCPTimingDevice):
	COMMAND_STOP_REWIND = 'stop_rewind'
	COMMAND_GET_SETTINGS = 'get_settings'
	commands = {
		TimingDeviceCommand.COMMAND_START: TimingDeviceCommand('R', response_type=None, sync=False),
		TimingDeviceCommand.COMMAND_STOP: TimingDeviceCommand('S', response_type=None, sync=False),
		TimingDeviceCommand.COMMAND_STATUS: UltraGetStatusCommand,
		TimingDeviceCommand.COMMAND_SET_TIME: UltraSetTimeCommand,
		TimingDeviceCommand.COMMAND_GET_TIME: TimingDeviceCommand('r', response_type=UltraDecoderTimeMessage, sync=True),
		TimingDeviceCommand.COMMAND_SEND_RECORDS: UltraSendRecordsCommand,
		COMMAND_STOP_REWIND: UltraStopResendRecords,
		COMMAND_GET_SETTINGS: TimingDeviceCommand('U', response_type=None, sync=False)
	}


	DEFAULT_PORT: int = 23
	DEFAULT_HOST: str = '127.0.0.1'  # Port to connect to the Ultra receiver.

	_delaySecs: int = 3
	_lastVoltage: datetime.datetime | None = None
	_computerTimeDiff: datetime.timedelta | None = None
	_crossing_listener: CrossingListenerCallableType | None = None
	__on_connect_action_set_time: bool = True
	__on_connect_action_start_if_stopped: bool = True
	__on_disconnect_send_stop: bool = False

	def __init__( self, host: str, port: int ):
		TimingDevice.__init__(self)
		TCPTimingDevice.__init__(self, host, port)

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

	async def on_socket_connect(self) -> bool:
		connectMessage = cast(UltraConnectConfirmationMessage, self.wait_for_message(timeout=5, messageType=UltraConnectConfirmationMessage))
		if connectMessage is not None:
			try:
				self._messageQueue.remove(connectMessage)
			except ValueError:
				# TODO: Lock messages and mark them as processed.
				self.getLog().debug('Connect message already removed from queue during on_socket_connect.  This can happen during parsing.')

			# Undecided if the best way is to spawn this or await it.
			# ThreadUtils.spawn_event(handler=self.on_connect, message=connectMessage)
			confirmed = await self.on_connect(connectMessage)
			return confirmed
		else:
			self.getLog(child='event').warning('Connected to decoder but didn\'t get confirmation after waiting.')
			return False

	async def on_connect(self, message: UltraConnectConfirmationMessage) -> bool:
		result = True
		try:
			if self.__on_connect_action_set_time:
				# Ultra devices require the time be given in UTC.
				time_now_local = datetime.datetime.now()
				time_now_utc = time_now_local.astimezone(datetime.timezone.utc)
				time_response = await self.set_time(time = time_now_utc)
				if time_response.response is not None:
					self.getLog(child='on_connect').info(f'Time set on decoder: {time_response.response}')

			if self.__on_connect_action_start_if_stopped:
				getStatusResult = await self.get_status()
				response: UltraDecoderStatusMessage = getStatusResult.response
				if response is not None:
					self.remove_from_queue(response)
				if response is not None and response.readStatus == False:
					self.begin_reading()

		except Exception as e:
			self.getLog(child='on_connect').exception('Failed while getting decoder status', exc_info=e)

		return result


	def autoconnect(self, autoDetectCallback) -> bool:
		self.getLog('autoconnect').info('Attempting AutoDetect...')
		HOST_AUTO = AutoDetect(callback=autoDetectCallback)
		if HOST_AUTO:
			self.getLog('autoconnect').info('{}: {}'.format(_('AutoDetect Ultra at'), HOST_AUTO))
			self._host = HOST_AUTO
		else:
			time.sleep(self._delaySecs)
		return False

	def setTime(self) -> bool:
		log = self.getLog('setTime')
		log.warning('Using deprecated setTime method')
		#-----------------------------------------------------------------------------------------------------
		# Set the reader's time.
		# Wait for the boundary of a second.  This is the best synchronization we are going to get.
		time.sleep( (1000000 - now().microsecond) / 1000000.0 )
		decoderMessage: str
		try:
			set_time_command: UltraSetTimeCommand = cast(UltraSetTimeCommand, self.get_command(TimingDeviceCommand.COMMAND_SET_TIME))
			self.send_command(set_time_command)
			response = set_time_command.response
			log.info('{}: {}'.format(_('Response to set time on decoder'), response))

			# We wait for the second boundary above and then set the offset to the response here so we know the round-trip offset.
			self.computerTimeDiff = datetime.timedelta(seconds=0)
		except ValueError as ve:
			log.exception(_('Invalid value when setting time on decoder'),
			           exc_info=ve)
			return False
		except Exception as e:
			log.exception('Failed to set time on decoder', exc_info=e)
			return False
		return True

	async def get_status( self, onStatusCallback: Callable[[UltraDecoderStatusMessage], None] | None = None ) -> UltraGetStatusCommand:
		getStatusCommand = await super().get_status(onStatusCallback)
		ultraStatusCommand = cast(UltraGetStatusCommand, getStatusCommand)
		return ultraStatusCommand

	def process_messages_on_queue(self) -> bool:
		message: DecoderMessage | None = self.peek_last_message()
		if message is None:
			return False

		delay_messages: list[DecoderMessage] = []

		while message := self.get_last_message():
			if isinstance(message, UltraConnectConfirmationMessage):
				self.getLog('process_messages').info('{}: "{}"'.format(_('Got \'Connected\' message, not processing yet...'), message))
				delay_messages.append(message)
				continue
			elif isinstance(message, UltraVoltageMessage):
				self._lastVoltage = now()  # If so, reset the last heartbeat time.
				continue
			elif isinstance(message, UltraChipReadMessage):
				self.on_td_read(message)
				continue

		while len(delay_messages) > 0:
			message = delay_messages.pop()
			# TODO: await here?
			self._push_back_message(message)

		return True

	def on_td_read(self, message: UltraChipReadMessage) -> bool:
		tagTimes = []
		times = set()
		chipRead: UltraChipReadMessage = message
		if not chipRead.hasValidTag():
			self.getLog('on_td_read').warning(_('Invalid tag in chip read message') + ' ' + chipRead)
			return False
		chip = chipRead.ChipCode
		tag = f'{chip}'

		crossingTime = chipRead.Time
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

		if self._crossing_listener is not None:
			if not callable(self._crossing_listener):
				self.getLog().error(_('Crossing listener is not callable.'))
			else:
				self._crossing_listener(tagTimes)

		return True

	def on_socket_timeout(self, ex: socket.timeout) -> None:
		if self._lastVoltage is None:
			self.getLog('on_socket_timeout').error(_('No heartbeat received.'))
		elif (now() - self._lastVoltage).total_seconds() > 15:
			self.getLog('on_socket_timeout').error(_('Lost heartbeat.'))

	def get_message_buffer(self) -> str:
		return TCPTimingDevice.get_message_buffer(self)

	def get_command(self, command_type: str, *args, **kwargs) -> TimingDeviceCommand:
		if command_type in UltraDecoder.commands:
			if inspect.isclass(UltraDecoder.commands[command_type]):
				return UltraDecoder.commands[command_type](*args, **kwargs)
			else:
				return UltraDecoder.commands[command_type]

		raise UnrecognisedCommandException(command_type)

	def parse(self, messageBuf: str) -> DecoderMessage | None:
		log = self.getLog(child='parse')
		if messageBuf is None:
			log.warning(f'Attempted to parse a empty message buffer.')
			return None

		try:
			if (msg := UltraConnectConfirmationMessage.parse(messageBuf)) is not None:
				return msg
			elif (msg := UltraVoltageMessage.parse(messageBuf)) is not None:
				return msg
			elif (msg := UltraDecoderStatusMessage.parse(messageBuf)) is not None:
				return msg
			elif (msg := UltraDecoderTimeMessage.parse(messageBuf)) is not None:
				return msg
			elif (msg := UltraSettingsMessage.parse(messageBuf)) is not None:
				return msg
			elif (msg := UltraChipReadMessage.parse(messageBuf)) is not None:
				# traceback.print_stack()
				return msg
		except Exception as e:
			log.exception(f'Failed to parse message {messageBuf}', e)
			raise ValueError(f'Failed to parse message {messageBuf}')

		if len(messageBuf.strip()) > 0:
			log.warning(f'Unrecognised message: {messageBuf}')
			return UnrecognisedDecoderMessage(messageBuf)

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

	def parse_message(self, messageBuf: str) -> DecoderMessage:
		log = self.getLog(child='parse_message')
		log.trace(f'Parsing message {messageBuf} and adding datat to message object.')
		return self.parse(messageBuf)

	def stop_reading(self):
		TimingDevice.stop_reading(self)

	def stop_rewind(self):
		command = self.get_command(UltraDecoder.COMMAND_STOP_REWIND)
		self.send_command(command)

	def send_data(self, payload: str):
		TCPTimingDevice.send_data(self, payload)

	def get_settings( self ) -> TimingDeviceCommand:
		getSettingsCommand = self.create_command(UltraDecoder.COMMAND_GET_SETTINGS)
		self.send_command(getSettingsCommand)
		return getSettingsCommand

	def connected(self) -> bool:
		return TCPTimingDevice.connected(self)

	async def disconnect(self, allow_reconnect: bool = False) -> bool:
		if self.connected() and self.__on_disconnect_send_stop == True:
			self.stop_reading()

		return await TCPTimingDevice.disconnect(self, allow_reconnect=allow_reconnect)

	async def reconnect(self) -> bool:
		if self.connected():
			await TCPTimingDevice.disconnect(self)
			return TCPTimingDevice.connect(self)
		else:
			raise TimingDeviceNotConnectedException('Decoder not connected - do not call reconnect without first checking connect state.')

	def send_command(self, command: TimingDeviceCommand):
		if not TCPTimingDevice.connected(self):
			errMsg = f'Decoder not connected, cannot send command {command}'
			self.getLog().error(errMsg)
			raise TimingDeviceNotConnectedException(errMsg)

		super().send_command(command)

	def send_records_from_record(self,
		start_record: int,
		end_record: int | None = None
		) -> UltraSendRecordsCommand:
		sendRecordsCommand = self.create_command(
			TimingDeviceCommand.COMMAND_SEND_RECORDS,
			from_record=start_record,
			to_record=end_record)
		self.send_command(sendRecordsCommand)
		return cast(UltraSendRecordsCommand, sendRecordsCommand)

