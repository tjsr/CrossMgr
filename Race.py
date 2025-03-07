import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Any


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

	_excelLink: Any
	__missing_tags: set[(int, datetime.datetime)]
	__unmatched_tags: dict[str, list[float]]
	__is_changed_flag = False

	def reset(self):
		self._excelLink = None
		self.__missing_tags = set()
		self.__unmatched_tags = dict()
		self.__is_changed_flag = True

	@property
	def excelLink(self) -> Any:
		return self._excelLink

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


