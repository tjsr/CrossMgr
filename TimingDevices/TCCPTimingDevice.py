import socket
from abc import abstractmethod
from logging import Logger

from SocketUtils import socketReadDelimited


class TCPTimingDevice:
	DEFAULT_PORT: int = 23
	DEFAULT_HOST: str = '127.0.0.1'

	_host: str = DEFAULT_HOST
	_port: int = DEFAULT_PORT
	_s: socket.socket | None = None
	_timeoutSecs: int = 5

	def __init__(self, host: str, port: int ):
		self._host = host
		self._port = port

	@abstractmethod
	def getLog(self) -> Logger:
		pass

	@abstractmethod
	def getDeviceType(self) -> str:
		pass

	def connect(self) -> bool:
		log = self.getLog()
		device = self.getDeviceType()
		# TODO: wrap with _ for internationalisation
		description = f'{device} decoder at {self._host}:{self._port}'

		# -----------------------------------------------------------------------------------------------------
		log.info(_('Attempting to connect to {}').format(description))
		try:
			self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self._s.settimeout(self._timeoutSecs)
			self._s.connect((self._host, self._port))

			self.on_connect()
		except Exception as e:
			log.exception('{}: {}'.format(_('Connection failed to {}'), description, e))
			self._s = None
			return False

		log.info(_('Successfully connected to {}').format(description))
		return True

	def disconnect(self) -> bool:
		if self._s is not None:
			try:
				self._s.shutdown(socket.SHUT_RDWR)
				self._s.close()
				return True
			except Exception:
				pass
		return False

	@abstractmethod
	def on_connect(self):
		pass

	def connected(self) -> bool:
		return self._s is not None

	def get_message_buffer(self) -> str|None:
		if self._s is None:
			return ''
		try:
			buffer: str = socketReadDelimited(self._s)
			return buffer
		except socket.timeout as ex:
			self.on_socket_timeout(ex)

		return None

	@abstractmethod
	def on_socket_timeout(self, ex: socket.timeout):
		pass

