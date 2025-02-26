import logging
import sys
from unittest import TestCase

from Log import CrossMgrLogger, getLogger


class TestLog(TestCase):
	def testShouldAcceptLogMessageForTrace(self):
		log: CrossMgrLogger = getLogger('TestLog.shouldAcceptLogMessageForTrace')
		log.trace('Message')

	def testWarning(self):
		log: CrossMgrLogger = getLogger('TestLog.testWarning')

		formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s] %(message)s')
		errHandler = logging.StreamHandler(sys.stderr)
		errHandler.setLevel(logging.WARNING)

		# Create a formatter and set it for the handler
		errHandler.setFormatter(formatter)

		# log.addHandler(errHandler)
		log.warning('WarningMessage')
		log.info('InfoMessage')

		root_logger = logging.getLogger()
		# root_logger.addHandler(errHandler)

	def testNoPropagateToRoot(self):
		log: CrossMgrLogger = getLogger('UltraDecoder.parse')
		log.warning('WarningMessage')
		log.info('InfoMessage')
		log.debug('DebugMessage')

		root_logger = logging.getLogger()
		root_logger.warning('RootWarningMessage')
		root_logger.info('RootInfoMessage')
		root_logger.debug('RootDebugMessage')