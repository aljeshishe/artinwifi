import logging.config
import pathlib
from datetime import datetime
import functools
import logging


log = logging.getLogger(__name__)


def trace(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        log.debug(f.__name__, args, kwargs)
        return f(*args, **kwargs)
    return wrapper

NOW_STR = datetime.now().strftime("%d%m%y_%H%M%S")


def default_config(filename=f'output/{NOW_STR}/log.log', console_level='INFO'):
    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '%(asctime)s.%(msecs)03d|%(levelname)-4.4s|%(thread)-6.6s|%(module)-6.6s|%(funcName)-10.10s|%(message)s',
                'datefmt': '%Y/%m/%d %H:%M:%S',
            },
        },
        'handlers': {
            'file_handler': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': filename,
                'formatter': 'verbose',
                'mode': 'w',
                'encoding': 'utf8',
            },
            'console_handler': {
                'level': console_level,
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'requests': {
                'handlers': ['file_handler', 'console_handler'],
                'level': 'INFO',
                'propagate': False,
            },
            'urllib3': {
                'handlers': ['file_handler', 'console_handler'],
                'level': 'INFO',
                'propagate': False,
            },
        },
        'root': {
            'handlers': ['file_handler', 'console_handler'],
            'level': 'DEBUG',
            'propagate': False,
        }
    }
    return log_config


def configure(config):
    file_name = config['handlers']['file_handler']['filename']
    pathlib.Path(file_name).parent.mkdir(parents=True, exist_ok=True)
    logging.config.dictConfig(config)
