import os

import wx
from wx import StandardPaths


def getHomeDir( appName='CrossMgr' ) -> str:
	sp: StandardPaths = wx.StandardPaths.Get()
	home_dir: str = sp.GetUserDataDir()
	try:
		if os.path.basename(home_dir) == '.{}'.format(appName):
			home_dir = os.path.join( os.path.dirname(home_dir), '.{}App'.format(appName) )
	except Exception:
		pass
	if not os.path.exists(home_dir):
		os.makedirs( home_dir )
	return home_dir

def getDocumentsDir() -> str:
	sp: StandardPaths = wx.StandardPaths.Get()
	dd: str = sp.GetDocumentsDir()
	if not os.path.exists(dd):
		os.makedirs( dd )
	return dd

# Returns the owning path of the file - but only if they exist when if_exists is True.
# When if_exists is false, it will return the given path of the file.
def get_path_from_file(path: str | os.PathLike, if_exists: bool = False) -> str | None:
	if path is None:
		return None

	if isinstance(path, os.PathLike):
		return get_path_from_file(str(path))

	file_dir = os.path.split(path)
	if len(file_dir) > 0:
		if (not if_exists) or (if_exists and os.path.exists(file_dir[0])):
			return file_dir[0]

	return None

# Returns the full file path or owning path of the file - but only if they exist when if_exists is True.
# When if_exists is false, it will return the given path of the file or full filename with path.
def get_file_or_path(file_path: str | os.PathLike, if_exists: bool = False) -> str | None:
	if file_path is None:
		return None

	if isinstance(file_path, os.PathLike):
		return get_file_or_path(str(file_path))

	if if_exists and os.path.exists(file_path):
		return file_path
	elif not if_exists:
		return file_path

	file_dir = get_path_from_file(file_path, if_exists)
	return file_dir
