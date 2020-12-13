#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from unittest import mock
from paho.mqtt.client import Client
import donkeycar.templates.cfg_complete as cfg
from donkeycar.parts.telemetry import MqttTelemetry
import pytest


def test_mqtt_telemetry():

    # Create receiver
    sub = Client(clean_session=True)

    # def on_message(client, userdata, message):
    #     data = message.payload
    #     print(message)

    on_message_mock = mock.Mock()
    sub.on_message = on_message_mock
    sub.connect(cfg.TELEMETRY_MQTT_BROKER_HOST)
    sub.loop_start()
    name = "donkey/%s/telemetry" % cfg.TELEMETRY_DONKEY_NAME
    sub.subscribe(name)

    t = MqttTelemetry(cfg, default_inputs=['angle'], default_types=['float'])
    t.publish()

    timestamp = t.report({'speed': 16, 'voltage': 12})
    t.run(33.3)
    assert t.qsize == 2

    time.sleep(1.5)

    t.publish()
    assert t.qsize == 0

    time.sleep(0.5)

    res = str.encode('[{"ts": %s, "values": {"speed": 16, "voltage": 12, "angle": 33.3}}]' % timestamp)
    assert on_message_mock.call_args_list[0][0][2].payload == res
