import datetime
from typing import Generic, TypeVar, Optional, Type

CommandResponse = TypeVar('CommandResponse')

class TimingDeviceCommandException(Exception):
	def __init__(self, msg: str | None, exception: Exception | None = None):
		super().__init__(msg, exception)

class DecoderStatusMessage():
	_readStatus: bool
	_sendStatus: bool

	@property
	def readStatus(self) -> bool:
		return self._readStatus

	@property
	def sendStatus(self) -> bool:
		return self._sendStatus

	def __init__(self, readStatus: bool, sendStatus: bool):
		self._readStatus = readStatus
		self._sendStatus = sendStatus

class TimingDeviceCommand(Generic[CommandResponse]):
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
	_response: CommandResponse
	_sent_at: datetime.datetime
	_comment = str
	_command_type: str
	_response_type: Type[CommandResponse]

	def __init__( self, _command_str: str, response_type: Type[CommandResponse], sync: bool = False ):
		self._command_str = _command_str
		self._sync = sync
		self._expectsResponse = sync
		self._providesResponse = True
		self._response_type = response_type
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
	def response(self) -> CommandResponse:
		return self._response

	@response.setter
	def response(self, response: CommandResponse):
		self._response = response

	def match_response(self, message: str) -> Optional[CommandResponse]:
		return None

	def match_message(self, message: CommandResponse) -> Optional[CommandResponse]:
		return None

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





