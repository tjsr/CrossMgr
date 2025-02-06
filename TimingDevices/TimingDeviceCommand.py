import datetime
from typing import Generic, Any, TypeVar, Optional

CommandResponse = TypeVar('CommandResponse')

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
	_response: Any
	_sent_at: datetime.datetime
	_comment = str

	def __init__( self, _command_str: str, sync: bool = False ):
		self._command_str = _command_str
		self._sync = sync
		self._expectsResponse = sync
		self._providesResponse = True

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

	def match_response(self, message: str) -> Optional[CommandResponse]:
		return None



