import unittest
from unittest.mock import patch, MagicMock
import socket

from TimingDevices.TCPTimingDevice import TCPTimingDevice

class TestTCPTimingDevice(TCPTimingDevice):
    def getDeviceType(self):
        return "TestDevice"

    async def _wait_until_ready(self):
        return True

    async def on_socket_connect(self):
        return True

    def on_socket_timeout(self, ex: socket.timeout):
        pass

    def on_connect(self, msg):
        return True

class TestTCPTimingDeviceConnect(unittest.TestCase):
    @patch('TimingDevices.TCPTimingDevice.socket.socket')
    def test_connect_success(self, mock_socket):
        mock_socket_instance = MagicMock()
        mock_socket_instance.settimeout = MagicMock()
        mock_socket.return_value = mock_socket_instance

        device = TestTCPTimingDevice('127.0.0.1', 23)
        result = device.connect()

        self.assertTrue(result)
        mock_socket_instance.settimeout.assert_called_with(device._timeoutSecs)
        mock_socket_instance.connect.assert_called_with(('127.0.0.1', 23))
        self.assertTrue(device._connected)

    @patch('TimingDevices.TCPTimingDevice.socket.socket')
    def test_connect_timeout_error(self, mock_socket):
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect.side_effect = socket.timeout
        mock_socket.return_value = mock_socket_instance

        device = TestTCPTimingDevice('127.0.0.1', 23)
        result = device.connect()

        self.assertFalse(result)
        self.assertFalse(device._connected)

    @patch('TimingDevices.TCPTimingDevice.socket.socket')
    def test_connect_general_exception(self, mock_socket):
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect.side_effect = Exception("General error")
        mock_socket.return_value = mock_socket_instance

        device = TestTCPTimingDevice('127.0.0.1', 23)
        result = device.connect()

        self.assertFalse(result)
        self.assertFalse(device._connected)

if __name__ == '__main__':
    unittest.main()
