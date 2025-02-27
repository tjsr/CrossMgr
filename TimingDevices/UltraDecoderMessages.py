import datetime
import re
from abc import abstractmethod, ABC
from logging import Logger
from typing import Optional, cast

from Log import getLogger
from TimingDevices.DecoderMessages import DecoderStatusMessage, DecoderMessage, DecoderTimeMessage, \
	DecoderCrossingMessage, TransponderCrossingMessage, TransponderIdType
from TimingDevices.UltraTimeUtils import UltraTimeUtils

CONNECT_INFO_FORMAT = r'^\d{1,2}:\d{1,2}:\d{1,2} \d{1,2}-\d{1,2}-\d{4} \(-?\d+\)$'


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

				lastTimeDate = UltraTimeUtils.ultra_epoch_to_datetime(int(parts[1]))

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


# class UltraConnectInfoMessage(UltraDecoderMessage):
# 	def __init__(self, ultraId: int):
# 		super().__init__(ultraId)
#
# 	@staticmethod
# 	def parse(message: str) -> Optional['UltraConnectInfoMessage']:
# 		if re.match(CONNECT_INFO_FORMAT, message) is not None:
# 			return UltraConnectInfoMessage(0)
# 		return None


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
class UltraChipReadMessage(UltraDecoderMessage, TransponderCrossingMessage[str|int]):
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

	def _getTransponderId(self) -> TransponderIdType:
		return self._ChipCode

	@property
	def Time(self) -> datetime.datetime:
		return UltraTimeUtils.ultra_epoch_to_datetime(ultra_epoch=self.Seconds, ultra_msec=self.Milliseconds)

	@staticmethod
	def chipNumberFromString(chipStr: str) -> int:
		if chipStr.startswith('0x'):
			return int(chipStr, 16)
		return int(chipStr)

	@staticmethod
	def parse(messageBuf: str) -> Optional['UltraChipReadMessage']:
		output: UltraChipReadMessage
		try:
			Zero, ChipCode, Seconds, Milliseconds, Extra = messageBuf.split(',', 4)

			output = UltraChipReadMessage(0, UltraChipReadMessage.chipNumberFromString(ChipCode))
			output.Seconds = int(Seconds)
			output.Milliseconds = int(Milliseconds)
		except ValueError as e:
			raise ValueError('Invalid crossing message format parsing {}'.format(messageBuf), e)

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
		UltraDecoderMessage.__init__(self, ultraId)
		TransponderCrossingMessage.__init__(self)
		self._ChipCode = chipCode

	def _getTime(self) -> datetime.datetime:
		return UltraTimeUtils.ultra_epoch_to_datetime(ultra_epoch=self.Seconds, ultra_msec=self.Milliseconds)

	@property
	def ChipCode(self) -> int:
		return self._ChipCode

	def hasValidTag(self) -> bool:
		return self._ChipCode != 0

	def match_message(self, message: 'UltraDecoderMessage') -> Optional['UltraDecoderMessage']:
		if not isinstance(message, UltraChipReadMessage):
			return None

		return message


class UltraDecoderTimeMessage(UltraDecoderMessage, DecoderTimeMessage):
	MESSAGE_FORMAT = r'^(\d{2}:\d{2}:\d{2} \d{2}-\d{2}-\d{4})(\s\(-?\d+\))?$'
	DATETIME_FORMAT = "%H:%M:%S %d-%m-%Y"

	@staticmethod
	def matches(messageBuf: str) -> bool:
		return re.match(UltraDecoderTimeMessage.MESSAGE_FORMAT, messageBuf) is not None

	def __init__(self, ultraId: int, time: datetime.datetime = None, is_invalid: bool = False, message: Optional['UltraDecoderTimeMessage'] = None):
		if message is not None:
			self.__init__(message.UltraId, message.time, message.HasInvalidData)
		else:
			super().__init__(ultraId, time, is_invalid)
			DecoderTimeMessage.__init__(self ,time, is_invalid)

	def match_message(self, message: UltraDecoderMessage) -> Optional['UltraDecoderTimeMessage']:
		if  UltraDecoderTimeMessage.matches(message.Data):
			return cast(UltraDecoderTimeMessage, message)
		return None

	@staticmethod
	def parse_epoch_component(epoch_tail: str) -> Optional[datetime.datetime]:
		epoch_component = (epoch_tail
		                   .replace('(', '')
		                   .replace(')', '')
		                   .strip())

		epoch_date = None
		if epoch_component != '':
			epoch = int(epoch_component)
			epoch_date = UltraTimeUtils.ultra_epoch_to_datetime(epoch)

		return epoch_date

	@staticmethod
	def log_message_state(log: Logger, parsed_time: datetime, epoch_date: datetime, invalid_epoch: bool) -> None:
		debug_msg = f'Parsed time {parsed_time}'

		if epoch_date:
			if epoch_date != parsed_time:
				debug_msg = f'{debug_msg} but epoch value did not match date stamp of {epoch_date}!'
				log.warning(debug_msg)
			else:
				debug_msg = f'{debug_msg} with epoch value {epoch_date}'
				log.debug(debug_msg)
		elif invalid_epoch:
			debug_msg = f'{debug_msg} but epoch value was invalid'
			log.warning(debug_msg)

	@staticmethod
	def parse(messageBuf: str) -> Optional['UltraDecoderTimeMessage']:
		log = getLogger('UltraDecoderTimeMessage.parse')

		assert isinstance(messageBuf, str)
		if messageBuf is None or messageBuf == '':
			log.warning('No message buffer provided when trying to parse Ultra Set Time response')
			return None

		parts = re.match(UltraDecoderTimeMessage.MESSAGE_FORMAT, messageBuf)
		if parts is None:
			return None

		time_component = messageBuf[parts.regs[1][0]:parts.regs[1][1]]

		invalid_epoch = False
		epoch_date = None
		try:
			epoch_date = UltraDecoderTimeMessage.parse_epoch_component(messageBuf[len(time_component):])
		except ValueError:
			invalid_epoch = True

		try:
			parsed_time = datetime.datetime.strptime(time_component, "%H:%M:%S %d-%m-%Y")
			UltraDecoderTimeMessage.log_message_state(log, parsed_time, epoch_date, invalid_epoch)

			return UltraDecoderTimeMessage(0, parsed_time, is_invalid=invalid_epoch)
		except ValueError:
			pass

		return None


class UltraSetTimeCommandResponse(UltraDecoderTimeMessage):
	def __init__(self, ultraId: int, message: UltraDecoderTimeMessage):
		super().__init__(ultraId=ultraId, message=message)
		self._message = message

	@property
	def message(self) -> UltraDecoderTimeMessage:
		return self._message

	def match_message(self, message: UltraDecoderMessage) -> Optional['UltraSetTimeCommandResponse']:
		if not isinstance(message, UltraDecoderTimeMessage):
			return None
		return UltraSetTimeCommandResponse.parse(message.Data)


class UltraSettingsMessage(UltraDecoderMessage):
	SETTING_GPRS_ON: bytes = 0x01
	SETTING_GPRS_SERVER_IP: bytes = 0x02
	SETTING_GPRS_SERVER_PORT: bytes = 0x03
	SETTING_APN_NAME: bytes = 0x04
	SETTING_APN_USER: bytes = 0x05
	SETTING_APN_PASSWORD: bytes = 0x06
	SETTING_REGULATORY_REGION: bytes = 0x07
	SETTING_COMMUNICATION_PROTOCOL: bytes = 0x08
	SETTING_CHIP_OUTPUT_TYPE: bytes = 0x09
	SETTING_READER1_ANT1_STATUS: bytes = 0x0C
	SETTING_READER1_ANT2_STATUS: bytes = 0x0D
	SETTING_READER1_ANT3_STATUS: bytes = 0x0E
	SETTING_READER1_ANT4_STATUS: bytes = 0x0F
	SETTING_READER2_ANT1_STATUS: bytes = 0x10
	SETTING_READER2_ANT2_STATUS: bytes = 0x11
	SETTING_READER2_ANT3_STATUS: bytes = 0x12
	SETTING_READER2_ANT4_STATUS: bytes = 0x13
	SETTING_READER1_MODE: bytes = 0x14
	SETTING_READER2_MODE: bytes = 0x15
	SETTING_READER1_SESSION: bytes = 0x16
	SETTING_READER2_SESSION: bytes = 0x17
	SETTING_READER1_POWER: bytes = 0x18
	SETTING_READER2_POWER: bytes = 0x19
	SETTING_READER1_IP_ADDRESS: bytes = 0x1A
	SETTING_READER2_IP_ADDRESS: bytes = 0x1B
	SETTING_GATING_MODE: bytes = 0x1D
	SETTING_GATING_INTERVAL: bytes = 0x1E
	SETTING_CHANNEL_NUMBER: bytes = 0x1F
	SETTING_BEEPER_VOLUME: bytes = 0x21
	SETTING_AUTO_SET_FROM_GPS_TIME: bytes = 0x22
	SETTING_TIME_ZONE: bytes = 0x23
	SETTING_DATA_SENDING: bytes = 0x24
	SETTING_ULTRA_ID: bytes = 0x25
	SETTING_READER1_ANT4_BACKUP: bytes = 0x26
	SETTING_READER2_ANT4_BACKUP: bytes = 0x27
	SETTING_BEEP_WHEN: bytes = 0x28
	SETTING_UPLOAD_URL: bytes = 0x29
	SETTING_GATEWAY: bytes = 0x2A
	SETTING_DNS_SERVER: bytes = 0x2B
	SAVE_SETTINGS: bytes = 0xFF


	def match_message(self, message: 'UltraDecoderMessage') -> Optional['UltraDecoderMessage']:
		if not isinstance(message, UltraSettingsMessage):
			return None
		return UltraSettingsMessage.parse(message.Data)

	MESSAGE_FORMAT = r'^U(.)(.*)$'
	setting: str = None

	@staticmethod
	def matches(messageBuf: str) -> bool:
		return re.match(UltraSettingsMessage.MESSAGE_FORMAT, messageBuf) is not None

	@staticmethod
	def parse(messageBuf: str) -> Optional['UltraSettingsMessage']:
		if messageBuf is None:
			return None
		if re.match(UltraSettingsMessage.MESSAGE_FORMAT, messageBuf) is not None:
			settings = messageBuf[2:]

			return UltraSettingsMessage(0)
		return None

