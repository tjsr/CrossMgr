import os
import random
import time

import wx
from wx import adv as adv

import Utils


class MyTipProvider( adv.TipProvider ):
	def __init__( self, fname, tipNo = None ):
		try:
			with open(fname, encoding='utf8') as f:
				tipStr = f.read()
		except Exception:
			tipStr = ''

		self.tips = [t.strip() for t in tipStr.split('\n')]
		self.tips = [t for t in self.tips if t and not t.startswith('#')]
		self.iTips = list( range(len(self.tips)) )
		random.shuffle( self.iTips )

		self.tipNo = tipNo if tipNo is not None else (int(round(time.time() * 1000)) * 13) % (len(self.tips) - 1)
		super().__init__( self.tipNo )

	def GetCurrentTip( self ):
		if self.tipNo < 0 or self.tipNo >= len(self.tips):
			self.tipNo = 0
		return self.iTips[self.tipNo]

	def GetTip( self ):
		if not self.tips:
			return _('No tips available.')
		tip = self.tips[self.GetCurrentTip()].replace(r'\n','\n').replace(r'\t','    ')
		self.tipNo += 1
		return tip

	def PreprocessTip( self, tip ):
		return tip

	def DeleteFirstTip( self ):
		if self.tips:
			self.tips.pop(0)

	def __len__( self ):
		return len(self.tips)

	@property
	def CurrentTip( self ):
		return self.GetCurrentTip()

	@property
	def Tip( self ):
		return self.GetTip()


def ShowTipAtStartup():
	mainWin = Utils.getMainWin()
	if mainWin and not mainWin.config.ReadBool('showTipAtStartup', True):
		return

	tipFile = os.path.join(Utils.getImageFolder(), "tips.txt")
	try:
		provider = MyTipProvider(tipFile)
		showTipAtStartup = wx.adv.ShowTip( None, provider, True )
		if mainWin:
			mainWin.config.WriteBool('showTipAtStartup', showTipAtStartup)
			mainWin.config.Flush()
	except Exception as e:
		pass
