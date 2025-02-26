import os

import wx
from wx import StandardPaths


def getHomeDir( appName='CrossMgr' ) -> str:
	sp: StandardPaths = wx.StandardPaths.Get()
	homedir: str = sp.GetUserDataDir()
	try:
		if os.path.basename(homedir) == '.{}'.format(appName):
			homedir = os.path.join( os.path.dirname(homedir), '.{}App'.format(appName) )
	except Exception:
		pass
	if not os.path.exists(homedir):
		os.makedirs( homedir )
	return homedir

def getDocumentsDir() -> str:
	sp: StandardPaths = wx.StandardPaths.Get()
	dd: str = sp.GetDocumentsDir()
	if not os.path.exists(dd):
		os.makedirs( dd )
	return dd
