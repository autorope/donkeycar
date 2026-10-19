"""
Serve the MCP tool surface over HTTP, guarded for a car on a shared network.

Both run modes -- `donkey mcp` and `manage.py drive --mcp` -- start the server
here, so the guard cannot be on in one and missing in the other.

The guard does two things. With MCP_SERVER_TOKEN set, it refuses any request
that does not carry `Authorization: Bearer <token>`: that is what keeps a guest
on the WiFi off the throttle. And it checks the request's Host header against
the names this car is reached by. That is DNS-rebinding protection: without it, a web page open in
any browser on the network can resolve its own domain to the car's address and
call the tools from inside that browser. The SDK only enables the check when
bound to 127.0.0.1; on a LAN address, which is how a laptop reaches the car, it
is off. Here it is always on.

Kept apart from `mcp_server` for the same reason as `mcp_tools`: it imports
the optional `mcp` package (and the uvicorn and starlette it brings) at module
scope.
"""

from __future__ import annotations

import hmac
import logging
import socket
from collections.abc import Iterable

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

LOCAL_NAMES = ("127.0.0.1", "localhost", "::1")

# Bind addresses that listen on every interface, so no single address names the car.
WILDCARD_BINDS = ("0.0.0.0", "::", "")


def _machine_names() -> list[str]:
    """The names this machine answers to: its hostname, short and with `.local`."""
    names: list[str] = []
    hostname = socket.gethostname()
    if hostname:
        short = hostname.split(".")[0]
        names += [hostname, short, f"{short}.local"]
    return names


def _machine_addresses() -> list[str]:
    """
    The addresses this machine reports for itself, for a wildcard bind.

    Two sources, because neither is reliable alone: the hostname can resolve to
    loopback only, and a machine with no default route has no primary address.
    """
    addresses: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            addresses.append(str(info[4][0]))
    except OSError:
        pass
    # The address a packet to the outside would leave from. connect() on UDP
    # sends nothing; it only asks the routing table.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 9))
            addresses.append(str(probe.getsockname()[0]))
    except OSError:
        pass
    return addresses


def allowed_host_names(bind_host: str, extra: Iterable[str] = ()) -> list[str]:
    """
    The Host header values a request may carry, without their port.

    The bind address, loopback, the machine's own names, every address it
    reports when bound to all interfaces, and whatever the car's config adds.
    """
    names: list[str] = [*LOCAL_NAMES, *_machine_names()]
    if bind_host in WILDCARD_BINDS:
        names += _machine_addresses()
    else:
        names.append(bind_host)
    names += [name for name in extra if name]

    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        key = name.strip("[]").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(key)
    return unique


def host_without_port(host_header: str) -> str:
    """`car.local:8891` -> `car.local`; `[fe80::1]:8891` -> `fe80::1`."""
    value = host_header.strip()
    if value.startswith("["):
        return value[1 : value.find("]")].lower() if "]" in value else value.lower()
    if value.count(":") == 1:
        return value.split(":", 1)[0].lower()
    # No port, or a bare IPv6 address.
    return value.lower()


def is_loopback(host: str) -> bool:
    return host.strip("[]").lower() in LOCAL_NAMES


class CarGuard:
    """
    ASGI middleware in front of the SDK's app: refuses requests whose Host is
    not one of the car's names, then requests without the right token.

    The SDK's own host check sits behind this and still runs, Origin included.
    This one runs first so that a refusal says how to fix it.

    The token is a shared secret checked here rather than through the SDK's
    `token_verifier`, which is built for OAuth: it needs an issuer, publishes
    OAuth discovery metadata, and its 401 sends clients off to log in to an
    authorization server the car does not have.
    """

    def __init__(self, app: ASGIApp, allowed_hosts: Iterable[str], token: str | None = None) -> None:
        self.app = app
        self.allowed_hosts = frozenset(allowed_hosts)
        self._expected = f"Bearer {token}".encode() if token else None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # Lifespan events start the SDK's session manager.
            await self.app(scope, receive, send)
            return

        headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope.get("headers", [])}
        host = host_without_port(headers.get("host", ""))
        if host not in self.allowed_hosts:
            logger.warning("Refused a request for host %r; allowed: %s", host, sorted(self.allowed_hosts))
            response = PlainTextResponse(
                f"Host {host!r} is not one this car answers to. If this is how you reach the car, add "
                f"{host!r} to MCP_SERVER_ALLOWED_HOSTS in myconfig.py and restart the server.",
                status_code=421,
            )
            await response(scope, receive, send)
            return

        if self._expected is not None:
            supplied = headers.get("authorization", "").encode("latin-1")
            # Constant time, so the response time does not leak how much of a
            # guess was right.
            if not hmac.compare_digest(supplied, self._expected):
                # Which of the two it was, never the value: logs get shared.
                reason = "no Authorization header" if not supplied else "a wrong token"
                logger.warning("Refused a request with %s", reason)
                response = PlainTextResponse(
                    "This car requires a token. Send 'Authorization: Bearer <MCP_SERVER_TOKEN>'.",
                    status_code=401,
                    headers={"WWW-Authenticate": 'Bearer realm="donkeycar"'},
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


def build_app(
    server: MCPServer, host: str, extra_allowed_hosts: Iterable[str] = (), token: str | None = None
) -> ASGIApp:
    """The guarded ASGI app for this server and bind address."""
    names = allowed_host_names(host, extra_allowed_hosts)
    # Brackets for IPv6 in the forms the SDK compares against.
    forms = [f"[{name}]" if ":" in name else name for name in names]
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[*forms, *(f"{form}:*" for form in forms)],
        allowed_origins=[f"http://{form}:*" for form in forms],
    )
    app = server.streamable_http_app(transport_security=security, host=host)
    return CarGuard(app, names, token)


def serve_http(
    server: MCPServer, host: str, port: int, extra_allowed_hosts: Iterable[str] = (), token: str | None = None
) -> None:
    """Run the guarded server on this thread until it is stopped."""
    app = build_app(server, host, extra_allowed_hosts, token)
    logger.info("MCP server listening on http://%s:%d/mcp", host, port)
    if token:
        logger.info("Requests must carry the MCP_SERVER_TOKEN bearer token.")
    elif not is_loopback(host):
        logger.warning(
            "MCP server is reachable from the network at %s with NO TOKEN: anyone who can reach this "
            "address can drive the car. Set MCP_SERVER_TOKEN in myconfig.py and restart.",
            host,
        )
    uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="info")).run()
