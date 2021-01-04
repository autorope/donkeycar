# -*- coding: utf-8 -*-
"""
Telemetry class distributing real-time metrics to external server

author: @miro (Meir Tseitlin) 2020

Note:
"""
import os
import queue
import time
import json
from logging import StreamHandler
from paho.mqtt.client import Client as MQTTClient


class MqttTelemetry(StreamHandler):
    """
    Telemetry class collects telemetry from different parts of the system and periodically sends updated to the server.
    Telemetry reports are timestamped and stored in memory until it is pushed to the server
    """

    def __init__(self, cfg, default_inputs=None, default_types=None):

        StreamHandler.__init__(self)

        self.PUBLISH_PERIOD = cfg.TELEMETRY_PUBLISH_PERIOD
        self._last_publish = time.time()
        self._telem_q = queue.Queue()
        self._default_inputs = default_inputs or []
        self._default_types = default_types or []
        self._total_updates = 0
        self._donkey_name = os.environ.get('DONKEY_NAME', cfg.TELEMETRY_DONKEY_NAME)
        self._mqtt_broker = os.environ.get('DONKEY_MQTT_BROKER', cfg.TELEMETRY_MQTT_BROKER_HOST)  # 'iot.eclipse.org'
        self._topic = cfg.TELEMETRY_MQTT_TOPIC_TEMPLATE % self._donkey_name
        self._use_json_format = cfg.TELEMETRY_MQTT_JSON_ENABLE
        self._mqtt_client = MQTTClient()
        self._mqtt_client.connect(self._mqtt_broker, cfg.TELEMETRY_MQTT_BROKER_PORT)
        self._mqtt_client.loop_start()
        self._on = True
        print(f"Telemetry MQTT server connected (publishing: {', '.join(self._default_inputs)}")

    @staticmethod
    def filter_supported_metrics(inputs, types):
        supported_inputs = []
        supported_types = []
        for ind in range(0, len(inputs or [])):
            if types[ind] in ['float', 'str', 'int']:
                supported_inputs.append(inputs[ind])
                supported_types.append(types[ind])
        return supported_inputs, supported_types

    def report(self, metrics):
        """
        Basic reporting - gets arbitrary dictionary with values
        """
        curr_time = int(time.time())

        # Store sample with time rounded to second
        try:
            self._telem_q.put((curr_time, metrics), block=False)
        except queue.Full:
            pass

        return curr_time

    def emit(self, record):
        """
        FUTURE: Added to support Logging interface (to allow to use Python logging module to log directly to telemetry)
        """
        # msg = self.format(record)
        self.report(record)

    @property
    def qsize(self):
        return self._telem_q.qsize()

    def publish(self):

        # Create packet
        packet = {}
        while not self._telem_q.empty():
            next_item = self._telem_q.get()
            packet.setdefault(next_item[0], {}).update(next_item[1])

        if not packet:
            return

        if self._use_json_format:
            packet = [{'ts': k, 'values': v} for k, v in packet.items()]
            payload = json.dumps(packet)

            self._mqtt_client.publish(self._topic, payload)
            # print(f'Total updates - {self._total_updates} (payload size={len(payload)})')
        else:
            # Publish only the last timestamp
            last_sample = packet[list(packet)[-1]]
            for k, v in last_sample.items():
                self._mqtt_client.publish('{}/{}'.format(self._topic, k), v)
            # print(f'Total updates - {self._total_updates} (values ={len(last_sample)})')

        self._total_updates += 1
        return

    def run(self, *args):
        """
        API function needed to use as a Donkey part. Accepts values,
        pairs them with their inputs keys and saves them to disk.
        """
        assert len(self._default_inputs) == len(args)

        # Add to queue
        record = dict(zip(self._default_inputs, args))
        self.report(record)

        # Periodic publish
        curr_time = time.time()
        if curr_time - self._last_publish > self.PUBLISH_PERIOD and self.qsize > 0:

            self.publish()
            self._last_publish = curr_time
        return self.qsize

    def run_threaded(self, *args):

        assert len(self._default_inputs) == len(args)

        # Add to queue
        record = dict(zip(self._default_inputs, args))
        self.report(record)
        return self.qsize

    def update(self):
        while self._on:
            self.publish()
            time.sleep(self.PUBLISH_PERIOD)

    def shutdown(self):
        # indicate that the thread should be stopped
        self._on = False
        print('Stopping MQTT Telemetry')
        time.sleep(.2)