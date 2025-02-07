import datetime
import unittest
from TimingDevices.UltraDecoderMessages import UltraConnectConfirmationMessage

class TestUltraConnectConfirmationMessage(unittest.TestCase):
	def test_parse_valid_message(self):
		message = "Connected,1423307035,U"
		result = UltraConnectConfirmationMessage.parse(message)
		self.assertIsNotNone(result)
		self.assertEqual(result.UltraId, 0)
		expectedDateTime = datetime.datetime(2025, 2, 6, 11, 3, 55)
		self.assertEqual(result.lastTimeSent, expectedDateTime)

	def test_parse_invalid_message_format(self):
		message = "InvalidMessageFormat"
		result = UltraConnectConfirmationMessage.parse(message)
		self.assertIsNone(result)

	def test_parse_invalid_message_value(self):
		message = "Connected,blah,U"
		result = UltraConnectConfirmationMessage.parse(message)
		self.assertIsNone(result)

if __name__ == '__main__':
	unittest.main()
