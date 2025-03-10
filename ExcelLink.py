import os
import re
from abc import abstractmethod, ABC
from typing import List, Tuple, Any

from Excel import GetExcelReader, ReadExcelXlsx

ExcelRowError = Tuple[int, str]

class ExcelDataFieldError(Exception):
	def __init__(self, row: int = None, msg: str = None, rider_number: int = None, errors: List[Tuple[int, str]] = None):
		if errors is None:
			full_msg = f'Row {row}:'
			full_msg += f' Rider {rider_number}:' if rider_number is not None else ''
			full_msg += f' {msg}'
			errors = [(row, full_msg)]

		self.errors = errors

class ExcelLink(ABC):
	OpenCode = 0
	MenCode = 1
	WomenCode = 2

	__has_categories_sheet = False
	__has_properties_sheet = False

	initCategoriesFromExcel = False

	__info_cache: Any = None
	__error_cache: list[ExcelRowError] = None
	__state_cache: Tuple[float, str, str,  dict[Any, int]] = None
	_numeric_fields: list[str] = None
	_ignore_fields: list[str] = None
	_field_col: dict[str, int] = None

	def __init__(self):
		self._file_name = None
		self._sheet_name = None
		self._read_from_file = True
		self._field_col = dict((f, c) for c, f in enumerate(self.Fields))
		self._numeric_fields = []

	@property
	def Fields(self) -> list[str]:
		return self._getFields()

	@property
	def NumericFields(self) -> list[str]:
		return self._numeric_fields

	@property
	def IgnoreFields(self) -> list[str]:
		return self._ignore_fields

	@property
	def ReadFromFile(self) -> bool:
		return self._read_from_file

	@property
	def FileName(self) -> str:
		return self._file_name

	@property
	def SheetName(self) -> str:
		return self._sheet_name

	@property
	def FieldCol(self) -> dict[str, int]:
		return self._field_col

	@abstractmethod
	def _getFields(self) -> [str]:
		pass

	@property
	def InfoCache(self) -> Any:
		return self.__info_cache

	def _add_numeric_field(self, field_name: str) -> None:
		if self._numeric_fields is None:
			self._numeric_fields = []

		if field_name not in self._numeric_fields:
			self._numeric_fields.append(field_name)

	def _checkCacheOk(self) -> bool:
		if self.__is_synced():
			return True

		if self.__state_cache:
			try:
				state = (self._file_name, self._sheet_name, self._field_col)
				if state == self.__state_cache[-3:]:
					return True
			except Exception:
				pass

		return False

	def __is_synced(self) -> bool:
		try:
			state = (os.path.getmtime(self._file_name), self._file_name, self._sheet_name, self._field_col)
			return state == self.__state_cache
		except Exception:
			return False

	def key(self) -> Tuple[str, str, dict]:
		return self._file_name, self._sheet_name, self._field_col

	def __eq__(self, other) -> bool:
		return self.key() == other.key()

	def __ne__(self, other) -> bool:
		return self.key() != other.key()

	def __lt__(self, other) -> bool:
		return self.key() < other.key()

	def __le__(self, other) -> bool:
		return self.key() <= other.key()

	def __gt__(self, other) -> bool:
		return self.key() > other.key()

	def __ge__(self, other) -> bool:
		return self.key() >= other.key()

	def setFileName(self, fname: str) -> None:
		self._file_name = fname

	def setSheetName(self, sname: str) -> None:
		self._sheet_name = sname

	def setFieldCol(self, fieldCol) -> None:
		self._field_col = fieldCol

	@abstractmethod
	def getDefaultFieldMap(self, fileName, sheetName) -> (str, int):
		pass

	def bindDefaultFieldCols(self) -> None:
		headers, fieldCol = self.getDefaultFieldMap(self._file_name, self._sheet_name)
		iNoMatch = len(headers) - 1
		self._field_col = {f: fieldCol[f] if fieldCol[f] != iNoMatch else -1 for f in fieldCol}

	def hasField(self, field) -> bool:
		return self._field_col.get(field, -1) >= 0

	def getFields(self) -> List[str]:
		return [f for f in self.Fields if self.hasField(f)]

	def get(self):
		# Check the cache, but don't bother with the modification date of the file for performance.
		if self._checkCacheOk() == True and self.__info_cache is not None:
			return self.__info_cache

		return None

	def getErrors(self) -> List[ExcelRowError]:
		self.read()
		return self.__error_cache

	reVersionField = re.compile(r'^(.+) \(([0-9]+)\)\.(?:xls|xlsx|xlsm)$', re.IGNORECASE)

	def getMostRecentFilename(self):
		dirname, basename = os.path.split(self._file_name)

		m = ExcelLink.reVersionField.match(basename)
		nameCur = m.group(1) if m else basename.splitext()[0]
		versionCur = int(m.group(2)) if m else 0

		mostRecentFilename = None
		for f in os.listdir(dirname):
			m = ExcelLink.reVersionField.match(f)
			if not m or m.group(1) != nameCur:
				continue
			version = int(m.group(2))
			if version > versionCur:
				versionCur = version
				mostRecentFilename = f
		return os.path.join(dirname, mostRecentFilename) if mostRecentFilename else None

	def updateFilenameToMostRecent(self):
		self._file_name = (self.getMostRecentFilename() or self._file_name)

	@abstractmethod
	def _handle_local_fields(self, *args, **kwargs) -> None:
		pass

	@abstractmethod
	def _parse_local_fields(self, *args, **kwargs) -> bool:
		pass

	def __parse_numeric_fields(self, data, field) -> bool:
		if field in self.NumericFields:
			try:
				data[field] = float(data[field])
				if data[field] == int(data[field]):
					data[field] = int(data[field])
			except ValueError:
				data[field] = 0
			return True
		return False

	def __parse_sheet_field(self, row: int, col: int, data: Any, field: str) -> None:
		try:
			data[field] = row[col].strip()
		except AttributeError:
			data[field] = row[col]

		if data[field] is None:
			data[field] = ''
			return

		if self._parse_local_fields(data, field):
			return
		if self.__parse_numeric_fields(data, field):
			return

		data[field] = '{}'.format(data[field])

	@abstractmethod
	def _process_sheet_data(self, reader: ReadExcelXlsx) -> None:
		pass

	def read(self, alwaysReturnCache=False):
		# Check the cache.  Return the last info if the file has not been modified, and the name, sheet and fields are the same.
		self._read_from_file = False
		if alwaysReturnCache and self.__info_cache is not None:
			return self.__info_cache

		if self._checkCacheOk():
			return self.__info_cache

		# Read the sheet and return the rider data.
		self._read_from_file = True
		try:
			reader: ReadExcelXlsx = GetExcelReader(self._file_name)
			if self._sheet_name not in reader.sheet_names():
				self.__info_cache = {}
				self.__error_cache = []
				return {}
		except Exception:
			self.__info_cache = {}
			self.__error_cache = []
			return {}

		info = {}
		rowInfo = []

		for r, row in enumerate(reader.iter_list(self._sheet_name)):
			data = {}
			for field, col in self._field_col.items():
				if col < 0:  # Skip unmapped columns.
					continue
				try:
					self.__parse_sheet_field(row, col, data, field)
				except IndexError:
					pass

			try:
				num = int(float(data[self.Fields[0]]))
			except (ValueError, TypeError, KeyError) as e:
				pass
			else:
				data[self.Fields[0]] = num
				info[num] = data
				rowInfo.append((r + 1, num, data))  # Add one to the row to make error reporting consistent.

		try:
			self._handle_local_fields(info=info, rowInfo=rowInfo)
		except ExcelDataFieldError as e:
			self.__error_cache = e.errors

		self.__state_cache = (os.path.getmtime(self._file_name), self._file_name, self._sheet_name, self._field_col)
		self.__info_cache = info

		self._process_sheet_data(reader)

		return self.__info_cache