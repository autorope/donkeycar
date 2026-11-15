"""Pose ordering and timing diagnostics for the Mighty camera (see MightyTiming)."""
import json
import logging
import math
from pathlib import Path
import queue
import threading
import time


class MightyTiming:
    """Decides which Mighty poses are in order, and logs their timing to a file.

    `MightyPose` owns one of these. It has two jobs.

    1. **Ordering gate.** `pose()` is called for every public body pose the
       SDK delivers. It returns True only when the pose's camera timestamp
       (`timestamp_ns`) is positive, finite and newer than every pose accepted
       so far in the current *epoch*. `MightyPose` keeps only accepted poses,
       so a late, duplicate or timestamp-less packet can never replace a newer
       pose or make a stale one look fresh. `reset()` starts a new epoch, for
       example after a camera reset or VIO restart, when the camera's
       timestamps may start again from a lower value.

    2. **Timing diagnostics.** Every pose (accepted or not), plus whatever
       `MightyPose` passes to `record()` (VIO state, camera resets, per-loop
       samples, SDK statistics, the high-rate-pose reply), is written as one
       JSON object per line to `<directory>/mighty-timing-<date>-<time>-<ns>.jsonl`.
       `snapshot()` returns the timing of the newest accepted pose. `MightyPose`
       publishes that as `mighty/timing`, and `path_follow` logs it as
       `DrivePoseTiming`.

    The camera and the Pi have separate clocks, so true latency cannot be
    measured. Instead each pose's `excess_delay_ms` is how much later it
    arrived, relative to its camera timestamp, than the quickest-arriving pose
    of the epoch: 0 for the quickest, and larger when a pose was held up. Other
    fields per pose: `arrival_dt_ms` (Pi time since the previous pose arrived),
    `source_dt_ms` (camera time since the previous pose), `sequence`, `epoch`,
    `accepted`, `rejection_reason`.

    Writing never blocks the caller. Rows go to a queue of up to 8192 that a
    background thread writes out. When the queue is full, new rows are dropped
    and counted in `dropped_records` on later rows. Call `close()` to flush and
    close the file.

    Thread safety: `record()` may be called from any thread. `pose()`,
    `reset()` and `snapshot()` share state and must be serialised by the
    caller; `MightyPose` calls them under its `pose_lock`.
    """
    def __init__(self, directory='logs'):
        """Create `directory` if needed, open a new log file, start the writer."""
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
        """Queue one log row: `kind`, the Pi monotonic time, and `fields`."""
        try:
            self.pending.put_nowait(dict(kind=kind, pi_monotonic=time.monotonic(),
                                         dropped_records=self.dropped, **fields))
        except queue.Full:
            self.dropped += 1

    def reset(self, reason):
        """Start a new epoch: forget the newest timestamp and the delay baseline.

        The next pose with any valid timestamp is accepted, even one older than
        before the reset. A `pose_epoch` row records `reason`.
        """
        self.epoch += 1
        self.last_arrival = self.last_stamp = self.newest_stamp = None
        self.minimum_offset = None
        self.latest = {}
        self.record('pose_epoch', epoch=self.epoch, reason=reason)

    def pose(self, pose):
        """Log a received pose and return True if it is newer than any accepted.

        See the class docstring for the rule and the fields logged.
        """
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
        """Timing of the newest accepted pose, plus how long ago it arrived.

        A copy of that pose's fields with `receive_age_ms` added; an empty dict
        before the first accepted pose of an epoch.
        """
        result = dict(self.latest)
        if result:
            result['receive_age_ms'] = (time.monotonic()-result['arrival_monotonic'])*1000
        return result

    def _write(self):
        """Writer thread: drain the queue to the file until close() is called."""
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
        """Stop the writer after it drains the queue, and close the file.

        Waits up to 3 s.
        """
        self.stopping.set()
        self.worker.join(timeout=3)
