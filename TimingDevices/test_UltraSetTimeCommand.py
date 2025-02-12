import unittest
import datetime
from TimingDevices.UltraDecoderCommands import UltraSetTimeCommand, UltraSetTimeCommandResponse
from TimingDevices.DecoderMessages import DecoderMessage


class TestUltraSetTimeCommand(unittest.TestCase):
    def test_create_ultra_set_time_command(self):
        command = UltraSetTimeCommand(timeToSet = datetime.datetime.fromtimestamp(1423307035))
        expectedDateTime = datetime.datetime(2025, 2, 6, 11, 3, 55)

        self.assertIsInstance(command, UltraSetTimeCommand)
        self.assertTrue(command.providesResponse)
        self.assertEquals(command.Time, expectedDateTime)

    def test_parse_valid_time(self):
        valid_message = "12:34:56 01-01-2023"
        response = UltraSetTimeCommandResponse.parse(valid_message)
        self.assertIsNotNone(response)
        self.assertIsInstance(response, UltraSetTimeCommandResponse)

    def test_parse_invalid_time(self):
        invalid_message = "invalid message"
        response = UltraSetTimeCommandResponse.parse(invalid_message)
        self.assertIsNone(response)

    def test_get_messages_of_ultra_set_time_command_type(self):
        messages = [
            "t 12:34:56 01-01-2023",
            "invalid message",
            "t 23:59:59 31-12-2023"
        ]
        command = UltraSetTimeCommand()
        responses = [UltraSetTimeCommandResponse.parse(msg) for msg in messages]
        valid_responses = [resp for resp in responses if resp is not None]
        self.assertEqual(len(valid_responses), 2, "Should return two valid responses")
        for response in valid_responses:
            self.assertIsInstance(response, UltraSetTimeCommandResponse)

if __name__ == '__main__':
    unittest.main()