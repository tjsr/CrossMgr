import sys
import traceback
from queue import Queue
from types import TracebackType
from typing import Type

import Utils

class LogQueue:
	_q: Queue
	_loggerName: str

	@property
	def name(self) -> str:
		return self._loggerName

	def __init__(self, q: Queue, name: str):
		self._q = q
		self._loggerName = name

	def q(self, category: str, message: str):
		self._q.put((category, message))
		Utils.writeLog('{}: {}: {}'.format(self._loggerName, category, message))

	def error(self, category: str, message: str):
		self._q.put((category, message))
		Utils.writeLog('ERROR ({}): {}: {}'.format(self._loggerName, category, message))

	def exception(self,
	              category: str,
	              e: Exception,
	              exc_info: tuple[Type[BaseException], BaseException, TracebackType] | tuple[None, None, None] | None
	) -> list[str]:
		ex: list[str]
		if exc_info is None:
			exc_info = sys.exc_info()

		eType, eValue, eTraceback = exc_info
		ex = traceback.format_exception(eType, e, eTraceback)

		for d in ex:
			for line in d.split('\n'):
				self._q.put((category, line))

		return ex
