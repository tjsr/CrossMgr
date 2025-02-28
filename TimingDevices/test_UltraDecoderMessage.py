from unittest import TestCase

from TimingDevices.UltraDecoderMessages import UltraDecoderMessage, UltraVoltageMessage


class TestUltraDecoderMessage(TestCase):
	def test_Constructor(self):
		id = 123
		udm = UltraVoltageMessage(id, 0.00)
		self.assertEqual(udm.UltraId, 123)
