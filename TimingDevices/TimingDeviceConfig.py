import json
from typing import List

from TimingDevices.TimingDevice import TimingDevice


class TimingDeviceConfig:
	__devices: List[TimingDevice]

	def __init__(self):
		self.__devices = []

	def add_device(self, device: TimingDevice):
		self.__devices.append(device)

	@property
	def Devices(self) -> List[TimingDevice]:
		return self.__devices

	def remove_device(self, device: TimingDevice):
		self.__devices.remove(device)

	def clear_devices(self):
		self.__devices.clear()

	def to_json(self) -> str:
		return json.dumps({
			'devices': json.dumps([device.__dict__ for device in self.__devices], indent=1)
		}, indent=1)

	@property
	def _file_name(self) -> str:
		return 'timing_devices.json'

	def write_config(self):
		with open(self._file_name, 'w') as file:
			output_buffer = self.to_json()
			file.write(output_buffer)


if __name__ == '__main__':
	config = TimingDeviceConfig()
	config.write_config()

