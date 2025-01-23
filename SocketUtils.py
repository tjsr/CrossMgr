import socket
from typing import List

from ByteUtils import ASCII_ENCODING, ISO_ENCODING, EOL, LF, encode_to_bytes

def socketSend( s: socket.socket, data: bytes ) -> None:
	if isinstance(data, str):
		data = data.encode(ASCII_ENCODING)
	if not isinstance(data, bytes):
		data = data.encode()

	sLen = 0
	while sLen < len(data):
		sLen += s.send( data[sLen:] )
  
def socketSendMessage( s: socket.socket, message: str ) -> None:
	socketSend( s, bytes(message, encoding=ASCII_ENCODING) )

def socketReadDelimited( s: socket.socket, delimiters: List[bytes]=[EOL, LF]) -> str|None:
	delimiters = encode_to_bytes(delimiters)

	buffer: bytes = s.recv( 4096 )

	while not any(buffer.endswith( delimiter ) for delimiter in delimiters):
		more = s.recv( 4096 )
		if more:
			buffer += more
		else:
			break

	if buffer is None:
		return None
	return buffer.decode(ISO_ENCODING)
