from datetime import datetime, timezone
from typing import Callable, cast, Any, Optional

import wx

import AlienImport
import DecoderReplayDialog
import ImpinjImport
import IpicoImport
import JChipImport
import JChipSetup
import Log
import Model
import OrionImport
import RaceResultImport
import Utils
from Utils import logCall
from ChipReader import ChipReaderType, ChipReader
import ChipReader as ChipReaderModule
from TimingDevices import TimingDevice, ThreadUtils
from TimingDevices.TCPTimingDevice import TCPTimingDevice
from TimingDevices.UltraTimingDevice import UltraDecoder
from UIMenuUtils import AppendMenuItemBitmap

CommandEventCallback = Callable[[wx.CommandEvent, Any, Any], None]

class UIMenuDecoder(wx.Menu):
	__log: Log.CrossMgrLogger = Log.getLogger(name='CrossMgr').getChild('UIMenuDecoder')
	__menuItemEnabledState: {int, Callable[[], bool]} = {}
	_commit_callback: Callable[[], None] | None = None

	@property
	def chipReader( self ) -> ChipReaderType:
		return ChipReaderModule.chipReaderCur

	@property
	def log ( self ) -> Log.CrossMgrLogger:
		if self.__log is None:
			self.__log = Log.getLogger('CrossMgr').getChild('UIMenuDecoder')
		return self.__log

	@property
	def _Decoder(self) -> TimingDevice:
		if self.chipReader is None:
			return None
		if not isinstance(self.chipReader, ChipReader):
			return None

		cr: ChipReader = cast(ChipReader, self.chipReader)
		return cr.CurrentDecoder() if cr.CurrentDecoder is not None and cr.chipReaderType == ChipReader.Ultra else None

	@property
	def HasChipReader(self) -> bool:
		if self.chipReader is not None:
			return False

		if not isinstance(self.chipReader, ChipReader):
			return False

		if cast(ChipReader, self.chipReader).chipReaderType is None:
			return False

		return True

	def setCommitCallback(self, callback: Callable[[], None]) -> None:
		self._commit_callback = callback

	def __init__(self, parent: wx.Window, *args, **kwargs):
		super(UIMenuDecoder, self).__init__(*args, **kwargs)
		self._parent = parent

		item = AppendMenuItemBitmap(self, wx.ID_ANY, _("Chip Reader &Setup..."),
		                            _("Configure and Test the Chip Reader"), Utils.GetPngBitmap('rfid-signal.png'))
		self.Bind(wx.EVT_MENU, self.menuJChip, item)

		self.AppendSeparator()

		self.addDecoderMenuItems()
		try:
			self.enableOrDisableMenuItems()
		except Exception as e:
			self.log.critical(f'Failed while enabling or disabling menu items: {e}')

		self.AppendSeparator()

		item = self.Append(wx.ID_ANY, _("Import JChip File..."), _("JChip Formatted File"))
		self.Bind(wx.EVT_MENU, self.menuJChipImport, item)

		item = self.Append(wx.ID_ANY, _("Import Impinj File..."), _("Impinj Formatted File"))
		self.Bind(wx.EVT_MENU, self.menuImpinjImport, item)

		item = self.Append(wx.ID_ANY, _("Import Ipico File..."), _("Ipico Formatted File"))
		self.Bind(wx.EVT_MENU, self.menuIpicoImport, item)

		item = self.Append(wx.ID_ANY, _("Import Alien File..."), _("Alien Formatted File"))
		self.Bind(wx.EVT_MENU, self.menuAlienImport, item)

		item = self.Append(wx.ID_ANY, _("Import Orion File..."), _("Orion Formatted File"))
		self.Bind(wx.EVT_MENU, self.menuOrionImport, item)

		item = self.Append(wx.ID_ANY, _("Import RaceResult File..."), _("RaceResult File"))
		self.Bind(wx.EVT_MENU, self.menuRaceResultImport, item)

	def __excel_link_check(self) -> bool:
		correct, reason = JChipSetup.CheckExcelLink()
		explain = '{}\n\n{}'.format(
			_('You must have a valid Excel sheet with associated tags and Bib numbers.'),
			_('See documentation for details.')
		)
		if not correct:
			Utils.MessageOK(self._parent, '{}\n\n    {}\n\n{}'.format(_('Problems with Excel sheet.'), reason, explain),
			                title=_('Excel Link Problem'), iconMask=wx.ICON_ERROR)
			return False
		return True

	def __has_listening_chip_reader(self) -> bool:
		return self.chipReader is not None and self.chipReader.IsListening()

	def hasActiveDecoderThread(self) -> bool:
		return self.HasChipReader and not self.isDecoderConnected() and not self.chipReader.IsListening()

	def canStopDecoderThread(self) -> bool:
		# Don't check 'HasChipReader' here as if the type is None but we still have a listener thread, it won't
		# allow us to stop it.
		return self.__has_listening_chip_reader()

	def addDecoderMenuItems(self) -> None:
		etdOnlyHintString: str = _("For electronic timing decoders only")
		options: (str, CommandEventCallback, Callable[[], bool]) = [
			("Disconnect from decoder.", self.menuDecoderDisconnect, self.isDecoderConnected),
			("&Connect/reconnect to decoder.", self.menuDecoderReconnect,
			 lambda: self.isRaceLoaded() and self.hasActiveDecoderThread()),
			("Start decoder read thread.", self.menuStartDecoderThread,
			 lambda: self.isRaceRunning() and not self.hasActiveDecoderThread()),
			("Stop decoder read thread.", self.menuStopDecoderThread, self.canStopDecoderThread),
			("Send 'start' command", self.menuDecoderSendStartRead, self.isDecoderConnected),
			("Send 'stop' command", self.menuDecoderSendStopRead, self.isDecoderConnected),
			("Send 'time' command", self.menuDecoderSendTime, self.isDecoderConnected),
			("Send 'get all settings' command", self.menuDecoderGetSettings, self.isDecoderConnected),
			("Re-send data...", self.menuShowReplay, self.isDecoderConnected),
			("Stop replaying data.", self.menuDecoderStopRewind, self.isDecoderConnected),
		]
		if self.__menuItemEnabledState is None:
			self.__menuItemEnabledState: {int, Callable[[], bool]} = {}

		for text, handler, enableCondition in options:
			handlerCall = lambda event, function=handler, *args, **kwargs: self.safeDecoderMenuCall(function, event=event)
			self.addMenuItem(self, text, etdOnlyHintString, handlerCall,
				enableCondition=enableCondition)

	def addMenuItem(self, menu: wx.Menu, text: str, help_text: str, handler: CommandEventCallback,
	                enableCondition: callable = None) -> wx.MenuItem:
		item = wx.MenuItem(menu, wx.ID_ANY, text, help_text)
		menu.Append(item)
		self.Bind(wx.EVT_MENU, handler, item)

		if enableCondition is not None and callable(enableCondition):
			self.__menuItemEnabledState[item.GetId()] = enableCondition

		return item

	def isDecoderConnected(self) -> bool:
		cr: ChipReaderType = self.chipReader
		if cr is not None:
			if not cr.IsListening or cr.IsListening() is not True:
				return False

			cd: TimingDevice = self._Decoder
			if cd is None and cr:
				return True
			elif isinstance(cd, TCPTimingDevice):
				tcp_device = cast(TCPTimingDevice, cd)
				return tcp_device.connected()
		return False

	@staticmethod
	def isRaceLoaded() -> bool:
		return Model.race is not None

	def isRaceRunning(self) -> bool:
		return self.isRaceLoaded() and Model.race.isRunning()

	def isMenuItemEnabled(self, item_id: int) -> bool:
		check = self.__menuItemEnabledState[item_id]
		if check is None or not callable(check):
			return True

		is_enabled = check()
		return is_enabled

	def find_menuItem_from_menu(self, needle_id: int) -> Optional[wx.MenuItem]:
		for item in self.GetMenuItems():
			if item.GetId() == needle_id:
				return item
		return None

	def enableOrDisableMenuItems(self) -> None:
		log = self.log.getChild('enableOrDisableMenuItems')
		log.trace(f'Enabling or disabling menu items for menu {self.GetTitle()}')
		for item_id, check in self.__menuItemEnabledState.items():
			try:
				is_enabled = self.isMenuItemEnabled(item_id)
				menuItem: wx.MenuItem = self.find_menuItem_from_menu(item_id)
				if menuItem is None:
					log.warning(f'Item {item_id} was in menu for enable check but UI control not found.')
					continue
				menuItem.Enable(enable=is_enabled)
			except Exception as e:
				log.exception(f'Error enabling menu item {item_id}', exc_info=e)

	def menuJChip(self, event: wx.CommandEvent) -> None:
		if not Model.race:
			Utils.MessageOK(self._parent, _("You must have a valid race.  Open or New a race first."), _("No Valid Race"),
			                iconMask=wx.ICON_ERROR)
			return

		if self._commit_callback is not None:
			self._commit_callback()

		if Model.race.isRunning():
			Utils.MessageOK(self._parent, _('Cannot perform RFID setup while race is running.'), _('Cannot Perform RFID Setup'),
			                iconMask=wx.ICON_ERROR)
			return
		with JChipSetup.JChipSetupDialog(self._parent) as dlg:
			dlg.ShowModal()

	def checkDecoderIsUltra(self, requires_current: bool = True) -> Optional[UltraDecoder]:
		if self.chipReader is None:
			Utils.MessageOK(self._parent, _("No Chip Reader"), _("No Chip Reader"), iconMask=wx.ICON_ERROR)
			return None

		if not isinstance(self.chipReader, ChipReader):
			return None

		cr: ChipReader = cast(ChipReader, self.chipReader)
		if cr.chipReaderType is None and Model.getRace().chipReaderType is not None:
			self.log.warning('Chip reader type for chip reader is not set but a value is set on model. Resetting.')
			cr.reset(Model.getRace().chipReaderType)

		if not (cr.chipReaderType == ChipReader.Ultra):
			Utils.MessageOK(self, _("Currently only supported for Ultra decoders"), _("No Ultra Decoder"),
			                iconMask=wx.ICON_ERROR)
			return None

		# requires_current here means that we need to have a current decoder thread running.
		# Where requires_current is false, it just needs to be configured as being an Ultra decoder,
		# but doesn't require an active thread.
		if Model.getRace().chipReaderType is None:
			self.log.warning('Chip reader type for race config is not set on model.')
		ultraDecoder: UltraDecoder | None = cr.CurrentDecoder()
		if requires_current and ultraDecoder is None:
			Utils.MessageOK(self._parent, _("No Ultra decoder thread currently running."), _("No Ultra Decoder"),
			                iconMask=wx.ICON_ERROR)
			return None

		return ultraDecoder

	def DecoderMenuItemError(self, e: Exception, function_name: str) -> None:
		self.log.critical('Error calling decoder action: %s', exc_info=e)
		Utils.MessageOK(self._parent, "Critical error interacting with decoder.  See log.", _(f"Error in {function_name}"),
		                iconMask=wx.ICON_ERROR)

	def safeDecoderMenuCall(self, function: CommandEventCallback, *args, **kwargs) -> None:
		try:
			function(*args[1:], **kwargs)
		except Exception as e:
			self.DecoderMenuItemError(e, function.__name__)

	@logCall
	def menuDecoderDisconnect(self, event: wx.CommandEvent) -> None:
		ultraDecoder: UltraDecoder | None = self.checkDecoderIsUltra(True)
		if ultraDecoder is None:
			return

		ThreadUtils.spawn_event(handler=ultraDecoder.disconnect)

	@logCall
	def menuDecoderReconnect(self, event: wx.CommandEvent) -> None:
		ultraDecoder: UltraDecoder | None = self.checkDecoderIsUltra(True)
		if ultraDecoder is None:
			return
		ThreadUtils.spawn_event(handler=ultraDecoder.reconnect)

	@logCall
	def menuStartDecoderThread(self, event: wx.CommandEvent) -> None:
		if not self.isRaceRunning():
			Utils.MessageOK(self._parent, _("Race must be active and running to start a decoder thread."),
			_("No Active race"), iconMask=wx.ICON_ERROR)

		# Do we actually care if it's an Ultra decoder here?
		if not self.checkDecoderIsUltra(False):
			return
		self.log.todo('Requires host, port, and start time')

		error_message = None
		if Model.getRace() is None:
			error_message = "No active race"

		if Model.race.chipReaderIpAddr is None or Model.race.chipReaderIpAddr.strip() == '':
			error_message = "Chip reader host not valid"

		if Model.race.chipReaderPort is None or Model.race.chipReaderPort <= 0:
			error_message = "Chip reader port not valid"

		if error_message is not None:
			Utils.MessageOK(self._parent, _(f'{error_message} - can not start decoder thread'),
			                _(f"Error starting decoder"),
			                iconMask=wx.ICON_ERROR)
			return

		if self.chipReader is None:
			self.log.warning('Chip reader has not been created - need to recreate.')

		try:
			self.chipReader.StartListener(startTime=datetime.now(), host=Model.race.chipReaderIpAddr.strip(), port=Model.race.chipReaderPort)
		except Exception as e:
			readerType = (cast(ChipReader, self.chipReader)).chipReaderType
			if readerType is not None:
				readerType = f'{ChipReader.Choices[readerType]} ({readerType})'
			self.log.exception(f'Exception while trying to start chipReader listener: type={readerType}', exc_info=e)
			self.DecoderMenuItemError(e, __name__)

	def menuStopDecoderThread(self, event: wx.CommandEvent) -> None:
		if not self.checkDecoderIsUltra(False):
			return
		self.chipReader.StopListener()

	@logCall
	def menuDecoderSendStartRead(self, event: wx.CommandEvent) -> None:
		ultraDecoder: UltraDecoder | None = self.checkDecoderIsUltra(True)
		if ultraDecoder is None:
			return
		ultraDecoder.begin_reading()

	@logCall
	def menuDecoderSendStopRead(self, event: wx.CommandEvent) -> None:
		ultraDecoder: UltraDecoder | None = self.checkDecoderIsUltra(True)
		if ultraDecoder is None:
			return
		ultraDecoder.stop_reading()

	@logCall
	def menuDecoderSendTime(self, event: wx.CommandEvent) -> None:
		ultraDecoder: UltraDecoder | None = self.checkDecoderIsUltra(True)
		if ultraDecoder is None:
			return
		ultraDecoder.get_time()

	@logCall
	def menuDecoderGetSettings(self, event: wx.CommandEvent) -> None:
		ultraDecoder: UltraDecoder | None = self.checkDecoderIsUltra(True)
		if ultraDecoder is None:
			return
		ultraDecoder.get_settings()

	@logCall
	def menuShowReplay(self, event: wx.CommandEvent) -> None:
		ultraDecoder: UltraDecoder | None = self.checkDecoderIsUltra(True)
		if ultraDecoder is None:
			return

		with DecoderReplayDialog.DecoderReplayDialog(parent=self._parent) as dlg:
			result = dlg.ShowModal()
			if result == wx.ID_OK:
				start = dlg.StartTime
				end = dlg.EndTime

				if start is None or end is None:
					self.log.error('Invalid start or end time')
					return

				if start.tzinfo is not None and start.tzinfo != timezone.utc:
					local_start = start
					start = start.astimezone(timezone.utc)
					start_str = f'{start}/{local_start} ({local_start.tzinfo})'
				else:
					start_str = f'{start}'

				if end.tzinfo is not None and end.tzinfo != timezone.utc:
					local_end = end
					end = end.astimezone(timezone.utc)
					end_str = f'{end}/{local_end} ({local_end.tzinfo})'
				else:
					end_str = f'{end}'

				self.log.info(f'Requesting replay from decoder of {start_str} to {end_str}')
				try:
					ultraDecoder.send_records_from_time(start_time=start, end_time=end)
				except Exception as e:
					self.DecoderMenuItemError(e, __name__)
			elif result == DecoderReplayDialog.ID_INVALID_START:
				self.log.error('Invalid start time')
			elif result == DecoderReplayDialog.ID_INVALID_END:
				self.log.error('Invalid end time')

	def menuDecoderStopRewind(self, event: wx.CommandEvent) -> None:
		ultraDecoder: UltraDecoder | None = self.checkDecoderIsUltra(True)
		if ultraDecoder is None:
			return

		if ultraDecoder.connected():
			ultraDecoder.stop_rewind()
		else:
			self.log.warning('stop_rewind command not sent - Decoder is not connected')

	def menuJChipImport(self, event: wx.CommandEvent) -> None:
		if not self.__excel_link_check():
			return

		with JChipImport.JChipImportDialog(self._parent) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def menuAlienImport(self, event: wx.CommandEvent) -> None:
		if not self.__excel_link_check():
			return

		with AlienImport.AlienImportDialog(self._parent) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def menuIpicoImport(self, event: wx.CommandEvent) -> None:
		if not self.__excel_link_check():
			return

		with IpicoImport.IpicoImportDialog(self._parent) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def menuImpinjImport(self, event: wx.CommandEvent) -> None:
		if not self.__excel_link_check():
			return

		with ImpinjImport.ImpinjImportDialog(self._parent) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def menuOrionImport(self, event: wx.CommandEvent) -> None:
		if not self.__excel_link_check():
			return

		with OrionImport.OrionImportDialog(self._parent) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def menuRaceResultImport(self, event: wx.CommandEvent) -> None:
		if not self.__excel_link_check():
			return

		with RaceResultImport.RaceResultImportDialog(self._parent) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def refresh(self):
		self.enableOrDisableMenuItems()
