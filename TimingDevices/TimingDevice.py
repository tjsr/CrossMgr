import datetime
from abc import abstractmethod
from logging import Logger, getLogger
from types import TracebackType
from typing import List, Type, Callable, Any

from LogQueue import LogQueue
from TimingDevices.TimingDeviceCommand import TimingDeviceCommand

CrossingListenerCallableType = Callable[[(str, datetime.datetime)], None]

class SettingChangeCommand:
	pass


class DecoderMessage:
	def __init__(self):
		pass

class UnknownTimingDeviceSetting(Exception):
	def __init__(self, setting: str):
		super().__init__(f'Unknown setting: {setting}')

class UnrecognisedDecoderMessage(DecoderMessage):
	_message: str
	def __init__(self, message: str):
		super().__init__()
		self._message = message


class TimingDevice:
	_readonly = False
	_logger: LogQueue | None = None
	_log: Logger | None = None
	_messageBuffer: List[DecoderMessage] = []

	def __init__(self):
		pass

	def getLog(self) -> Logger:
		if self._log is None:
			self._log = getLogger(self.__class__.__name__)
		return self._log

	def is_readonly_device(self) -> bool:
		return self._readonly

	def add_message(self, message: DecoderMessage) -> int:
		self._messageBuffer.append(message)
		return len(self._messageBuffer)

	def get_messages(self) -> List[DecoderMessage]:
		return self._messageBuffer

	def process_message_buffer(self, buffer: str) -> int:
		maxBufSize = -1
		for bufMessage in buffer.splitlines(False):
			nextMessage = self.parse_message(bufMessage)
			maxBufSize = self.add_message(nextMessage)
		return maxBufSize

	@abstractmethod
	def parse_message(self, message: str) -> DecoderMessage:
		pass

	def get_last_message(self) -> DecoderMessage | None:
		if len(self._messageBuffer) == 0:
			return None
		return self._messageBuffer.pop()

	def peek_last_message(self) -> DecoderMessage | None:
		if len(self._messageBuffer) == 0:
			return None
		return self._messageBuffer[-1]

	@property
	def logger(self) -> LogQueue | None:
		return self._logger

	@logger.setter
	def logger(self, value: LogQueue):
		self._logger = value

	def log(self, category: str, message: str):
		if self._logger:
			self._logger.q(category, message)
		pass

	def logEx(self, category: str, msg: str, e: Exception, exc_info: tuple[Type[BaseException], BaseException, TracebackType] | tuple[None, None, None] | None = None) -> list[str] | None:
		if self._logger:
			trace = self._logger.exception(category, e, exc_info)
			self.log(category, msg)
		return None

	def begin_reading( self ):
		if not self.is_readonly_device():
			self.send_command('start')
		pass

	def get_status( self ):
		self.send_command(TimingDeviceCommand.COMMAND_STATUS)
		pass

	def get_time( self ):
		self.send_command(TimingDeviceCommand.COMMAND_GET_TIME)
		pass

	def send_records_from_last(self):
		self.send_command(TimingDeviceCommand.COMMAND_SEND_RECORDS)
		pass

	def send_records_from_time(self, time: datetime.datetime):
		self.send_command('send_records')
		pass

	def get_setting(self, setting: str):
		if not self.is_valid_setting(setting):
			raise UnknownTimingDeviceSetting(setting)
		self.send_command('get_setting')
		pass

	def change_setting(self, settingChangeCommand: SettingChangeCommand):
		raise NotImplementedError()

	def is_valid_setting(self, setting: str) -> bool:
		# TODO: Implement this
		return True

	# TODO: Remove 'comment'.
	def sync_send_command(self, command: str, comment: str = None):
		pass

	# TODO: Remove 'comment'.
	def async_send_command(self, command: str, expect_response: bool = False, comment: str = None):
		pass

	def send_command(self, command: str, params: Any = None, comment: str = None):
		cmd = self.get_command(command)
		cmd.params = params
		cmd.comment = comment
		self.push_command(cmd, comment)
		if cmd.is_sync_command():
			self.sync_send_command(cmd.get_command_string(), comment)
		else:
			self.async_send_command(cmd.get_command_string(), False, comment)

	@abstractmethod
	def get_command(self, command_type: str) -> TimingDeviceCommand:
		pass

	def push_command(self, command: TimingDeviceCommand, comment: str = None):
		pass

	@abstractmethod
	def stop_reading(self):
		pass


class UnrecognisedCommandException(Exception):
	def __init__(self, command: str):
		super().__init__('Unrecognised command type: {}'.format(command))

