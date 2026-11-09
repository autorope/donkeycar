"""Bounded asynchronous pose diagnostics; camera and Pi clocks are distinct."""
import json
import logging
import math
from pathlib import Path
import queue
import threading
import time


class MightyTiming:
    def __init__(self, directory='logs'):
        Path(directory).mkdir(parents=True, exist_ok=True)
        self.path = Path(directory) / ('mighty-timing-' + time.strftime('%Y%m%d-%H%M%S')
                                       + '-' + str(time.monotonic_ns()) + '.jsonl')
        self.file = self.path.open('x', buffering=65536)
        self.pending = queue.Queue(maxsize=8192)
        self.stopping = threading.Event()
        self.dropped = 0
        self.sequence = 0
        self.last_arrival = None
        self.last_stamp = None
        self.minimum_offset = None
        self.latest = {}
        self.epoch = 0
        self.newest_stamp = None
        self.rejected = 0
        self.worker = threading.Thread(target=self._write, daemon=True)
        self.worker.start()
        logging.info('Mighty timing log: %s (clock-relative delay, not absolute latency)', self.path)

    def record(self, kind, **fields):
        try:
            self.pending.put_nowait(dict(kind=kind, pi_monotonic=time.monotonic(),
                                         dropped_records=self.dropped, **fields))
        except queue.Full:
            self.dropped += 1

    def reset(self, reason):
        self.epoch += 1
        self.last_arrival = self.last_stamp = self.newest_stamp = None
        self.minimum_offset = None
        self.latest = {}
        self.record('pose_epoch', epoch=self.epoch, reason=reason)

    def pose(self, pose):
        now = time.monotonic()
        stamp = pose.get('timestamp_ns')
        stamp = stamp if (isinstance(stamp, (int, float)) and not isinstance(stamp, bool)
                          and math.isfinite(stamp) and stamp > 0) else None
        self.sequence += 1
        arrival_dt = None if self.last_arrival is None else now - self.last_arrival
        source_dt = None if stamp is None or self.last_stamp is None else (stamp-self.last_stamp)/1e9
        accepted = stamp is not None and (self.newest_stamp is None or stamp > self.newest_stamp)
        reason = None if accepted else ('missing_timestamp' if stamp is None else 'non_increasing_timestamp')
        if not accepted:
            self.rejected += 1
        excess = None
        if stamp is not None:
            offset = now - stamp/1e9
            self.minimum_offset = offset if self.minimum_offset is None else min(self.minimum_offset, offset)
            excess = 1000 * (offset-self.minimum_offset)
        details = dict(sequence=self.sequence, timestamp_ns=stamp,
                           arrival_monotonic=now, arrival_dt_ms=None if arrival_dt is None else arrival_dt*1000,
                           source_dt_ms=None if source_dt is None else source_dt*1000,
                           excess_delay_ms=excess, epoch=self.epoch)
        if accepted:
            self.latest = details
            self.newest_stamp = stamp
        self.last_arrival, self.last_stamp = now, stamp
        self.record('pose', **details, accepted=accepted, rejection_reason=reason,
                    rejected_total=self.rejected, pose=pose)
        return accepted

    def snapshot(self):
        result = dict(self.latest)
        if result:
            result['receive_age_ms'] = (time.monotonic()-result['arrival_monotonic'])*1000
        return result

    def _write(self):
        try:
            while not self.stopping.is_set() or not self.pending.empty():
                try:
                    row = self.pending.get(timeout=.25)
                except queue.Empty:
                    self.file.flush()
                    continue
                self.file.write(json.dumps(row, default=str) + '\n')
        except Exception:
            logging.exception('Mighty timing writer failed')
        finally:
            self.file.close()

    def close(self):
        self.stopping.set()
        self.worker.join(timeout=3)
