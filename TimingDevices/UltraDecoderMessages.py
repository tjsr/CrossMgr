import datetime
import re
from abc import abstractmethod
from typing import Optional, cast

from TimingDevices.DecoderMessages import DecoderStatusMessage, DecoderMessage

CONNECT_INFO_FORMAT = r'^\d{1,2}:\d{1,2}:\d{1,2} \d{1,2}-\d{1,2}-\d{4} \(-?\d+\)$'
EPOCH_TIME = datetime.datetime(1980, 1, 1)

class UltraDecoderMessage(DecoderMessage):
	_UltraId: int | None # Integer value. See section 3.1

	def __init__(self, ultraId: int | None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._UltraId = ultraId

	@abstractmethod
	def match_message(self, message: 'UltraDecoderMessage') -> Optional['UltraDecoderMessage']:
		pass

	@property
	def UltraId(self) -> int | None:
		return self._UltraId

	@UltraId.setter
	def UltraId(self, value: int):
		self._UltraId = value


class UltraCommandResponse(UltraDecoderMessage):
	_timeReceived: datetime.datetime
	def __init__(self):
		super().__init__(None)
		self._timeReceived = datetime.datetime.now()

	@property
	def timeReceived(self) -> datetime.datetime:
		return self._timeReceived

	@abstractmethod
	def match_message(self, message: 'UltraDecoderMessage') -> Optional['UltraCommandResponse']:
		pass


class UltraConnectConfirmationMessage(UltraDecoderMessage):
	MESSAGE_FORMAT = r'^Connected,\d+(,[U|N])?$'
	def __init__(self, lastTimeSent: datetime.datetime, hasUpdates: bool):
		super().__init__(0)
		self._lastTimeSent = lastTimeSent
		self._hasUpdates = hasUpdates

	@abstractmethod
	def match_message(self, message: 'UltraDecoderMessage') -> Optional['UltraConnectConfirmationMessage']:
		pass

	@staticmethod
	def parse(message: str) -> Optional['UltraConnectConfirmationMessage']:
		if re.match(UltraConnectConfirmationMessage.MESSAGE_FORMAT, message):
			try:
				parts = message.split(',')
				num = len(parts)
				if num > 3 or num < 2:
					return None

				lastTimeDate = datetime.datetime.fromtimestamp(EPOCH_TIME.timestamp() + int(parts[1]))

				CommandCode = parts[2] if num == 3 else None

				hasUpdates = CommandCode == 'U'
				# CommandCode tells us if any data has been missed, but the docs don't say what are valid values.
				return UltraConnectConfirmationMessage(lastTimeDate, hasUpdates)
			except ValueError:
				return None
		return None

	@property
	def lastTimeSent(self) -> datetime.datetime:
		return self._lastTimeSent

	@property
	def hasUpdates(self) -> bool:
		return self._hasUpdates


class UltraConnectInfoMessage(UltraDecoderMessage):
	def __init__(self, ultraId: int):
		super().__init__(ultraId)

	@staticmethod
	def parse(message: str) -> Optional['UltraConnectInfoMessage']:
		if re.match(CONNECT_INFO_FORMAT, message) is not None:
			return UltraConnectInfoMessage(0)
		return None


class UltraVoltageMessage(UltraDecoderMessage):
	def match_message(self, message: UltraDecoderMessage) -> Optional['UltraVoltageMessage']:
		if not isinstance(message, UltraVoltageMessage):
			return None
		return message

	MESSAGE_FORMAT = r'^V=\d+(\.\d+)?$'
	Voltage: float

	@staticmethod
	def parse(messageBuf: str) -> Optional['UltraVoltageMessage']:
		if messageBuf is not None and messageBuf.startswith('V='):
			return UltraVoltageMessage(0, float(messageBuf[2:]))
		return None


	def __init__(self, ultraId: int, voltage: float):
		super().__init__(ultraId)
		self._Voltage = voltage

	@property
	def Voltage(self) -> float:
		return self._Voltage

class UltraDecoderStatusMessage(UltraDecoderMessage, DecoderStatusMessage):
	MESSAGE_FORMAT = r'^S=[01]{2}$'

	def match_message(self, message: UltraDecoderMessage) -> Optional['UltraDecoderStatusMessage']:
		if not isinstance(message, UltraDecoderStatusMessage):
			return None

		return UltraDecoderStatusMessage.parse(message.Data)

	@staticmethod
	def parse(messageBuf: str) -> Optional['UltraDecoderStatusMessage']:
		if messageBuf is None:
			return None
		if re.match(UltraDecoderStatusMessage.MESSAGE_FORMAT, messageBuf) is not None:
			return UltraDecoderStatusMessage(messageBuf[2] == '1', messageBuf[3] == '1')
		return None

	@staticmethod
	def matches(messageBuf: str) -> bool:
		if messageBuf is None:
			return False
		return re.match(UltraDecoderStatusMessage.MESSAGE_FORMAT, messageBuf) is not None

	def __init__(self, readStatus: bool, sendStatus: bool, *args, **kwargs):
		DecoderStatusMessage.__init__(self, readStatus, sendStatus, *args, **kwargs)


# Definitions from https://rfidtiming.com/Software/UltraManual.pdf Pg41
class UltraChipReadMessage(UltraDecoderMessage):
	# Retain this field order
	Zero: int  # Zero (unused at present)
	_ChipCode: int  # Could be the chip code decimal or hexadecimal value, depending on current setting in Ultra (see section 3.8)
	Seconds: int  # Integer value representing the number of seconds after 01/01/1980
	Milliseconds: int  # Integer value representing the millisecond portion of the time.
	RSSI: int  # Negative integer value. This is the signal strength for the chip
	IsRewind: int  # 0 or 1. A value of 1 means the data is being transmitted from a rewind command,
	# in other words it is not a ‘live’ read. Live and rewound data will be mixed up in between
	# each other if you do a ‘rewind while reading’.
	ReaderNo: int  # Integer value of from 1 to 3 representing the reader number. There are 2
	# readers in an Ultra. A reader number of 3 is used for MTB downhill start times.
	# UltraId: int  # Integer value. See section 3.1 - Defined in superclass
	ReaderTime: str  # 8 characters representing the 64-bit time recorded by the UHF readers. Not
	# available for some Ultra models – please speak to your supplier for more information.
	StartTime: int  # For MTB downhill racing. Integer value representing the number of seconds after 01/01/1980
	LogId: int  # Integer value representing the record’s position in the log (starting at one)

	# Derived fields
	ChipCodeAsHexValue: bool

	@staticmethod
	def chipNumberFromString(chipStr: str) -> int:
		if chipStr.startswith('0x'):
			return int(chipStr, 16)
		return int(chipStr)

	@staticmethod
	def parse(message: str) -> 'UltraChipReadMessage | None':
		output: UltraChipReadMessage
		try:
			Zero, ChipCode, Seconds, Milliseconds, Extra = message.split(',', 4)

			output = UltraChipReadMessage(0, UltraChipReadMessage.chipNumberFromString(ChipCode))
			output.Seconds = int(Seconds)
			output.Milliseconds = int(Milliseconds)
		except ValueError as e:
			raise ValueError('Invalid crossing message format parsing {}'.format(message), e)

		try:
			if Extra is not None:
				AntennaNo, RSSI, IsRewind, ReaderNo, UltraID, ReaderTime, StartTime, LogID = Extra.split(',', 7)
				output.AntennaNo = int(AntennaNo)
				output.RSSI = int(RSSI)
				output.IsRewind = int(IsRewind)
				output.ReaderNo = int(ReaderNo)
				output.UltraId = int(UltraID)
				output.ReaderTime = ReaderTime
				output.StartTime = int(StartTime)
				output.LogId = int(LogID)

		except ValueError:
			pass

		return output

	def __init__(self, ultraId: int, chipCode: int):
		super().__init__(ultraId)
		self._ChipCode = chipCode

	def getTagTime(self) -> datetime.datetime:
		return EPOCH_TIME + datetime.timedelta(seconds=self.Seconds, milliseconds=self.Milliseconds)

	@property
	def ChipCode(self) -> int:
		return self._ChipCode

	def hasValidTag(self) -> bool:
		return self._ChipCode != 0


class UltraDecoderTimeMessage(UltraDecoderMessage):
	MESSAGE_FORMAT = r'^t \d{2}:\d{2}:\d{2} \d{2}-\d{2}-\d{4}$'
	DATETIME_FORMAT = "%H:%M:%S %d-%m-%Y"
	_time: datetime.datetime

	@staticmethod
	def matches(message: str) -> bool:
		return re.match(UltraDecoderTimeMessage.MESSAGE_FORMAT, message) is not None

	def __init__(self, ultraId: int, time: datetime.datetime):
		super().__init__(ultraId)
		self._time = time

	@property
	def time(self) -> datetime.datetime:
		return self._time

	def match_message(self, message: UltraDecoderMessage) -> Optional['UltraDecoderTimeMessage']:
		if  UltraDecoderTimeMessage.matches(message.Data):
			return cast(UltraDecoderTimeMessage, message)
		return None

	@staticmethod
	def parse(message: str) -> Optional['UltraDecoderTimeMessage']:
		if message is not None and message.startswith('t '):
			try:
				time_str = message[2:]
				parsed_time = datetime.datetime.strptime(time_str, "%H:%M:%S %d-%m-%Y")
				return UltraDecoderTimeMessage(0, parsed_time)
			except ValueError:
				pass
		return None