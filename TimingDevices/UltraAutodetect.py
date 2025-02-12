import socket

import Utils
from SocketUtils import socketReadDelimited

DEFAULT_PORT = 23
#DEFAULT_PORT = 8642
DEFAULT_HOST = '127.0.0.1'		# Port to connect to the Ultra receiver.

def iterAdjacentIPs():
	""" Return ip addresses adjacent to the computer in an attempt to find the reader. """
	ip = [int(i) for i in Utils.GetDefaultHost().split('.')]
	ipPrefix = '.'.join('{}'.format(v) for v in ip[:-1])
	ipLast = ip[-1]

	count = 0
	j = 0
	while 1:
		j = -j if j > 0 else -j + 1

		ipTest = ipLast + j
		if 0 <= ipTest < 256:
			yield '{}.{}'.format(ipPrefix, ipTest)
			count += 1
			if count >= 8:
				break


def AutoDetect(ultraPort=DEFAULT_PORT, callback=None):
	for ultraHost in iterAdjacentIPs():
		if callback:
			if not callback('{}:{}'.format(ultraHost, ultraPort)):
				return None

		try:
			s: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.settimeout(0.5)
			s.connect((ultraHost, ultraPort))
		except Exception:
			continue

		try:
			buffer: str = socketReadDelimited(s)
		except Exception:
			continue

		try:
			s.close()
		except Exception:
			pass

		if buffer.startswith('Connected'):
			return ultraHost

	return None