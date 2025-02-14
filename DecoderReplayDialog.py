import datetime
import logging

import wx
import wx.adv
import wx.lib.newevent

from wx.adv import DatePickerCtrl

import Utils
from HighPrecisionTimeEdit import HighPrecisionTimeEdit

DateTimeChangeEvent, EVT_DATETIME_CHANGE = wx.lib.newevent.NewEvent()

class DateTimeControlPair(wx.EvtHandler):
	log = logging.getLogger('CrossMgr.DateTimeControlPair')
	_time: datetime.datetime
	_parent: wx.Dialog

	def __init__(self, parent: wx.Dialog, labelText: str, time: datetime.datetime = datetime.datetime.now(), size=(127, -1), min_size=(127, -1)):
		super().__init__()
		self._time = time

		self._parent = parent
		self._label = wx.StaticText(parent, label = labelText)
		self._dateEdit = DatePickerCtrl(parent, style = wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY )
		self._dateEdit.SetMinSize(min_size)
		self._dateEdit.SetValue(self._time)
		self._dateEdit.Bind( wx.adv.EVT_DATE_CHANGED, self.onSetDate )

		self._timeEdit = HighPrecisionTimeEdit( parent, display_milliseconds=False, seconds=time, size=size )
		self._timeEdit.SetMinSize(min_size)
		self._timeEdit.SetValue(self._time)
		self._timeEdit.Bind(wx.EVT_TEXT, self.onSetTime)

		self.Bind( wx.EVT_TEXT, self.onSetTime )

	@property
	def DateEdit(self) -> DatePickerCtrl:
		return self._dateEdit

	@property
	def TimeEdit(self) -> HighPrecisionTimeEdit:
		return self._timeEdit

	@property
	def Label(self) -> wx.StaticText:
		return self._label

	@property
	def DateTime(self) -> datetime.datetime:
		#
		# date = self._dateEdit.GetValue()
		# seconds = self._timeEdit.GetSeconds()
		return self._time

		# if seconds is None:
		# 	modified_time = self.get_updated_time(seconds)


	def get_updated_time(self, seconds: float) -> datetime.datetime:
		microseconds = int((seconds - int(seconds)) * 1000000)
		minutes = int(seconds) / 60
		remainingSeconds = int(seconds % 60)
		hours = int(minutes / 60)
		minutes = int(minutes) % 60

		return self._time.replace(hour=hours, minute=minutes, second=remainingSeconds, microsecond=microseconds)

	def onSetTime(self, event: wx.CommandEvent) -> None:
		self.log.info('Set time event')
		eventObject = event.GetEventObject()
		if not isinstance(eventObject, HighPrecisionTimeEdit):
			self.fire_datetime_invalid()
			return
		updatedValue = event.String

		timeEditor: HighPrecisionTimeEdit = eventObject
		wx.CallAfter(timeEditor.Validate)
		validator = timeEditor.GetValidator()
		if not validator.ValidateTimeFormat(updatedValue):
			self.fire_datetime_invalid()
			return

		self.log.debug('Time editor value: %s', timeEditor.GetValue())

		seconds = timeEditor.GetSeconds()
		if seconds is None:
			self.fire_datetime_invalid()
			return

		modified_time = self.get_updated_time(seconds)
		self._time = modified_time
		self.fire_datetime_changed(modified_time)

	def onSetDate(self, event: wx.CommandEvent) -> None:
		eventObject = event.GetEventObject()
		if not isinstance(eventObject, DatePickerCtrl):
			self.fire_datetime_invalid()
			return
		picker: DatePickerCtrl = eventObject
		updatedDate = picker.GetValue()
		assert isinstance(updatedDate, datetime.date)
		modified_time = self._time.replace(year=updatedDate.year, month=updatedDate.month, day=updatedDate.day)

		if self._timeEdit.Validate():
			self._time = modified_time
			self.fire_datetime_changed(modified_time)
		else:
			self.fire_datetime_invalid()

	def fire_datetime_changed(self, modified_time: datetime.datetime) -> None:
		dateTimeChanged = DateTimeChangeEvent(datetime=modified_time)
		dateTimeChanged.SetEventObject(self)
		self.log.info(f'Firing date time changed event for { modified_time}')
		wx.PostEvent(self, dateTimeChanged)

	def fire_datetime_invalid(self) -> None:
		dateTimeChanged = DateTimeChangeEvent(datetime=None)
		dateTimeChanged.SetEventObject(self)
		self.log.info(f'Firing date time changed to an invalid valid')
		wx.PostEvent(self, dateTimeChanged)


ID_INVALID_END = wx.NewId()
ID_INVALID_START = wx.NewId()

class DecoderReplayDialog(wx.Dialog):
	log = logging.getLogger('CrossMgr.DecoderReplayDialog')
	_gridSizer: wx.GridBagSizer

	def __init__(self, parent = None, id = wx.ID_ANY):
		super().__init__(parent=parent, id=id, title=_("Resend data from decoder"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self._boxSizer = wx.BoxSizer(wx.VERTICAL)
		self._gridSizer = wx.GridBagSizer(vgap=4, hgap=4)
		border = 4

		startTime = datetime.datetime.fromisoformat("2025-02-03 18:58:00")
		endTime = datetime.datetime.fromisoformat("2025-02-03 22:00:00")
		self._startField = self.addDateTimeField("Start Time", startTime, 0)
		self._endField = self.addDateTimeField("End Time", endTime, 1)
		self._startField.Bind(EVT_DATETIME_CHANGE, self.onSetStartDateTime)
		self._endField.Bind(EVT_DATETIME_CHANGE, self.onSetEndDateTime)

		self._boxSizer.Add(self._gridSizer, 1, wx.EXPAND | wx.ALL, border)

		# btnSizer = self.CreateStdDialogButtonSizer( wx.OK|wx.CANCEL )
		btnSizer = self.CreateButtonSizer( wx.OK|wx.CANCEL )

		self.Bind( wx.EVT_BUTTON, self.onOK, id=wx.ID_OK )
		self.Bind( wx.EVT_BUTTON, self.onCancel, id=wx.ID_CANCEL )
		if btnSizer:
			self._boxSizer.Add(btnSizer, 0, wx.EXPAND | wx.ALL, border)

		self._gridSizer.Fit(self)
		self._boxSizer.Fit(self)
		self.SetSizer(self._boxSizer)

	def addDateTimeField(self, labelText: str, time: datetime.datetime, row: int) -> DateTimeControlPair:
		dateTimePair = DateTimeControlPair(self, labelText, time)

		self._gridSizer.Add(dateTimePair.Label, pos=(row, 0), span=(1, 1), border = 4, flag=wx.ALIGN_RIGHT | wx.LEFT | wx.BOTTOM | wx.TOP | wx.ALIGN_CENTRE_VERTICAL)
		self._gridSizer.Add(dateTimePair.DateEdit, pos=(row, 1), span=(1, 1), border = 4, flag=wx.BOTTOM | wx.TOP | wx.ALIGN_LEFT)
		self._gridSizer.Add(dateTimePair.TimeEdit, pos=(row, 2), span=(1, 1), border = 4, flag=wx.RIGHT | wx.BOTTOM | wx.TOP | wx.ALIGN_LEFT)

		return dateTimePair

	def onSetStartDateTime(self, event: DateTimeChangeEvent) -> None:
		self.log.debug('Date changed to %s', event.datetime)

	def onSetEndDateTime(self, event: DateTimeChangeEvent) -> None:
		self.log.debug('Date changed to %s', event.datetime)

	def onOK(self, event):
		start = self._startField.DateTime
		end = self._endField.DateTime
		if self._startField.DateTime is None:
			self.EndModal(ID_INVALID_START)
		elif self._endField.DateTime is None:
			self.EndModal(ID_INVALID_END)
		else:
			wx.CallAfter(Utils.refresh)
			self.EndModal(wx.ID_OK)

	def onCancel(self, event):
		self.EndModal(wx.ID_CANCEL)

	@property
	def StartTime(self) -> datetime.datetime:
		return self._startField.DateTime

	@property
	def EndTime(self) -> datetime.datetime:
		return self._endField.DateTime

global mainWin

if __name__ == '__main__':
	# time = '10:00:001'
	# time_format = '%H:%M:%S'
	# # time_format = '%H:%M:%S.%f'
	# res = datetime.datetime.strptime(time, time_format)
	# print(res)

	#sys.exit()
	app = wx.App(False)
	mainWin = wx.Frame(None, title="CrossMan", size=(600, 400))
	mainWin.Show()
	with DecoderReplayDialog() as dlg:
		dlg.ShowModal()

