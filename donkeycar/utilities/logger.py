import logging

def init_special_logger(namespace):
    _logger = logging.getLogger(namespace)
    _logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    _logger.addHandler(sh)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    sh.setFormatter(formatter)
    _logger.propagate = False
    return _logger

