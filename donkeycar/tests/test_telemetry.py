#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from unittest import mock
from unittest.mock import patch, MagicMock
import donkeycar.templates.cfg_complete as cfg
from donkeycar.parts.telemetry import MqttTelemetry
import pytest
from random import randint


@patch('donkeycar.parts.telemetry.MQTTClient')
def test_mqtt_telemetry(mock_mqtt_client):
    """Test MQTT telemetry functionality with mocked MQTT client"""
    
    # Setup configuration
    cfg.TELEMETRY_DEFAULT_INPUTS = 'pilot/angle,pilot/throttle'
    cfg.TELEMETRY_DONKEY_NAME = 'test{}'.format(randint(0, 1000))
    cfg.TELEMETRY_MQTT_JSON_ENABLE = True

    # Create mock MQTT client
    mock_client_instance = MagicMock()
    mock_mqtt_client.return_value = mock_client_instance

    # Create telemetry instance
    t = MqttTelemetry(cfg)
    
    # Verify MQTT client was initialized correctly
    mock_mqtt_client.assert_called_once_with(callback_api_version=mock.ANY)
    mock_client_instance.connect.assert_called_once_with(
        cfg.TELEMETRY_MQTT_BROKER_HOST, 
        cfg.TELEMETRY_MQTT_BROKER_PORT
    )
    mock_client_instance.loop_start.assert_called_once()

    # Test adding step inputs
    t.add_step_inputs(inputs=['my/voltage'], types=['float'])
    expected_inputs = ['pilot/angle', 'pilot/throttle', 'my/voltage']
    expected_types = ['float', 'float', 'float']
    assert t._step_inputs == expected_inputs
    assert t._step_types == expected_types

    # Test initial publish (should do nothing as queue is empty)
    t.publish()
    mock_client_instance.publish.assert_not_called()

    # Test reporting data
    timestamp = t.report({'my/speed': 16, 'my/voltage': 12})
    assert isinstance(timestamp, int)
    assert t.qsize == 1

    # Test run method (adds step inputs to queue)
    t.run(33.3, 22.2, 11.1)
    assert t.qsize == 2

    # Test publishing with data
    t.publish()
    assert t.qsize == 0
    
    # Verify publish was called
    assert mock_client_instance.publish.called
    call_args = mock_client_instance.publish.call_args
    topic, payload = call_args[0]
    
    # Verify topic format
    expected_topic = cfg.TELEMETRY_MQTT_TOPIC_TEMPLATE % cfg.TELEMETRY_DONKEY_NAME
    assert topic == expected_topic
    
    # Verify JSON payload structure
    import json
    payload_data = json.loads(payload)
    assert isinstance(payload_data, list)
    assert len(payload_data) >= 1
    
    # Check that data contains expected keys
    data_entry = payload_data[0]
    assert 'ts' in data_entry
    assert 'values' in data_entry
    assert 'my/speed' in data_entry['values']
    assert 'pilot/angle' in data_entry['values']
    assert 'pilot/throttle' in data_entry['values']


def test_mqtt_telemetry_connection_error():
    """Test MQTT telemetry handles connection errors gracefully"""
    
    cfg.TELEMETRY_DEFAULT_INPUTS = 'pilot/angle,pilot/throttle'
    cfg.TELEMETRY_DONKEY_NAME = 'test{}'.format(randint(0, 1000))
    cfg.TELEMETRY_MQTT_JSON_ENABLE = True

    with patch('donkeycar.parts.telemetry.MQTTClient') as mock_mqtt_client:
        # Simulate connection failure
        mock_client_instance = MagicMock()
        mock_client_instance.connect.side_effect = ConnectionError("Connection failed")
        mock_mqtt_client.return_value = mock_client_instance

        # Connection error should be raised during initialization
        with pytest.raises(ConnectionError):
            t = MqttTelemetry(cfg)
