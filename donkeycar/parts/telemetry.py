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
import logging
import numpy as np
from logging import StreamHandler
from paho.mqtt.client import Client as MQTTClient

logger = logging.getLogger()

LOG_MQTT_KEY = 'log/default'


class MqttTelemetry(StreamHandler):
    """
    Telemetry class collects telemetry from different parts of the system and periodically sends updated to the server.
    Telemetry reports are timestamped and stored in memory until it is pushed to the server
    """

    def __init__(self, cfg):

        StreamHandler.__init__(self)

        self.PUBLISH_PERIOD = cfg.TELEMETRY_PUBLISH_PERIOD
        self._last_publish = time.time()
        self._telem_q = queue.Queue()
        self._step_inputs = cfg.TELEMETRY_DEFAULT_INPUTS.split(',')
        self._step_types = cfg.TELEMETRY_DEFAULT_TYPES.split(',')
        self._total_updates = 0
        self._donkey_name = os.environ.get('DONKEY_NAME', cfg.TELEMETRY_DONKEY_NAME)
        self._mqtt_broker = os.environ.get('DONKEY_MQTT_BROKER', cfg.TELEMETRY_MQTT_BROKER_HOST)  # 'iot.eclipse.org'
        self._topic = cfg.TELEMETRY_MQTT_TOPIC_TEMPLATE % self._donkey_name
        self._use_json_format = cfg.TELEMETRY_MQTT_JSON_ENABLE
        self._mqtt_client = MQTTClient()
        self._mqtt_client.connect(self._mqtt_broker, cfg.TELEMETRY_MQTT_BROKER_PORT)
        self._mqtt_client.loop_start()
        self._on = True
        if cfg.TELEMETRY_LOGGING_ENABLE:
            self.setLevel(logging.getLevelName(cfg.TELEMETRY_LOGGING_LEVEL))
            self.setFormatter(logging.Formatter(cfg.TELEMETRY_LOGGING_FORMAT))
            logger.addHandler(self)

    def add_step_inputs(self, inputs, types):
   
        # Add inputs if supported and not yet registered
        for ind in range(0, len(inputs or [])):
            if types[ind] in ['float', 'str', 'int'] and inputs[ind] not in self._step_inputs:
                self._step_inputs.append(inputs[ind])
                self._step_types.append(types[ind])
                
        return self._step_inputs, self._step_types        

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
        Logging interface (to allow to use Python logging module to log directly to telemetry)
        """
        msg = {LOG_MQTT_KEY: self.format(record)}
        self.report(msg)

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

            try:
                self._mqtt_client.publish(self._topic, payload)
            except Exception as e:
                logger.error(f'Error publishing log {self._topic}: {e}')
        else:
            # Publish only the last timestamp for per step metrics
            last_sample = packet[list(packet)[-1]]
            for k, v in last_sample.items():
                if k in self._step_inputs:
                    topic = f'{self._topic}/{k}'
                    
                    try:
                        # Convert unsupported numpy types to python standard
                        if isinstance(v, np.generic):
                            v = np.asscalar(v)

                        self._mqtt_client.publish(topic, v)
                    except TypeError:
                        logger.error(f'Cannot publish topic "{topic}" with value of type {type(v)}')
                    except Exception as e:
                        logger.error(f'Error publishing log {topic}: {e}')

            # Publish all logs
            for tm, sample in packet.items():
                if LOG_MQTT_KEY in sample:
                    topic = f'{self._topic}/{LOG_MQTT_KEY}'
                    try:
                        self._mqtt_client.publish(topic, sample[LOG_MQTT_KEY])
                    except Exception as e:
                        logger.error(f'Error publishing log {topic}: {e}')

        self._total_updates += 1
        return

    def run(self, *args):
        """
        API function needed to use as a Donkey part. Accepts values,
        pairs them with their inputs keys and saves them to disk.
        """
        assert len(self._step_inputs) == len(args)
        
        # Add to queue
        record = dict(zip(self._step_inputs, args))
        self.report(record)

        # Periodic publish
        curr_time = time.time()
        if curr_time - self._last_publish > self.PUBLISH_PERIOD and self.qsize > 0:

            self.publish()
            self._last_publish = curr_time
        return self.qsize

    def run_threaded(self, *args):

        assert len(self._step_inputs) == len(args)

        # Add to queue
        record = dict(zip(self._step_inputs, args))
        self.report(record)
        return self.qsize

    def update(self):
        logger.info(f"Telemetry MQTT server connected (publishing: { ', '.join(self._step_inputs) })")
        while self._on:
            self.publish()
            time.sleep(self.PUBLISH_PERIOD)

    def shutdown(self):
        # indicate that the thread should be stopped
        self._on = False
        logger.debug('Stopping MQTT Telemetry')
        time.sleep(.2)
