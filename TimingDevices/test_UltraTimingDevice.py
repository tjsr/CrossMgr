# test_UltraTimingDevice.py

import unittest
from unittest.mock import Mock

from TimingDevices.TimingDeviceCommand import TimingDeviceCommand
from UltraTimingDevice import UltraDecoder

class TestUltraTimingDevice(unittest.TestCase):

	def setUp(self):
		mock_log = Mock()
		# Set up any necessary test data or state
		self.device = UltraDecoder(mock_log, 'test', 0)

	def test_get_status_command(self):
		command = self.device.get_command(TimingDeviceCommand.COMMAND_STATUS)
		self.assertEqual(command.get_command_string(), '?')

if __name__ == '__main__':
	unittest.main()