import wx
from wx import Size, Point


class SimulateDialog(wx.Dialog):
	ID_MASS_START = 0
	ID_TIME_TRIAL = 1

	def __init__(
			self, parent: wx.Frame, fName: str, id: int=wx.ID_ANY, title: str=_('Simulation'), size: Size=wx.DefaultSize, pos: Point=wx.DefaultPosition,
			style: int=wx.DEFAULT_DIALOG_STYLE, name: str='dialog'
	):
		super().__init__(parent, id, title, pos, size, style, name)

		explain = '\n'.join([
			_('Simulate Race'),
			'',
			_('This will simulate a race using randomly generated data.'),
			_("It is a good illustration of CrossMgr's functionality with real time data."),
			'',
			_('The simulation takes about 8 minutes.'),
			_('In the Time Trial simulation, riders start on 15 second intervals.'),
			'',
			'{}:\n    "{}"'.format(_('The race will be written to'), fName),
			'',
			_('Continue?'),
		])

		# Now continue with the normal construction of the dialog
		# contents
		sizer = wx.BoxSizer(wx.VERTICAL)

		label = wx.StaticText(self, label=explain)
		sizer.Add(label, flag=wx.ALIGN_CENTRE | wx.ALL, border=4)

		btnsizer = wx.BoxSizer(wx.HORIZONTAL)

		# ---------------------------------------------------------------
		box = wx.StaticBox(self, label=_('Mass Start Race'))
		sboxsizer = wx.StaticBoxSizer(box, wx.VERTICAL)

		btn = wx.Button(self, label=_('Start'))
		btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(self.ID_MASS_START))
		btn.SetDefault()
		sboxsizer.Add(btn, flag=wx.ALL, border=4)

		self.rfidResetStartClockOnFirstTag = wx.CheckBox(self, label=_('Simulate RFID Reset Start Clock on First Read'))
		sboxsizer.Add(self.rfidResetStartClockOnFirstTag, flag=wx.ALL, border=4)

		btnsizer.Add(sboxsizer, flag=wx.ALL, border=4)

		# ---------------------------------------------------------------

		box = wx.StaticBox(self, label=_('Time Trial'))
		sboxsizer = wx.StaticBoxSizer(box, wx.VERTICAL)

		btn = wx.Button(self, label=_('Start'))
		btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(self.ID_TIME_TRIAL))
		sboxsizer.Add(btn, flag=wx.ALL, border=4)

		btnsizer.Add(sboxsizer, flag=wx.ALL, border=4)

		# ---------------------------------------------------------------
		sizer.Add(btnsizer, 0, wx.ALL, 8)

		# ---------------------------------------------------------------
		btn = wx.Button(self, wx.ID_CANCEL)
		sizer.Add(btn, flag=wx.ALIGN_RIGHT | wx.ALL, border=8)

		self.SetSizer(sizer)
		sizer.Fit(self)
