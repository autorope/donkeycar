# CV track settings: tape labels, autopilot settings, namespacing — Plan

Three follow-ups to `TRACK_CONFIG_PLAN.md`:

1. The centreline's real colour is the HSV window in `myconfig.py`
   (`COLOR_THRESHOLD_LOW` / `COLOR_THRESHOLD_HIGH`). The colour in `track.yml` is only a label, and
   it should be named so it cannot be confused with the side tape's.
2. The agent should be able to see the settings the CV autopilot is actually running with, and
   use them if it judges them relevant.
3. Everything `track.yml` holds today is specific to the `cv_control` template, so it moves under
   a `cv_control:` section. A future template gets its own section and cannot collide.

**Branch:** `mcp-server`

---

## Progress — 1 of 3

- [x] **S1** — Namespace the CV fields under `cv_control:`, and rename `color` to `tape_color` in each tape block
- [ ] **S2** — `get_autopilot` and `get_autopilot_config` tools
- [ ] **S3** — Docs and the published user manual

Items 1 and 3 land together in S1: both rewrite the same schema, and doing them apart would mean
a format that lives for one commit. If you would rather have all of it as one commit, say so and
S1–S3 become one.

---

## Decisions

Settled with Ed before S1 started.

| # | Question | Proposal | Why |
| --- | --- | --- | --- |
| N1 | Shape of the tape fields | **Keep the `centerline` and `side_lines` blocks**, and rename `color` to `tape_color` inside each | The block already says which tape it is; `tape_color` says the value is the tape's colour label, not the follower's colour window. |
| N2 | What sits at the top level | `name` and `description` only; they describe the track, not a template. Everything else goes under `cv_control:` | Two templates driving the same track share its name; they do not share lane offsets. |
| N3 | Namespace key | The template's name, `cv_control` | It is what `donkey createcar --template` and `donkey update --template` already call it. |
| N4 | Other top-level keys | Refused, as now. A new template's section becomes allowed when that template is added to the MCP server | Keeps typo protection. Ignoring unknown sections would let `cv_contrl:` read as "no track". |
| N5 | A file in the current, un-namespaced shape | **Refused**, naming the fields that must move under `cv_control:` | Consistent with how segment files are refused. Nothing has been pushed in that shape, so only your car files have it. |
| N6 | Is `cv_control:` required | Yes, while `cv_control` is the only template the server drives | Its `continuous` and `lanes` are required, so the section is too. |
| N7 | Autopilot settings: new tool or part of `get_track_config` | **New tool, `get_autopilot_config`** | They come from `config.py` / `myconfig.py` and change on every `stop`/`start`, while the track description is call-once. Separate tools keep "what the track is" apart from "how the car is tuned". |
| N8 | Which settings | The line follower's and the loop's, listed below. No PWM, pin or joystick settings | These are what explain the car's behaviour on the track. Hardware calibration explains nothing the agent can act on. |
| N9 | Shape of the report | `{"template": "cv_control", "source": "config.py + myconfig.py", "settings": {NAME: value, ...}}`, keyed by the real config names | The agent can quote a name back to you verbatim, and the namespace mirrors `track.yml`. |
| N10 | How the agent knows which namespace to read | **A `get_autopilot` tool** returning the autopilot's name (`cv_control`) | Added by Ed. When a second template is added, the agent asks which autopilot is running and reads that section of `get_track_config` and that `get_autopilot_config`. For now the bridge only drives `cv_control`, so the name is fixed there. |

### Settings `get_autopilot_config` reports (N8)

| Group | Settings |
| --- | --- |
| Line colour (HSV) | `COLOR_THRESHOLD_LOW`, `COLOR_THRESHOLD_HIGH`, `CONFIDENCE_THRESHOLD` |
| Where it looks | `SCAN_Y`, `SCAN_HEIGHT`, `IMAGE_W`, `IMAGE_H` |
| Steering | `TARGET_PIXEL`, `TARGET_THRESHOLD`, `PID_P`, `PID_I`, `PID_D`, `LOST_LINE_STEERING_DECAY` |
| Speed | `THROTTLE_MIN`, `THROTTLE_MAX`, `THROTTLE_INITIAL`, `THROTTLE_STEP` |
| Loop and frame | `DRIVE_LOOP_HZ`, `OVERLAY_IMAGE`, `CV_PIXELS_PER_INCH`, `MCP_COMMAND_TIMEOUT_S` |

A setting the config does not define is reported as `null`, not left out, so "unset" and "not
reported" cannot be confused.

---

## Schema, before and after

**Before** (current, un-namespaced):

```yaml
name: Kitchen loop
continuous: true
lap_length_inches: 480.0
centerline: {color: yellow, width_inches: 1.0, dashed: true}
side_lines: {color: white, left_inches: 18.0, right_inches: 18.0}
lanes: {left: -9.0, right: 9.0}
```

**After:**

```yaml
name: Kitchen loop
description: Yellow centreline, white side tape, one gentle S-bend.

cv_control:
  continuous: true                 # required
  lanes:                           # required: left < 0, right > 0; center is implicit
    left: -9.0
    right: 9.0

  lap_length_inches: 480.0         # optional, nominal

  centerline:
    tape_color: yellow             # label only; the real colour is COLOR_THRESHOLD_* in myconfig.py
    width_inches: 1.0
    dashed: true

  side_lines:                      # optional: omit if there is no side tape
    tape_color: white
    left_inches: 18.0              # nominal distance from the centreline
    right_inches: 18.0
```

`get_track_config` returns the same shape: `name`, `description`, `nominal`, `note`, and a
`cv_control` object. The note adds that `centerline.tape_color` is a label and points at
`get_autopilot_config` for the real colour window.

---

## S1 — Namespaced schema

**Files:** `donkeycar/parts/track_config.py`, `donkeycar/templates/track.yml`,
`donkeycar/parts/mcp_server.py` (lane lookup reads the section), `donkeycar/mcp_agent/policies.py`
(reads `continuous`, `lap_length_inches`, `lanes` from the section), and their tests.

- `TrackConfig` keeps `name` and `description`, and gains a `cv_control: CvTrack` holding everything
  else. `Centerline.color` and `SideLines.color` become `tape_color`.
- Un-namespaced CV fields at the top level are refused, naming each and saying it belongs under
  `cv_control:` (N5). Segment-era fields are still refused as before.
- The config-constant fallback (`TRACK_CONTINUOUS`, `TRACK_LANES_INCHES`, `TRACK_LAP_LENGTH_INCHES`)
  fills the `cv_control` section. Those constants already live in the CV template's config, so they
  keep their names.

**Acceptance**

- [x] The packaged template loads, with every CV field under `cv_control:`.
- [x] A file with `continuous` or `lanes` at the top level fails, naming them and `cv_control`.
- [x] A misspelt section (`cv_contrl:`) fails as an unknown field.
- [x] `tape_color` is accepted in both blocks, and the old `color` key is refused in both.
- [x] Lane rules unchanged: `left` < 0 and `right` > 0 required, a configured `center` refused.

## S2 — `get_autopilot` and `get_autopilot_config`

**Files:** `donkeycar/parts/mcp_server.py`, `donkeycar/parts/mcp_tools.py`, `donkeycar/tests/test_mcp_server.py`.

- `get_autopilot` returns `{"autopilot": "cv_control"}` plus a line saying which `get_track_config`
  section and which `get_autopilot_config` belong to it (N10).
- The bridge reports the settings above from its current config, which `start` reloads, so the
  answer is always what the running car uses.
- Tool descriptions and `INSTRUCTIONS`: call `get_autopilot` first to learn the namespace; the
  settings are the autopilot's live ones; `centerline.tape_color` in the track is a label, `COLOR_THRESHOLD_*` is the colour the follower actually matches.

**Acceptance**

- [ ] Over a real MCP client, `get_autopilot` returns `cv_control`, and the same name keys `get_track_config`'s section.
- [ ] Over a real MCP client, `get_autopilot_config` returns `template: "cv_control"` and every listed setting.
- [ ] An unset setting is `null`.
- [ ] After editing the config and calling `stop` then `start`, it reports the new value.

## S3 — Docs

**Files:** `docs/mcp-server.md`; the published user manual is updated to match after this lands.

- §2 "Describe the track" shows the namespaced file and says the tape colours are labels.
- §5 tool table gains `get_autopilot` and `get_autopilot_config`.
- The upgrade note says to move the fields under `cv_control:` and rename `color` to `tape_color`.

---

## Out of scope

- Making the line follower use `centerline.tape_color`. The HSV window in `myconfig.py` stays the
  only colour it matches.
- Letting the agent change any setting. `get_autopilot_config` is read-only.
- Car directories: you update `mycar-cv/track.yml` and the Pi's yourself.
