import unittest
import datetime
from zoneinfo import ZoneInfo

from TimingDevices.UltraDecoderCommands import UltraSetTimeCommand
from TimingDevices.UltraDecoderMessages import UltraDecoderTimeMessage
from TimingDevices.UltraTimeUtils import UltraTimeUtils

zone_utc = ZoneInfo('UTC')
zone_melbourne = ZoneInfo('Australia/Victoria')

class TestUltraSetTimeCommand(unittest.TestCase):
    def test_create_ultra_set_time_command_local(self):
        ultra_epoch = 1423307035
        test_datetime = UltraTimeUtils.ultra_epoch_to_datetime(ultra_epoch, tz=zone_melbourne)
        command = UltraSetTimeCommand(timeToSet = test_datetime)
        expectedDateTime = datetime.datetime(2025, 2, 6, 11, 3, 55, tzinfo = zone_utc)

        self.assertIsInstance(command, UltraSetTimeCommand)
        self.assertTrue(command.providesResponse)
        self.assertEqual(command.Time, expectedDateTime)

    def test_create_ultra_set_time_command_melbourne(self):
        ultra_epoch = 1423307035
        test_datetime = UltraTimeUtils.ultra_epoch_to_datetime(ultra_epoch, tz=zone_melbourne)
        command = UltraSetTimeCommand(timeToSet = test_datetime)
        expectedDateTime = datetime.datetime(2025, 2, 6, 11, 3, 55, tzinfo = zone_utc)

        self.assertIsInstance(command, UltraSetTimeCommand)
        self.assertTrue(command.providesResponse)
        self.assertEqual(command.Time, expectedDateTime)

    def test_parse_valid_time(self):
        valid_message = "12:34:56 01-01-2023"
        response = UltraDecoderTimeMessage.parse(valid_message)
        self.assertIsNotNone(response)
        self.assertIsInstance(response, UltraDecoderTimeMessage)

    def test_parse_invalid_time(self):
        invalid_message = "invalid message"
        response = UltraDecoderTimeMessage.parse(invalid_message)
        self.assertIsNone(response)

    def test_get_messages_of_ultra_set_time_command_type(self):
        messages = [
            "12:34:56 01-01-2023",
            "invalid message",
            "23:59:59 31-12-2023"
        ]
        responses = [UltraDecoderTimeMessage.parse(msg) for msg in messages]
        valid_responses = [resp for resp in responses if resp is not None]
        self.assertEqual(2, len(valid_responses), "Should return two valid responses")
        for response in valid_responses:
            self.assertIsInstance(response, UltraDecoderTimeMessage)

if __name__ == '__main__':
    unittest.main()