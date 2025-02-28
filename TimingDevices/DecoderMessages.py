from abc import abstractmethod, ABC
from datetime import datetime
from typing import Type, TypeVar, Generic


class DecoderMessage:
	_data: str | None
	pushed_back_count: int = 0
	__received_at: datetime | None = None

	def __init__(self, *args, **kwargs):
		self._data = None

	def is_message_type(self, searchType: Type) -> bool:
		return isinstance(self, searchType)

	@abstractmethod
	def match_message(self, message: 'DecoderMessage'):
		pass

	@property
	def Data(self) -> str | None:
		return self._data

	@property
	def received_at(self) -> datetime | None:
		return self.__received_at

	@received_at.setter
	def received_at(self, value: datetime):
		self.__received_at = value

	@Data.setter
	def Data(self, value: str):
		self._data = value

	def __str__(self):
		if self._data is not None:
			return self._data
		return f'{self.__class__.__name__}: ' + str(self.__dict__)


class DecoderStatusMessage(DecoderMessage, ABC):
	_readStatus: bool
	_sendStatus: bool

	@property
	def readStatus(self) -> bool:
		return self._readStatus

	@property
	def sendStatus(self) -> bool:
		return self._sendStatus

	def __init__(self, readStatus: bool, sendStatus: bool, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._readStatus = readStatus
		self._sendStatus = sendStatus


class DecoderTimeMessage(DecoderMessage, ABC):
	_time: datetime
	_invalidTime: bool = False

	@property
	def time(self) -> datetime:
		return self._time

	def __init__(self, time: datetime, is_invalid: bool = False, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._time = time
		self._invalidTime = is_invalid

	@property
	def HasInvalidData(self) -> bool:
		return self._time is None or self._invalidTime


class UnrecognisedDecoderMessage(DecoderMessage):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def match_message(self, received: DecoderMessage) -> DecoderMessage:
		return received


last_crossing_id: int = 0


class DecoderCrossingMessage(DecoderMessage, ABC):
	_crossingId: int

	@property
	def CrossingId(self) -> int:
		return self._crossingId

	@abstractmethod
	def _getTime(self) -> datetime:
		pass

	@property
	def Time(self) -> datetime:
		return self._getTime()

	@staticmethod
	def generate_crossing_id() -> int:
		global last_crossing_id
		last_crossing_id = last_crossing_id + 1
		return last_crossing_id

	def __init__(self, crossingId: int = generate_crossing_id(), *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._crossingId = crossingId

	@abstractmethod
	def match_message(self, received: DecoderMessage) -> DecoderMessage:
		return received


TransponderIdType = TypeVar('TransponderIdType', str, int)

class TransponderCrossingMessage(Generic[TransponderIdType], DecoderCrossingMessage, ABC):
	@abstractmethod
	def _getTransponderId(self):
		pass

	@property
	def TransponderId(self) -> TransponderIdType:
		return self._getTransponderId()

	def __init__(self, crossingId: int = None, txValueAsString: bool = False, *args, **kwargs):
		super().__init__(crossingId, *args, **kwargs)