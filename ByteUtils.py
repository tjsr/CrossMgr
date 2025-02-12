from typing import List, Union

UTF8_ENCODING = "utf-8"
ASCII_ENCODING = 'ascii'
ISO_ENCODING = 'iso-8859-1'
LF = b'\n'
CR = b'\r'
EOL = CR
CRLF = b'\r\n'

def encode_to_bytes(input_array: List[Union[str, bytes]], encoding: str = ISO_ENCODING) -> List[bytes]:
	encoded_array = []
	
	if isinstance(input_array, bytes):
		raise ValueError("Input array must be a list of strings or bytes, not an array of bytes")

	if isinstance(input_array, str):
		raise ValueError("Input array must be a list of strings or bytes, not string")

	for element in input_array:
			if isinstance(element, bytes):
					encoded_array.append(element)
			else:
					encoded_array.append(element.encode(encoding))
	return encoded_array
