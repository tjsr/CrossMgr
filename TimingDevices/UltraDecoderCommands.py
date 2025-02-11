import datetime
from typing import Optional, cast

from TimingDevices.DecoderMessages import DecoderMessage
from TimingDevices.TimingDeviceCommand import TimingDeviceCommand
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


class UltraSetTimeCommand(TimingDeviceCommand):
	_time: datetime.datetime
	def __init__(self, timeToSet: datetime.datetime = datetime.datetime.now()):
		super().__init__('t', response_type=UltraDecoderTimeMessage, sync=True)
		self._time = timeToSet

	def match_response(self, messageBuf: str) -> Optional[UltraSetTimeCommandResponse]:
		return UltraSetTimeCommandResponse.parse(messageBuf)

	def get_command_string(self) -> str:
		decoderMessage = 't {}'.format(self._time.strftime('%H:%M:%S %d-%m-%Y'))
		return decoderMessage

