from unittest import TestCase

from TimingDevices.DecoderMessages import DecoderStatusMessage


class TestDecoderStatusMessage(TestCase):
	def test_Constructor(self):
		dsm = DecoderStatusMessage(True, True)
		self.assertTrue(dsm.readStatus)
		self.assertTrue(dsm.sendStatus)

