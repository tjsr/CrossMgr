import datetime
import unittest
from Ultra import UltraDecoderMessage, parseTagTime, socketSend, socketReadDelimited

class TestUltra(unittest.TestCase):
	def test_parseTagTime(self):
		s = "1,12345,678,910,11"
		expected_chip_code = "12345"
		expected_time = datetime.datetime(1980, 1, 1) + datetime.timedelta(seconds=678, milliseconds=910)
		chip_code, time = parseTagTime(s)
		self.assertEqual(chip_code, expected_chip_code)
		self.assertEqual(time, expected_time)

	def test_socketSend(self):
		# Mock socket and message
		s = MockSocket()
		message = "test message"
		socketSend(s, message)
		self.assertEqual(s.sent_data, message.encode())

	def test_socketReadDelimited(self):
		# Mock socket
		s = MockSocket()
		s.set_recv_data(b"test data\r")
		result = socketReadDelimited(s)
		self.assertEqual(result, b"test data\r")
  
class TestUltraConnectMessage(unittest.TestCase):
	def test_connect_time_string(self):
		timeString: str = '10:51:23 28-12-2024 (1419850283)'
		self.assertTrue(UltraDecoderMessage.is_connect_info_message(timeString))

	def test_connect_time_negative_index(self):
		timeString: str = '10:51:23 28-12-2024 (-1419850283)'
		self.assertTrue(UltraDecoderMessage.is_connect_info_message(timeString))

		timeString = '11:29:36 28-12-2067 (-1518202720)'
		self.assertTrue(UltraDecoderMessage.is_connect_info_message(timeString))

class MockSocket:
	def __init__(self):
		self.sent_data = b""
		self.recv_data = b""

	def send(self, data):
		self.sent_data += data
		return len(data)

	def recv(self, bufsize):
		data = self.recv_data[:bufsize]
		self.recv_data = self.recv_data[bufsize:]
		return data

	def set_recv_data(self, data):
		self.recv_data = data
	
	def fileno(self):
		return 1

if __name__ == '__main__':
	unittest.main()