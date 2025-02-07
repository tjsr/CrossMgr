import os

def DebugMode() -> bool:
	if os.getenv('DEBUG', 'False').lower() in ('true', '1', 't'):
		return True
	return True
