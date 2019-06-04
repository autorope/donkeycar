#!/usr/bin/env python

import datetime
import donkeycar.log as log_utils

log = log_utils.get_log(
    name='test-fluent-bit-logging',
    config='/opt/dc/donkeycar/splunk/log_config.json')

log.info(
    'test message {}'.format(
        datetime.datetime.utcnow()))
