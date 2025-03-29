from unittest import TestCase

from FileSystemUtils import get_safe_current_dir


class FileSystemUtilsTest(TestCase):
	def test_get_safe_current_dir_file_exists(self) -> None:
		os_safe_path = 'c:\\temp\\test.txt'
		safe_dir = get_safe_current_dir(os_safe_path)
		self.assertEqual('c:\\temp', safe_dir)

	def test_get_safe_current_dir_file_not_exists(self) -> None:
		os_safe_nofile_path = 'c:\\temp\\fdsafkjdahfjkhasd.xyz'
		safe_nofile_dir = get_safe_current_dir(os_safe_nofile_path)
		self.assertEqual('c:\\temp', safe_nofile_dir)
 