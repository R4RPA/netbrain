import os

# from test_services.config import settings

import logging

from logging.handlers import RotatingFileHandler
from logging.handlers import SMTPHandler


# This is in order to allow log level customization in the config via LOG_LEVEL=
log_levels = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

# package version
__version__ = '0.1.0'

# configure logging
if not os.path.exists('logs'):
    os.mkdir('logs')
log_level = log_levels['DEBUG']

# set handler to rollover log file at 5mb each, 50mb total
file_handler = RotatingFileHandler('logs/netbrain_service.log', maxBytes=5000000000, backupCount=50)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(log_level)

logger = logging.getLogger('test_services')
logger.addHandler(file_handler)
# logger.addHandler(mail_handler)
logger.setLevel(log_level)
