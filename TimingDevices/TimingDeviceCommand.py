import datetime
from abc import abstractmethod, ABC
from typing import Generic, TypeVar, Optional, Type

from TimingDevices.DecoderMessages import DecoderTimeMessage
from TimingDevices.TimingDeviceExceptions import CommandNotSentError

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
	_expectMultipleResponses: bool = False
	_response_messages: list[CommandResponseType]
	_sent_at: datetime.datetime | None
	_comment = str
	_command_type: str
	_response_type: Type[CommandResponseType]
	_success: bool = False
	__response_expected_before: datetime.datetime | None = None
	__all_responses_received: bool = False

	def __init__(self, command_str: str | None = None, response_type: Type[CommandResponseType] | None = None, sync: bool = False):
		if sync is True and response_type is None:
			raise ValueError('A TimingDeviceCommand that synchronously waits for a response must know what response_type to wait for.')

		self._command_str = command_str
		self._sync = sync
		self._expectsResponse = sync
		self._response_type = response_type
		self._response_messages = []
		self._sent_at = None
		self._command_type = self.__class__.__name__

	@property
	def is_sync_command(self) -> bool:
		return self._sync

	@property
	def expectMultipleResponses(self) -> bool:
		return self._expectMultipleResponses

	@expectMultipleResponses.setter
	def expectMultipleResponses(self, value: bool):
		self._expectMultipleResponses = value

	@property
	def comment(self) -> str | None:
		return self._comment

	@comment.setter
	def comment(self, comment: str|None):
		self._comment = comment

	@property
	def response(self) -> CommandResponseType | None:
		if self._expectMultipleResponses:
			raise ValueError('This command expects multiple responses.  Use the responses property instead.')
		if len(self._response_messages) == 0:
			return None
		return self._response_messages[0]

	@response.setter
	def response(self, response: CommandResponseType):
		if self._expectMultipleResponses is False:
			if len(self._response_messages) == 0:
				self._response_messages = [response]
			else:
				self._response_messages[0] = response
			self.__all_responses_received = True
		else:
			if response not in self._response_messages:
				self._response_messages.append(response)

	@property
	def expectsResponse(self) -> bool:
		return self._expectsResponse

	@property
	def providesResponse(self) -> bool:
		return self._response_type is not None

	@property
	def response_type(self) -> Type[CommandResponseType] | None:
		if not self.providesResponse:
			return None
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

	@property
	def sent(self) -> bool:
		return self._sent_at is not None

	@property
	def expecting_response(self) -> bool:
		if self.providesResponse is False:
			return False
		if self.sent is False:
			return False

		if self.expectMultipleResponses:
			if self.__all_responses_received is True:
				return False
		else:
			if self.response is None or len(self._response_messages) == 0:
				return True

		return True

	@property
	def response_expected_before(self) -> datetime.datetime | None:
		return self.__response_expected_before

	@response_expected_before.setter
	def response_expected_before(self, time: datetime.datetime) -> None:
		self.__response_expected_before = time

	@property
	def awaiting_response(self) -> bool:
		if self.expecting_response is False:
			return False

		time_now = datetime.datetime.now()
		if self.__response_expected_before is not None and time_now > self.__response_expected_before:
			return False

		if self.__all_responses_received:
			return False

		if not self.expectMultipleResponses and self.response is not None:
			return False

		return True

	@property
	def id(self) -> int:
		return self._id

	def match_response(self, message: DecoderMessageType) -> Optional[CommandResponseType]:
		if message is None:
			return None

		t = self.response_type
		if t is None:
			raise NotImplementedError(
				'A TimingDeviceCommand that expects a response required a specific implementation of match_response')

		if self.sentAt is None:
			command_name = message.__class__.__name__
			raise CommandNotSentError(f'Cannot match a {command_name} response to a command that has not been sent.')

		if message.received_at is not None and self.sentAt is not None:
			# This might still be okay - we just can't verify it.
			if message.received_at < self.sentAt:
				return None

		matched_response = t.match_message(message)
		if matched_response is None:
			return None

		self.response = message
		return matched_response

	def match_message(self, message: DecoderMessageType) -> Optional[CommandResponseType]:
		assert self is not None
		assert not isinstance(message, str)
		assert message.Data is not None
		return message.matches(message)

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
