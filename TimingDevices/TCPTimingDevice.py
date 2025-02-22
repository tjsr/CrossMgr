import datetime
import socket
import time
from abc import abstractmethod

import Log
from Log import CrossMgrLogger
from SocketUtils import socketReadDelimited, socketSendMessage
from TimingDevices import ThreadUtils
from TimingDevices.TimingDevice import TimingDeviceConnectMessage


class TCPTimingDevice:
	DEFAULT_PORT: int = 23
	DEFAULT_HOST: str = '127.0.0.1'
	LOG_TYPE_TCP_EVENT = 'tcpevent'
	CONNECTION_RETRY_TIME_INTERVAL: int = 5

	_host: str = DEFAULT_HOST
	_port: int = DEFAULT_PORT
	_s: socket.socket | None = None
	_connected: bool = False
	_timeoutSecs: int = 5
	_log: CrossMgrLogger | None = None
	__unsuccessfulConnectionAttempts: int = 0
	__maximumReconnectionAttempts: int = 5
	__attempt_reconnect_after: datetime.datetime | None = datetime.datetime.fromtimestamp(0)

	def __init__(self, host: str, port: int ):
		self._host = host
		self._port = port
		self._s = None
		self._connected = False
		self.__reset_reconnect_backoff()
		self.__maximumReconnectionAttempts = 5

	def getLog(self, child:str = None) -> CrossMgrLogger:
		log = self._log if self._log is not None else Log.getLogger(name='TCPTimingDevice')

		if child is not None:
			log = log.getChild(child)
		return log

	def setLog(self, log: CrossMgrLogger) -> None:
		self._log = log

	@abstractmethod
	def getDeviceType(self) -> str:
		pass

	def __spawn_on_socket_connect(self):
		ThreadUtils.spawn_event(handler=self.on_socket_connect)

	def connect(self) -> bool:
		log = self.getLog(child=TCPTimingDevice.LOG_TYPE_TCP_EVENT)
		device = self.getDeviceType()
		# TODO: wrap with _ for internationalisation
		description = f'{device} decoder at {self._host}:{self._port}'

		# -----------------------------------------------------------------------------------------------------
		msg = _('Attempting to connect to {}').format(description)
		log.info(msg)
		try:
			self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self._s.settimeout(self._timeoutSecs)
			self._s.connect((self._host, self._port))
			self.__reset_reconnect_backoff()
			self.__unsuccessfulConnectionAttempts = 0
			self._connected = True

			# Wait for the connection to be established.
			time.sleep(2)

			self.__spawn_on_socket_connect()
		except TimeoutError as e:
			errDesc = _('Connection failed to {}: {}').format(description, e.__class__.__name__)
			log.error(errDesc)
			self._s = None
			self._connected = False
			self.__set_reconnect_backoff()
			return False
		except Exception as e:
			log.exception('{}: {}'.format(_('Unknown error connecting to {}'), description, e))
			self._s = None
			self._connected = False
			self.__set_reconnect_backoff()
			return False

		log.info(_('Successfully connected to {}').format(description))
		return True

	@abstractmethod
	async def _wait_until_ready(self) -> bool:
		pass

	async def disconnect(self, allow_reconnect: bool = False) -> bool:
		await self._wait_until_ready()

		self.__unsuccessfulConnectionAttempts = 0
		if allow_reconnect is True:
			self.__attempt_reconnect_after = datetime.datetime.now() + datetime.timedelta(seconds=TCPTimingDevice.CONNECTION_RETRY_TIME_INTERVAL)
		else:
			self.__unsuccessfulConnectionAttempts = 0
			self.__attempt_reconnect_after = None

		if self._s is not None:
			try:
				self.getLog(child=TCPTimingDevice.LOG_TYPE_TCP_EVENT).info(_('Disconnecting from {}').format(self.getDeviceType()))
				self._s.shutdown(socket.SHUT_RDWR)
				self._s.close()
				self._s = None
				self._connected = False
				return True
			except Exception:
				self._s = None
				self._connected = False
				pass
		self._connected = False
		return False

	@abstractmethod
	async def on_socket_connect(self):
		pass

	def connected(self) -> bool:
		return self._s is not None and self._connected is True

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

	@abstractmethod
	def on_connect(self, msg: TimingDeviceConnectMessage) -> bool:
		pass

	def send_data(self, payload: str) -> None:
		# cmd = payload.split(';', 1)[0]
		log = self.getLog(child='output')
		log.info(payload)
		try:
			socketSendMessage(self._s, payload)
		except Exception as e:
			log.exception(msg='{}: {}'.format(payload, _('Failed sending data')), exc_info=e)
			raise e

	@property
	def UnsuccessfulConnectionAttempts(self) -> int:
		return self.__unsuccessfulConnectionAttempts

	@property
	def WaitForReconnect(self) -> bool:
		if self.__unsuccessfulConnectionAttempts >= self.__maximumReconnectionAttempts:
			return False
		if not self.connected() and not (datetime.datetime.now() > self.__attempt_reconnect_after):
			return True
		return False

	def __set_reconnect_backoff(self):
		self.__unsuccessfulConnectionAttempts += 1
		if self.__unsuccessfulConnectionAttempts >= self.__maximumReconnectionAttempts:
			self.__attempt_reconnect_after = None
			return

		delta = TCPTimingDevice.CONNECTION_RETRY_TIME_INTERVAL
		if self.__unsuccessfulConnectionAttempts == 3:
			delta += TCPTimingDevice.CONNECTION_RETRY_TIME_INTERVAL
		if self.__unsuccessfulConnectionAttempts == 5:
			delta += (TCPTimingDevice.CONNECTION_RETRY_TIME_INTERVAL * 4)

		self.__attempt_reconnect_after = datetime.datetime.now() + datetime.timedelta(seconds=delta)

	def __reset_reconnect_backoff(self):
		self.__attempt_reconnect_after = datetime.datetime.fromtimestamp(0)
		self.__unsuccessfulConnectionAttempts = 0

	@property
	def NextReconnectTime(self) -> datetime.datetime:
		return self.__attempt_reconnect_after

	@property
	def ReconnectAttemptCount(self) -> int:
		return self.__unsuccessfulConnectionAttempts

	@property
	def MaximumReconnectionAttempts(self) -> int:
		return self.__maximumReconnectionAttempts

	@MaximumReconnectionAttempts.setter
	def MaximumReconnectionAttempts(self, value: int):
		self.__maximumReconnectionAttempts = value

	@property
	def ShouldReconnect(self) -> bool:
		if self.__maximumReconnectionAttempts is not None and self.__unsuccessfulConnectionAttempts >= self.__maximumReconnectionAttempts:
			return False

		if self.__attempt_reconnect_after is None:
			return False

		return True

