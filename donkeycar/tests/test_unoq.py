"""
Tests for the Arduino UNO Q bridge client and drive train.

No hardware, no arduino-router and no MCU: a fake socket speaks MsgPack-RPC
back, so these run anywhere.
"""
import queue
import threading
import types

import pytest

msgpack = pytest.importorskip("msgpack")

from donkeycar.parts.unoq_bridge import (  # noqa: E402
    UnoQBridge, UnoQBridgeError, DEFAULT_ADDRESS,
)
from donkeycar.parts.unoq import UnoQRcHatDriver, UnoQRcHatController  # noqa: E402


class FakeSocket:
    """
    Stands in for a socket to arduino-router.

    Requests are answered from `methods`; anything sent can be inspected in
    `sent`. `push()` injects a message as though the MCU had sent it.
    """

    def __init__(self, methods=None, answer_requests=True):
        self.methods = methods or {}
        self.answer_requests = answer_requests
        self.sent = []
        self._inbound = queue.Queue()
        self.closed = False

    # -- socket surface --
    def settimeout(self, t): pass

    def sendall(self, data):
        if self.closed:
            raise OSError("socket closed")
        unpacker = msgpack.Unpacker(raw=False)
        unpacker.feed(data)
        for msg in unpacker:
            self.sent.append(msg)
            if msg[0] == 0 and self.answer_requests:      # request
                _, msgid, method, params = msg
                if method in self.methods:
                    try:
                        self.push([1, msgid, None, self.methods[method](*params)])
                    except Exception as e:
                        self.push([1, msgid, str(e), None])
                else:
                    self.push([1, msgid, None, None])      # accept, e.g. $/register

    def recv(self, n):
        if self.closed:
            return b""
        item = self._inbound.get()
        return item if item is not None else b""

    def shutdown(self, how): pass

    def close(self):
        self.closed = True
        self._inbound.put(None)

    # -- test helpers --
    def push(self, message):
        self._inbound.put(msgpack.packb(message, use_bin_type=True))

    def requests_for(self, method):
        return [m for m in self.sent if m[0] == 0 and m[2] == method]

    def notifications_for(self, method):
        return [m for m in self.sent if m[0] == 2 and m[1] == method]


def make_bridge(sock, **kw):
    return UnoQBridge(address=DEFAULT_ADDRESS, timeout=2.0,
                      connect=lambda a, t: sock, **kw)


#
# ----- the bridge client -----
#
def test_call_round_trips_a_result():
    sock = FakeSocket({"set_pulse": lambda st, th: 0})
    b = make_bridge(sock)
    assert b.call("set_pulse", 1500, 1500) == 0
    req = sock.requests_for("set_pulse")[0]
    assert req[0] == 0 and req[2] == "set_pulse" and req[3] == [1500, 1500]
    b.close()


def test_call_uses_msgpack_rpc_framing():
    """[0, msgid, method, params] out; [1, msgid, error, result] back."""
    sock = FakeSocket({"ping": lambda v: v})
    b = make_bridge(sock)
    assert b.call("ping", 7) == 7
    kind, msgid, method, params = sock.requests_for("ping")[0]
    assert (kind, method, params) == (0, "ping", [7])
    assert isinstance(msgid, int)
    b.close()


def test_msgids_are_distinct_across_calls():
    sock = FakeSocket({"ping": lambda v: v})
    b = make_bridge(sock)
    for i in range(5):
        b.call("ping", i)
    ids = [m[1] for m in sock.requests_for("ping")]
    assert len(set(ids)) == 5
    b.close()


def test_remote_error_raises():
    def boom():
        raise ValueError("no such pin")
    sock = FakeSocket({"bad": boom})
    b = make_bridge(sock)
    with pytest.raises(UnoQBridgeError, match="no such pin"):
        b.call("bad")
    b.close()


def test_timeout_raises_rather_than_hanging():
    sock = FakeSocket(answer_requests=False)
    b = make_bridge(sock)
    with pytest.raises(UnoQBridgeError, match="Timed out"):
        b.call("never_answers", timeout=0.2)
    b.close()


def test_notify_sends_no_msgid_and_expects_no_reply():
    sock = FakeSocket()
    b = make_bridge(sock)
    b.notify("rc_input", 1500, 1500, 1000)
    assert sock.notifications_for("rc_input")[0] == [2, "rc_input", [1500, 1500, 1000]]
    b.close()


def test_provide_registers_with_the_router():
    """The MCU can only push to us if the router knows we handle it."""
    sock = FakeSocket()
    b = make_bridge(sock)
    b.provide("rc_input", lambda *a: None)
    assert sock.requests_for("$/register")[0][3] == ["rc_input"]
    b.close()


def test_pushed_notification_reaches_the_handler():
    sock = FakeSocket()
    b = make_bridge(sock)
    got = []
    seen = threading.Event()
    b.provide("rc_input", lambda st, th, md: (got.append((st, th, md)), seen.set()))
    sock.push([2, "rc_input", [1600, 1400, 1000]])
    assert seen.wait(2.0)
    assert got == [(1600, 1400, 1000)]
    b.close()


def test_inbound_request_is_answered():
    sock = FakeSocket()
    b = make_bridge(sock)
    b.provide("add", lambda a, c: a + c)
    sock.push([0, 42, "add", [2, 3]])
    for _ in range(200):
        replies = [m for m in sock.sent if m[0] == 1 and m[1] == 42]
        if replies:
            assert replies[0] == [1, 42, None, 5]
            break
        threading.Event().wait(0.01)
    else:
        pytest.fail("inbound request was never answered")
    b.close()


def test_unknown_inbound_notification_is_ignored():
    sock = FakeSocket()
    b = make_bridge(sock)
    sock.push([2, "nobody_handles_this", [1]])
    sock.push([2, "nobody_handles_this", [2]])
    assert b.call("$/register", "x") is None   # still responsive
    b.close()


@pytest.mark.parametrize("bad", [[], "not a list", [99, 1, 2, 3], [1, 2]])
def test_malformed_messages_do_not_kill_the_reader(bad):
    sock = FakeSocket({"ping": lambda: "ok"})
    b = make_bridge(sock)
    sock.push(bad)
    assert b.call("ping") == "ok"
    b.close()


def test_unprovide_stops_dispatch():
    sock = FakeSocket()
    b = make_bridge(sock)
    got = []
    b.provide("rc_input", lambda *a: got.append(a))
    b.unprovide("rc_input")
    sock.push([2, "rc_input", [1500, 1500, 1000]])
    threading.Event().wait(0.2)
    assert got == []
    b.close()


def test_unprovide_survives_a_router_without_unregister():
    """
    The arduino-router build on the tested board has no `$/unregister`.
    Dispatch must still stop, and it must not raise into a part's shutdown.
    """
    def refuse(*_a):
        raise ValueError("method $/unregister not available")
    sock = FakeSocket({"$/unregister": refuse})
    b = make_bridge(sock)
    got = []
    b.provide("rc_input", lambda *a: got.append(a))
    b.unprovide("rc_input")               # must not raise
    sock.push([2, "rc_input", [1500, 1500, 1000]])
    threading.Event().wait(0.2)
    assert got == []
    b.close()


def test_close_is_idempotent_and_blocks_further_calls():
    sock = FakeSocket({"ping": lambda: 1})
    b = make_bridge(sock)
    b.close()
    b.close()
    with pytest.raises(UnoQBridgeError):
        b.call("ping")


def test_unsupported_address_is_rejected():
    with pytest.raises(UnoQBridgeError, match="Unsupported bridge address"):
        UnoQBridge(address="serial:///dev/ttyHS1")


def test_context_manager_closes():
    sock = FakeSocket()
    with make_bridge(sock) as b:
        assert "open" in repr(b)
    assert sock.closed


#
# ----- the drive train -----
#
def cfg_stub(**over):
    c = types.SimpleNamespace(
        UNOQ_BRIDGE_ADDRESS=DEFAULT_ADDRESS,
        UNOQ_STEERING_MID=1500,
        UNOQ_MAX_FORWARD=2000,
        UNOQ_STOPPED_PWM=1500,
        UNOQ_MAX_REVERSE=1000,
    )
    for k, v in over.items():
        setattr(c, k, v)
    return c


@pytest.fixture
def driver_pair():
    sock = FakeSocket({"set_pulse": lambda st, th: 0})
    b = make_bridge(sock)
    d = UnoQRcHatDriver(cfg_stub(), bridge=b)
    yield d, sock
    b.close()


def test_driver_neutralises_on_construction(driver_pair):
    """A car must not inherit a throttle from whatever ran before."""
    d, sock = driver_pair
    assert sock.requests_for("set_pulse")[0][3] == [1500, 1500]


def test_driver_sends_one_call_for_both_channels(driver_pair):
    d, sock = driver_pair
    before = len(sock.requests_for("set_pulse"))
    d.run(0.5, 0.5)
    assert len(sock.requests_for("set_pulse")) == before + 1


@pytest.mark.parametrize("throttle,expected", [
    (0.0, 1500), (1.0, 2000), (-1.0, 1000), (0.5, 1750), (-0.5, 1250),
])
def test_driver_maps_throttle_to_pulse(driver_pair, throttle, expected):
    d, sock = driver_pair
    d.run(0.0, throttle)
    assert sock.requests_for("set_pulse")[-1][3][1] == expected


@pytest.mark.parametrize("steering,expected", [
    (0.0, 1500), (1.0, 2250), (-1.0, 750),
])
def test_driver_maps_steering_to_pulse(driver_pair, steering, expected):
    d, sock = driver_pair
    d.run(steering, 0.0)
    assert sock.requests_for("set_pulse")[-1][3][0] == expected


@pytest.mark.parametrize("value", [2.0, -2.0, 99.0])
def test_driver_clamps_out_of_range_input(driver_pair, value):
    d, sock = driver_pair
    d.run(value, value)
    st, th = sock.requests_for("set_pulse")[-1][3]
    assert 500 <= st <= 2500 and 500 <= th <= 2500


def test_driver_survives_a_dead_bridge():
    """A failed send must be logged, not raised into the drive loop."""
    sock = FakeSocket({"set_pulse": lambda st, th: 0})
    b = make_bridge(sock)
    d = UnoQRcHatDriver(cfg_stub(), bridge=b)
    b.close()
    d.run(0.5, 0.5)          # must not raise
    d.shutdown()             # nor here


def test_driver_stops_the_car_on_shutdown(driver_pair):
    d, sock = driver_pair
    d.run(0.0, 1.0)
    d.shutdown()
    assert sock.requests_for("set_pulse")[-1][3] == [1500, 1500]


#
# ----- the RC controller -----
#
@pytest.fixture
def controller_pair():
    sock = FakeSocket()
    b = make_bridge(sock)
    c = UnoQRcHatController(cfg_stub(), bridge=b)
    yield c, sock
    b.close()


def test_controller_registers_for_pushed_rc(controller_pair):
    c, sock = controller_pair
    assert sock.requests_for("$/register")[0][3] == ["rc_input"]


@pytest.mark.parametrize("steering_us,expected", [
    (1500, 0.0), (2000, 1.0), (1000, -1.0),
])
def test_controller_maps_rc_steering(controller_pair, steering_us, expected):
    c, _ = controller_pair
    c._on_rc_input(steering_us, 1500, 1000)
    assert c.angle == pytest.approx(expected, abs=0.01)


@pytest.mark.parametrize("throttle_us,expected", [
    (1500, 0.0), (2000, 1.0), (1000, -1.0),
])
def test_controller_maps_rc_throttle(controller_pair, throttle_us, expected):
    c, _ = controller_pair
    c._on_rc_input(1500, throttle_us, 1000)
    assert c.throttle == pytest.approx(expected, abs=0.01)


def test_controller_ignores_absent_channels(controller_pair):
    """
    A channel with no signal reads 0.  Mapping that as a pulse would come out
    as full reverse, which would be a car that drives off on its own.
    """
    c, _ = controller_pair
    c._on_rc_input(1700, 1700, 1000)
    angle, throttle = c.angle, c.throttle
    c._on_rc_input(0, 0, 0)
    assert (c.angle, c.throttle) == (angle, throttle)


def test_controller_applies_a_throttle_deadzone(controller_pair):
    c, _ = controller_pair
    c.DEAD_ZONE = 0.2
    c._on_rc_input(1500, 1510, 1000)
    assert c.throttle == 0.0


def test_controller_run_threaded_reports_latest(controller_pair):
    c, _ = controller_pair
    c._on_rc_input(2000, 2000, 1000)
    angle, throttle, mode, recording = c.run_threaded(None, "user", False)
    assert angle == pytest.approx(1.0, abs=0.01)
    assert throttle == pytest.approx(1.0, abs=0.01)
    assert mode == "user"


def test_controller_survives_a_garbled_frame(controller_pair):
    c, _ = controller_pair
    c._on_rc_input("nonsense", None, 0)   # must not raise
    assert c.angle == 0.0


def test_controller_polling_fallback_parses_get_rc():
    sock = FakeSocket({"get_rc": lambda: "2000, 1000, 1500, 12"})
    b = make_bridge(sock)
    c = UnoQRcHatController(cfg_stub(UNOQ_RC_POLL=True), bridge=b)
    c.read_rc()
    assert c.angle == pytest.approx(1.0, abs=0.01)
    assert c.throttle == pytest.approx(-1.0, abs=0.01)
    b.close()


def test_controller_polling_ignores_a_short_reply():
    sock = FakeSocket({"get_rc": lambda: "garbage"})
    b = make_bridge(sock)
    c = UnoQRcHatController(cfg_stub(UNOQ_RC_POLL=True), bridge=b)
    c.read_rc()
    assert c.angle == 0.0
    b.close()
