import inspect
import logging
import logging.config
import yaml
import os
from typing import Any, cast

from YamlUtil import merge_yaml


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
    if level <= Log.TRACE:
      filename, lineNumber, functionName, stack = self.findCaller()
      caller = '{}:{}#{}'.format(filename, lineNumber, functionName)
      msg = '{}: {}'.format(caller, msg)

    return super().log(level, msg, *args, **kwargs)

  def entering(self, msg: object, *args: tuple[Any, ...], **kwargs: Any) -> None:
    return self.log(Log.ENTER, msg, *args, **kwargs)

  def exiting(self, msg: object, *args: tuple[Any, ...], **kwargs: Any) -> None:
    return self.log(Log.EXIT, msg, *args, **kwargs)

  def trace(self, msg: object, *args, **kwargs) -> None:
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


with open('logging.yml', 'r') as logConfig:
  config = yaml.safe_load(logConfig.read())
if os.getenv('DEBUG', 'False').lower() in ('true', '1', 't') or True:
  with open('logging.debug.yml', 'r') as logConfig:
    debugConfig = yaml.safe_load(logConfig.read())
    config = merge_yaml(config, debugConfig)

logging.config.dictConfig(config)
