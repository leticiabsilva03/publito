import logging
from logging.handlers import TimedRotatingFileHandler

def configure_logging():
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO
    )

    file_handler = TimedRotatingFileHandler(
        "logs/bot.log", when="midnight", backupCount=7, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    logging.getLogger().addHandler(file_handler)
