from unittest import TestCase

from TimingDevices.UltraDecoderMessages import UltraDecoderTimeMessage


class TestMatchesValidUltraDecoderTimeMessage(TestCase):
	def test_matches_time_message(self):
		valid_message = "21:25:26 11-02-2025"
		response = UltraDecoderTimeMessage.matches(valid_message)
		self.assertTrue(response)

	def test_matches_time_message_with_brackets(self):
		valid_message = "21:25:26 11-02-2025 (1423776326)"
		response = UltraDecoderTimeMessage.matches(valid_message)
		self.assertTrue(response)

	def test_match_odd_time(self):
		# On occasion weird time values are sent to the decoder, such as below.  Ensure it doesn't crash.
		odd_message = "22:36:50 11-02-2074 (-1324885886)"
		response = UltraDecoderTimeMessage.matches(odd_message)
		self.assertTrue(response)

	def test_should_match_time_with_single_hour_digit(self):
		valid_message = '4:47:41 27-2-2025 (1425098861)'
		result = UltraDecoderTimeMessage.matches(valid_message)
		self.assertTrue(result)

	def test_should_match_time_with_single_minute_digit(self):
		# You would think this string would be invalid, but the decoder has been seen to send it.
		valid_message = '6:28:6 27-2-2077 (-1228867210)'
		result = UltraDecoderTimeMessage.matches(valid_message)
		self.assertTrue(result)

class TestParsesValidUltraDecoderTimeMessage(TestCase):
	def test_parse_valid_time(self):
		valid_message = "21:25:26 11-02-2025"
		response = UltraDecoderTimeMessage.parse(valid_message)
		self.assertIsNotNone(response)
		self.assertIsInstance(response, UltraDecoderTimeMessage)

	def test_parse_valid_time_with_brackets(self):
		valid_message = "21:25:27 11-02-2025 (1423776327)"
		response = UltraDecoderTimeMessage.parse(valid_message)
		self.assertIsNotNone(response)
		self.assertIsInstance(response, UltraDecoderTimeMessage)

	def test_parse_valid_time_with_diff_epoch(self):
		valid_message = "21:25:28 11-02-2025 (1423776300)"
		response = UltraDecoderTimeMessage.parse(valid_message)
		self.assertIsNotNone(response)
		self.assertIsInstance(response, UltraDecoderTimeMessage)

	def test_parse_time_with_single_minute_digit(self):
		# You would think this string would be invalid, but the decoder has been seen to send it.
		valid_message = '6:28:6 27-2-2077 (-1228867210)'
		response = UltraDecoderTimeMessage.parse(valid_message)
		self.assertIsNotNone(response)
		self.assertIsInstance(response, UltraDecoderTimeMessage)


class TestInvalidUltraDecoderTimeMessage(TestCase):
	def test_parse_odd_time(self):
		# On occasion weird time values are sent to the decoder, such as below.  Ensure it doesn't crash.
		odd_message = "22:36:50 11-02-2074 (-1324885886)"
		response: UltraDecoderTimeMessage = UltraDecoderTimeMessage.parse(odd_message)
		self.assertIsNotNone(response)
		self.assertTrue(response.HasInvalidData)
		self.assertIsNotNone(response.time)

	def test_parse_too_many_params(self):
		invalid_message = "21:25:26 11-02-2025 (1423776326) 123"
		response = UltraDecoderTimeMessage.parse(invalid_message)
		self.assertIsNone(response)

	def test_should_not_match_chip_read(self):
		invalid_message = "0,838871135,1423827949,253,1,-62,0,1,1,0000000000000000,0,363710"
		result = UltraDecoderTimeMessage.matches(invalid_message)
		self.assertFalse(result)

	def test_should_not_parse_chip_read(self):
		invalid_message = "0,838871135,1423827949,253,1,-62,0,1,1,0000000000000000,0,363710"
		result = UltraDecoderTimeMessage.parse(invalid_message)
		self.assertIsNone(result)
