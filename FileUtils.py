import os
from typing import List, Callable


def get_file_from_directory(file_name: str, dir: str) -> str|None:
  file_path = os.path.join(dir, file_name)
  if os.path.isfile(file_path):
    return file_path
  return None


def get_project_base_path() -> str:
  return os.path.abspath(os.path.dirname(__file__))


def get_user_home_directory() -> str:
  return os.path.expanduser('~')


def find_file(file_name: str, search_functions: List[Callable[[], str|None]]) -> str|None:
  for func in search_functions:
    directory = func()
    file_path = os.path.join(directory, file_name)
    if os.path.isfile(file_path):
      return file_path
  return None


default_search_functions = [
	os.getcwd,
	get_project_base_path,
	get_user_home_directory
]

def config_search(file_name: str) -> str:
  config_path = find_file(file_name, default_search_functions)
  return config_path

