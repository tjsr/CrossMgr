import datetime
from abc import abstractmethod, ABC
from typing import Optional, cast

from Log import getLogger
from TimingDevices.DecoderMessages import DecoderMessage
from TimingDevices.TimingDeviceCommand import TimingDeviceCommand, TimingDeviceSetTimeCommand, \
	TimingDeviceStopResendRecords, TimingDeviceCommandException, TimingDeviceSendRecordsCommand
from TimingDevices.UltraDecoderMessages import UltraCommandResponse, UltraDecoderStatusMessage, UltraDecoderTimeMessage, \
	UltraDecoderMessage

class UltraSetTimeCommandResponse(UltraCommandResponse, UltraDecoderTimeMessage):
	def match_message(self, message: 'UltraDecoderMessage') -> Optional[UltraDecoderTimeMessage]:
		if isinstance(message, UltraSetTimeCommandResponse):
			return cast('UltraSetTimeCommandResponse', message)

		if UltraSetTimeCommandResponse.match_message(self, message):
			return UltraSetTimeCommandResponse(message=cast('UltraSetTimeCommandResponse', message))

		return None

	def __init__(self, time: datetime.datetime = None, message: UltraDecoderTimeMessage = None):
		if message is not None:
			UltraDecoderTimeMessage.__init__(self, message.UltraId, message.time)
		else:
			UltraDecoderTimeMessage.__init__(self, 0, time)

	@staticmethod
	def matches(messageBuf: str) -> bool:
		return UltraDecoderTimeMessage.matches(messageBuf)

	@staticmethod
	def parse(messageBuf: str) -> Optional['UltraSetTimeCommandResponse']:
		assert isinstance(messageBuf, str)
		if messageBuf is None or messageBuf == '':
			log = getLogger(name='UltraSetTimeCommandResponse.parse')
			log.warning('No message buffer provided when trying to parse Ultra Set Time response')
			return None

		response = UltraDecoderTimeMessage.parse(messageBuf)
		if response is not None:
			return UltraSetTimeCommandResponse(message=response)
		return None


class UltraGetStatusCommandResponse(UltraDecoderStatusMessage):
	def match_message(self, message: DecoderMessage) -> 'UltraGetStatusCommandResponse':
		if UltraGetStatusCommandResponse.matches(message.Data):
			return UltraGetStatusCommandResponse.parse(message.Data)

	def __init__(self, messageObj: UltraDecoderStatusMessage, *args, **kwargs):
		super().__init__(messageObj.readStatus, messageObj.sendStatus, *args, **kwargs)

	@staticmethod
	def matches(messageBuf: str) -> bool:
		return UltraDecoderStatusMessage.matches(messageBuf)

	@staticmethod
	def parse(messageBuf: str) -> Optional['UltraGetStatusCommandResponse']:
		messageBuf = UltraDecoderStatusMessage.parse(messageBuf)
		if messageBuf is not None:
			return UltraGetStatusCommandResponse(messageBuf)
		return None


class UltraGetStatusCommand(TimingDeviceCommand):
	def __init__(self):
		super().__init__('?', response_type=UltraDecoderStatusMessage, sync=True)

	def get_command_string(self) -> str:
		return '?'

	def match_response(self, message: UltraDecoderMessage) -> Optional[UltraGetStatusCommandResponse]:
		if not isinstance(message, UltraDecoderStatusMessage):
			return None
		if isinstance(message, UltraGetStatusCommandResponse):
			self.response = message
			return message
		return UltraGetStatusCommandResponse(message)


class UltraSetTimeCommand(TimingDeviceSetTimeCommand, TimingDeviceCommand):
	_time: datetime.datetime
	def __init__(self, timeToSet: datetime.datetime = datetime.datetime.now()):
		# TODO: Fix response_type cast
		TimingDeviceSetTimeCommand.__init__(self, 't', response_type=UltraDecoderTimeMessage, sync=True)
		self._time = timeToSet

	def match_response(self, message: UltraDecoderMessage) -> Optional[UltraSetTimeCommandResponse]:
		if not isinstance(message, UltraDecoderTimeMessage):
			return None
		return cast(UltraSetTimeCommandResponse, message)

	def get_command_string(self) -> str:
		decoderMessage = 't {}'.format(self._time.strftime('%H:%M:%S %d-%m-%Y'))
		return decoderMessage

	@property
	def Time(self) -> datetime.datetime:
		return self._time


class UltraCommandException(TimingDeviceCommandException):
	pass


class UltraSendRecordsCommand(TimingDeviceSendRecordsCommand):
	_from_date_time: datetime.datetime | None
	_to_date_time: datetime.datetime | None

	_from_record: int | None
	_to_record: int | None

	def validate_parameters(self, start_time: datetime.datetime | None, end_time: datetime.datetime | None, from_record: int | None, to_record: int | None):
		if start_time is not None:
			if from_record is not None or to_record is not None:
				raise TimingDeviceCommandException('A UltraSendRecordsCommand must have either datetime record values, not both')
			if end_time is not None and start_time > end_time:
				raise UltraCommandException('The start timestamp must be before the end timestamp.')
		if end_time is not None:
			if from_record is not None or to_record is not None:
				raise TimingDeviceCommandException('A UltraSendRecordsCommand must have either datetime record values, not both')
			if start_time is None:
				raise UltraCommandException('An UltraSendRecordsCommand may not have an end timestamp without specifying the start timestamp.')

		if from_record is not None:
			if to_record is not None and from_record > to_record:
				raise UltraCommandException('The start record must be before the end record.')
		else:
			if to_record is not None:
				raise UltraCommandException('An UltraSendRecordsCommand may not have an end record without specifying the start record.')

		return True

	def __init__(self, start_time: datetime.datetime | None = None, end_time: datetime.datetime | None = None, from_record: int | None = None, to_record: int | None = None):
		super().__init__(command_str=None, response_type=None, sync=False)
		UltraSendRecordsCommand.validate_parameters(self, start_time, end_time, from_record, to_record)

		self._from_record = from_record
		self._to_record = to_record

		self._from_date_time = start_time
		self._to_date_time = end_time


	def get_command_string(self) -> str:
		if self._from_date_time is not None:
			t1980 = datetime.datetime(1980, 1, 1).timestamp()
			from_epoch = int(self._from_date_time.timestamp() - t1980)
			to_epoch = int(self._to_date_time.timestamp() if self._to_date_time is not None else datetime.datetime.now().timestamp() - t1980)

			return f'800{from_epoch}\0x0D{to_epoch}'
		elif self._from_record is not None:
			if self._to_record is not None:
				return f'600{self._from_record}\0x0D{self._to_record}'
			else:
				return f'600{self._from_record}'

		raise ValueError('UltraSendRecordsCommand must have either a datetime range or record range')

	def match_response(self, message: UltraDecoderMessage) -> Optional[UltraDecoderMessage]:
		if not isinstance(message, UltraDecoderMessage):
			return None
		return message


class UltraStopResendRecords(TimingDeviceStopResendRecords, ABC):
	def __init__(self):
		super().__init__(command_str='9', response_type=None, sync=False)
