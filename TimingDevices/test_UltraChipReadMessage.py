from datetime import datetime, timezone
from unittest import TestCase

from TimingDevices.UltraDecoderMessages import UltraChipReadMessage


class TestUltraChipReadMessage(TestCase):
	def test_basic_line(self):
		msg = UltraChipReadMessage.parse('0,838871135,1424859562,565,1,-64,0,1,1,0000000000000000,0,409851')
		self.assertEqual(1, msg.UltraId)
		self.assertEqual(838871135, msg.TransponderId)
		expected_datetime = datetime(2025, 2, 24, 10, 19, 22, 565000, tzinfo=timezone.utc)
		self.assertEqual(expected_datetime, msg.Time)