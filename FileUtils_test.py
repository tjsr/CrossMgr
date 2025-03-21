from unittest import TestCase
from FileUtils import is_empty_or_current_dir

class FileUtilsTest(TestCase):
	def test_is_empty_or_current_dir(self) -> None:
		self.assertTrue(is_empty_or_current_dir(None))
		self.assertTrue(is_empty_or_current_dir(''))
		self.assertTrue(is_empty_or_current_dir('.'))
		self.assertTrue(is_empty_or_current_dir('  '))

		self.assertFalse(is_empty_or_current_dir('a'))
		self.assertFalse(is_empty_or_current_dir('a/b'))
		self.assertFalse(is_empty_or_current_dir('a/b/c'))
		self.assertFalse(is_empty_or_current_dir('a/b/c.ext'))
		self.assertFalse(is_empty_or_current_dir('a/b/c/'))

		with self.assertRaises(ValueError):
			is_empty_or_current_dir(1)
		with self.assertRaises(ValueError):
			is_empty_or_current_dir(1.0)
		with self.assertRaises(ValueError):
			is_empty_or_current_dir([])
		with self.assertRaises(ValueError):
			is_empty_or_current_dir({})