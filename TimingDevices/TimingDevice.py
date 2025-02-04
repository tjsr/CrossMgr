import datetime
import socket
from abc import abstractmethod
from logging import Logger, getLogger
from types import TracebackType
from typing import List, Type, Callable, Any, Generic, TypeVar

from LogQueue import LogQueue

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

CommandResponse = TypeVar('CommandResponse')

class TimingDeviceCommand(Generic[CommandResponse]):
	_command_str: str
	_sync: bool = False
	_response: Any

	def __init__( self, _command_str: str, sync: bool = False ):
		self._command_str = _command_str
		self._sync = sync

	def is_sync_command(self) -> bool:
		return self._sync

	def get_command_string(self) -> str:
		return self._command_str

	@property
	def response(self) -> CommandResponse:
		return self._response


class TCPTimingDevice:
	DEFAULT_PORT: int = 23
	DEFAULT_HOST: str = '127.0.0.1'

	_host: str = DEFAULT_HOST
	_port: int = DEFAULT_PORT
	_s: socket.socket | None = None
	_timeoutSecs: int = 5

	def __init__(self, host: str, port: int ):
		self._host = host
		self._port = port

	@abstractmethod
	def getLog(self) -> Logger:
		pass

	@abstractmethod
	def getDeviceType(self) -> str:
		pass

	def connect(self) -> bool:
		log = self.getLog()
		device = self.getDeviceType()
		# TODO: wrap with _ for internationalisation
		description = f'{device} decoder at {self._host}:{self._port}'

		# -----------------------------------------------------------------------------------------------------
		log.info(_('Attempting to connect to {}').format(description))
		try:
			self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self._s.settimeout(self._timeoutSecs)
			self._s.connect((self._host, self._port))
		except Exception as e:
			log.exception('{}: {}'.format(_('Connection failed to {}'), description, e))
			self._s = None
			return False

		log.info(_('Successfully connected to {}').format(description))
		return True

	def disconnect(self) -> bool:
		if self._s is not None:
			try:
				self._s.shutdown(socket.SHUT_RDWR)
				self._s.close()
				return True
			except Exception:
				pass
		return False


class TimingDevice:
	_readonly = False
	_logger: LogQueue | None = None
	_log: Logger | None = None
	_messageBuffer: List[DecoderMessage] = []

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
		self.send_command('status')
		pass

	def get_time( self ):
		self.send_command('get_time')
		pass

	def send_records_from_last(self):
		self.send_command('send_records')
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

