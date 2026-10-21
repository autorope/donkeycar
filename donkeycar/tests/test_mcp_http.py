"""
Tests for serving MCP over HTTP: the host check that guards against DNS
rebinding, and the MCP_SERVER_TOKEN bearer token.

The live tests start a real uvicorn server on a free port and talk to it over
a socket, because the point is what a request from the network gets back.
"""

import http.client
import importlib.util
import json
import socket
import threading
import time
from typing import ClassVar

import pytest

requires_mcp = pytest.mark.skipif(
    importlib.util.find_spec("mcp") is None,
    reason="the `mcp` extra is not installed (pip install 'donkeycar[mcp]')",
)

pytestmark = requires_mcp


class Cfg:
    MCP_COMMAND_TIMEOUT_S = 2.0
    CV_PIXELS_PER_INCH = 4.0
    MCP_SERVER_ALLOWED_HOSTS: ClassVar[list[str]] = []
    MCP_SERVER_TOKEN = None


TOKEN = "correct-horse-battery-staple"


class WithToken(Cfg):
    MCP_SERVER_TOKEN = TOKEN


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LiveServer:
    """A guarded MCP server on a free localhost port, for the length of a test."""

    def __init__(self, cfg=None, bind_host="127.0.0.1"):
        import uvicorn

        from donkeycar.parts.mcp_http import build_app
        from donkeycar.parts.mcp_server import MCPBridge

        self.cfg = cfg or Cfg()
        self.bridge = MCPBridge(self.cfg, serve=False)
        self.port = _free_port()
        app = build_app(
            self.bridge.build_server(), bind_host, self.cfg.MCP_SERVER_ALLOWED_HOSTS, self.cfg.MCP_SERVER_TOKEN
        )
        # Listen on loopback whatever the bind host the app was built for, so
        # the tests never open a port on the network.
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        deadline = time.monotonic() + 10
        while not self.server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("server did not start")
            time.sleep(0.02)
        return self

    def __exit__(self, *exc):
        self.server.should_exit = True
        self.thread.join(timeout=10)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}/mcp"

    def post(self, host_header, headers=None):
        """POST an MCP initialize with an explicit Host header; return (status, body)."""
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            }
        )
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.putrequest("POST", "/mcp", skip_host=True)
            conn.putheader("Host", host_header)
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Accept", "application/json, text/event-stream")
            for key, value in (headers or {}).items():
                conn.putheader(key, value)
            conn.putheader("Content-Length", str(len(body)))
            conn.endheaders(body.encode())
            response = conn.getresponse()
            return response.status, response.read().decode(errors="replace")
        finally:
            conn.close()


def call_tool(url, tool, headers=None):
    """Make a real MCP tool call over HTTP and return the result."""
    import anyio
    import httpx2
    from mcp.client.client import Client
    from mcp.client.streamable_http import streamable_http_client

    async def go():
        async with (
            httpx2.AsyncClient(headers=headers or {}) as http_client,
            Client(streamable_http_client(url, http_client=http_client)) as client,
        ):
            return await client.call_tool(tool, {})

    return anyio.run(go)


# ------------------------------------------------------------------ host names


def test_host_without_port():
    from donkeycar.parts.mcp_http import host_without_port

    assert host_without_port("car.local:8891") == "car.local"
    assert host_without_port("Car.Local") == "car.local"
    assert host_without_port("192.168.1.42:8891") == "192.168.1.42"
    assert host_without_port("[fe80::1]:8891") == "fe80::1"
    assert host_without_port("[::1]") == "::1"


def test_allowed_names_cover_loopback_the_machine_and_the_bind_address():
    from donkeycar.parts.mcp_http import allowed_host_names

    names = allowed_host_names("192.168.1.42")
    hostname = socket.gethostname().split(".")[0].lower()
    assert {"127.0.0.1", "localhost", "::1", "192.168.1.42"} <= set(names)
    assert hostname in names
    assert f"{hostname}.local" in names


def test_a_wildcard_bind_allows_the_machines_own_names_not_itself():
    from donkeycar.parts.mcp_http import allowed_host_names

    names = allowed_host_names("0.0.0.0")
    assert "0.0.0.0" not in names
    assert "localhost" in names
    assert socket.gethostname().split(".")[0].lower() in names


def test_configured_names_are_added_case_insensitively():
    from donkeycar.parts.mcp_http import allowed_host_names

    names = allowed_host_names("127.0.0.1", ["Racecar.Example"])
    assert "racecar.example" in names


# ------------------------------------------------------------------ live server


def test_the_bound_address_is_accepted_and_a_tool_call_works():
    with LiveServer() as live:
        result = call_tool(live.url, "get_autopilot")
    assert result.is_error is False


def test_a_foreign_host_is_refused_and_told_how_to_fix_it():
    """A DNS-rebinding page arrives with its own domain in the Host header."""
    with LiveServer() as live:
        status, body = live.post("evil.example:8891")
    assert status == 421
    assert "MCP_SERVER_ALLOWED_HOSTS" in body
    assert "evil.example" in body


def test_a_lan_bind_accepts_its_address_and_refuses_others():
    with LiveServer(bind_host="192.168.1.42") as live:
        accepted, _ = live.post("192.168.1.42:8891")
        refused, _ = live.post("192.168.1.99:8891")
    assert accepted == 200
    assert refused == 421


def test_a_configured_host_is_accepted():
    class Named(Cfg):
        MCP_SERVER_ALLOWED_HOSTS: ClassVar[list[str]] = ["racecar.example"]

    with LiveServer(Named()) as live:
        status, _ = live.post("racecar.example:8891")
    assert status == 200


def test_a_foreign_browser_origin_is_refused():
    """The SDK's own Origin check still runs behind the host check."""
    with LiveServer() as live:
        status, _ = live.post(f"127.0.0.1:{live.port}", headers={"Origin": "http://evil.example"})
    assert status == 403


# ------------------------------------------------------------------ token


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-the-token"},
        {"Authorization": f"Basic {TOKEN}"},
        {"Authorization": TOKEN},
        {"Authorization": f"Bearer {TOKEN}x"},
    ],
    ids=["missing", "wrong", "not-bearer", "no-scheme", "longer"],
)
def test_requests_without_the_right_token_are_refused(headers):
    with LiveServer(WithToken()) as live:
        status, body = live.post(f"127.0.0.1:{live.port}", headers=headers)
    assert status == 401
    assert "Authorization: Bearer" in body
    assert TOKEN not in body


def test_the_right_token_reaches_a_real_tool_call():
    with LiveServer(WithToken()) as live:
        result = call_tool(live.url, "get_autopilot", headers={"Authorization": f"Bearer {TOKEN}"})
    assert result.is_error is False


def test_a_refused_token_is_not_logged(caplog):
    """Logs get pasted into issues; a token in them is a token given away."""
    with caplog.at_level("WARNING"), LiveServer(WithToken()) as live:
        live.post(f"127.0.0.1:{live.port}", headers={"Authorization": "Bearer guessed-wrong"})
    assert "Refused a request with a wrong token" in caplog.text
    assert "guessed-wrong" not in caplog.text
    assert TOKEN not in caplog.text


def test_the_host_check_comes_before_the_token():
    """A rebinding page with a stolen token is still refused for its Host."""
    with LiveServer(WithToken()) as live:
        status, _ = live.post("evil.example", headers={"Authorization": f"Bearer {TOKEN}"})
    assert status == 421


def _serve_without_listening(monkeypatch, host, token):
    """Run serve_http's startup logging without binding a socket."""
    import uvicorn

    from donkeycar.parts.mcp_http import serve_http
    from donkeycar.parts.mcp_server import MCPBridge

    monkeypatch.setattr(uvicorn.Server, "run", lambda self: None)
    serve_http(MCPBridge(Cfg(), serve=False).build_server(), host, _free_port(), token=token)


def test_a_network_bind_without_a_token_warns(monkeypatch, caplog):
    with caplog.at_level("WARNING"):
        _serve_without_listening(monkeypatch, "0.0.0.0", None)
    assert "NO TOKEN" in caplog.text
    assert "MCP_SERVER_TOKEN" in caplog.text


def test_a_loopback_bind_without_a_token_does_not_warn(monkeypatch, caplog):
    with caplog.at_level("WARNING"):
        _serve_without_listening(monkeypatch, "127.0.0.1", None)
    assert "NO TOKEN" not in caplog.text


def test_a_network_bind_with_a_token_does_not_warn(monkeypatch, caplog):
    with caplog.at_level("INFO"):
        _serve_without_listening(monkeypatch, "0.0.0.0", TOKEN)
    assert "NO TOKEN" not in caplog.text
    assert "must carry the MCP_SERVER_TOKEN" in caplog.text
    assert TOKEN not in caplog.text
