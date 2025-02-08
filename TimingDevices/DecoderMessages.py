from typing import Type


class DecoderMessage:
	def __init__(self, *args, **kwargs):
		pass

	def is_message_type(self, searchType: Type) -> bool:
		return isinstance(self, searchType)


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
		super().__init__(self, *args, **kwargs)
		self._readStatus = readStatus
		self._sendStatus = sendStatus


class UnrecognisedDecoderMessage(DecoderMessage):
	_message: str
	def __init__(self, message: str):
		super().__init__()
		self._message = message
