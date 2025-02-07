import datetime
import re
from abc import abstractmethod
from typing import Optional

from TimingDevices.TimingDeviceCommand import TimingDeviceCommand
from TimingDevices.UltraDecoderMessages import UltraCommandResponse


class UltraSetTimeCommandResponse(UltraCommandResponse):
	_time: datetime.datetime

	@staticmethod
	def matches(message: str) -> bool:
		return re.match(r'^t \d{2}:\d{2}:\d{2} \d{2}-\d{2}-\d{4}$', message) is not None

	@staticmethod
	def parse(message: str) -> Optional['UltraSetTimeCommandResponse']:
		if UltraSetTimeCommandResponse.matches(message):
			# TODO: Set the time from the string we got
			return UltraSetTimeCommandResponse()
		return None


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

