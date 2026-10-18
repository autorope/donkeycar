# Track config without segments — Plan

The track turned out not to be a chain of "T" segments. It is a centreline, possibly dashed,
with optional left and right side-lines, and its width and the centreline's position vary along
the course. This plan drops the segment model from `track.yml`, the MCP server and the agent, and
recasts what remains as **nominal guidance**, not ground truth.

**Branch:** `mcp-server`

---

## Progress — 4 of 4

- [x] **T1** — Track schema: centreline, side-lines, lap length; segments gone
- [x] **T2** — MCP surface tells the agent the track values are nominal
- [x] **T3** — Reference policies stop reading `segment_count`
- [x] **T4** — Docs: building and describing a track

Each box is ticked in the commit that does the work. Ruff, mypy and the full test suite pass on
every commit.

---

## Decisions

Settled with Ed before T1 started.

| # | Question | Proposal | Why |
| --- | --- | --- | --- |
| D1 | What replaces the segment fields | `lap_length_inches`, a `centerline` block and a `side_lines` block, all optional | These are what can actually be measured on this kind of track. They are optional because the agent can measure them from the image once the ground plane is calibrated. |
| D2 | Old `track.yml` files that still have `segment_length_inches` etc. | **Refuse to load**, with a message naming the retired fields and saying to delete them | Matches the existing strict schema: a silently ignored field reads as "configured" when it is not. An existing car fails `start` until its file is edited. |
| D3 | Is `continuous` still required | **Required**, as now | Whether the track loops is always known when it is laid. |
| D4 | Named lanes | **Required**, and must name `left` (negative), `center` (exactly 0) and `right` (positive). Further named lanes are still allowed. No derivation from side-lines | Lane positions can always be measured ahead of time. Requiring the three names guarantees `set_control(lane="left" \| "center" \| "right")` works on every track: left lane, on the centreline, right lane. |
| D5 | Where the "nominal" message lives | In `get_track_config`'s payload (`"nominal": true` plus a `note`), its docstring, and the server `INSTRUCTIONS` | The agent reads all three; any one alone is easy to miss. |
| D6 | Retired `TRACK_SEGMENT_*` constants in `config.py` | **Ignored** — neither refused nor warned about | Settled after T4. They are config values nothing reads any more; every older car's `config.py` copy has them. |
| D7 | Configuring the `center` lane | **Not configured**: always 0, added by the loader. Only `left` and `right` are required. A configured `center` is **refused**, even at 0 | Settled after D6. The centre lane is the centreline by definition, so there is nothing to configure. |

---

## Schema, before and after

**Retired:** `segment_length_inches`, `cross_length_inches`, `segment_count`, `cross_colors`,
`tape_width_inches`, `tape_color` (the last two move into `centerline`).

```yaml
name: Kitchen loop
description: Yellow centreline, white side-lines, one gentle S-bend.

lap_length_inches: 480.0     # measured along the centreline; omit if not measured
continuous: true             # omit if unknown

centerline:
  color: yellow
  width_inches: 1.0
  dashed: true

side_lines:                  # omit the block, or either side, if there are none
  color: white
  left_inches: 18.0          # nominal distance from the centreline
  right_inches: 18.0

lanes:                       # required: left < 0, right > 0; center is always 0
  left: -9.0
  right: 9.0
```

Validation stays strict: unknown keys are rejected, numbers must be positive, `dashed` and
`continuous` must be booleans. Required: `continuous` and `lanes`.

---

## T1 — Track schema

**Files:** `donkeycar/parts/track_config.py`, `donkeycar/templates/track.yml`,
`donkeycar/parts/mcp_server.py`, `donkeycar/templates/cfg_cv_control.py`,
`donkeycar/tests/test_track_config.py`, the inline YAML fixtures in `test_mcp_server.py` and
`test_mcp_agent.py`.

- `TrackConfig` gains `lap_length_inches`, `centerline` (`color`, `width_inches`, `dashed`) and
  `side_lines` (`color`, `left_inches`, `right_inches`). `continuous` and `lanes` stay required.
- Retired keys raise `TrackConfigError` naming each one and saying it is no longer used (D2).
- `lanes` must contain `left` < 0, `center` == 0 and `right` > 0 (D4); sign convention unchanged.
- `default_track()` keeps `continuous: false` and the three lanes, with no invented geometry.
- Template `track.yml` rewritten to the new shape, with comments explaining that every value is
  nominal.
- `TrackConfig.to_dict()` carries `"nominal": true` and the `note`, so `get_track_config` reports
  them from this commit on.
- The config-constant fallback (`TRACK_*` in `config.py`, used only with no `track.yml`) goes
  through the same validation as a file. Retired `TRACK_SEGMENT_*` constants are **silently
  ignored** (D6): every older car's `config.py` copy contains them, and they describe nothing.

**Acceptance**

- [x] A file with only `continuous` and the three lanes loads.
- [x] A file containing any retired key fails with a message naming that key.
- [x] Missing `continuous`, missing `lanes`, or `lanes` lacking any of `left`/`center`/`right` fails, naming what is missing.
- [x] `left >= 0`, `right <= 0` or `center != 0` fails.
- [x] The packaged template loads.

## T2 — MCP surface

**Files:** `donkeycar/parts/mcp_tools.py`, `donkeycar/tests/test_mcp_server.py`.

- `get_track_config`'s docstring and `INSTRUCTIONS` say the same, and stop describing the track as segments.

**Acceptance**

- [x] `get_track_config` over a real MCP client returns no segment fields and carries `nominal` and `note`.
- [x] `INSTRUCTIONS` and the tool description contain no mention of segments, and both point at `measure_ground_point`.

## T3 — Reference policies

**Files:** `donkeycar/mcp_agent/policies.py`, `donkeycar/tests/test_mcp_agent.py`.

- The start-of-run note reports whether the track loops and its lap length (when measured),
  instead of `segment_count`.

**Acceptance**

- [x] All five activities still pass against the vehicle loop with a track file that has no lap length.

## T4 — Docs

**Files:** `docs/mcp-server.md`; the published user manual is updated to match after this lands.

- §1 "Build a track" describes a centreline (solid or dashed) with optional side-lines, not "T"
  segments.
- §2 "Describe the track" shows the new schema, says every value is guidance, and names the
  retired fields for anyone upgrading a car.
- §5 tool table: `get_track_config` described as nominal.

`mcp-server-prompt.md` and `MCP_SERVER_PLAN.md` are records of what was originally asked for and
planned, so they are left as they are.

---

## Out of scope

- Car directories such as `mycar-cv/` are never committed; their `track.yml` is edited on the car.

- Teaching the line follower about side-lines. It still tracks the centreline colour only.
- Having the server measure track width itself. The agent can do that with
  `measure_ground_point`; a server-side measurement would be a separate piece of work.
