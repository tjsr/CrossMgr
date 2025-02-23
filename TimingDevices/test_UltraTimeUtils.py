from datetime import datetime, timezone
from unittest import TestCase
from zoneinfo import ZoneInfo

from TimingDevices.UltraTimeUtils import UltraTimeUtils, InvalidTimeZoneError

zone_utc = ZoneInfo('UTC')
zone_melbourne = ZoneInfo('Australia/Victoria')


class TestUltraTimeUtils_unix_to_ultra_epoch(TestCase):
	def test_unix_to_ultra_epoch_at_ultra_epoch(self):
		unix_time: float = 315532800.000
		ultra_value = UltraTimeUtils.unix_to_ultra_epoch(unix_time)
		self.assertEqual(ultra_value, (0, 0))

		unix_time: float = 315532800.444
		ultra_value = UltraTimeUtils.unix_to_ultra_epoch(unix_time)
		self.assertEqual(ultra_value, (0, 444))

	def test_unix_to_ultra_epoch_at_modern_date(self):
		unix_time: float = 1738937826.815
		ultra_value = UltraTimeUtils.unix_to_ultra_epoch(unix_time)
		self.assertEqual(ultra_value, (1423405026, 815))

	def test_unix_to_ultra_epoch_high_precision(self):
		unix_time: float = 1738937826.815621
		ultra_value = UltraTimeUtils.unix_to_ultra_epoch(unix_time)
		self.assertEqual(ultra_value, (1423405026, 816))

	def test_ultra_to_unix_epoch_microseconds(self):
		t1980 = datetime(1980, 1, 1, microsecond=0, tzinfo=zone_utc)
		utc_epoch = t1980.timestamp()
		self.assertEqual(utc_epoch, 315532800.000)
		self.assertEqual(UltraTimeUtils.unix_to_ultra_epoch(utc_epoch), (0, 0))

		t1980 = datetime(1980, 1, 1, microsecond=876543, tzinfo=zone_utc)
		unix_epoch = t1980.timestamp()
		self.assertEqual(UltraTimeUtils.unix_to_ultra_epoch(unix_epoch), (0, 877))

	def test_ultra_to_unix_epoch_microseconds_builtin_utc(self):
		t1980 = datetime(1980, 1, 1, microsecond=0, tzinfo=timezone.utc)
		utc_epoch = t1980.timestamp()
		self.assertEqual(utc_epoch, 315532800.000)
		self.assertEqual(UltraTimeUtils.unix_to_ultra_epoch(utc_epoch), (0, 0))


class TestUltraTimeUtils_datetime_to_ultra_epoch(TestCase):
	def test_convert_1980utc_date_ultra(self):
		t1980 = datetime(1980, 1, 1, tzinfo=zone_utc)
		utc_epoch = t1980.timestamp()
		self.assertEqual(utc_epoch, 315532800.000)
		self.assertEqual(UltraTimeUtils.UNIX_EPOCH_1980, utc_epoch)
		output = UltraTimeUtils.datetime_to_ultra_epoch(t1980)
		self.assertEqual(output, (0, 0))

	def test_convert_1980utc_date_ultra_with_microseconds(self):
		for utc in [zone_utc, timezone.utc]:
			t1980 = datetime(1980, 1, 1, microsecond=876543, tzinfo=utc)
			unix_epoch = t1980.timestamp()
			self.assertEqual(UltraTimeUtils.unix_to_ultra_epoch(unix_epoch), (0, 877))
			output = UltraTimeUtils.datetime_to_ultra_epoch(t1980)
			self.assertEqual(output, (0, 877))

	def test_convert_1980utc_epoch_ultra(self):
		self.assertEqual(UltraTimeUtils.UNIX_EPOCH_1980, 315532800.000)
		for utc in [zone_utc, timezone.utc]:
			t1980 = datetime.fromtimestamp(315532800.000, tz=utc)
			output = UltraTimeUtils.datetime_to_ultra_epoch(t1980)
			self.assertEqual(output, (0, 0))

	def test_convert_1980_melbourne_date_ultra(self):
		t1980 = datetime(1980, 1, 1, tzinfo=zone_melbourne)
		melb_epoch = t1980.timestamp()

		self.assertEqual(melb_epoch, 315493200.000)
		self.assertRaises(ValueError, UltraTimeUtils.datetime_to_ultra_epoch, t1980)

	def test_refuse_1980_melbourne_epoch_ultra(self):
		t1980 = datetime.fromtimestamp(315532800.000, tz=zone_melbourne)
		self.assertRaises(InvalidTimeZoneError, UltraTimeUtils.datetime_to_ultra_epoch, t1980)

		t1980ms = datetime.fromtimestamp(315532800.515, tz=zone_melbourne)
		self.assertRaises(InvalidTimeZoneError, UltraTimeUtils.datetime_to_ultra_epoch, t1980ms)

	def test_convert_1980_melbourne_epoch_ultra(self):
		t1980 = datetime.fromtimestamp(315532800.000, tz=zone_melbourne)
		t1980_utc = t1980.astimezone(zone_utc)
		output = UltraTimeUtils.datetime_to_ultra_epoch(t1980_utc)
		self.assertEqual((0, 0), output)

		t1980ms = datetime.fromtimestamp(315532800.515, tz=zone_melbourne)
		t1980ms_utc = t1980ms.astimezone(zone_utc)
		ms_output = UltraTimeUtils.datetime_to_ultra_epoch(t1980ms_utc)
		self.assertEqual((0, 515), ms_output)

	def test_convert_epoch_after_1980(self):
		for utc in [zone_utc, timezone.utc]:
			t1980 = datetime.fromtimestamp(1738937826.731, tz=utc)
			timestamp_convert_output = UltraTimeUtils.datetime_to_ultra_epoch(t1980)
			self.assertEqual(timestamp_convert_output, (1423405026,731))

	def test_convert_time_before_1980(self):
		intel_launch = datetime(1971, 11, 5)

		self.assertRaises(ValueError, UltraTimeUtils.datetime_to_ultra_epoch, intel_launch)


class TestUltraTimeUtils_microseconds_to_milliseconds(TestCase):
	def test_round_microseconds_to_milliseconds(self):
		self.assertEqual(UltraTimeUtils.microseconds_to_milliseconds(141952), 142)
		self.assertEqual(UltraTimeUtils.microseconds_to_milliseconds(141152), 141)

	def test_microseconds_to_milliseconds_no_rounding(self):
		self.assertEqual(UltraTimeUtils.microseconds_to_milliseconds(141952, False), 141)
		self.assertEqual(UltraTimeUtils.microseconds_to_milliseconds(141152, False), 141)
		self.assertEqual(UltraTimeUtils.microseconds_to_milliseconds(578711, False), 578)
		self.assertEqual(UltraTimeUtils.microseconds_to_milliseconds(578999, False), 578)
		self.assertEqual(UltraTimeUtils.microseconds_to_milliseconds(578000, False), 578)


class TestUltraTimeUtils_ultra_to_unix_epoch(TestCase):
	def test_convert_ultra_epoch_to_unix_epoch(self):
		# 1424170202, 779 => 2025-02-16 10:50:02.779 AEDT

		ultra_epoch = 1424170202
		ultra_msec = 779
		output = UltraTimeUtils.ultra_to_unix_epoch(ultra_epoch, ultra_msec)

		epoch_utc = datetime.fromisoformat('2025-02-16T10:50:02.779+00:00')

		self.assertEqual(output, epoch_utc.timestamp())
		self.assertEqual(output, 1739703002.779)

	def test_tzdata(self):
		epoch_aedt = datetime.fromisoformat('2025-02-16T10:50:02.779+11:00')
		date_aedt = datetime(2025, 2, 16, 10, 50, 2, 779000, tzinfo=zone_melbourne)
		self.assertEqual(epoch_aedt.timestamp(), date_aedt.timestamp())
		self.assertEqual(epoch_aedt.timestamp(), 1739663402.779)
		self.assertEqual(date_aedt.timestamp(), 1739663402.779)
		# self.assertEqual(epoch_aedt.timestamp(), 1739668202.779) # 4.8s offset for some reason.

		epoch_2025_aedt = datetime.fromisoformat('2025-01-01T00:00:00.779+11:00')
		date_2025_aedt = datetime(2025, 1, 1, 0, 0, 0, 779000, tzinfo=zone_melbourne)
		self.assertEqual(epoch_2025_aedt.timestamp(), date_2025_aedt.timestamp())
		self.assertEqual(epoch_2025_aedt.timestamp(), 1735650000.779)

		epoch_utc = datetime.fromisoformat('2025-02-16T10:50:02.779+00:00')
		date_utc = datetime(2025, 2, 16, 10, 50, 2, 779000, tzinfo=zone_utc)
		self.assertEqual(epoch_utc.timestamp(), date_utc.timestamp())
		self.assertEqual(epoch_utc.timestamp(), 1739703002.779)

		epoch_diff = epoch_utc.timestamp() - epoch_aedt.timestamp()
		date_diff = date_utc.timestamp() - date_aedt.timestamp()

		self.assertEqual(epoch_diff, 39600.0)
		self.assertEqual(date_diff, 39600.0)

	def test_convert_epoch_after_1980(self):
		for utc in [zone_utc, timezone.utc]:
			epoch_convert_output = UltraTimeUtils.unix_to_ultra_epoch(1738937826.422)
			self.assertEqual(epoch_convert_output, (1423405026, 422))


class TestUltraTimeUtils_ultra_epoch_to_datetime(TestCase):
	_epoch_utc = datetime.fromisoformat('2025-02-16T10:50:02.779+00:00')
	_ultra_epoch = 1424170202
	_ultra_msec = 779

	def setUp(self):
		self._testOutput = UltraTimeUtils.ultra_epoch_to_datetime(self._ultra_epoch, self._ultra_msec)

	def test_ultra_to_datetime_is_utc(self):
		self.assertEqual(timezone.utc, self._testOutput.tzinfo)

	def test_convert_ultra_epoch_to_datetime(self):
		expected_datetime = datetime.fromisoformat('2025-02-16T10:50:02.779+00:00')
		self.assertEqual(expected_datetime, self._testOutput)

