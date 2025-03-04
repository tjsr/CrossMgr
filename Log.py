import faulthandler
import hashlib
import inspect
import logging
import logging.config
import os
import shutil
import sys

from typing import Any, cast

import yaml

from FileUtils import config_search
from YamlUtil import merge_yaml

log_base_dir = None

def eprint(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)

def set_log_base_dir(base_dir: str) -> str:
  global log_base_dir
  if not os.path.exists(base_dir):
    os.makedirs(base_dir)
    if not os.access(base_dir, os.W_OK):
      err_message = f"Write permission denied for directory: {base_dir}"
      eprint(err_message)
      raise PermissionError(err_message)
    print(f'Log directory created at {base_dir}')
  log_base_dir = base_dir
  return log_base_dir

set_log_base_dir(os.path.join(os.path.expanduser('~'), 'CrossMgr'))

def get_log_path(log_name: str) -> str:
  return os.path.abspath(os.path.join(log_base_dir, log_name))

class Log:
  TRACE = 6
  ENTER = 4
  EXIT = 2
  RETURN = 3
  APPLICATION_END = 5
  TODO = logging.WARNING + 5


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

  def todo(self, msg: object, *args: tuple[Any, ...], **kwargs: Any) -> None:
    return self.log(Log.TODO, 'TODO: ' + str(msg), *args, **kwargs)

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

def getLogBaseDir() -> str:
  return os.path.join(os.path.expanduser('~'), 'Documents', 'CrossMgr')

file_handlers = {}


def make_safe_key(file_path: str) -> str:
  return hashlib.md5(file_path.encode()).hexdigest()

def owned_file_handler(filename: str | os.PathLike[str], mode: str= 'a', encoding: str | None=None, owner=None):
  log_path = get_log_path(filename)
  log_parent = os.path.dirname(log_path)
  if not os.path.exists(log_parent):
    os.makedirs(log_parent)
    if not os.access(log_parent, os.W_OK):
      err_message = f"Write permission denied for directory: {log_parent}"
      print(err_message)
      raise PermissionError(err_message)
    print(f'Log directory created at {log_parent}')

  if owner:
    shutil.chown(log_path, *owner)

  open(log_path, 'a').close()
  if not os.access(log_path, os.W_OK):
    err_message = f"Write permission denied for log file: {log_path}"
    eprint(err_message)
    raise PermissionError(err_message)

  key = make_safe_key(log_path)
  if not key in file_handlers or file_handlers[key] is None:
    file_handlers[key] = logging.FileHandler(log_path, mode, encoding)

  return file_handlers[key]

def load_logging_config_files() -> None:
  logConfigPath = config_search('logging.yml')

  if logConfigPath is None:
    eprint('No logging configuration file found in any search pat h.')
    return

  with open(logConfigPath, 'r') as logConfig:
    config = yaml.safe_load(logConfig.read())
    logConfig.close()

    if os.getenv('DEBUG', 'False').lower() in ('true', '1', 't') or True:
      debugLogConfigPath = config_search('logging.debug.yml')
      if debugLogConfigPath is not None:
        with open(debugLogConfigPath, 'r') as debugLogConfig:
          debugConfig = yaml.safe_load(debugLogConfig.read())

          config = merge_yaml(config, debugConfig)
          debugLogConfig.close()

    logging.config.dictConfig(config)

try:
  if __name__ == '__main__':
    faulthandler.enable()
  load_logging_config_files()
except Exception as e:
  eprint('Error loading logging configuration: {}'.format(e))
  if e.__cause__ is not None and isinstance(e.__cause__, FileNotFoundError):
    eprint('FileNotFound: {}'.format(e.__cause__))
except BaseException as be:
  eprint('Error loading logging configuration: {}'.format(be))
  if be.__cause__ is not None:
    eprint('Cause: {}'.format(e.__cause__))

if __name__ == '__main__':
  logging.getLogger().info("Test")
