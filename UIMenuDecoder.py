from typing import Callable, cast, Any, Optional

import wx

import AlienImport
import ChipReader
import ImpinjImport
import IpicoImport
import JChipImport
import JChipSetup
import Log
import Model
import OrionImport
import RaceResultImport
import Utils
from ChipReader import ChipReaderType
from TimingDevices import TimingDevice
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
		return ChipReader.chipReaderCur

	@property
	def log ( self ) -> Log.CrossMgrLogger:
		if self.__log is None:
			self.__log = Log.getLogger('CrossMgr').getChild('UIMenuDecoder')
		return self.__log

	def __init__(self, *args, **kwargs):
		super(UIMenuDecoder, self).__init__(*args, **kwargs)
		self.chipMenu = wx.Menu()

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

	@property
	def HasChipReader(self) -> bool:
		return self.chipReader is not None and self.chipReader.chipReaderType is not None

	def hasActiveDecoderThread(self) -> bool:
		return self.HasChipReader and not self.isDecoderConnected() and not self.chipReader.IsListening()

	def canStopDecoderThread(self) -> bool:
		# Don't check 'HasChipReader' here as if the type is None but we still have a listener thread, it won't
		# allow us to stop it.
		return self.chipReader is not None and self.chipReader.IsListening()

	def addDecoderMenuItems(self) -> None:
		etdOnlyHintString: str = _("For electronic timing decoders only")
		options: (str, CommandEventCallback, Callable[[], bool]) = [
			("Disconnect from decoder.", self.menuDecoderDisconnect, self.isDecoderConnected),
			("&Connect/reconnect to decoder.", self.menuDecoderReconnect,
			 lambda: self.isRaceLoaded() and self.hasActiveDecoderThread()),
			("Start decoder read thread.", self.menuStartDecoderThread,
			 lambda: self.isRaceLoaded() and self.hasActiveDecoderThread()),
			("Stop decoder read thread.", self.menuStopDecoderThread, self.canStopDecoderThread),
			("Send 'start' command", self.menuDecoderSendStartRead, self.isDecoderConnected),
			("Send 'stop' command", self.menuDecoderSendStopRead, self.isDecoderConnected),
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
		cr: ChipReader.ChipReader = self.chipReader
		if cr is not None:
			if not cr.IsListening():
				return False

			cd: TimingDevice = cr.CurrentDecoder()
			if cd is None and cr:
				return True
			elif isinstance(cd, TCPTimingDevice):
				return cd.connected()
		return False

	def isRaceLoaded(self) -> bool:
		return Model.race is not None

	def isRaceRunning(self) -> bool:
		return self.isRaceLoaded() and Model.race.isRunning()

	def isMenuItemEnabled(self, item_id: int) -> bool:
		is_enabled = True

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
		log.trace(f'Enabling or disabling menu items for menu {menu.GetTitle()}')
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

	def menuJChip(self, _event: wx.CommandEvent) -> None:
		if not Model.race:
			Utils.MessageOK(self, _("You must have a valid race.  Open or New a race first."), _("No Valid Race"),
			                iconMask=wx.ICON_ERROR)
			return

		if self._commit_callback is not None:
			self._commit_callback()

		if Model.race.isRunning():
			Utils.MessageOK(self, _('Cannot perform RFID setup while race is running.'), _('Cannot Perform RFID Setup'),
			                iconMask=wx.ICON_ERROR)
			return
		with JChipSetup.JChipSetupDialog(self) as dlg:
			dlg.ShowModal()

	def checkDecoderIsUltra(self, requires_current: bool = True) -> Optional[UltraDecoder]:
		if self.chipReader is None:
			Utils.MessageOK(self, _("No Chip Reader"), _("No Chip Reader"), iconMask=wx.ICON_ERROR)
			return False

		# TODO: Fix this to be a reference to the Ultra value not a magic number
		if not (self.chipReader.chipReaderType == ChipReader.ChipReader.Ultra):
			Utils.MessageOK(self, _("Currently only supprted for Ultra decoders"), _("No Ultra Decoder"),
			                iconMask=wx.ICON_ERROR)
			return False

		ultraDecoder: UltraDecoder | None = self.chipReader.CurrentDecoder()
		if requires_current and ultraDecoder is None:
			Utils.MessageOK(self, _("No Ultra decoder thread currently running."), _("No Ultra Decoder"),
			                iconMask=wx.ICON_ERROR)
			return False

		return True

	def DecoderMenuItemError(self, e: Exception, function_name: str) -> None:
		logging.critical('Error calling decoder action: %s', exc_info=e)
		Utils.MessageOK(self, "Critical error interacting with decoder.  See log.", _("Error in {function_name}"),
		                iconMask=wx.ICON_ERROR)

	def safeDecoderMenuCall(self, function: CommandEventCallback, *args, **kwargs) -> None:
		try:
			function(*args[1:], **kwargs)
		except Exception as e:
			self.DecoderMenuItemError(e, function.__name__)

	@logCall
	def menuDecoderDisconnect(self, _event: wx.CommandEvent) -> None:
		if ultraDecoder := self.checkDecoderIsUltra(True) is None:
			return

		ultraDecoder.disconnect()

	@logCall
	async def menuDecoderReconnect(self, _event: wx.CommandEvent) -> None:
		if ultraDecoder := self.checkDecoderIsUltra(True) is None:
			return
		await ultraDecoder.reconnect()

	@logCall
	def menuStartDecoderThread(self, _event: wx.CommandEvent) -> None:
		# Do we actually care if it's an Ultra decoder here?
		if not self.checkDecoderIsUltra(False):
			return
		self.log.todo('Requires host, port, and start time')
		self.chipReader.StartListener()

	def menuStopDecoderThread(self, _event: wx.CommandEvent) -> None:
		if not self.checkDecoderIsUltra(False):
			return
		self.chipReader.StopListener()

	@logCall
	def menuDecoderSendStartRead(self, _event: wx.CommandEvent) -> None:
		if ultraDecoder := self.checkDecoderIsUltra(True) is None:
			return
		ultraDecoder.begin_reading()

	@logCall
	def menuDecoderSendStopRead(self, _event: wx.CommandEvent) -> None:
		if ultraDecoder := self.checkDecoderIsUltra(True) is None:
			return
		ultraDecoder.stop_reading()

	@logCall
	def menuShowReplay(self, _event: wx.CommandEvent) -> None:
		if ultraDecoder := self.checkDecoderIsUltra(True) is None:
			return

		with DecoderReplayDialog.DecoderReplayDialog(self) as dlg:
			result = dlg.ShowModal()
			if result == wx.ID_OK:
				start = dlg.StartTime
				end = dlg.EndTime

				if start is None or end is None:
					self.log.error('Invalid start or end time')
					return

				self.log.info('Requesting replay from decoder of %s to %s', start, end)
				try:
					ultraDecoder.send_records_from_time(start_time=start, end_time=end)
				except Exception as e:
					self.DecoderMenuItemError(e, __name__)
			elif result == DecoderReplayDialog.ID_INVALID_START:
				self.log.error('Invalid start time')
			elif result == DecoderReplayDialog.ID_INVALID_END:
				self.log.error('Invalid end time')

	def menuDecoderStopRewind(self, _event: wx.CommandEvent) -> None:
		if ultraDecoder := self.checkDecoderIsUltra(True) is None:
			return

		if ultraDecoder.connected():
			ultraDecoder.stop_rewind()
		else:
			self.log.warning('stop_rewind command not sent - Decoder is not connected')

	def sendUltraCommand(self, command: wx.CommandEvent):
		if not self.chipReader:
			Utils.MessageOK(self, _('No Chip Reader'), _('No Chip Reader'), iconMask=wx.ICON_ERROR)
			return
		if not self.chipReader.isUltra():
			Utils.MessageOK(self, _('Ultra Decoder Only'), _('Ultra Decoder Only'), iconMask=wx.ICON_ERROR)
			return
		self.chipReader.sendUltraCommand(command)

	def menuJChipImport(self, event: wx.CommandEvent):
		correct, reason = JChipSetup.CheckExcelLink()
		explain = '{}\n\n{}'.format(
			_('You must have a valid Excel sheet with associated tags and Bib numbers.'),
			_('See documentation for details.')
		)
		if not correct:
			Utils.MessageOK(self, '{}\n\n    {}\n\n{}'.format(_('Problems with Excel sheet.'), reason, explain),
			                title=_('Excel Link Problem'), iconMask=wx.ICON_ERROR)
			return

		with JChipImport.JChipImportDialog(self) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def menuAlienImport(self, event):
		correct, reason = JChipSetup.CheckExcelLink()
		explain = '{}\n\n{}'.format(
			_('You must have a valid Excel sheet with associated tags and Bib numbers.'),
			_('See documentation for details.')
		)
		if not correct:
			Utils.MessageOK(self, '{}\n\n    {}\n\n{}'.format(_('Problems with Excel sheet.'), reason, explain),
			                title=_('Excel Link Problem'), iconMask=wx.ICON_ERROR)
			return

		with AlienImport.AlienImportDialog(self) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def menuIpicoImport(self, event):
		correct, reason = JChipSetup.CheckExcelLink()
		explain = '{}\n\n{}'.format(
			_('You must have a valid Excel sheet with associated tags and Bib numbers.'),
			_('See documentation for details.')
		)
		if not correct:
			Utils.MessageOK(self, '{}\n\n    {}\n\n{}'.format(_('Problems with Excel sheet.'), reason, explain),
			                title=_('Excel Link Problem'), iconMask=wx.ICON_ERROR)
			return

		with IpicoImport.IpicoImportDialog(self) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def menuImpinjImport(self, event):
		correct, reason = JChipSetup.CheckExcelLink()
		explain = '{}\n\n{}'.format(
			_('You must have a valid Excel sheet with associated tags and Bib numbers.'),
			_('See documentation for details.')
		)
		if not correct:
			Utils.MessageOK(self, '{}\n\n    {}\n\n{}'.format(_('Problems with Excel sheet.'), reason, explain),
			                title=_('Excel Link Problem'), iconMask=wx.ICON_ERROR)
			return

		with ImpinjImport.ImpinjImportDialog(self) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def menuOrionImport(self, event):
		correct, reason = JChipSetup.CheckExcelLink()
		explain = '{}\n\n{}'.format(
			_('You must have a valid Excel sheet with associated tags and Bib numbers.'),
			_('See documentation for details.')
		)
		if not correct:
			Utils.MessageOK(self, '{}\n\n    {}\n\n{}'.format(_('Problems with Excel sheet.'), reason, explain),
			                title=_('Excel Link Problem'), iconMask=wx.ICON_ERROR)
			return

		with OrionImport.OrionImportDialog(self) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def menuRaceResultImport(self, event):
		correct, reason = JChipSetup.CheckExcelLink()
		explain = '{}\n\n{}'.format(
			_('You must have a valid Excel sheet with associated tags and Bib numbers.'),
			_('See documentation for details.')
		)
		if not correct:
			Utils.MessageOK(self, '{}\n\n    {}\n\n{}'.format(_('Problems with Excel sheet.'), reason, explain),
			                title=_('Excel Link Problem'), iconMask=wx.ICON_ERROR)
			return

		with RaceResultImport.RaceResultImportDialog(self) as dlg:
			dlg.ShowModal()
		wx.CallAfter(self.refresh)

	def refresh(self):
		self.enableOrDisableMenuItems()
