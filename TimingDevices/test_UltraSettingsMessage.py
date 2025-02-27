from unittest import TestCase

from TimingDevices.UltraDecoderMessages import UltraSettingsMessage


class TestUltraSettingsMessage(TestCase):
	def test_shouldParseSettingsMessage(self):
		msg = "U\x012"
		usm: UltraSettingsMessage = UltraSettingsMessage.parse(msg)
		usm.Data = msg
		self.assertEqual(usm.Data, 'U\x012')