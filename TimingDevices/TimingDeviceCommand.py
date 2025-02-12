import datetime
from abc import abstractmethod
from typing import Generic, TypeVar, Optional, Type

from TimingDevices.DecoderMessages import DecoderTimeMessage

CommandResponseType = TypeVar('CommandResponseType', bound='TimingDeviceMessage')
DecoderMessageType = TypeVar('DecoderMessageType', bound='DecoderMessage')

class TimingDeviceCommandException(Exception):
	def __init__(self, msg: str | None, exception: Exception | None = None):
		super().__init__(msg, exception)


class TimingDeviceCommand(Generic[CommandResponseType]):
	COMMAND_SEND_RECORDS = 'send_records'
	COMMAND_GET_TIME = 'get_time'
	COMMAND_SET_TIME = 'set_time'
	COMMAND_STATUS = 'status'
	COMMAND_START = 'start'
	COMMAND_STOP = 'stop'

	_command_str: str
	_sync: bool = False
	_expectsResponse: bool = True
	_providesResponse: bool = True
	_response: CommandResponseType | None
	_sent_at: datetime.datetime | None
	_comment = str
	_command_type: str
	_response_type: Type[CommandResponseType]
	_success: bool = False

	def __init__(self, _command_str: str, response_type: Type[CommandResponseType] | None, sync: bool = False):
		self._command_str = _command_str
		self._sync = sync
		self._expectsResponse = sync
		self._providesResponse = True
		self._response_type = response_type
		self._response = None
		self._sent_at = None
		self._command_type = self.__class__.__name__

	def is_sync_command(self) -> bool:
		return self._sync

	def get_command_string(self) -> str:
		return self._command_str

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
		return self._providesResponse

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


class TimingDeviceSetTimeCommand(TimingDeviceCommand):
	def __init__(self, _command_str: str, response_type: Type[CommandResponseType], sync: bool = False):
		super().__init__(_command_str, response_type, sync)

	@abstractmethod
	def get_command_string(self) -> str:
		raise NotImplementedError('A TimingDeviceSetTimeCommand must implement get_command_string')

	def match_response(self, message: DecoderMessageType) -> Optional[CommandResponseType]:
		if not isinstance(message, DecoderTimeMessage):
			return None
		raise NotImplementedError('A TimingDeviceSetTimeCommand must implement match_response')