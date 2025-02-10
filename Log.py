import inspect
import logging
import os
import sys
import threading
from typing import Any

lock = threading.Lock()

formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s] %(message)s')
methodFormatter = logging.Formatter('%(asctime)s %(name)s:%(funcName)s [%(levelname)s] %(message)s')
traceFormatter = logging.Formatter('%(asctime)s %(name)s@%(filename)s:%(lineno)d:%(funcName)s [%(levelname)s] %(message)s')
# Create a handler that writes log messages to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

errHandler = logging.StreamHandler(sys.stderr)
errHandler.setLevel(logging.ERROR)

# Create a formatter and set it for the handler
handler.setFormatter(formatter)
errHandler.setFormatter(formatter)

class Log:
	TRACE = 6
	ENTER = 4
	EXIT = 2
	RETURN = 3
	APPLICATION_END = 5

class CrossMgrLogger(logging.Logger):
  def __init__(self, name: str, level: int | str = logging.NOTSET) -> None:
    super().__init__(name, level)

	def log(self, level: int, msg: object, *args: tuple[Any, ...], **kwargs: Any) -> None:
		if level == Log.ENTER < logging.DEBUG:
			filename, lineNumber, functionName, stack = self.findCaller()
			caller = '{}:{}#{}'.format(filename, lineNumber, functionName)
			updatedMsg = '{}: {}'.format(caller, msg)
			return super().log(level, updatedMsg, *args, **kwargs)

		return super().log(level, msg, *args, **kwargs)

	def entering(self, msg: object, *args: tuple[Any, ...], **kwargs: Any) -> None:
		return self.log(Log.ENTER, msg, *args, **kwargs)

	def exiting(self, msg: object, *args: tuple[Any, ...], **kwargs: Any) -> None:
		return self.log(Log.EXIT, msg, *args, **kwargs)

	def trace(self, msg: object, *args: tuple[Any, ...], **kwargs: Any) -> None:
		return self.log(Log.TRACE, msg, *args, **kwargs)

	def returning(self, msg: object, *args: tuple[Any, ...], **kwargs: Any) -> None:
		return self.log(Log.RETURN, msg, *args, **kwargs)

	def exitApp(self, msg: object = 'Application exiting', *args: tuple[Any, ...], **kwargs: Any) -> None:
		return self.log(Log.APPLICATION_END, msg, *args, **kwargs)

logging.setLoggerClass(CrossMgrLogger)

def getLogger(name: str = None) -> CrossMgrLogger:
  if name is None:
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    logger_name = module.__name__ if module else '__main__'
  else:
    logger_name = name

  log = logging.getLogger(name=logger_name)

  return cast(CrossMgrLogger, log)



