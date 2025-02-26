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
		return self._time

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
		updatedValue = event.GetString()

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
		if not isinstance(updatedDate, wx.DateTime):
			self.log.warning('Date returned from event was not a wx.DateTime object')
			self.fire_datetime_invalid()
			return
		modified_time = self._time.replace(
			year=updatedDate.GetYear(),
			month=updatedDate.GetMonth(),
			day=updatedDate.GetDay()
		)

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


ID_INVALID_END = wx.NewIdRef(count=1)
ID_INVALID_START = wx.NewIdRef(count=1)

class DecoderReplayDialog(wx.Dialog):
	log = logging.getLogger('CrossMgr.DecoderReplayDialog')
	_gridSizer: wx.GridBagSizer
	_isUtc: bool = False
	_utc_checkbox: wx.CheckBox = None

	CONTROL_BORDER_SIZE:int = 4

	@property
	def StartTime(self) -> datetime.datetime:
		return self.__local_or_utc_time(self._startField.DateTime)

	@property
	def EndTime(self) -> datetime.datetime:
		return self.__local_or_utc_time(self._endField.DateTime)

	@property
	def IsUtc(self) -> bool:
		return self._isUtc

	@staticmethod
	def __first_hour_before(hour: int = None, start_times: [int,] = (8, 10, 12, 14, 16)) -> int:
		if hour is None:
			hour = datetime.datetime.now().hour

		for start_time in start_times:
			if start_time >= hour:
				return start_time
		return start_times[0]

	def __get_default_time_window(self, minutes: int = 120) -> (datetime.datetime, datetime.datetime):
		start_time_hour = self.__first_hour_before()
		start_time = datetime.datetime.now().replace(hour=start_time_hour, minute=0, second=0, microsecond=0, tzinfo=self.__get_selected_tz())
		end_time = start_time + datetime.timedelta(minutes=minutes)

		return start_time, end_time

	def __init__(self, parent: wx.Window = None, id = wx.ID_ANY):
		super().__init__(parent=parent, id=id, title=_("Resend data from decoder"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self._boxSizer = wx.BoxSizer(wx.VERTICAL)
		self._gridSizer = wx.GridBagSizer(vgap=4, hgap=4)
		border = self.CONTROL_BORDER_SIZE

		_timeZone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo

		start_time, end_time = self.__get_default_time_window()
		self._startField = self.addDateTimeField(_("Start Time"), start_time, 0)
		self._endField = self.addDateTimeField(_("End Time"), end_time, 1)
		self._startField.Bind(EVT_DATETIME_CHANGE, self.onSetStartDateTime)
		self._endField.Bind(EVT_DATETIME_CHANGE, self.onSetEndDateTime)

		self._boxSizer.Add(self._gridSizer, 1, wx.EXPAND | wx.ALL, border)

		# btnSizer = self.CreateStdDialogButtonSizer( wx.OK|wx.CANCEL )
		self.__create_utc_checkbox()

		btnSizer = self.CreateButtonSizer( wx.OK|wx.CANCEL )

		self.Bind( wx.EVT_BUTTON, self.onOK, id=wx.ID_OK )
		self.Bind( wx.EVT_BUTTON, self.onCancel, id=wx.ID_CANCEL )
		if btnSizer:
			self._boxSizer.Add(btnSizer, 0, wx.EXPAND | wx.ALL, border)

		self._gridSizer.Fit(self)
		self._boxSizer.Fit(self)
		self.SetSizer(self._boxSizer)

	def __create_utc_checkbox(self, border: int = CONTROL_BORDER_SIZE) -> wx.CheckBox:
		tz = self.__get_system_tz()
		tz_name = tz.tzname(None)

		# The size of the dialog will expand to fit the checkbox text here.
		utc_checkbox = wx.CheckBox(self, label=f'UTC Time instead of local time\n({tz_name})')
		utc_checkbox.SetValue(self._isUtc)
		self._boxSizer.Add(utc_checkbox, 0, wx.CENTER | wx.WRAPSIZER_DEFAULT_FLAGS, border)
		self.Bind(wx.EVT_CHECKBOX, self.__on_utc_checkbox, utc_checkbox)

		self._utc_checkbox = utc_checkbox
		return self._utc_checkbox

	def __get_selected_tz(self) -> datetime.tzinfo:
		if self.IsUtc:
			return datetime.timezone.utc
		else:
			return self.__get_system_tz()

	def __local_or_utc_time(self, dt: datetime.datetime, isUtc: bool = None) -> datetime.datetime:
		if isUtc is True:
			tz = datetime.timezone.utc
		else:
			tz = self.__get_selected_tz()

		return datetime.datetime.fromtimestamp(dt.timestamp(), tz)

	def __date_from_iso(self, value: str, isUtc: bool = None) -> datetime.datetime:
		if isUtc is None:
			isUtc = self.IsUtc
		# Append 'Z' if it's a UTC time, else ISO-8601 parses as local time when not specified *except on Apple*.
		isoTzFlag = 'Z' if isUtc else ''
		return datetime.datetime.fromisoformat(value + isoTzFlag)

	def __on_utc_checkbox(self, event: wx.CommandEvent) -> None:
		self._isUtc = self._utc_checkbox.IsChecked()

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
		if self._startField.DateTime is None:
			self.EndModal(ID_INVALID_START)
		elif self._endField.DateTime is None:
			self.EndModal(ID_INVALID_END)
		else:
			wx.CallAfter(Utils.refresh)
			self.EndModal(wx.ID_OK)

	def onCancel(self, event):
		self.EndModal(wx.ID_CANCEL)

	@staticmethod
	def __get_system_tz() -> datetime.tzinfo:
		return datetime.datetime.now().astimezone().tzinfo

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
		res = dlg.ShowModal()
		if res == wx.ID_OK:
			print(dlg.StartTime, dlg.EndTime)

