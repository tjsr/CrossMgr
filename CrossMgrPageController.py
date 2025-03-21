import logging
from abc import abstractmethod, ABC
from typing import Any

import wx
from wx.lib.agw import flatnotebook

import Log
import Model
from Actions import Actions
from Announcer import Announcer
from Categories import Categories
from FileDrop import FileDrop
from Gantt import Gantt
from GapChart import GapChart
from HistogramPanel import HistogramPanel
from History import History
from LapCounter import LapCounter
from Primes import Primes
from Prizes import Prizes
from Properties import Properties
from Pulled import Pulled
from RaceAnimation import RaceAnimation
from Recommendations import Recommendations
from Record import Record
from ResultNote import ResultNote
from Results import Results
from RiderDetail import RiderDetail
from TeamResults import TeamResults


class AbstractPageController(ABC):
	__log: logging.Logger = None
	_notebook: flatnotebook.FlatNotebook
	_pages: list[Any] = None
	__file_drop: FileDrop
	__refresh_windows: callable

	attrClassName: list[(str, type, str)]
	attrWindowSet: set[str]

	def addPage(self, page: Any, name: str) -> None:
		self._notebook.AddPage(page, name)
		self._pages.append(page)

	def __init__(self, notebook: flatnotebook.FlatNotebook, refresh_windows: callable):
		self._notebook = notebook
		self.__refresh_windows = refresh_windows
		self._notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onPageChanging)
		self.__file_drop = FileDrop()	# Create a file drop target for all the main pages.

		self.attrClassName = []
		self.__create_pages()

		self.attrWindowSet = {'results', 'history', 'gantt', 'raceAnimation', 'gapChart', 'announcer', 'lapCounter',
		                      'teamResults'}

	@property
	def log(self) -> logging.Logger:
		if self.__log is None:
			self.__log = Log.getLogger()
		return self.__log

	@property
	def window_classes(self) -> list[(str, type, str)]:
		res: list[(str, type, str)] = []
		for attr, cls, name in self.attrClassName:
			if attr not in self.attrWindowSet:
				continue
			res.append((attr, cls, name))
		return res

	@abstractmethod
	def _get_page_types(self) -> list[(str, type, str)]:
		pass

	@abstractmethod
	def _alias_local_pages(self) -> None:
		pass

	@property
	def pages(self) -> list[Any]:
		return self._pages

	@staticmethod
	def __ensure_lowercase_keys(page_types: list[(str, type, str)]) -> list[(str, type, str)]:
		return [(alias.lower(), cls, label) for alias, cls, label in page_types]

	def __create_pages(self) -> None:
		# Add all the pages to the notebook.
		self._pages = []
		page_types = self._get_page_types()
		page_types = self.__ensure_lowercase_keys(page_types)
		self.attrClassName.extend(page_types)

		for index, (alias, class_name, label_text) in enumerate(self.attrClassName):
			setattr(self, alias, class_name(self._notebook))
			getattr(self, alias).SetDropTarget(self.__file_drop)
			self.addPage(getattr(self, alias), '{}. {}'.format(index + 1, label_text))
			setattr(self, 'i' + alias[0].upper() + alias[1:] + 'Page', index)

		self._alias_local_pages()

	def callPageCommit( self, i: int | None = None ) -> None:
		if i is None:
			i = self._notebook.GetSelection()

		if i < 0:
			return
		elif i >= len(self._pages):
			self.log.warning(f'Page commit was called with out-of-range index {i}.')
			return
		elif not self._pages[i]:
			self.log.warning(f'Page commit was called with None page at index {i}.')
			return
		try:
			self._pages[i].commit()
		except (AttributeError, IndexError) as ex:
			self.log.exception(msg=f'Exception while commiting page {self._pages[i].__class__.__name__}', exc_info=ex)
			pass
		self.__refresh_windows()

	def callPageRefresh(self, i: int | None = None, refresh_all: bool = False) -> None:
		if i is None:
			i = self._notebook.GetSelection()

		try:
			page = self._pages[i]
		except IndexError:
			return

		try:
			if refresh_all is True:
				page.refreshAll()
			else:
				page.refresh()
		except AttributeError:
			pass

	def getCurrentPage(self):
		return self._pages[self._notebook.GetSelection()]

	def get_page_label(self, index: int | None = None) -> str:
		if index is None:
			index = self._notebook.GetSelection()
		label = self.attrClassName[index][2]
		return label

	def isShowingPage(self, page) -> bool:
		# TODO: Type on page param
		return page == self._pages[self._notebook.GetSelection()]

	def showPage(self, iPage: int, commitFirst=True) -> None:
		if commitFirst:
			self.callPageCommit(self._notebook.GetSelection())

		self.callPageRefresh(iPage)
		self._notebook.SetSelection(iPage)
		self._pages[self._notebook.GetSelection()].Layout()

	def get_page_index_by_id(self, page_id: str) -> int | None:
		page_id = page_id.replace(' ', '').lower()
		for i, (id, cls, label) in enumerate(self.attrClassName):
			if id == page_id:
				return i
		return None

	def get_page_index_by_name(self, name: str) -> int | None:
		name = name.replace(' ', '').lower()
		for i, (id, cls, label) in enumerate(self.attrClassName):
			if label.replace(' ', '').lower() == name:
				return i
		return None

	def get_page_by_id(self, page_id: str, required: bool = True) -> Any | None:
		index = self.get_page_index_by_id(page_id)
		if index is not None:
			return self._pages[index]

		if required:
			self.log.error(f'Page with id {page_id} not found.')
			raise ValueError(f'Page with id {page_id} not found.')

		return None

	def get_page_by_name(self, name: str) -> Any | None:
		index = self.get_page_index_by_name(name)
		if index is not None:
			return self._pages[index]
		return None

	def showPageName(self, name: str) -> None:
		index = self.get_page_index_by_name(name)
		if index is not None:
			self.showPage(index)

	def onPageChanging(self, event):
		notebook = event.GetEventObject()
		if notebook == self._notebook:
			self.callPageCommit(event.GetOldSelection())
			self.callPageRefresh(event.GetSelection())
		try:
			self.log.info('page: {}'.format(notebook.GetPage(event.GetSelection()).__class__.__name__))
		except IndexError:
			self.log.warning('page: Index error when trying to get notebook page')

		event.Skip()  # Required to properly repaint the screen.

	def refreshAll(self) -> None:
		iSelect = self._notebook.GetSelection()
		for i, p in enumerate(self._pages):
			if i != iSelect:
				self.callPageRefresh( i )


class CrossMgrPageController(AbstractPageController):
	raceAnimation: RaceAnimation
	iChartPage: int
	iGanttPage: int
	iPassingsPage: int
	iHistoryPage : int
	iRecordPage: int
	iResultsPage: int

	def __init__(self, notebook: flatnotebook.FlatNotebook, refresh_windows: callable):
		super().__init__(notebook, refresh_windows)

	def _alias_local_pages(self) -> None:
		# Add page alternate names.
		self.iChartPage = self.iGanttPage
		self.iPassingsPage = self.iHistoryPage

	def _get_page_types(self) -> list[(str, type, str)]:
		return [
			['actions', Actions, _('Actions')],
			['record', Record, _('Record')],
			['results', Results, _('Results')],
			['pulled', Pulled, _('Pulled')],
			['history', History, _('Passings')],
			['riderDetail', RiderDetail, _('RiderDetail')],
			['gantt', Gantt, _('Chart')],
			['recommendations', Recommendations, _('Recommendations')],
			['categories', Categories, _('Categories')],
			['properties', Properties, _('Properties')],
			['primes', Primes, _('Primes')],
			['resultNote', ResultNote, _('Result Notes')],
			['prizes', Prizes, _('Prizes')],
			['raceAnimation', RaceAnimation, _('Animation')],
			# [ 'situation',		Situation,			_('Situation') ],
			['gapChart', GapChart, _('GapChart')],
			['lapCounter', LapCounter, _('LapCounter')],
			['announcer', Announcer, _('Announcer')],
			['histogram', HistogramPanel, _('Histogram')],
			['teamResults', TeamResults, _('Team Results')],
		]

	def refreshRaceAnimation(self) -> None:
		if self._pages[self._notebook.GetSelection()] == self.raceAnimation:
			self.raceAnimation.refresh()

	def showResultsPage(self) -> None:
		self.showPage(self.iResultsPage)

	def refreshTTStart( self, refreshCurrentPage: callable) -> None:
		if Model.race:
			# If a rider started the TT, force the results to be re-computed if necessary.
			Model.race.setChanged()
		if self._notebook.GetSelection() in (self.iHistoryPage, self.iRecordPage):
			refreshCurrentPage()

