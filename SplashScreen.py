import os

import wx
from wx import adv as adv

import Utils
import Version


def ShowSplashScreen( nextCallback = None ):
	bitmap = wx.Bitmap( os.path.join(Utils.getImageFolder(), 'CrossMgrSplash.png'), wx.BITMAP_TYPE_PNG )

	# Write in the version number into the bitmap.
	w, h = bitmap.GetSize()
	dc = wx.MemoryDC()
	dc.SelectObject( bitmap )
	fontHeight = h//10
	dc.SetFont( wx.Font( (0,fontHeight), wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL ) )
	v = Version.AppVerName.split('-',2)
	yText = int(h * 0.44)
	for i, v in enumerate(Version.AppVerName.split('-',2)):
		dc.DrawText( v.replace('CrossMgr','Version'), w // 20, yText + i*fontHeight )

	dc.SelectObject( wx.NullBitmap )

	showSeconds = 2.5
	ss = adv.SplashScreen(bitmap, adv.SPLASH_CENTRE_ON_SCREEN|adv.SPLASH_TIMEOUT, int(showSeconds*1000), None)
	ss.Show()
	if nextCallback:
		def cb( event ):
			event.Skip()
			ss.Hide()
			wx.CallAfter( nextCallback )

		ss.Bind( wx.EVT_CLOSE, cb )
