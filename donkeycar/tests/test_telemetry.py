#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from unittest import mock
from paho.mqtt.client import Client
from paho.mqtt.enums import CallbackAPIVersion

import donkeycar.templates.cfg_complete as cfg
from donkeycar.parts.telemetry import MqttTelemetry
from random import randint


def test_mqtt_telemetry():

    cfg.TELEMETRY_DEFAULT_INPUTS = 'pilot/angle,pilot/throttle'
    cfg.TELEMETRY_DONKEY_NAME = 'test{}'.format(randint(0, 1000))
    cfg.TELEMETRY_MQTT_JSON_ENABLE = True

    # Create receiver
    sub = Client(callback_api_version=CallbackAPIVersion.VERSION2,
                 clean_session=True)

    on_message_mock = mock.Mock()
    on_connect_mock = mock.Mock()
    sub.on_message = on_message_mock
    sub.on_connect = on_connect_mock
    
    try:
        sub.connect(cfg.TELEMETRY_MQTT_BROKER_HOST, 1883, 60)
    except Exception as e:
        # Skip test if MQTT broker is not available
        import pytest
        pytest.skip(f"MQTT broker not available: {e}")
    
    sub.loop_start()
    
    # Wait for connection
    connection_timeout = 5.0
    start_time = time.time()
    while not on_connect_mock.called and (time.time() - start_time) < connection_timeout:
        time.sleep(0.1)
    
    if not on_connect_mock.called:
        sub.loop_stop()
        import pytest
        pytest.skip("MQTT broker connection timeout")
    
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

    # Wait for MQTT message with retries
    max_retries = 10
    retry_delay = 0.2
    for attempt in range(max_retries):
        if len(on_message_mock.call_args_list) > 0:
            break
        time.sleep(retry_delay)
    else:
        # Final attempt after all retries
        time.sleep(0.5)
    
    # Ensure MQTT message was received
    assert len(on_message_mock.call_args_list) > 0, "No MQTT messages received after {} attempts".format(max_retries + 1)
    
    res = str.encode('[{"ts": %s, "values": {"my/speed": 16, "my/voltage": 11.1, "pilot/angle": 33.3, '
                     '"pilot/throttle": 22.2}}]' % timestamp)
    assert on_message_mock.call_args_list[0][0][2].payload == res
    
    # Cleanup
    sub.loop_stop()
    sub.disconnect()
