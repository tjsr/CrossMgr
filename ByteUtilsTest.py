import unittest
from typing import List, Union

from ByteUtils import CR, LF, encode_to_bytes

class TestEncodeToBytes(unittest.TestCase):
    def test_all_strings(self):
        input_array = ['hello', 'world', 'test']
        expected_output = [b'hello', b'world', b'test']
        self.assertEqual(encode_to_bytes(input_array), expected_output)

    def test_all_bytes(self):
        input_array = [b'hello', b'world', b'test']
        expected_output = [b'hello', b'world', b'test']
        self.assertEqual(encode_to_bytes(input_array), expected_output)

    def test_mixed_strings_and_bytes(self):
        input_array = ['hello', b'world', 'test']
        expected_output = [b'hello', b'world', b'test']
        self.assertEqual(encode_to_bytes(input_array), expected_output)

    def test_empty_array(self):
        input_array = []
        expected_output = []
        self.assertEqual(encode_to_bytes(input_array), expected_output)

    def test_custom_encoding(self):
        input_array = ['hello', 'world', 'test']
        expected_output = [b'hello', b'world', b'test']
        self.assertEqual(encode_to_bytes(input_array, encoding='utf-8'), expected_output)

    def test_single_string(self):
        input_array = ['hello']
        expected_output = [b'hello']
        self.assertEqual(encode_to_bytes(input_array), expected_output)

    def test_single_byte(self):
        input_array = b'\n'
        expected_output = [b'\n']
        self.assertRaises(ValueError, encode_to_bytes, input_array, 'utf-8')

    def test_single_string_custom_encoding(self):
        input_array = '\r'
        self.assertRaises(ValueError, encode_to_bytes, input_array, 'utf-8')

    def test_convert_cr_or_lf_list(self):
        input_array = [CR, LF]
        expected_output = [b'\r', b'\n']
        self.assertEqual(encode_to_bytes(input_array), expected_output)

    def test_convert_cr_or_lf_bytes(self):
        input_array = b'\r\n'
        self.assertRaises(ValueError, encode_to_bytes, input_array)

    def test_convert_cr_or_lf_string(self):
        input_array = '\r\n'
        self.assertRaises(ValueError, encode_to_bytes, input_array)

if __name__ == '__main__':
    unittest.main()