import logging
from logging.handlers import TimedRotatingFileHandler
import os


class logger:
    def __init__(self, app) -> None:

        app.logger.setLevel(logging.DEBUG)

        log_file = app.config["BASE_DIR"]+'/logs/app.log'
        if not os.path.exists(log_file):
            open(log_file, 'w').close()

        log_handler = TimedRotatingFileHandler(
            log_file, when='midnight', interval=1, backupCount=7)

        log_handler.setLevel(logging.DEBUG)

        log_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)

        app.logger.addHandler(log_handler)
