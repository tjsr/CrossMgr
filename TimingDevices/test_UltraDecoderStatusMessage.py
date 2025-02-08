from unittest import TestCase

from TimingDevices.UltraDecoderMessages import UltraDecoderStatusMessage


class TestUltraDecoderStatusMessage(TestCase):
	def test_Constructor(self):
		statusMessage = UltraDecoderStatusMessage(True, False)
		assert statusMessage.readStatus == True
		assert statusMessage.sendStatus == False
		statusMessage = UltraDecoderStatusMessage(False, True)
		assert statusMessage.readStatus == False
		assert statusMessage.sendStatus == True
		statusMessage = UltraDecoderStatusMessage(True, True)
		assert statusMessage.readStatus == True
		assert statusMessage.sendStatus == True
		statusMessage = UltraDecoderStatusMessage(False, False)
		assert statusMessage.readStatus == False
		assert statusMessage.sendStatus == False
