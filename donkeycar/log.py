import os
import logging.config


def setup(log_file_path=None):

    if log_file_path is None:
        log_file_path = os.path.expanduser('~/donkey.log')

    config_default = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },
            "error_file_handler": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "simple",
                "filename": log_file_path,
                "maxBytes": 10485760,
                "backupCount": 20,
                "encoding": "utf8"
            },
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "error_file_handler"]
        }
    }

    logging.config.dictConfig(config_default)


def get_logger(name):
    """
    Return a logger that will contextualize the logs with the name.
    """
    logger = logging.getLogger(name)
    return logger


# get a logger specific to this file
logger = get_logger(__name__)
logger.info('Logging configured and loaded.')


if __name__ == '__main__':
    print('run')
    logger.error('test')

