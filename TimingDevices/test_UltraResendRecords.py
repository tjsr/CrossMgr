from datetime import datetime
from unittest import TestCase, mock

from TimingDevices.TimingDevice import TimingDevice
from TimingDevices.UltraTimingDevice import UltraDecoder


class TestUltraResendRecord(TestCase):
	def test_send_records_from_record(self):
		host = '127.0.0.1'
		port = 23
		with mock.patch.object(TimingDevice, 'send_command', return_value=None) as mock_send_command:
			td = UltraDecoder(None, host, port)

			# Create a matcher for the command
			td.send_records_from_record(start_record=10, end_record=20)
			mock_send_command.assert_called_once()

			assert mock_send_command.call_args[0][0]._from_record == 10
			assert mock_send_command.call_args[0][0]._to_record == 20

	def test_send_records_from_date(self):
		host = '127.0.0.1'
		port = 23
		with mock.patch.object(TimingDevice, 'send_command', return_value=None) as mock_send_command:
			td = UltraDecoder(None, host, port)

			start = datetime(2021, 3, 1, 10, 25, 00)
			end = datetime(2021, 3, 1, 11, 00, 00)
			# Create a matcher for the command
			td.send_records_from_time(start_time=start, end_time=end)
			mock_send_command.assert_called_once()

			self.assertIsNotNone(mock_send_command.call_args[0][0]._from_date_time)
			self.assertIsNotNone(mock_send_command.call_args[0][0]._to_date_time)
			self.assertEqual(mock_send_command.call_args[0][0]._from_date_time.timestamp(), 1614554700.0)
			self.assertEqual(mock_send_command.call_args[0][0]._to_date_time.timestamp(), 1614556800.0)
