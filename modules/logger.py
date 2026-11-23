import logging
from logging.handlers import TimedRotatingFileHandler
import os


class Logger:
    def __init__(self, app) -> None:
        log_dir = app.config["BASE_DIR"] + '/logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        app.logger.setLevel(logging.DEBUG)

        log_file = log_dir + '/app.log'
        if not os.path.exists(log_file):
            open(log_file, 'w').close()

        log_handler = TimedRotatingFileHandler(
            log_file, when='midnight', interval=1, backupCount=7)

        log_handler.setLevel(logging.DEBUG)

        log_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        log_handler.setFormatter(log_formatter)

        app.logger.addHandler(log_handler)

        # 操作紀錄另存一份檔案（middlewares 寫入），每天一個檔、留 90 天
        audit_handler = TimedRotatingFileHandler(
            log_dir + '/audit.log', when='midnight', interval=1, backupCount=90, encoding='utf-8')
        audit_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        audit = logging.getLogger('audit')
        audit.setLevel(logging.INFO)
        audit.propagate = False
        audit.addHandler(audit_handler)
