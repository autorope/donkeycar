"""
A reference agent for the donkeycar MCP server.

The five activities in the learning progression are implemented here as
policies: the control logic that decides what to do with the throttle and the
lane, given what the agent can see. Perception -- actually recognising a stop
sign in a camera frame -- is a separate, pluggable piece, because that is the
part a real LLM agent supplies and the part CI cannot.

Splitting it that way means the tool usage and the driving logic are testable
against a real vehicle loop with a MOCK camera, while the vision stays where it
belongs.
"""

from donkeycar.mcp_agent.perception import Perception, ScriptedPerception, Sighting
from donkeycar.mcp_agent.policies import (
    AddressPolicy,
    LapPolicy,
    ObstacleAvoidPolicy,
    ObstacleHaltPolicy,
    Policy,
    StopSignPolicy,
    build_policy,
)
from donkeycar.mcp_agent.session import BridgeSession, CarSession, McpSession

__all__ = [
    "AddressPolicy",
    "BridgeSession",
    "CarSession",
    "LapPolicy",
    "McpSession",
    "ObstacleAvoidPolicy",
    "ObstacleHaltPolicy",
    "Perception",
    "Policy",
    "ScriptedPerception",
    "Sighting",
    "StopSignPolicy",
    "build_policy",
]
