# One home for the track: track.yml, chosen at start-up — Plan

The track is described in two places: `track.yml` in the car directory, and the `TRACK_CONTINUOUS`,
`TRACK_LAP_LENGTH_INCHES` and `TRACK_LANES_INCHES` constants in `cfg_cv_control.py`. Neither is read
by the CV autopilot; both are read only by the MCP bridge (`MCPBridge._load_track`), to answer
`cv_control-get_track_config` and to turn a lane name into an offset. The constants are a fallback
used only when there is no `track.yml`, and `donkey createcar` always copies one in, so on a normal
car they are settings that look live but do nothing. They also describe less than the file: no
name, description, centreline or side-lines.

This plan makes `track.yml` the only way to describe a track, and adds a `--track` option so a car
can be pointed at one of several track files without editing anything.

**Branch:** `mcp-server`

---

## Progress — 2 of 3

- [x] **F1** — `--track` option on `manage.py drive` and `donkey mcp`
- [x] **F2** — Retire the `TRACK_*` constants; warn when falling back to the default track
- [ ] **F3** — Docs and the published user manual

Each box is ticked in the commit that does the work. Ruff, mypy and the full test suite pass on
every commit.

---

## Decisions

| # | Question | Proposal | Why |
| --- | --- | --- | --- |
| D1 | Where the track is described | **`track.yml` only.** The `TRACK_*` constants go | The file holds everything the constants do and more, and it is already what every new car uses. Two sources for one thing is how this question came up. |
| D2 | No track file at all | **Use the default track and log a warning** naming the file that was looked for | Settled with Ed. A missing description is less dangerous than a wrong one; a malformed file still refuses to start, as now. |
| D3 | How `--track` reaches the bridge | **Passed to `MCPBridge` as a constructor argument**, not written into `cfg` | `donkey mcp` re-reads `config.py`/`myconfig.py` on every `start`, which would silently drop a value stored in `cfg` and fall back to the car directory's `track.yml`. |
| D4 | Relative `--track` paths | **Resolved against the car directory.** Absolute and `~` paths are used as given | `donkey mcp --car ~/mycar --track office.yml` should mean `~/mycar/office.yml`. For `manage.py drive` the car directory is the working directory, so nothing changes there. |
| D5 | `--track` names a file that does not exist | **Refuse to start**, naming the resolved path | Asking for a track by name and getting the default instead is the silent mis-description D2 is careful to avoid. The warning applies only when no file was asked for. |
| D6 | The undocumented `TRACK_FILE` config lookup | **Removed** in favour of `--track` | Nothing sets it and no doc mentions it. One way to choose a file is enough; the car directory's `track.yml` remains the default. |
| D7 | `TRACK_*` constants left in older cars' `config.py` copies | **Ignored**, neither refused nor warned about | Same as the retired `TRACK_SEGMENT_*` constants: they are values nothing reads any more. Ed removes them from his own car directories. |

---

## F1 — `--track` option

**Files:** `donkeycar/templates/cv_control.py`, `donkeycar/management/mcp.py`,
`donkeycar/parts/mcp_server.py`, and their tests.

- `cv_control.py`: `--track=<file>` added to the `drive` usage line and passed through to
  `MCPBridge`. It only has an effect with `--mcp`; without it, the option is accepted and ignored.
- `donkey mcp`: `--track FILE` added, passed to `VehicleSupervisor` and on to the bridge.
- `MCPBridge.__init__` gains `track_file: str | None`. `_load_track` uses it when set, resolved
  per D4, and otherwise looks for `track.yml` in the car directory. The `TRACK_FILE` lookup is
  removed (D6).
- `reload_config` re-reads the same chosen file, so editing it and calling `stop` then `start`
  picks up the change.
- The existing "Loaded track description from …" log line stays and shows the resolved path.

**Acceptance**

- [x] `drive --mcp --track=other.yml` reports `other.yml`'s track from `get_track_config`, with a
      different `track.yml` also present in the car directory.
- [x] `donkey mcp --car DIR --track other.yml` loads `DIR/other.yml`.
- [x] An absolute `--track` path is used as given.
- [x] A `--track` file that does not exist refuses to start, and the message names the resolved path.
- [x] After `stop` and `start` under `donkey mcp` (config reloaded), the `--track` file is still the
      one in use.
- [x] Without `--track`, the car directory's `track.yml` is used, as now.

## F2 — Retire the constants

**Files:** `donkeycar/templates/cfg_cv_control.py`, `donkeycar/parts/mcp_server.py`,
`donkeycar/parts/track_config.py`, `donkeycar/tests/test_mcp_server.py`,
`donkeycar/tests/test_mcp_http.py`.

- The `# TRACK` block is removed from `cfg_cv_control.py`.
- `_load_track` loses the constants fallback: chosen file, else `track.yml`, else
  `default_track()` with a `logger.warning` naming the path it looked for and saying the agent is
  getting generic lanes.
- The stale "M4 and M5 replace these…" comment above `_load_track` is removed.
- Tests that described the track with `TRACK_*` constants write a `track.yml` instead. The test
  that config-described lanes obey the file's lane rules goes, since that path no longer exists.

**Acceptance**

- [x] No `TRACK_CONTINUOUS`, `TRACK_LAP_LENGTH_INCHES` or `TRACK_LANES_INCHES` remains in
      `donkeycar/` outside tests that check they are ignored.
- [x] A config that still sets the `TRACK_*` constants, with no track file, gets the default track
      and the warning: the constants are not read.
- [x] With no track file, a warning is logged once per load and `get_track_config` reports the
      default track.
- [x] A malformed `track.yml` still refuses to start.

## F3 — Docs

**Files:** `docs/mcp-server.md`, `docs/mcp-server-manual.html`.

- "Describe the track" says `track.yml` is the only place a track is described, and shows
  `--track` for keeping several tracks side by side (for example `track-garage.yml`,
  `track-office.yml`).
- The `--track` option is added to the `donkey mcp` options table and to the `drive --mcp`
  description.
- The upgrade note gains a line: `TRACK_CONTINUOUS`, `TRACK_LAP_LENGTH_INCHES` and
  `TRACK_LANES_INCHES` in an old `config.py` or `myconfig.py` are ignored; move their values into
  `track.yml`.
- What happens with no track file: the default track and a warning in the log.

---

## Out of scope

- Car directories such as `mycar-cv/` are never committed. Its `config.py` still has the `TRACK_*`
  constants and its `myconfig.py` has them commented out; Ed removes them himself.
- Choosing a track from the MCP side (a tool to switch track files at runtime). Restarting the
  command with a different `--track` covers it for now.
- Changes to the `track.yml` schema itself.
