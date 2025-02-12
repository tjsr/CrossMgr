from abc import abstractmethod
from datetime import datetime
from typing import Type


class DecoderMessage:
	_data: str | None

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

	@Data.setter
	def Data(self, value: str):
		self._data = value

	def __str__(self):
		if self._data is not None:
			return self._data
		return f'{self.__class__.__name__}: ' + str(self.__dict__)


class DecoderStatusMessage(DecoderMessage):
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

	@abstractmethod
	def match_message(self, message: DecoderMessage) -> DecoderMessage:
		pass


class DecoderTimeMessage(DecoderMessage):
	_time: datetime
	_invalidTime: bool = False

	@property
	def time(self) -> datetime:
		return self._time

	def __init__(self, time: datetime, is_invalid: bool = False, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._time = time
		self._invalidTime = is_invalid

	@abstractmethod
	def match_message(self, message: DecoderMessage) -> DecoderMessage:
		pass

	@property
	def HasInvalidData(self) -> bool:
		return self._time is None or self._invalidTime


class UnrecognisedDecoderMessage(DecoderMessage):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	@abstractmethod
	def match_message(self, received: DecoderMessage) -> DecoderMessage:
		return received

