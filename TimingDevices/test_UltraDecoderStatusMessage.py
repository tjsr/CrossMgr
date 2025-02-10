from unittest import TestCase

from TimingDevices.UltraDecoderCommands import UltraGetStatusCommandResponse
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

	def test_shouldParseValidLine(self):
		message = UltraDecoderStatusMessage.parse('S=11')
		assert message.readStatus == True
		assert message.sendStatus == True
		message = UltraDecoderStatusMessage.parse('S=10')
		assert message.readStatus == True
		assert message.sendStatus == False
		message = UltraDecoderStatusMessage.parse('S=01')
		assert message.readStatus == False
		assert message.sendStatus == True
		message = UltraDecoderStatusMessage.parse('S=00')
		assert message.readStatus == False
		assert message.sendStatus == False

	def test_shouldRejectInvalidStatusValues(self):
		message = UltraDecoderStatusMessage.parse('S=24')
		self.assertIsNone(message)

		response = UltraGetStatusCommandResponse.parse('S=24')
		self.assertIsNone(response)

	def test_shouldRejectInvalidStatusLength(self):
		message = UltraDecoderStatusMessage.parse('S=111')
		self.assertIsNone(message)

		response = UltraGetStatusCommandResponse.parse('S=111')
		self.assertIsNone(response)



	# def getMessageParser(self):
	# 	mockTD = mock.Mock( UltraDecoder )
	# 	msg: TimingDeviceMessage = mockTD.parse('S=11')
	#
	# 		# messages= self.get_messages(responseClass)
	# 	)