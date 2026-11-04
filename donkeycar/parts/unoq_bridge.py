"""
unoq_bridge.py - MsgPack-RPC client for the Arduino UNO Q's router bridge.

On the UNO Q the Arduino-shaped header pins belong to the STM32U585, not the
Qualcomm SoC running Linux, so donkeycar cannot reach a servo, an ESC or an
RC receiver through /dev/i2c-* or any GPIO character device.  It has to ask
the MCU, and the path to the MCU is `arduino-router`, a daemon that owns the
SoC-to-MCU UART (/dev/ttyHS1) and speaks MsgPack-RPC on a unix socket.

Arduino ship a client for this in `arduino_app_bricks`, but that package lives
only inside App Lab's Docker image -- it is not on PyPI and not installed on
the board -- and most of it is AI and cloud features donkeycar never uses.
The wire format is just standard MsgPack-RPC, so this speaks it directly and
depends on nothing but msgpack:

    request      [0, msgid, method, params]
    response     [1, msgid, error, result]
    notification [2, method, params]

Registering a handler so the MCU can push to us is `$/register`, which is the
router's own convention.

Typical use, against the unoq_rc_hat sketch in arduino/:

    bridge = UnoQBridge()
    bridge.call("set_pulse", 1500, 1500)
    bridge.provide("rc_input", lambda st, th, mode: ...)

"""
from typing import Any, Callable, Dict, Optional, Tuple
import logging
import socket
import threading

logger = logging.getLogger(__name__)

DEFAULT_ADDRESS = "unix:///var/run/arduino-router.sock"

# MsgPack-RPC message types
_REQUEST = 0
_RESPONSE = 1
_NOTIFICATION = 2

_REGISTER = "$/register"
_UNREGISTER = "$/unregister"


class UnoQBridgeError(RuntimeError):
    """A call failed, or the bridge is not usable."""


def _connect(address: str, timeout: float) -> socket.socket:
    """
    Open a socket to the router.
    :param address: "unix:///path/to.sock" or "tcp://host:port"
    :param timeout: connect timeout in seconds
    :return: a connected socket
    :except: UnoQBridgeError if the address is malformed or unreachable
    """
    if address.startswith("unix://"):
        path = address[len("unix://"):]
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect(path)
        except OSError as e:
            sock.close()
            raise UnoQBridgeError(
                f"Cannot reach arduino-router at {path}: {e}. "
                "Is the arduino-router service running?") from e
        return sock
    if address.startswith("tcp://"):
        host, _, port = address[len("tcp://"):].rpartition(":")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((host, int(port)))
        except OSError as e:
            sock.close()
            raise UnoQBridgeError(f"Cannot reach arduino-router at {address}: {e}") from e
        return sock
    raise UnoQBridgeError(
        f"Unsupported bridge address {address!r}; expected unix:// or tcp://")


class UnoQBridge:
    """
    A MsgPack-RPC connection to arduino-router.

    Thread safe: a single reader thread demultiplexes responses to waiting
    callers and dispatches inbound requests and notifications to handlers.
    """

    def __init__(self, address: str = DEFAULT_ADDRESS,
                 timeout: float = 5.0,
                 connect: Callable[[str, float], socket.socket] = _connect) -> None:
        """
        :param address: router address, unix:// or tcp://
        :param timeout: default seconds to wait for a call's response
        :param connect: socket factory, injectable for testing
        :except: ImportError if msgpack is missing
        :except: UnoQBridgeError if the router cannot be reached
        """
        try:
            import msgpack
        except ImportError as e:
            raise ImportError(
                "The Arduino UNO Q bridge needs msgpack. "
                "Install it with 'pip install msgpack', or install donkeycar's "
                "unoq extra.") from e
        self._msgpack = msgpack

        self.address = address
        self.timeout = timeout
        self._sock = connect(address, timeout)
        # The reader blocks on recv, so it must not inherit the connect timeout.
        self._sock.settimeout(None)

        self._send_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._next_msgid = 0
        self._pending: Dict[int, Tuple[threading.Event, list]] = {}
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._closed = False

        self._reader = threading.Thread(
            target=self._read_loop, name="unoq-bridge", daemon=True)
        self._reader.start()
        logger.info(f"UNO Q bridge connected to {address}")

    #
    # ----- outbound -----
    #
    def _send(self, message: list) -> None:
        payload = self._msgpack.packb(message, use_bin_type=True)
        with self._send_lock:
            if self._closed:
                raise UnoQBridgeError("Bridge is closed")
            try:
                self._sock.sendall(payload)
            except OSError as e:
                raise UnoQBridgeError(f"Bridge send failed: {e}") from e

    def notify(self, method: str, *params: Any) -> None:
        """
        Fire and forget.  No reply is waited for, so this costs almost nothing
        and cannot report a remote error.
        """
        self._send([_NOTIFICATION, method, list(params)])

    def call(self, method: str, *params: Any,
             timeout: Optional[float] = None) -> Any:
        """
        Call a method the MCU provides and wait for its result.
        :param timeout: seconds; defaults to the bridge's timeout
        :return: whatever the method returned
        :except: UnoQBridgeError on a remote error or a timeout
        """
        with self._state_lock:
            if self._closed:
                raise UnoQBridgeError("Bridge is closed")
            self._next_msgid = (self._next_msgid + 1) % (2 ** 32)
            msgid = self._next_msgid
            done, slot = threading.Event(), []
            self._pending[msgid] = (done, slot)

        try:
            self._send([_REQUEST, msgid, method, list(params)])
            if not done.wait(self.timeout if timeout is None else timeout):
                raise UnoQBridgeError(
                    f"Timed out calling {method!r} after "
                    f"{self.timeout if timeout is None else timeout}s")
        finally:
            with self._state_lock:
                self._pending.pop(msgid, None)

        error, result = slot[0]
        if error is not None:
            raise UnoQBridgeError(f"Remote error from {method!r}: {error}")
        return result

    #
    # ----- inbound -----
    #
    def provide(self, method: str, handler: Callable[..., Any]) -> None:
        """
        Register a handler the MCU can call or push to.  This is what makes
        the sketch's `Bridge.notify("rc_input", ...)` reach us.
        :except: UnoQBridgeError if the router refuses the registration
        """
        if not callable(handler):
            raise ValueError(f"handler for {method!r} must be callable")
        with self._state_lock:
            self._handlers[method] = handler
        try:
            self.call(_REGISTER, method)
        except UnoQBridgeError:
            with self._state_lock:
                self._handlers.pop(method, None)
            raise

    def unprovide(self, method: str) -> None:
        """
        Stop handling a method.  Safe to call when not registered.

        The local handler is dropped first, so dispatch stops either way.
        Telling the router is best-effort: not every arduino-router build
        implements `$/unregister` (the one on the tested board does not), and
        that is harmless -- it will route a method we no longer answer, and
        an unhandled inbound notification is already ignored.
        """
        with self._state_lock:
            had = self._handlers.pop(method, None) is not None
        if not had:
            return
        try:
            self.call(_UNREGISTER, method)
        except UnoQBridgeError as e:
            logger.debug(
                f"Router would not unregister {method!r} ({e}); "
                "dispatch is stopped locally regardless")

    def _read_loop(self) -> None:
        unpacker = self._msgpack.Unpacker(raw=False, strict_map_key=False)
        while not self._closed:
            try:
                data = self._sock.recv(4096)
            except OSError:
                break
            if not data:
                break
            unpacker.feed(data)
            for message in unpacker:
                try:
                    self._dispatch(message)
                except Exception as e:
                    logger.error(f"Error handling bridge message: {e}")
        if not self._closed:
            logger.warning("UNO Q bridge connection closed by the router")
        # Never leave a caller blocked on a connection that has gone away.
        with self._state_lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for done, slot in pending:
            slot.append(("bridge connection closed", None))
            done.set()

    def _dispatch(self, message: Any) -> None:
        if not isinstance(message, (list, tuple)) or not message:
            logger.warning(f"Ignoring malformed bridge message: {message!r}")
            return

        kind = message[0]

        if kind == _RESPONSE and len(message) == 4:
            _, msgid, error, result = message
            with self._state_lock:
                waiter = self._pending.get(msgid)
            if waiter is None:
                # A late reply to a call that already timed out.
                return
            done, slot = waiter
            slot.append((error, result))
            done.set()
            return

        if kind == _NOTIFICATION and len(message) == 3:
            _, method, params = message
            handler = self._handlers.get(method)
            if handler is None:
                return
            handler(*(params or []))
            return

        if kind == _REQUEST and len(message) == 4:
            _, msgid, method, params = message
            handler = self._handlers.get(method)
            if handler is None:
                self._send([_RESPONSE, msgid, f"Method not found: {method!r}", None])
                return
            try:
                self._send([_RESPONSE, msgid, None, handler(*(params or []))])
            except Exception as e:
                self._send([_RESPONSE, msgid, str(e), None])
            return

        logger.warning(f"Ignoring unknown bridge message type: {message!r}")

    #
    # ----- lifecycle -----
    #
    def close(self) -> None:
        """Close the connection.  Idempotent."""
        with self._send_lock:
            if self._closed:
                return
            self._closed = True
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._sock.close()
        logger.info("UNO Q bridge closed")

    def __enter__(self) -> "UnoQBridge":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return (f"UnoQBridge(address={self.address!r}, "
                f"{'closed' if self._closed else 'open'})")


#
# ----- command line -----
#
# Talking to the MCU from a shell, for bring-up and field debugging:
#
#   python -m donkeycar.parts.unoq_bridge get_last_pulse
#   python -m donkeycar.parts.unoq_bridge set_pulse 1500 1500
#   python -m donkeycar.parts.unoq_bridge --listen rc_input --seconds 3
#
def _coerce(value: str) -> Any:
    """CLI args arrive as strings; send numbers as numbers."""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


if __name__ == "__main__":
    import argparse
    import sys
    import time

    parser = argparse.ArgumentParser(
        description="Call a method the Arduino UNO Q's MCU provides, or watch "
                    "for values it pushes. Requires the arduino-router service "
                    "and a sketch such as arduino/unoq_rc_hat/.")
    parser.add_argument("method", nargs="?",
                        help="method to call, e.g. get_last_pulse or set_pulse")
    parser.add_argument("params", nargs="*",
                        help="arguments to the method, e.g. 1500 1500")
    parser.add_argument("-a", "--address", default=DEFAULT_ADDRESS,
                        help=f"router address (default {DEFAULT_ADDRESS})")
    parser.add_argument("-l", "--listen", default=None,
                        help="instead of calling, print values the MCU pushes "
                             "under this name, e.g. rc_input")
    parser.add_argument("-s", "--seconds", type=float, default=3.0,
                        help="how long to listen for (default 3)")
    parser.add_argument("-t", "--timeout", type=float, default=5.0,
                        help="seconds to wait for a reply (default 5)")
    args = parser.parse_args()

    if not args.method and not args.listen:
        parser.error("give a method to call, or --listen NAME")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        bridge = UnoQBridge(args.address, timeout=args.timeout)
    except (UnoQBridgeError, ImportError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.listen:
            count = 0

            def _show(*values: Any) -> None:
                global count
                count += 1
                print(f"{args.listen}: {', '.join(str(v) for v in values)}")

            bridge.provide(args.listen, _show)
            print(f"listening for {args.listen!r} for {args.seconds}s "
                  f"(Ctrl-C to stop)")
            try:
                time.sleep(args.seconds)
            except KeyboardInterrupt:
                pass
            print(f"{count} pushed in {args.seconds}s "
                  f"({count / args.seconds:.1f} Hz)")
            bridge.unprovide(args.listen)
        else:
            result = bridge.call(args.method,
                                 *[_coerce(p) for p in args.params])
            print(result)
    except UnoQBridgeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        bridge.close()
