import os
import random
import time
from typing import Type

import wx
from wx import adv as adv

import Utils


class CrossMgrTipProvider(adv.TipProvider):
	def __init__(self, tips_filename: int | str | bytes | os.PathLike[str] | os.PathLike[bytes], tipNo = None):
		try:
			with open(tips_filename, encoding='utf8') as f:
				tipStr = f.read()
		except Exception:
			tipStr = ''

		self.tips = [t.strip() for t in tipStr.split('\n')]
		self.tips = [t for t in self.tips if t and not t.startswith('#')]
		self.iTips = list( range(len(self.tips)) )
		random.shuffle( self.iTips )

		self.tipNo = tipNo if tipNo is not None else (int(round(time.time() * 1000)) * 13) % (len(self.tips) - 1)
		super().__init__( self.tipNo )

	def GetCurrentTip( self ) -> Type[adv.TipProvider.GetCurrentTip]:
		if self.tipNo < 0 or self.tipNo >= len(self.tips):
			self.tipNo = 0
		return self.iTips[self.tipNo]

	def GetTip( self ) -> Type[adv.TipProvider.GetTip]:
		if not self.tips:
			return _('No tips available.')
		tip = self.tips[self.GetCurrentTip()].replace(r'\n','\n').replace(r'\t','    ')
		self.tipNo += 1
		return tip

	def PreprocessTip( self, tip: str ) -> str:
		return tip

	def DeleteFirstTip( self ) -> None:
		if self.tips:
			self.tips.pop(0)

	def __len__( self ) -> int:
		return len(self.tips)

	@property
	def CurrentTip( self ) -> Type[GetCurrentTip]:
		return self.GetCurrentTip()

	@property
	def Tip( self ) -> Type[GetTip]:
		return self.GetTip()


def ShowTipAtStartup():
	mainWin = Utils.getMainWin()
	if mainWin and not mainWin.config.ReadBool('showTipAtStartup', True):
		return

	tipFile = os.path.join(Utils.getImageFolder(), "tips.txt")
	try:
		provider = CrossMgrTipProvider(tipFile)
		showTipAtStartup = wx.adv.ShowTip( None, provider, True )
		if mainWin:
			mainWin.config.WriteBool('showTipAtStartup', showTipAtStartup)
			mainWin.config.Flush()
	except Exception as e:
		pass
