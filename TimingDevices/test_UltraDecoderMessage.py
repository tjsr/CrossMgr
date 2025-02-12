from unittest import TestCase

from TimingDevices.UltraDecoderMessages import UltraDecoderMessage


class TestUltraDecoderMessage(TestCase):
	def test_Constructor(self):
		id = 123
		udm = UltraDecoderMessage(id)
		self.assertEqual(udm.UltraId, 123)
