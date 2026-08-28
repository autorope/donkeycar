"""
Run one activity against a running MCP server.

    python -m donkeycar.mcp_agent.runner --activity lap --url http://car.local:8891/mcp

Perception is left to you: the default refuses to invent sightings, because an
agent that hallucinates a stop sign is worse than one that sees none. Point
`--demo-script` at a JSON file of scripted sightings to exercise the loop
without a vision model.
"""

from __future__ import annotations

import argparse
import json
import logging
import time

from donkeycar.mcp_agent.perception import ScriptedPerception, Sighting
from donkeycar.mcp_agent.policies import POLICIES, build_policy
from donkeycar.mcp_agent.session import McpSession

logger = logging.getLogger(__name__)


def load_script(path: str) -> ScriptedPerception:
    """Read scripted sightings: a list of ticks, each a list of sightings."""
    with open(path) as handle:
        raw = json.load(handle)
    script = [
        [
            Sighting(
                kind=item["kind"],
                pixel=tuple(item["pixel"]),
                text=item.get("text"),
                blocking=item.get("blocking", True),
            )
            for item in tick
        ]
        for tick in raw
    ]
    return ScriptedPerception(script)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="donkeycar.mcp_agent.runner")
    parser.add_argument("--activity", choices=sorted(POLICIES), required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8891/mcp")
    parser.add_argument("--destination", default=None, help="address to drive to, for the address activity")
    parser.add_argument("--demo-script", default=None, help="JSON file of scripted sightings")
    parser.add_argument("--ticks", type=int, default=200, help="maximum agent ticks before giving up")
    parser.add_argument("--interval", type=float, default=0.5, help="seconds between ticks")
    args = parser.parse_args(argv)

    if args.demo_script is None:
        parser.error(
            "No perception configured. Pass --demo-script to replay scripted sightings, or import "
            "these policies and supply your own Perception implementation."
        )

    logging.basicConfig(level=logging.INFO)
    perception = load_script(args.demo_script)

    import anyio
    from mcp.client.client import Client

    async def go() -> int:
        async with Client(args.url) as client:
            session = McpSession(client)
            kwargs = {"destination": args.destination} if args.activity == "address" else {}
            policy = build_policy(args.activity, session, perception, **kwargs)
            policy.begin()
            try:
                for _ in range(args.ticks):
                    policy.step()
                    if policy.finished:
                        break
                    time.sleep(args.interval)
            finally:
                policy.end()
            for line in policy.log:
                logger.info("%s", line)
            return 0

    return int(anyio.run(go))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
