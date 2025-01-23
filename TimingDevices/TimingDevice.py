from abc import abstractmethod
from types import TracebackType
from typing import List, Type

from LogQueue import LogQueue


class DecoderMessage:
	def __init__(self):
		pass

class UnrecognisedDecoderMessage(DecoderMessage):
	_message: str
	def __init__(self, message: str):
		super().__init__()
		self._message = message

class TimingDeviceCommand:
	_command_str: str
	_sync: bool = False

	def __init__( self, _command_str: str, sync: bool = False ):
		self._command_str = _command_str
		self._sync = sync

	def is_sync_command(self) -> bool:
		return self._sync

	def get_command_string(self) -> str:
		return self._command_str


class TimingDevice:
	_readonly = False
	_logger: LogQueue | None = None
	_messageBuffer: List[DecoderMessage] = []

	def is_readonly_device(self) -> bool:
		return self._readonly

	def add_message(self, message: DecoderMessage) -> int:
		self._messageBuffer.append(message)
		return len(self._messageBuffer)

	def get_messages(self) -> List[DecoderMessage]:
		return self._messageBuffer

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

	def sync_send_command(self, command: str, comment: str = None):
		pass

	def async_send_command(self, command: str, expect_response: bool = False, comment: str = None):
		pass

	def send_command(self, command: str, comment: str = None):
		cmd = self.get_command(command)
		if cmd.is_sync_command():
			self.sync_send_command(cmd.get_command_string(), comment)
		else:
			self.async_send_command(cmd.get_command_string(), False, comment)

	@abstractmethod
	def get_command(self, command_type: str) -> TimingDeviceCommand:
		pass

	@abstractmethod
	def stop_reading(self):
		pass


class UnrecognisedCommandException(Exception):
	def __init__(self, command: str):
		super().__init__('Unrecognised command type: {}'.format(command))

