from datetime import datetime


class UltraTimeUtils:
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
		# Ultra epochs are always ints in milliseconds
		milliseconds = UltraTimeUtils.microseconds_to_milliseconds(int(unix_epoch * 1000000) % 1000000)
		return int(unix_epoch - UltraTimeUtils.UNIX_EPOCH_1980), milliseconds

	@staticmethod
	def ultra_to_unix_epoch(ultra_epoch: int, ultra_msec: int = 000) -> float:
		# Unix and Ultra epochs will also be UTC time.
		return (float(ultra_epoch) + (ultra_msec/1000.000)) + UltraTimeUtils.UNIX_EPOCH_1980

	@staticmethod
	def ultra_epoch_to_datetime(ultra_epoch: int, ultra_msec: int = 000) -> datetime:
		unix_epoch: float = UltraTimeUtils.ultra_to_unix_epoch(ultra_epoch, ultra_msec)
		return datetime.fromtimestamp(unix_epoch)

	@staticmethod
	def datetime_to_ultra_epoch(dt: datetime) -> (int, int):
		unix_epoch:float = dt.timestamp()
		if unix_epoch < UltraTimeUtils.UNIX_EPOCH_1980:
			raise ValueError(f'Cannot convert time {dt} ({unix_epoch}) before 1980 to Ultra epoch')
		return UltraTimeUtils.unix_to_ultra_epoch(unix_epoch)