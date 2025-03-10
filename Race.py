import datetime
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Any, Optional

import Log
import Utils
from ExcelLink import ExcelLink


class ChipReaderRaceInfo:
	chipReaderType: int = 0
	chipReaderPort:int = 3601
	chipReaderIpAddr: str = '127.0.0.1'

	enableJChipIntegration: bool = False
	timeTrialNoRFIDStart: bool = False
	resetStartClockOnFirstTag: bool = False
	firstRecordedTime: datetime.datetime = None
	skipFirstTagRead: bool = False

	__tag_nums: Dict[str, int] = None

	#--------------------------------------
	rfidRestartTime: datetime.datetime|None = None		# Restart time (used to ignore intervening tag reads)
	#--------------------------------------

	@property
	def tagNums(self) -> Dict[str, int]:
		if self.__tag_nums is None:
			self.__tag_nums = {}
		return self.__tag_nums

	@tagNums.setter
	def tagNums(self, value: Dict[str, int]):
		self.__tag_nums = value

	def __init__(self):
		self.__tag_nums = Dict[str, int]()

	def reset(self):
		self.__tag_nums = {}
		self.rfidRestartTime = None
		self.enableJChipIntegration = False

	def clearTagNums(self) -> None:
		# Clear the tagNums cache as it will be reset after reading the spreadsheet.
		try:
			self.__tag_nums = {}
		except AttributeError:
			pass

	def ensure_tag_nums(self) -> None:
		if getattr(self, '__tag_nums', None) is None or self.__tag_nums is None:
			self.__tag_nums = {}


class RaceType(ABC, ChipReaderRaceInfo):
	MAX_UNMATCHED_TAGS: int = 2000

	_excelLink: Optional[ExcelLink] = None
	__missing_tags: set[(int, datetime.datetime)] = set()
	__unmatched_tags: dict[str, list[float]] = dict()
	__is_changed_flag:bool = False
	__race_num: int = 1
	__date: datetime.date = datetime.date.today()
	__memo: str | None = None
	__name: str = 'MyEventName'
	__long_name: str|None = None
	__race_duration: datetime.timedelta = datetime.timedelta(minutes=60)
	__log: logging.Logger = Log.getLogger()

	def reset(self):
		self._excelLink = None
		self.__missing_tags = set()
		self.__unmatched_tags = dict()
		self.__is_changed_flag = True
		self.__race_num = 1
		self.__date = datetime.date.today()
		self.__memo = None
		self.__name = 'MyEventName'
		self.__long_name = None

	@property
	def excelLink(self) -> ExcelLink | None:
		return self._excelLink

	@excelLink.setter
	def excelLink(self, value: ExcelLink | None):
		self._excelLink = value

	@property
	def unmatchedTags(self) -> Dict[str, List[float]]:
		return self.__unmatched_tags

	def addUnmatchedTag(self, tag: str, elapsed_time_seconds: float) -> None:
		try:
			if len(self.__unmatched_tags[tag]) < self.MAX_UNMATCHED_TAGS:
				self.__unmatched_tags[tag].append(elapsed_time_seconds)
		except KeyError:
			self.__unmatched_tags[tag] = [elapsed_time_seconds]
		except (AttributeError, TypeError):
			self.__unmatched_tags = {tag: [elapsed_time_seconds]}

	@abstractmethod
	def addTime(self, num: int, time: datetime.datetime) -> None:
		pass

	def setChanged(self, is_changed: bool = True) -> None:
		self.__is_changed_flag = is_changed

	@property
	def missingTags(self) -> set[(int, datetime.datetime)]:
		return self.__missing_tags

	@missingTags.setter
	def missingTags(self, value: set[(int, datetime.datetime)]):
		self.__missing_tags = value

	def isChanged(self):
		return self.__is_changed_flag

	@property
	def changed(self) -> bool:
		return self.__is_changed_flag

	@changed.setter
	def changed(self, value: bool):
		self.__is_changed_flag = value

	@property
	def FileName(self) -> str:
		return Utils.GetFileName(
			self.__date.strftime('%Y-%m-%d'),
			self.__name,
			self.__race_num,
			self.__memo
		)

	@property
	def Name(self) -> str:
		return self.__name

	@Name.setter
	def Name(self, value: str):
		self.__name = value

	@property
	def LongName(self) -> str | None:
		return self.__long_name

	@LongName.setter
	def LongName(self, value: str):
		self.__long_name = value

	@property
	def RaceNum(self) -> int | None:
		return self.__race_num

	@RaceNum.setter
	def RaceNum(self, value: int):
		self.__race_num = value

	@property
	def Minutes(self) -> int | None:
		if self.__race_duration is None:
			return None
		return self.__race_duration.seconds // 60

	@Minutes.setter
	def Minutes(self, value: int):
		self.__race_duration = datetime.timedelta(minutes=value)

	@property
	def Memo(self) -> str | None:
		return self.__memo

	@Memo.setter
	def Memo(self, value: str | None):
		self.__memo = value

	@property
	def _log(self) -> logging.Logger:
		if self.__log is None:
			self.__log = Log.getLogger()
		return self.__log

	@property
	def log(self) -> None:
		raise NotImplementedError('Use ._log not .log property must be overridden.')
