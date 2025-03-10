import pickle
import pprint
import unittest
from typing import cast

import Model
from ModuleUnpickler import ModuleUnpickler
from Race import RaceType
from ReadSignOnSheet import HasExcelLink


class TestLoadRaceData(unittest.TestCase):
	test_data_file = 'data/2024-08-26-TestEvent-r1-.cmn'

	def test_load_format_3_1_168(self):
		with open(self.test_data_file, 'rb') as fp, Model.LockRace() as race:
			race = pickle.load( fp, encoding='latin1', errors='replace' )
			pprint.pprint(race)

		pprint.pprint(race.excelLink)

		self.assertFalse(HasExcelLink(race))

	def test_load_format_3_1_168_with_excel_link(self):
		sign_on_link_test_data_file = 'data/2025-03-07-No Frills Race 5 - test-r1-.cmn'
		with open(sign_on_link_test_data_file, 'rb') as fp, Model.LockRace() as race:
			race = pickle.load( fp, encoding='latin1', errors='replace' )

			pprint.pprint(race)
			pprint.pprint(race.excelLink)
			self.assertTrue(HasExcelLink(race))

			cast_race: RaceType = cast(RaceType, race)
			pprint.pprint(cast_race)
			pprint.pprint(cast_race.excelLink)
			self.assertTrue(HasExcelLink(cast_race))

		pprint.pprint(race.excelLink)


	def test_load_format_3_1_168_module_unpickle(self):
		with open(self.test_data_file, 'rb') as fp, Model.LockRace() as race:
			# try:
			# 	race = pickle.load( fp, encoding='latin1', errors='replace' )
			# except Exception as ex:
			# 	fp.seek( 0 )
			race = ModuleUnpickler( fp, module='CrossMgr', encoding='latin1', errors='replace' ).load()
			pprint.pprint(race)
