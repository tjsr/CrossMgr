import logging

from Log import CrossMgrLogger, load_logging_config_files

logging.setLoggerClass(CrossMgrLogger)

load_logging_config_files()
