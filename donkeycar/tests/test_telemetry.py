#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from unittest import mock
from paho.mqtt.client import Client
import donkeycar.templates.cfg_complete as cfg
from donkeycar.parts.telemetry import MqttTelemetry
import pytest
from random import randint


def test_mqtt_telemetry():

    cfg.TELEMETRY_DEFAULT_INPUTS = 'pilot/angle,pilot/throttle'
    cfg.TELEMETRY_DONKEY_NAME = 'test{}'.format(randint(0, 1000))
    cfg.TELEMETRY_MQTT_JSON_ENABLE = True

    # Create receiver
    sub = Client(clean_session=True)

    # def on_message(client, userdata, message):
    #     data = message.payload
    #     print(message)

    on_message_mock = mock.Mock()
    sub.on_message = on_message_mock
    sub.connect(cfg.TELEMETRY_MQTT_BROKER_HOST)
    sub.loop_start()
    name = "donkey/%s/#" % cfg.TELEMETRY_DONKEY_NAME
    sub.subscribe(name)

    t = MqttTelemetry(cfg)
    t.add_step_inputs(inputs=['my/voltage'], types=['float'])
    t.publish()

    timestamp = t.report({'my/speed': 16, 'my/voltage': 12})
    t.run(33.3, 22.2, 11.1)
    assert t.qsize == 2

    time.sleep(1.5)

    t.publish()
    assert t.qsize == 0

    time.sleep(0.5)

    res = str.encode('[{"ts": %s, "values": {"my/speed": 16, "my/voltage": 11.1, "pilot/angle": 33.3, '
                     '"pilot/throttle": 22.2}}]' % timestamp)
    assert on_message_mock.call_args_list[0][0][2].payload == res
