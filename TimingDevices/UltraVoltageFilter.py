from logging import Filter, LogRecord

class UltraVoltageFilter(Filter):
	def filter(self, record: LogRecord) -> bool:
		if record.name == 'input' and record.levelname == 'INFO' and record.getMessage().startswith('V=0'):
			return False
		return True
