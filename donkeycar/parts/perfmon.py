#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance monitor for analyzing real-time CPU/mem/execution frequency

author: @miro (Meir Tseitlin) 2020

Note:
"""
import time
import psutil


class PerfMonitor:

    def __init__(self, cfg):

        self.STATS_BUFFER_SIZE = 10
        self._calc_buffer = [cfg.DRIVE_LOOP_HZ for i in range(self.STATS_BUFFER_SIZE)]
        self._runs_counter = 0
        self._last_calc_time = time.time()
        self._on = True
        self._update_metrics()
        print("Performance monitor activated.")

    def _update_metrics(self):
        self._mem_percent = psutil.virtual_memory().percent
        self._cpu_percent = psutil.cpu_percent()

    def update(self):
        while self._on:
            self._update_metrics()
            time.sleep(2)

    def shutdown(self):
        # indicate that the thread should be stopped
        self._on = False
        print('Stopping Perf Monitor')
        time.sleep(.2)

    def run_threaded(self):

        # Calc real frequency
        curr_time = time.time()
        if curr_time - self._last_calc_time > 1:
            self._calc_buffer[int(curr_time) % self.STATS_BUFFER_SIZE] = self._runs_counter
            self._runs_counter = 0
            self._last_calc_time = curr_time

        self._runs_counter += 1

        vehicle_frequency = float(sum(self._calc_buffer)) / self.STATS_BUFFER_SIZE

        return self._cpu_percent, self._mem_percent, vehicle_frequency
