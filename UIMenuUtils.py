import wx


def AppendMenuItemBitmap( menu, id, name, help, bitmap ):
	mi = wx.MenuItem( menu, id, name, help )
	mi.SetBitmap( bitmap )
	menu.Append( mi )
	return mi
