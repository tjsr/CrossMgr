import asyncio
import datetime
from abc import abstractmethod
from queue import Queue
from types import TracebackType
from typing import List, Type, Callable, Optional, cast

import Log
from Log import CrossMgrLogger

from LogQueue import LogQueue
from TimingDevices.TimingDeviceCommand import TimingDeviceCommand, TimingDeviceCommandException, \
	TimingDeviceSetTimeCommand, TimingDeviceSendRecordsCommand
from TimingDevices.DecoderMessages import DecoderStatusMessage, DecoderMessage, UnrecognisedDecoderMessage
from TimingDevices.UltraDecoderCommands import UltraSetTimeCommand

CrossingListenerCallableType = Callable[[(str, datetime.datetime)], None]

class SettingChangeCommand:
	pass


class UnknownTimingDeviceSetting(Exception):
	def __init__(self, setting: str):
		super().__init__(f'Unknown setting: {setting}')


class DeviceStatusMessage(DecoderMessage):
	def __init__(self, *args, **kwargs):
		super().__init__(args, kwargs)

	@abstractmethod
	def status(self) -> str:
		pass


class TimingDeviceConnectMessage(DecoderMessage):
	@abstractmethod
	def match_message(self, message: 'DecoderMessage'):
		pass

	def __init__(self, *args, **kwargs):
		super().__init__(args, kwargs)


class LogQueueClass:
	_logger: LogQueue | None = None

	@property
	def logger(self) -> LogQueue | None:
		return self._logger

	@logger.setter
	def logger(self, value: LogQueue):
		self._logger = value

	def log(self, category: str, message: str):
		if self._logger:
			self._logger.q(category, message)

	def logEx(self, category: str, msg: str, e: Exception, exc_info: tuple[Type[BaseException], BaseException, TracebackType] | tuple[None, None, None] | None = None) -> list[str] | None:
		if self._logger:
			trace = self._logger.exception(category, e, exc_info)
			self.log(category, msg)
		return None


class TimingDevice():
	_readonly = False
	_log: CrossMgrLogger | None = None
	_messageQueue: List[DecoderMessage] = None
	_commandQueue: Queue[TimingDeviceCommand] = None

	STATE_NONE: int = 0
	STATE_WAIT_READY: int = 1
	STATE_CONNECTED: int = 2
	STATE_SENDING_COMMANDS: int = 4
	STATE_READING_DATA: int = 8
	STATE_PROCESSING_DATA: int = 16

	_state: int = STATE_NONE

	def __init__(self):
		self._commandQueue = Queue()
		self._messageQueue = []

	def getLogName(self) -> str:
		class_name = self.__class__.__name__
		return f'TimingDevice[{class_name}]'

	def getLog(self, child: str | None = None) -> CrossMgrLogger:
		if self._log is not None:
			log = self._log
		else:
			log = Log.getLogger(name=self.getLogName())
		if child is not None:
			log = log.getChild(child)
		return log

	def is_readonly_device(self) -> bool:
		return self._readonly

	def add_message(self, message: DecoderMessage) -> int:
		self._messageQueue.append(message)
		return len(self._messageQueue)

	@abstractmethod
	def get_message_buffer(self) -> str | None:
		pass

	def process_queued_outgoing_commands(self):
		while not self._commandQueue.empty():
			command = self._commandQueue.get()
			self.sync_send_command(command)

	def get_incoming_messages_from_stream(self, searchType: Type[DecoderMessage] | None = None) -> List[DecoderMessage]:
		buffer: str = self.get_message_buffer()
		# log = self.getLog(name='TimingDevice.get_messages')

		if buffer is not None:
			log = self.getLog()
			buffer_size = len(buffer)
			log.trace(f'Got {buffer_size} bytes of messages from buffer...')

			_msgCount = self.process_message_buffer(buffer)
			# log.debug(f'Processed message buffer now has {msgCount} messages.')

		if searchType is not None:
			# Filter messages by type and return them
			return [message for message in self._messageQueue if isinstance(message, searchType)]

		return self._messageQueue

	def process_message_buffer(self, buffer: str) -> int:
		maxBufSize = -1
		inputLog = self.getLog(child='input')
		for bufMessage in buffer.splitlines(False):
			try:
				nextMessage = self.parse_message(bufMessage)
				if nextMessage is not None:
					nextMessage.Data = bufMessage
				if isinstance(nextMessage, UnrecognisedDecoderMessage):
					inputLog.warning(bufMessage)
				else:
					inputLog.info(bufMessage)

				maxBufSize = self.add_message(nextMessage)
			except Exception as e:
				inputLog.error(bufMessage)
		return maxBufSize

	@abstractmethod
	def parse_message(self, messageBuf: str) -> DecoderMessage:
		pass

	@property
	def messageQueueLength(self) -> int:
		return len(self._messageQueue)

	@property
	def commandQueueLength(self) -> int:
		return self._commandQueue.qsize()

	def get_last_message(self) -> DecoderMessage | None:
		if len(self._messageQueue) == 0:
			return None
		return self._messageQueue.pop()

	def peek_last_message(self) -> DecoderMessage | None:
		if len(self._messageQueue) == 0:
			return None
		return self._messageQueue[-1]

	def create_command(self, command_type: str, *args, **kwargs) -> TimingDeviceCommand:
		return self.get_command(command_type, *args, **kwargs)

	def begin_reading( self ) -> TimingDeviceCommand | None:
		if not self.is_readonly_device():
			startDeviceCommand = self.create_command(TimingDeviceCommand.COMMAND_START)
			self.send_command(startDeviceCommand)
			return startDeviceCommand

		return None

	async def get_status( self, onStatusCallback: Callable[[DecoderStatusMessage], None] | None = None ) -> TimingDeviceCommand[DecoderStatusMessage]:
		getStatusCommand = self.create_command(TimingDeviceCommand.COMMAND_STATUS)
		self.send_command(getStatusCommand)
		return getStatusCommand

	def get_time( self ) -> TimingDeviceCommand:
		getTimeCommand = self.create_command(TimingDeviceCommand.COMMAND_GET_TIME)
		self.send_command(getTimeCommand)
		return getTimeCommand

	async def set_time(self, time: datetime.datetime = datetime.datetime.now()) -> TimingDeviceSetTimeCommand:
		setTimeCommand = self.create_command(TimingDeviceCommand.COMMAND_SET_TIME, time)
		success = self.send_command(setTimeCommand)
		if success and setTimeCommand.response is not None:
			setTimeCommand.Success = success
		return cast(UltraSetTimeCommand, setTimeCommand)

	def send_records_from_last(self) -> TimingDeviceCommand:
		sendRecordsCommand = self.create_command(TimingDeviceCommand.COMMAND_SEND_RECORDS)
		self.send_command(sendRecordsCommand)
		return sendRecordsCommand

	def send_records_from_time(self, start_time: datetime.datetime, end_time: datetime.datetime) -> TimingDeviceSendRecordsCommand:
		sendRecordsCommand = self.create_command(TimingDeviceCommand.COMMAND_SEND_RECORDS, start_time=start_time, end_time=end_time)
		self.send_command(sendRecordsCommand)
		return cast(TimingDeviceSendRecordsCommand, sendRecordsCommand)

	def get_setting(self, setting: str):
		if not self.is_valid_setting(setting):
			raise UnknownTimingDeviceSetting(setting)
		getSettingCommand = self.create_command('get_setting', setting)
		self.send_command(getSettingCommand)
		return getSettingCommand

	def change_setting(self, settingChangeCommand: SettingChangeCommand):
		raise NotImplementedError()

	def is_valid_setting(self, setting: str) -> bool:
		self.getLog(child='is_valid_setting').todo(f'Implement this. Checking setting for {setting}')
		# TODO: Implement this
		return True

	# TODO: Remove 'comment'.
	def sync_send_command(self, command: TimingDeviceCommand) -> bool:
		data = command.get_command_string()
		self.send_data(data)
		command.sentAt = datetime.datetime.now()
		commandType = command.CommandType
		self.getLog().debug(f'Send {commandType} command immediately to decoder: {data}, expectsResponse: {command.expectsResponse}')
		if command.expectsResponse:
			response = self.wait_for_response(5, command)
			if response is not None:
				command.response = response
				return True
			else:
				return False
		else:
			self.getLog().debug(f'No response expected for command: {data}')
			return True


	# TODO: Remove 'comment'.
	def async_send_command(self, command: TimingDeviceCommand) -> bool:
		# Push to the queue and send later.
		data = command.get_command_string()
		self.getLog().debug(f'Queuing async command to decoder: {data}')
		self.push_command(command)
		return True

	@abstractmethod
	def send_data(self, payload: str):
		pass

	def send_command(self, command: TimingDeviceCommand) -> bool:
		assert isinstance(command, TimingDeviceCommand)
		if command.is_sync_command():
			return self.sync_send_command(command)
		else:
			return self.async_send_command(command)

	@abstractmethod
	def get_command(self, command_type: str, *args, **kwargs) -> TimingDeviceCommand:
		pass

	def push_command(self, command: TimingDeviceCommand):
		self._commandQueue.put(command)

	@abstractmethod
	def stop_reading(self):
		if not self.is_readonly_device():
			command = self.get_command(TimingDeviceCommand.COMMAND_STOP)
			self.send_command(command)

	async def _wait_until_ready(self, timeout_seconds: int = 5) -> bool:
		# Re-write this to use a thread sleep.
		timeoutAt = datetime.datetime.now() + datetime.timedelta(seconds=timeout_seconds)
		while not self._state & TimingDevice.STATE_WAIT_READY:
			if datetime.datetime.now() > timeoutAt:
				return False
			await asyncio.sleep(0.1)
		return True

	def wait_for_message(self, timeout: int, messageType: Type[DecoderMessage]) -> Optional[DecoderMessage]:
		# TODO: We can abstract this with wait_for_response
		# log = self.getLog(name='TimingDevice.wait_for_message')
		log = self.getLog()
		message_type_name = messageType.__name__
		log.debug(f'Waiting for a matching {message_type_name} message before continuing...')

		current_time = datetime.datetime.now()
		start_time = datetime.datetime.now()

		timeout_exceeded = (current_time - start_time).seconds > timeout
		messages = []
		attempts = 1
		while not timeout_exceeded:
			messages = self.get_incoming_messages_from_stream(messageType)
			msgCount = len(messages)
			if msgCount == 0:
				log.debug(f'No messages for {message_type_name} iteration on attempt {attempts} with {self.messageQueueLength}...')
			else:
				log.debug(f'Got {msgCount} messages for {message_type_name} iteration on attempt {attempts}...')

			for message in messages:
				if isinstance(message, messageType):
					log.debug(f'Received awaited {message_type_name} message after {attempts} attempts and {self.messageQueueLength} messages on queue: {message}')
					return message
			attempts += 1
			current_time = datetime.datetime.now()
			timeout_exceeded = (current_time - start_time).seconds > timeout

		messageCount = len(messages)
		total_messages = self.messageQueueLength

		msgList = [str(message) for message in messages]
		log.warning(f'Got no matching {message_type_name} message in {timeout} seconds with {messageCount} ' +
			f' matched messages and {total_messages} total in the queue [{msgList}]')
		return None

	def wait_for_response(self, timeout: int, command: TimingDeviceCommand) -> Optional[DecoderMessage]:
		if not command.providesResponse:
			raise TimingDeviceCommandException(f'Command {command.__class__} does not provide a response')
		current_time = datetime.datetime.now()
		start_time = datetime.datetime.now()

		timeout_exceeded = (current_time - start_time).seconds > timeout
		messages = []
		log = self.getLog()
		attempts = 1
		commandClass = command.__class__.__name__
		responseClass = command.get_response_type()
		while not timeout_exceeded:
			messages = self.get_incoming_messages_from_stream(responseClass)
			msgCount = len(messages)
			if msgCount == 0:
				log.trace(f'No response for {commandClass} iteration on attempt {attempts} with {self.messageQueueLength}...')
			else:
				log.trace(f'Got {msgCount} response for {commandClass} iteration on attempt {attempts}...')

			for message in messages:
				if command.match_response(message):
					log.debug(f'Received awaited {commandClass} response after {attempts} attempts and {self.messageQueueLength} messages on queue: {message}')
					## TODO: Pop this from the queue
					log.todo('Pop the message from the queue after processing it')
					return message
			attempts += 1
			current_time = datetime.datetime.now()
			timeout_exceeded = (current_time - start_time).seconds > timeout

		total_messages = self.messageQueueLength
		messageCount = len(messages)
		msgList = [str(message) for message in messages]
		log.warning(f'Timed out after {timeout}s waiting for {commandClass} response. {messageCount}/{total_messages} in the queue [{msgList}]')
		return None

	@abstractmethod
	def on_connect(self, msg: TimingDeviceConnectMessage) -> bool:
		pass

	@abstractmethod
	def process_messages_on_queue(self) -> None:
		pass

	def process(self) -> bool:
		self.getLog().info(_('Reading data from decoder...'))

		try:
			self._state = self._state | TimingDevice.STATE_SENDING_COMMANDS
			self.process_queued_outgoing_commands()
			self._state = (self._state & ~TimingDevice.STATE_SENDING_COMMANDS) | TimingDevice.STATE_READING_DATA
			self.get_incoming_messages_from_stream()
			self._state = (self._state & ~TimingDevice.STATE_READING_DATA) | TimingDevice.STATE_PROCESSING_DATA
			self.process_messages_on_queue()
			self._state = (self._state & ~TimingDevice.STATE_PROCESSING_DATA) | TimingDevice.STATE_WAIT_READY
			return True
		except Exception as e:
			self.getLog(child='process').exception('Error processing messages', e)
		return False
