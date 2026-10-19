# MCP server token and DNS-rebinding protection — Plan

The docs promise a token and DNS-rebinding protection that the car does not have. With the
server bound to a LAN address, anyone on that network can call every tool, including `start`
and `cv_control-set_control`. This plan adds both, and makes the docs describe what exists.

**Branch:** `mcp-server`

---

## Progress — 0 of 3

- [ ] **A1** — One place that starts the HTTP server, with DNS-rebinding protection for the bound address
- [ ] **A2** — `MCP_SERVER_TOKEN`: requests without the right bearer token are refused
- [ ] **A3** — Docs: guide and HTML manual, including how each client sends the token

Each box is ticked in the commit that does the work. Ruff, mypy and the full test suite pass on
every commit.

---

## Decisions

Settled with Ed before A1 started.

| # | Question | Proposal | Why |
| --- | --- | --- | --- |
| T1 | How the token is checked | **Our own small middleware** around the SDK's HTTP app: a request without `Authorization: Bearer <token>` gets a plain `401`. Compared in constant time | The SDK's `token_verifier` is built for OAuth: it requires an issuer URL, publishes OAuth discovery metadata, and its `401` points clients at that metadata, so Claude Code and others try to start an OAuth login against a car that has no login. A shared secret needs none of that. |
| T2 | Where the token is set | `MCP_SERVER_TOKEN` in `myconfig.py`, default `None` (no token). No command-line flag | A flag puts the secret in `ps` output and shell history. `myconfig.py` is already where the car's local settings live and is never committed. |
| T3 | A LAN-bound server with no token | **Start, with a loud warning** naming the risk and the setting | Refusing would stop your current setup (`--host 0.0.0.0`) until a token is set. If you would rather it refuse, say so. |
| T4 | DNS-rebinding protection | **Always on**, for every bind address. Allowed `Host` values: the bind address, `localhost` / `127.0.0.1` / `[::1]`, the machine's hostname and `<hostname>.local`, plus anything in `MCP_SERVER_ALLOWED_HOSTS` | The SDK only turns it on for `127.0.0.1`; on a LAN address it is off. This guards against a web page in someone's browser driving the car. |
| T5 | Binding to `0.0.0.0` | Allowed hosts become every address the machine reports for its own hostname, plus the names above and `MCP_SERVER_ALLOWED_HOSTS` | There is no single address to allow. If a client connects by a name or address not on the list, the error says which value to add to `MCP_SERVER_ALLOWED_HOSTS`. |
| T6 | Changing the token without a restart | Not supported. Like host and port, the token is fixed when the socket is bound; `start` logs a warning if `myconfig.py` changed it | The HTTP app is built once per process. |
| T7 | Which run modes | Both: `donkey mcp` and `manage.py drive --mcp` | They currently start the server in two places; A1 makes it one. |

---

## A1 — One server start, with DNS-rebinding protection

**Files:** `donkeycar/parts/mcp_tools.py` (new `serve_http`), `donkeycar/parts/mcp_server.py`,
`donkeycar/management/mcp.py`, `donkeycar/templates/cfg_cv_control.py`, tests.

- `serve_http(server, host, port, token, extra_allowed_hosts)` builds the SDK's streamable-HTTP app
  with `TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=..., allowed_origins=...)`
  and runs it with uvicorn. Both run modes call it.
- New setting `MCP_SERVER_ALLOWED_HOSTS = []`.

**Acceptance**

- [ ] A request whose `Host` header is the bound address succeeds; one with a foreign `Host` is refused.
- [ ] With `0.0.0.0`, `localhost` and the machine's hostname are accepted.
- [ ] A name added to `MCP_SERVER_ALLOWED_HOSTS` is accepted.

## A2 — `MCP_SERVER_TOKEN`

**Files:** `donkeycar/parts/mcp_tools.py`, `donkeycar/management/mcp.py`,
`donkeycar/templates/cfg_cv_control.py`, tests.

- Middleware refuses requests without the right `Authorization: Bearer` header with `401` and a
  one-line reason; the token never appears in logs.
- Startup log says whether a token is required. Bound beyond localhost with no token: a warning (T3).
- `start` warns if `MCP_SERVER_TOKEN` changed in the reloaded config (T6).

**Acceptance**

- [ ] No header, a wrong token, and a non-Bearer scheme each get `401`; the right token gets through to a real tool call.
- [ ] With no token configured, requests succeed as before.
- [ ] The warning appears for a LAN bind without a token, and not for `127.0.0.1`.

## A3 — Docs

**Files:** `docs/mcp-server.md`, `docs/mcp-server-manual.html`.

- Security section describes what now exists: the token, the rebinding allow-list, and the warning.
- Connecting a client shows the token for each client:
  `claude mcp add --transport http donkeycar <url> --header "Authorization: Bearer <token>"`, and
  `"headers": {"Authorization": "Bearer <token>"}` in the JSON config.
- Config table gains `MCP_SERVER_TOKEN` and `MCP_SERVER_ALLOWED_HOSTS`; troubleshooting gains the `401`
  and refused-host cases.

---

## Out of scope

- TLS. The token travels in clear text over plain HTTP, so it keeps out a guest on the network but
  not someone capturing its traffic. The docs will say so.
- OAuth and per-user tokens.
