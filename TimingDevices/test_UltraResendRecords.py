from datetime import datetime, timezone
from unittest import TestCase, mock
from zoneinfo import ZoneInfo

from TimingDevices.TCPTimingDevice import TCPTimingDevice
from TimingDevices.TimingDevice import TimingDevice
from TimingDevices.TimingDeviceExceptions import TimingDeviceNotConnectedException
from TimingDevices.UltraTimingDevice import UltraDecoder

zone_melbourne = ZoneInfo('Australia/Victoria')

class TestUltraResendRecord(TestCase):
	def test_send_records_from_record(self):
		host = '127.0.0.1'
		port = 23
		with mock.patch.object(TimingDevice, 'send_command', return_value=None) as mock_send_command, \
				mock.patch.object(TCPTimingDevice, 'connected', return_value=True) as mock_connected:
			td = UltraDecoder(host, port)

			# Create a matcher for the command
			td.send_records_from_record(start_record=10, end_record=20)
			mock_send_command.assert_called_once()
			mock_connected.assert_called_once()

			assert mock_send_command.call_args[0][0]._from_record == 10
			assert mock_send_command.call_args[0][0]._to_record == 20

			self.assertTrue(mock_connected)

	def test_send_records_from_converted_date(self):
		host = '127.0.0.1'
		port = 23

		with mock.patch.object(TimingDevice, 'send_command', return_value=None) as mock_send_command, \
				mock.patch.object(TCPTimingDevice, 'connected', return_value=True) as mock_connected:
			td = UltraDecoder(host, port)
			start_melb = datetime(2021, 3, 1, 10, 25, 00, tzinfo=zone_melbourne)
			end_melb = datetime(2021, 3, 1, 11, 00, 00, tzinfo=zone_melbourne)
			start = start_melb.astimezone(timezone.utc)
			end = end_melb.astimezone(timezone.utc)

			# Create a matcher for the command
			td.send_records_from_time(start_time=start, end_time=end)
			mock_send_command.assert_called_once()
			mock_connected.assert_called_once()

			self.assertIsNotNone(mock_send_command.call_args[0][0]._from_date_time)
			self.assertIsNotNone(mock_send_command.call_args[0][0]._to_date_time)
			self.assertEqual(1614554700.0, mock_send_command.call_args[0][0]._from_date_time.timestamp())
			self.assertEqual(1614556800.0, mock_send_command.call_args[0][0]._to_date_time.timestamp())

			self.assertTrue(mock_connected)

	def test_send_records_from_date(self):
		host = '127.0.0.1'
		port = 23

		with mock.patch.object(TimingDevice, 'send_command', return_value=None) as mock_send_command, \
				mock.patch.object(TCPTimingDevice, 'connected', return_value=True) as mock_connected:
			td = UltraDecoder(host, port)
			start = datetime(2021, 3, 1, 10, 25, 00, tzinfo=timezone.utc)
			end = datetime(2021, 3, 1, 11, 00, 00, tzinfo=timezone.utc)

			# Create a matcher for the command
			td.send_records_from_time(start_time=start, end_time=end)
			mock_send_command.assert_called_once()
			mock_connected.assert_called_once()

			self.assertIsNotNone(mock_send_command.call_args[0][0]._from_date_time)
			self.assertIsNotNone(mock_send_command.call_args[0][0]._to_date_time)
			self.assertEqual(1614594300.0, mock_send_command.call_args[0][0]._from_date_time.timestamp())
			self.assertEqual(1614596400.0, mock_send_command.call_args[0][0]._to_date_time.timestamp())

			self.assertTrue(mock_connected)

	def test_send_records_requires_utc(self):
		host = '127.0.0.1'
		port = 23

		td = UltraDecoder(host, port)
		start = datetime(2021, 3, 1, 10, 25, 00)
		end = datetime(2021, 3, 1, 11, 00, 00)

		self.assertRaises(ValueError, td.send_records_from_time, start_time=start, end_time=end)


	def test_send_records_exception_when_disconnected(self):
		host = '127.0.0.1'
		port = 23

		td = UltraDecoder(host, port)
		start = datetime(2021, 3, 1, 10, 25, 00, tzinfo=timezone.utc)
		end = datetime(2021, 3, 1, 11, 00, 00, tzinfo=timezone.utc)

		self.assertRaises(TimingDeviceNotConnectedException, td.send_records_from_time, start_time=start, end_time=end)
