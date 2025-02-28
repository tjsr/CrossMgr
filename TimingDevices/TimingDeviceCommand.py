import datetime
from abc import abstractmethod, ABC
from typing import Generic, TypeVar, Optional, Type

from TimingDevices.DecoderMessages import DecoderTimeMessage

CommandResponseType = TypeVar('CommandResponseType', bound='TimingDeviceMessage | None')
DecoderMessageType = TypeVar('DecoderMessageType', bound='DecoderMessage')

class TimingDeviceCommandException(Exception):
	def __init__(self, msg: str | None, exception: Exception | None = None):
		super().__init__(msg, exception)

seq: int = 1
def genId() -> int:
	global seq
	seq += 1
	return seq

class TimingDeviceCommand(Generic[CommandResponseType], ABC):
	COMMAND_SEND_RECORDS = 'send_records'
	COMMAND_GET_TIME = 'get_time'
	COMMAND_SET_TIME = 'set_time'
	COMMAND_STATUS = 'status'
	COMMAND_START = 'start'
	COMMAND_STOP = 'stop'

	_id: int = genId()
	_command_str: str | None
	_sync: bool = False
	_expectsResponse: bool = True
	_response: CommandResponseType | None
	_sent_at: datetime.datetime | None
	_comment = str
	_command_type: str
	_response_type: Type[CommandResponseType]
	_success: bool = False

	def __init__(self, command_str: str | None = None, response_type: Type[CommandResponseType] | None = None, sync: bool = False):
		if sync is True and response_type is None:
			raise ValueError('A TimingDeviceCommand that synchronously waits for a response must know what response_type to wait for.')

		self._command_str = command_str
		self._sync = sync
		self._expectsResponse = sync
		self._response_type = response_type
		self._response = None
		self._sent_at = None
		self._command_type = self.__class__.__name__

	def is_sync_command(self) -> bool:
		return self._sync

	@property
	def comment(self) -> str | None:
		return self._comment

	@comment.setter
	def comment(self, comment: str|None):
		self._comment = comment

	@property
	def response(self) -> CommandResponseType:
		return self._response

	@response.setter
	def response(self, response: CommandResponseType):
		self._response = response

	def match_response(self, message: DecoderMessageType) -> Optional[CommandResponseType]:
		t = self.get_response_type()
		if t is not None:
			self._response = message
			return t.match_response(message)
		raise NotImplementedError('A TimingDeviceCommand that expects a response required a specific implementation of match_response')

	def match_message(self, message: DecoderMessageType) -> Optional[CommandResponseType]:
		assert self is not None
		assert not isinstance(message, str)
		assert message.Data is not None
		return message.matches(message)

	@property
	def expectsResponse(self) -> bool:
		return self._expectsResponse

	@property
	def providesResponse(self) -> bool:
		return self._response_type is not None

	def get_response_type(self):
		return self._response_type

	@property
	def sentAt(self) -> datetime.datetime:
		return self._sent_at

	@sentAt.setter
	def sentAt(self, time: datetime.datetime) -> None:
		self._sent_at = time

	@property
	def CommandType(self) -> str:
		return self._command_type

	@property
	def Success(self) -> bool:
		return self._success

	@Success.setter
	def Success(self, success: bool) -> None:
		self._success = success

	def get_command_string(self) -> str:
		if self._command_str is not None:
			return self._command_str
		raise NotImplementedError('A TimingDeviceCommand must implement get_command_string if no simple command string is provided')

	@property
	def payload(self) -> str:
		return self.get_command_string()


class TimingDeviceSetTimeCommand(TimingDeviceCommand):
	_time: datetime.datetime

	@property
	def Time(self) -> datetime.datetime:
		return self._time

	def __init__(self,
			command_str: str,
			response_type: Type[CommandResponseType],
			timeToSet: datetime.datetime = datetime.datetime.now(),
			sync: bool = False):
		assert timeToSet.tzinfo is not None, 'Setting a time on a device requires the timezone be specified.'
		super().__init__(command_str, response_type, sync)
		self._time = timeToSet

	@abstractmethod
	def get_command_string(self) -> str:
		raise NotImplementedError('A TimingDeviceSetTimeCommand must implement get_command_string')

	def match_response(self, message: DecoderMessageType) -> Optional[CommandResponseType]:
		if not isinstance(message, DecoderTimeMessage):
			return None
		raise NotImplementedError('A TimingDeviceSetTimeCommand must implement match_response')


class TimingDeviceSendRecordsCommand(TimingDeviceCommand, ABC):
	def __init__(self, *args, **kwargs):
		kwargs['sync'] = kwargs.get('sync', False)
		kwargs['response_type'] = kwargs.get('response_type', None)
		kwargs['command_str'] = kwargs.get('command_str', None)
		super().__init__(*args, **kwargs)


class TimingDeviceStopResendRecords(TimingDeviceCommand, ABC):
	def __init__(self, *args, **kwargs):
		kwargs['sync'] = kwargs.get('sync', False)
		kwargs['response_type'] = kwargs.get('response_type', None)
		kwargs['command_str'] = kwargs.get('command_str', None)
		super().__init__(*args, **kwargs)
