from datetime import datetime, timezone, timedelta


class InvalidTimeZoneError(ValueError):
	def __init__(self, tz: datetime.tzinfo = None, permittedTimeZones:list[datetime.tzinfo] = None):
		if permittedTimeZones is not None:
			message = f'Time zone {tz} is not valid. Permitted time zones are {permittedTimeZones}'
		else:
			message = f'Time zone {tz} is not valid'
		super().__init__(message)

###
# This can get really confusing because the Ultra decoder docs don't actually tell us whether times should
# be in UTC or local time. The docs say that the time is the number of seconds since 01/01/1980, but they
# don't say what time zone that is in. You have the ability to set the time zone of the decoder, but it
# always send you an 'Ultra time' (seconds since the 1980 epoch) based on what you set - it doesn't account
# for any timezone data.
# It means you could set the decoder time to be your datetime, including UTC offset, but any times it tells
# you won't indicate whether that's a UTC or local time.
# I therefore recommend we *always communicate in UTC time*.
###

class UltraTimeUtils:
	ULTRA_EPOCH_TIME = datetime(1980, 1, 1, tzinfo=timezone.utc)
	UNIX_EPOCH_1980: float = 315532800.000
	ULTRA_EPOCH_1980_OFFSET = (315532800, 000)

	@staticmethod
	def microseconds_to_milliseconds(microseconds: int, rounding: bool = True) -> int:
		if rounding:
			return (microseconds + 500) // 1000
		return microseconds // 1000

	@staticmethod
	def unix_to_ultra_epoch(unix_epoch: float) -> (int, int):
		# Unix and Ultra epochs will also be UTC time.
		# Ultra epochs are always ints in seconds, with milliseconds specified separately.
		milliseconds = UltraTimeUtils.microseconds_to_milliseconds(int(unix_epoch * 1000000) % 1000000)
		return int(unix_epoch - UltraTimeUtils.UNIX_EPOCH_1980), milliseconds

	@staticmethod
	def ultra_to_unix_epoch(ultra_epoch: int, ultra_msec: int = 000) -> float:
		# Unix and Ultra epochs will also be UTC time.
		return (float(ultra_epoch) + (ultra_msec/1000.000)) + UltraTimeUtils.UNIX_EPOCH_1980

	@staticmethod
	def ultra_epoch_to_datetime(ultra_epoch: int, ultra_msec: int = 000, tz: datetime.tzinfo = timezone.utc) -> datetime:
		if ultra_epoch < 0:
			raise ValueError(f'Epoch value {ultra_epoch} is invalid')

		tzEpoch = datetime.astimezone(UltraTimeUtils.ULTRA_EPOCH_TIME, tz)
		return tzEpoch + timedelta(seconds=ultra_epoch, milliseconds=ultra_msec)

	@staticmethod
	def datetime_to_ultra_epoch(dt: datetime) -> (int, int):
		if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) != timedelta(0):
			raise InvalidTimeZoneError(dt.tzinfo, [timezone.utc])

		unix_epoch:float = dt.timestamp()
		if unix_epoch < UltraTimeUtils.UNIX_EPOCH_1980:
			raise ValueError(f'Cannot convert time {dt} ({unix_epoch}) before 1980 to Ultra epoch')
		return UltraTimeUtils.unix_to_ultra_epoch(unix_epoch)