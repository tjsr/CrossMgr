import logging.handlers
from typing import cast
from unittest import TestCase

import Log

class LogRedirect:
	def __init__(self, log):
		self.log = log

	def write(self, message):
		self.log.info(message)

	def flush(self):
		pass

class TestLogRedirect(TestCase):
	def test_redirect(self) -> None:
		test_logger = Log.getLogger('TimingDevice[UltraDecoder].output')
		test_logger.info('test12.')
		for h in test_logger.handlers:
			try:
				# test_logger.info(f'Checking handler {h.name} of t  ype {h.__class__}')
				print(f'Checking handler {h.name} of type {h.__class__}')
			except Exception as ex:
				print(ex)
			# print(h.name, h.__class__)
			if isinstance(h, logging.handlers.QueueHandler):
				qh: logging.handlers.QueueHandler = cast(logging.handlers.QueueHandler, h)
				print(qh.name, qh.queue)
				# test_logger.info(f'Found QH {qh.name} with queue {qh.queue}')
				# qh.queue()
				# qh.start()


