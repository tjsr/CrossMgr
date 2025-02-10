import datetime
import re
from typing import Optional

from TimingDevices.TimingDeviceCommand import TimingDeviceCommand
from TimingDevices.UltraDecoderMessages import UltraCommandResponse, UltraDecoderStatusMessage, UltraDecoderTimeMessage


class UltraSetTimeCommandResponse(UltraCommandResponse, UltraDecoderTimeMessage):
	def __init__(self, time: datetime.datetime = None, message: UltraDecoderTimeMessage = None):
		if message is not None:
			UltraDecoderTimeMessage.__init__(self, message.UltraId, message.time)
		else:
			UltraDecoderTimeMessage.__init__(self, 0, time)

	@staticmethod
	def matches(message: str) -> bool:
		return UltraDecoderTimeMessage.matches(message)

	@staticmethod
	def parse(message: str) -> Optional['UltraSetTimeCommandResponse']:
		response = UltraDecoderTimeMessage.parse(message)
		if response is not None:
			return UltraSetTimeCommandResponse(message=response)
		return None


class UltraGetStatusCommandResponse(UltraDecoderStatusMessage):
	def __init__(self, message: UltraDecoderStatusMessage, *args, **kwargs):
		super().__init__(message.readStatus, message.sendStatus, *args, **kwargs)

	@staticmethod
	def matches(message: str) -> bool:
		return re.match(UltraDecoderStatusMessage.MESSAGE_FORMAT, message) is not None

	@staticmethod
	def parse(message: str) -> Optional['UltraGetStatusCommandResponse']:
		message = UltraDecoderStatusMessage.parse(message)
		if message is not None:
			return UltraGetStatusCommandResponse(message)
		return None


class UltraGetStatusCommand(TimingDeviceCommand):
	def __init__(self):
		super().__init__('?', response_type=UltraGetStatusCommandResponse, sync=True)

	def get_command_string(self) -> str:
		return '?'

	def match_response(self, message: str) -> Optional[UltraGetStatusCommandResponse]:
		return UltraGetStatusCommandResponse.parse(message)


class UltraSetTimeCommand(TimingDeviceCommand):
	_time: datetime.datetime
	def __init__(self, timeToSet: datetime.datetime = datetime.datetime.now()):
		super().__init__('t', response_type=UltraSetTimeCommandResponse, sync=True)
		self._time = timeToSet

	def match_response(self, message: str) -> Optional[UltraSetTimeCommandResponse]:
		return UltraSetTimeCommandResponse.parse(message)

	def get_command_string(self) -> str:
		decoderMessage = 't {}'.format(self._time.strftime('%H:%M:%S %d-%m-%Y'))
		return decoderMessage

