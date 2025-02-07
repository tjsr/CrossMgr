import unittest
import datetime
from TimingDevices.UltraDecoderCommands import UltraSetTimeCommand, UltraSetTimeCommandResponse
from TimingDevices.TimingDevice import DecoderMessage

class TestUltraSetTimeCommand(unittest.TestCase):

    def test_create_ultra_set_time_command(self):
        command = UltraSetTimeCommand(timeToSet = datetime.datetime.fromtimestamp(1423307035))
        expectedDateTime = datetime.datetime(2025, 2, 6, 11, 3, 55)

        self.assertIsInstance(command, UltraSetTimeCommand)
        self.assertTrue(command.providesResponse)

    def test_match_response(self):
        valid_message = "t 12:34:56 01-01-2023"
        invalid_message = "invalid message"
        response = UltraSetTimeCommandResponse.parse(valid_message)
        self.assertIsNotNone(response)
        self.assertIsInstance(response, UltraSetTimeCommandResponse)
        self.assertIsNone(UltraSetTimeCommandResponse.parse(invalid_message))

    def test_get_messages_of_ultra_set_time_command_type(self):
        messages = [
            "t 12:34:56 01-01-2023",
            "invalid message",
            "t 23:59:59 31-12-2023"
        ]
        command = UltraSetTimeCommand()
        responses = [UltraSetTimeCommandResponse.parse(msg) for msg in messages]
        valid_responses = [resp for resp in responses if resp is not None]
        self.assertEqual(len(valid_responses), 2)
        for response in valid_responses:
            self.assertIsInstance(response, UltraSetTimeCommandResponse)

if __name__ == '__main__':
    unittest.main()