# MCP Server for the CV Autopilot — Implementation Plan

Letting an LLM agent read the car's state and set steering intent while the computer-vision autopilot
keeps following the tape line at 20 Hz.

**Branch:** `mcp-server` (based on `ba25266b`)
**Companion:** a rendered version of this plan with a dataflow diagram is published as an Artifact.

---

## Progress

- [x] **M0** — Fix the toolchain, stand up the gate, split assembly from run
- [x] **M1** — Lane offset in `LineFollower`
- [x] **M2** — `MCPBridge` part and the tool surface
- [x] **M3** — `donkey mcp` supervisor
- [x] **M4** — `track.yml` schema and loader
- [ ] **M5** — Camera calibration with live preview *(parallel to M2–M4)*
- [ ] **M6** — Docs and the activity progression

---

## Decisions on record

| Decision | Choice | Consequence |
| --- | --- | --- |
| Transport | Streamable HTTP — a TCP socket | Revised from "HTTP and stdio". The HTTP transport *is* the socket, so stdio buys nothing and costs the stdout conflict. One transport, no logging changes. |
| Run modes | All three | Plain CLI untouched; `drive --mcp` for in-loop control; `donkey mcp` supervisor for true start/stop. |
| Calibration | Ground homography + live preview | Gives inches-per-pixel at any row *and* distance-to-feature, which the stop-sign and obstacle activities need. |
| Lane offset | Named lanes + inches override | Agent normally names a lane; a numeric inches argument is there for edging past an obstacle. |
| Track description | `track.yml` in the car directory | Swap tracks without editing Python. `pyyaml` is already a dependency. |
| Lint/format | Ruff for both; black retired | One tool, one config block. Line length 120. |
| Agent throttle | A ceiling on CV throttle, not a replacement | Agent can slow and stop but never outrun what the controller thinks is safe for the current curvature. |

### Throttle semantics — settled

**Agent throttle acts as a ceiling on the CV controller's throttle, not a replacement for it.**

`LineFollower` computes its own throttle, ramping between `THROTTLE_MIN` and `THROTTLE_MAX` and slowing
itself in corners (`donkeycar/parts/line_follower.py:91-102`). An absolute agent value would fight that
ramp and corner too fast. So `set_control(throttle=v)` resolves to `min(v, cv_throttle)` for forward
motion, with `0` as a hard stop.

Three consequences to hold onto while implementing M2:

- The agent has authority to **slow and stop**, never to push the car past what the controller thinks is
  safe for the current curvature.
- The controller keeps its cornering slow-down, so lane changes and obstacle passes stay stable.
- A `mode="absolute"` flag is the escape hatch if some later activity genuinely needs direct command. It
  is **not** part of the initial tool surface — adding it later is a smaller change than removing it.

---

## What the codebase already gives you

Four pieces of existing machinery do most of the work, which is why this plan stays small.

- **Normalized control values are already in vehicle memory.** `pilot/steering`, `pilot/throttle`,
  `steering`, `throttle` all live in the −1…1 range; PWM conversion happens downstream in the drivetrain.
  The "high-level values only" requirement costs nothing.
- **Lane offset is a shift of one number.** `LineFollower` steers to hold the yellow line at
  `self.target_pixel` (`line_follower.py:81`). A lane offset is that target plus a delta — no new CV, no new part.
- **The CV controller is swappable by config.** `cv_control.py:104` resolves the controller through
  `cfg.CV_CONTROLLER_MODULE` / `_CLASS` / `_INPUTS` / `_OUTPUTS`, so a new input can be wired in without
  forking the template.
- **`LocalWebController` is the precedent for a network server as a part.** It runs Tornado inside `update()`
  and exchanges state through `run_threaded()` once per loop (`web_controller/web.py:146`).

### Where the server sits in the loop

```
Camera
  │  cam/image_array
  ▼
LineFollower  ◄─────────────────┐
  │  pilot/steering + throttle  │  mcp/lane_offset_px
  ▼                             │  (arrives next loop, +50 ms)
MCPBridge  ◄──── MCP tools ────►│  LLM agent (off-vehicle, HTTP socket)
  │  pilot/throttle (capped)    │
  ▼                             │
DriveMode ──────────────────────┘
  │  steering + throttle
  ▼
Drivetrain (PWM out)
```

`MCPBridge` inserts after `add_cv_controller()` (`cv_control.py:104`) and before `DriveMode`
(`cv_control.py:165`). The one-loop delay on lane offset is 50 ms at `DRIVE_LOOP_HZ = 20` and is normal
donkeycar dataflow — it needs a comment, not a mitigation, so nobody "fixes" it later.

---

## Verified SDK surface

Installed and inspected: **`mcp` 2.1.1**. Do not write this from memory — the current API differs from
most references.

- **`FastMCP` no longer exists.** It was renamed in 2.x — `from mcp.server.mcpserver import MCPServer`.
  The old import path raises a `ModuleNotFoundError` that names the rename.
- **The transport is a socket server, not a pipe.** `run(transport="streamable-http", host=…, port=…)`
  delegates to `run_streamable_http_async(host="127.0.0.1", port=8000, streamable_http_path="/mcp", …)`,
  which builds a Starlette app and serves it under uvicorn. It touches no file descriptor donkeycar uses.
- **It blocks.** `run()` is synchronous and calls `anyio.run(…)` internally — which is exactly why it
  belongs in a part's `update()`, mirroring `LocalWebController`.
- **The default bind is already the safe one:** `127.0.0.1`. Reaching the car from a laptop is a
  deliberate `host` change.
- **Images are first class.** `Image(data=<bytes>, format="jpeg")` — pair with the existing
  `utils.arr_to_binary()` (`donkeycar/utils.py:73`).
- **A `lifespan` hook exists on the constructor**, taking an async context manager. This is where the
  supervisor builds and tears down the `Vehicle`.
- If you specifically want a **Unix domain socket**, `streamable_http_app()` returns the Starlette app,
  which you can hand to uvicorn with `uds=<path>`. Only worth it for local-only setups.

Add as an optional extra and import it lazily inside the part:

```toml
[project.optional-dependencies]
mcp = ["mcp>=2.1,<3"]
```

---

## Standards every milestone inherits

- **Modern typing, fully annotated.** Every function, method, and module-level constant in new code
  carries annotations. The 3.12 floor gives you `X | None`, `list[str]`, `dict[str, float]` natively — so
  no `typing.Optional`, no `typing.List`, and no `from __future__ import annotations`.
- **New modules pass `mypy` strict; all new code passes `ruff check` and `ruff format --check`.**
  Enforced by the gate M0 stands up, scoped per-module so legacy code is not dragged in.
- **Legacy files get annotated only where this work already touches them.** `LineFollower.run()` gains a
  real signature in M1 because M1 changes it. The other ~2,000 functions stay as they are — this is
  opportunistic typing, not a repo migration, and treating it as one would sink the plan.

---

## The tool surface

### Required

| Tool | Returns / accepts |
| --- | --- |
| `get_track_config` | Named lane offsets, segment geometry (36 in stem, 12 in cross), segment count, loop vs dead-end. From `track.yml`. |
| `get_vehicle_state` | Camera frame as a JPEG `Image`, plus throttle, steering, active lane and offset in inches, drive mode, armed flag, and a monotonic loop counter so the agent can tell a stale frame from a fresh one. |
| `set_control` | Accepts `throttle`, and either `lane` (a name from the track config) or `lane_offset_inches`. Single call so the agent can stop and re-center atomically. |
| `start` | Supervisor mode: build and run the vehicle. Part mode: arm the bridge. |
| `stop` | The inverse. Always zeroes throttle first, then tears down. |

### Recommended additions

| Tool | Why it earns a place |
| --- | --- |
| `measure_ground_point` | Agent passes an image pixel, gets ground coordinates in inches via the homography. The agent's only source of depth — without it, every braking decision is a guess from apparent size. |
| `emergency_stop` | Distinct from `stop`: zeroes throttle immediately without touching lifecycle, so it stays correct in both run modes and is unambiguous under latency. |
| `get_calibration` | Exposes pixels-per-inch, the 3×3 matrix, and capture metadata, so the agent can convert on its own and can tell when calibration is stale. |

---

# Milestones

## M0 — Fix the toolchain, stand up the gate, split assembly from run

- [x] **M0 done**

**Depends on:** nothing. **Blocks:** everything else. Three steps, in this order.

### Step 1 — reconcile the Python version

This is not housekeeping: M0's own verification test cannot run until it's done. Four things disagree.

- `.python-version` pins **3.11**, below the `requires-python = ">=3.12.0,<3.14"` floor at
  `pyproject.toml:24`. `uv` reads that file, so it will select an interpreter the project then rejects.
- **No installed interpreter satisfies the constraint.** pyenv has `3.11.14` and `3.14.0` — one below the
  floor, the other excluded by `<3.14`.
- **`uv` is not on PATH**, yet `Makefile` (`uv run pytest`, `uv build`) and CI
  (`.github/workflows/python-package.yml:22`) both depend on it. `make tests` fails before collecting a test.
- The `env/` venv is `3.11.14`, also below the floor. It is gitignored, so recreating it costs nothing.

Fix: install `uv`, set `.python-version` to **3.12** to match the CI matrix (`python-package.yml:16`), let
`uv` provision that interpreter, rebuild the venv. `.python-version` is untracked but *not* gitignored —
commit it so the pin travels with the branch instead of being rediscovered by the next person.

The `mcp` floor is a non-issue: it needs `>=3.10`, so anything satisfying donkeycar satisfies it.

### Step 2 — stand up the lint and type gate

Neither linting nor type checking is enforced today, so this step has to *create* the gate.

- **Adopt ruff for lint and format; retire black.** Swap `black` → `ruff` in the `dev` extras and delete
  `.github/linters/.python-black`, which still targets `py37` at 80 columns.
- **Line length is 120**, not ruff's default 88 nor black's old 80. Donkeycar part signatures and the
  `V.add(…, inputs=[…], outputs=[…])` calls that fill the templates are naturally wide; 120 keeps them on
  one line. It also drops the legacy `E501` backlog from 1,106 to 240.
- **Make CI capable of failing.** `superlinter.yml` disables enforcement three separate ways:
  `continue-on-error: true`, `DISABLE_ERRORS: true`, and `DEFAULT_BRANCH: master` on a repo whose default
  branch is `main`. Replace it with a job running `ruff check`, `ruff format --check`, and `mypy`.
- **Gate the diff, not the repo.** Measured at `line-length = 120`, a repo-wide run reports **5,443**
  findings — **1,876** excluding annotation rules, led by 240 `E501`, 171 `I001`, 147 `F401`. Clearing that
  is separate work and explicitly not part of this plan, which is also exactly what "all *new* code passes
  linting" means:

  ```sh
  git diff --name-only --diff-filter=ACM origin/main...HEAD -- '*.py' | xargs -r ruff check
  ```

Config, validated against ruff 0.16.5 and mypy rather than written from memory:

```toml
[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "ANN", "RUF"]

[tool.ruff.lint.per-file-ignores]
"donkeycar/tests/*" = ["ANN"]

[tool.mypy]
python_version = "3.12"
ignore_missing_imports = true   # cv2, adafruit, tensorflow ship no stubs

# Strict on new modules ONLY. Listing them explicitly is what keeps
# the ~1,670 unannotated legacy functions out of the gate.
[[tool.mypy.overrides]]
module = [
    "donkeycar.parts.mcp_server",
    "donkeycar.management.mcp",
]
disallow_untyped_defs = true
disallow_incomplete_defs = true
disallow_untyped_calls = true
disallow_any_generics = true
warn_return_any = true
no_implicit_optional = true
check_untyped_defs = true
strict_equality = true
warn_unused_ignores = true
extra_checks = true
```

> **One trap, verified by experiment.** `strict = true` inside `[[tool.mypy.overrides]]` does **not**
> scope. Mypy accepts it without any config error and applies it globally: in a two-module test,
> `strict = true` scoped to one module also flagged an untouched legacy file, while the explicit flag list
> above confined strictness correctly. Write the flags out — the short form fails silently in the direction
> that looks like it worked.

### Step 3 — the refactor

In `cv_control.py`, extract everything currently in `drive()` into
`build_vehicle(cfg, …, enable_mcp=False)` returning `V`, and leave `drive()` as a two-line wrapper that
calls it and then `V.start()`. Add the `mcp` optional extra.

### Implementation notes

- **The mypy gate is scoped to changed files, not the repo.** A repo-wide run reports **257** pre-existing
  errors even under permissive settings (`attr-defined` and friends, which `ignore_missing_imports` does not
  touch), so it could never have gone green. `follow_imports = "silent"` is set in `pyproject.toml` so
  imported legacy modules are still read for types but stay quiet. Same treatment as ruff, same reason.
- **`cv_control.py` was cleaned rather than exempted.** Touching it put 39 findings in scope. Rather than
  add a per-file ignore, the file was brought up to the bar: annotations, f-strings/lazy logging, sorted
  imports, four unused imports removed.
- **A real bug fell out of that.** `meta=[]` was a mutable default and line 206 did `meta += cfg.METADATA`,
  which mutates it in place. Harmless while `drive()` ran once per process — but M3's supervisor rebuilds
  the vehicle repeatedly in one process, so every restart would have re-appended the metadata. Fixed by
  copying, and pinned by `test_build_vehicle_does_not_accumulate_metadata`.
- **Pre-existing failure, left alone:** `test_scripts.py::test_bad_command_fails` fails at baseline too
  (verified by stashing this work and re-running). Unrelated to the MCP work and out of scope.
- `print()` calls in the template became `logger.info()`. Same information, and it keeps stdout clean.

### Acceptance criteria

- [x] `uv` is installed and `uv run pytest` executes (not "command not found")
- [x] `.python-version` contains a version satisfying `>=3.12.0,<3.14`, and is committed to git
- [x] In the project venv, `python -c "import sys; assert (3,12) <= sys.version_info < (3,14)"` exits 0
- [x] `ruff` is in `dev` extras, `black` is gone, `.github/linters/.python-black` is deleted
- [x] `ruff check` and `ruff format --check` both exit 0 on the branch diff
- [x] `mypy` exits 0 on the changed files with the overrides in place
- [x] **Override scoping proven:** an untyped `def` added to a module listed in the override *fails* mypy,
      and the same `def` added to a non-listed legacy module *passes* — confirming strictness is confined
- [x] A CI job fails the build on lint or type error — no `continue-on-error`, no `DISABLE_ERRORS`, and the
      diff base is `main`
- [x] `build_vehicle()` returns an unstarted `Vehicle`; `drive()` calls it and then `V.start()`
- [x] The template test (`CAMERA_TYPE='MOCK'`, `DRIVE_TRAIN_TYPE='None'`, `MAX_LOOPS=10`, per
      `donkeycar/tests/test_template.py:17`) passes **unchanged**
- [x] `python manage.py drive` still works in an environment where `mcp` is **not** installed, proving the
      optional extra and lazy import

---

## M1 — Lane offset in `LineFollower`

- [x] **M1 done**

**Depends on:** M0. **Independent of the server; fully unit-testable.**

Add an optional second input, defaulting to `None` so existing behavior is untouched:

```python
def run(self, cam_img, lane_offset_px=None):
    target = self.target_pixel + (lane_offset_px or 0)
    target = min(max(target, 0), self.image_w - 1)   # clamp
```

Three details the current code makes easy to get wrong:

1. The PID setpoint check at `line_follower.py:81` compares against `self.target_pixel` and must compare
   against the **effective** target.
2. The cornering test at `line_follower.py:91` must do the same.
3. The clamp needs `IMAGE_W`, which the part does not currently read from config.

Wire it in by config alone: `CV_CONTROLLER_INPUTS = ['cam/image_array', 'mcp/lane_offset_px']`.

### Implementation notes

- All three predicted traps were real and are covered by tests: the PID setpoint and the throttle ramp both
  now read `effective_target_pixel`, and `IMAGE_W` was indeed absent from the part (it falls back to the
  frame width when the config omits it).
- **Two further bugs surfaced while typing the file.** `run()` returned a *four*-tuple when handed no image
  while the part declares three outputs, so `cv/image_array` was being set to `False`. And
  `simple_pid.PID.__call__` returns `None` until it has produced an output, which was being assigned
  straight to `self.steering` and would have propagated `None` into the drivetrain. Both fixed, both pinned
  by tests.
- **Config templates are exempt from `E501` and from the formatter.** They are hand-aligned reference
  documents whose trailing comments are the documentation; formatting `cfg_cv_control.py` rewrote the whole
  file and parenthesised constants. `force-exclude = true` is required for the exclusion to hold when CI
  names files explicitly. The resulting config diff is 4 lines rather than ~1,500.
- `config.py` was left alone deliberately: putting the shared `CarConfig` alias there would have pulled 20
  findings into the gate for no benefit, so the alias is declared locally in each file that needs it.

### Acceptance criteria

- [x] `run(cam_img)` with no offset produces **bit-identical** steering and throttle to the pre-M1
      implementation on a fixed test image (regression test)
- [x] A non-zero offset shifts the effective target: steering sign flips as the offset crosses the detected
      line position
- [x] The effective target drives **both** the PID setpoint *and* the cornering/throttle-ramp comparison —
      asserted separately, since fixing only the setpoint is the likely bug
- [x] Offsets beyond the frame clamp to `[0, IMAGE_W - 1]` rather than wrapping, going negative, or raising
- [x] End-to-end with MOCK camera: setting `mcp/lane_offset_px` in memory changes the steering output
- [x] All touched functions carry annotations; `ruff` and `mypy` gates pass

---

## M2 — `MCPBridge` part and the tool surface

- [x] **M2 done**

**Depends on:** M0, M1. **Delivers:** `drive --mcp`.

New file `donkeycar/parts/mcp_server.py`, shaped on `LocalWebController`: `MCPServer.run()` goes in
`update()`, state is exchanged in `run_threaded()`.

- **Inputs** `cam/image_array`, `cv/image_array`, `pilot/steering`, `pilot/throttle`, `user/mode`.
  **Outputs** `pilot/throttle`, `mcp/lane_offset_px`, `mcp/armed`.
- **Guard the state exchange with an explicit `threading.Lock`.** `run_threaded()` runs on the vehicle-loop
  thread; tool handlers run on the server's asyncio thread. `LocalWebController` gets away with bare
  attribute assignment; a frame plus several correlated scalars is a torn read waiting to happen.
- Encode the frame once per request, not once per loop.
- **Include the watchdog from the start** — far easier to build in than to retrofit.
- **Arming cannot be done by writing `user/mode`.** `LocalWebController` outputs `user/mode` every loop
  (`donkeycar/templates/complete.py:697`), so a write from the bridge is clobbered on the next iteration.
  Gate throttle instead (which is what "stop" should mean anyway — the CV controller keeps steering while
  throttle is zero). For a genuine mode switch, hold a reference to the controller and set `ctr.mode_latch`,
  the same mechanism the web UI buttons use.
- Port **8891** — 8887 is the web controller, 8890 is `WebFpv`.

### Implementation notes

- **Split into two modules.** `mcp_server.py` holds the part and never imports `mcp`, so a car without the
  extra can still import and run it. `mcp_tools.py` holds the protocol surface and imports `mcp` freely.
  That split is not just tidiness: the SDK resolves tool return annotations against *module* globals, so
  types imported inside a function body fail to resolve at decoration time.
- **A live client caught a bug 27 unit tests missed.** Returning `[dict, Image]` from a tool annotated
  `-> list[Any]` fails to serialise: the SDK inspects the *annotation* to decide between content blocks and
  structured JSON, and a loose one sends the image down the JSON path, where it raises at request time.
  Fixed by annotating `-> list[TextContent | ImageContent]`. There are now tests that drive the server
  through an in-process MCP client, because the bridge's own API cannot expose this class of fault.
- **Validation errors were being swallowed.** Only a `ToolError`'s message reaches the client; every other
  exception is reported as a bare "Error executing tool <name>". `set_control(lane="shoulder")` was telling
  the agent nothing. Bridge `ValueError`s are now translated, so the agent gets
  "Unknown lane 'shoulder'. Known lanes: ['center', 'left', 'right']".
- **`disallow_untyped_calls` was dropped from the strict override set.** New modules necessarily call into
  donkeycar's untyped legacy code, and keeping it would have meant a `type: ignore` on nearly every such
  call. Verified that the remaining flags still reject an untyped def in these modules.
- **Arming, not mode switching.** As predicted, the bridge cannot write `user/mode` (the web controller
  rewrites it every loop), so `stop` gates throttle to zero and lets the CV controller keep steering.

### Acceptance criteria

- [x] Server is reachable over streamable HTTP; `tools/list` returns the 5 required tools plus whichever
      recommended ones are implemented
- [x] `get_vehicle_state` returns a **decodable** JPEG plus throttle, steering, lane, offset, mode, and loop counter
- [x] The loop counter strictly increases between two calls while the loop runs, so the agent can detect a stale frame
- [x] `set_control(throttle=0)` drives the drivetrain input to `0` within 2 loop iterations
- [x] **Ceiling honored:** `set_control(throttle=v)` with `v` *above* the CV controller's current throttle
      does not raise the applied throttle above the CV value
- [x] **CV authority preserved:** with the agent's ceiling set high, the controller's cornering slow-down
      still occurs — proving the ceiling caps rather than replaces
- [x] `set_control(lane=...)` changes `mcp/lane_offset_px`, and `LineFollower` consumes it on the next iteration
- [x] **Watchdog:** with no agent command for longer than `MCP_COMMAND_TIMEOUT_S`, throttle returns to 0 automatically
- [x] **No torn reads:** many concurrent `get_vehicle_state` calls against a running loop never return a
      frame paired with mismatched scalars
- [x] `python manage.py drive` *without* `--mcp` produces a part list identical to pre-M2 — the MCP part is
      genuinely absent, not merely idle
- [x] Nothing on the server path writes to stdout
- [x] Tool handlers are unit-tested against a synthetic state object, with no `Vehicle` and no camera
- [x] `mypy` strict passes for `donkeycar.parts.mcp_server`

---

## M3 — `donkey mcp` supervisor

- [x] **M3 done**

**Depends on:** M2. **Delivers:** true start/stop.

The MCP server owns the process and runs `V.start()` on a background thread it can join and rebuild, using
the SDK's `lifespan` hook for setup and teardown. Register it in the command table at
`donkeycar/management/base.py:605`.

Resolve `build_vehicle` from the car directory's own `manage.py` when it exposes one, falling back to the
packaged template. Necessary because `manage.py` is a *copy* (`base.py:101`) — existing car folders won't
have `build_vehicle` until `donkey update`, and cars with local customizations deserve to keep them.

### Implementation notes

- **The bridge outlives the vehicle.** The supervisor owns one `MCPBridge` and injects it into each build via
  a new `mcp_bridge=` parameter, so an agent keeps its connection and its command state across a restart.
- **A restart bug in the web controller had to be fixed first.** `LocalWebController.shutdown()` was `pass`
  and `update()` discarded the server handle, so the tornado loop and its listening socket outlived
  `V.stop()`. Harmless when the process exits with the vehicle; fatal for M3, where the rebuilt controller
  could not rebind and the web UI would have come back dead, still attached to the torn-down vehicle. Fixing
  it took three passes, each exposed by a test: release the socket on the loop's own thread; *wait* for that
  release rather than returning while it is still open; and gate the wait on a loop that is actually running,
  since a shutdown arriving mid-startup otherwise waits out the full timeout (that one turned a 0.5s test
  run into 25s). A shutdown flag checked around the bind closes the last race deterministically.
- **`web.py` is exempted from the annotation rules, visibly.** 52 of its 56 findings are `ANN` on 450 lines
  of untyped legacy that this work only visits to fix that leak. The exemption is written into
  `pyproject.toml` with its reason rather than left implicit; every other rule still applies, and the three
  real findings it surfaced were fixed.

### Acceptance criteria

- [x] `donkey mcp --car=<path>` starts and serves tools with **no vehicle running** until `start` is called
- [x] `start` → loop runs; `stop` → loop stops and every part's `shutdown()` is called; `start` again →
      loop runs again. This restart cycle is the whole point of M3 and is what part-mode cannot do
- [x] `stop` leaves throttle at 0 — no coasting drivetrain
- [x] Uses the car directory's `build_vehicle` when present; falls back to the packaged template when
      absent. **Both paths asserted.**
- [x] `donkey mcp` appears in the CLI usage listing
- [x] `mypy` strict passes for `donkeycar.management.mcp`

---

## M4 — `track.yml` schema and loader

- [x] **M4 done**

**Depends on:** M2. **Completes:** `get_track_config`.

Segment count, stem and cross lengths, cross-tick colors, continuity, and named lane offsets in inches.
Validate on load and fail loudly — a silently wrong lane width is a car in the wall.

**The file describes track geometry only — no traffic feature list.** Stop signs, addresses, and obstacles
are discovered visually by the agent from the camera frame, which is what the learning progression is
actually about. This keeps the schema small and means a physical track can be re-arranged, or features moved
around it, without editing the file.

One knock-on: it makes `measure_ground_point` (M5) load-bearing rather than optional. If the agent cannot
look up where a stop sign is, its only way to know when to brake is to measure how far away the one it can
see actually is.

### Implementation notes

- **Unknown keys are rejected.** That is what keeps traffic features out of the schema: a file that tries to
  list them fails loudly rather than having the section silently ignored. It also catches typos, which would
  otherwise read as "that field was never set".
- **A malformed track file refuses to start.** Driving a track you have mis-described is worse than not
  starting, so a bad file raises rather than quietly falling back to defaults. A *missing* file does fall
  back — first to the config constants, then to a built-in default.
- **Case-different lane names count as duplicates.** YAML cannot repeat a key, but `Left` and `left` in the
  same file read as a duplicate to a human and one would silently shadow the other.
- An example `track.yml` ships with the templates and `donkey createcar` copies it when absent. A test
  parses that shipped file, so the example cannot rot.

### Acceptance criteria

- [x] `get_track_config` returns segment count, stem/cross lengths, continuity, and named lane offsets
      sourced from the file
- [x] Each invalid input fails at load with a message naming the offending field: missing required key,
      wrong type, negative length, duplicate or unknown lane name
- [x] The schema carries **no** traffic-feature list — geometry and lanes only
- [x] A `lane` name passed to `set_control` is validated against the track config; an unknown name is an
      explicit error, never a silent fallback to 0
- [x] Swapping in a different `track.yml` changes `get_track_config` output with no code edit

---

## M5 — Camera calibration with live preview

- [ ] **M5 done**

**Depends on:** nothing. **Parallel to M2–M4; must never block them.**

Ship a plain `CV_PIXELS_PER_INCH` config constant first so nothing downstream waits on this.

- **Detection:** `cv2.findChessboardCornersSB`, not the classic detector — a board flat on the floor under
  a low pitched camera is exactly where the old one gets flaky. Base OpenCV, so no `contrib` requirement.
- **Solve:** `cv2.findHomography` from corners to ground-plane inches. Persist the scalar at `SCAN_Y` *and*
  the full matrix, stamped with a timestamp and the `SCAN_Y` / `IMAGE_W` / `CAMERA_TYPE` in force at capture.
- **Preview:** reuse `VideoAPI`'s MJPEG stream (`web_controller/web.py:353`); `WebFpv`
  (`web_controller/web.py:401`) is a ~30-line precedent. Overlay the `SCAN_Y` band and paint corners green
  on detection, so the task becomes "make the green line cross the board." Copy the existing `/calibrate`
  page idiom rather than inventing one.
- **Fallback:** two strips of the follow-tape at a known separation, measured with the existing
  `get_i_color()`. ~20 lines, no new detection code, and it calibrates in the controller's own colorspace.
  Covers "no printer" and "board won't detect."

**Known limits, so this doesn't over-promise:** wide-angle Pi cameras have real barrel distortion and a
single homography assumes a pinhole model, so accuracy degrades toward frame edges (fine for the few-inch,
near-center offsets a lane change needs). It calibrates the *mounting* as much as the lens, so any bump
invalidates it. And the board must lie flat on the floor — held vertically the numbers are meaningless.

### Acceptance criteria

- [ ] `donkey calibrate-cv` detects a board and writes a calibration file containing the scalar, the 3×3
      homography, and metadata (timestamp, `SCAN_Y`, `IMAGE_W`, `CAMERA_TYPE`)
- [ ] Preview page streams MJPEG with the `SCAN_Y` band drawn and corners painted green on detection
- [ ] **Accuracy round-trip:** a known board corner maps back to its true ground coordinates within a
      stated tolerance (propose ±0.5 in at 24 in from the camera)
- [ ] `measure_ground_point` returns inches consistent with that tolerance
- [ ] **Staleness detected:** changing `SCAN_Y` in config makes `get_calibration` report the stored
      calibration as stale rather than silently returning it
- [ ] Tape-strip fallback produces a scalar within a stated tolerance of the board result on the same setup
- [ ] With no calibration file present, a manually set `CV_PIXELS_PER_INCH` is still honored
- [ ] Detection and solve are unit-tested against a saved board image — no camera required in CI

---

## M6 — Docs and the activity progression

- [ ] **M6 done**

**Depends on:** M2–M5.

Track construction guide, calibration walkthrough, and one worked agent example per activity. The examples
double as the integration test suite for the tool surface.

### Acceptance criteria

- [ ] Track construction guide: 1 in yellow tape, 3 ft segments, 1 ft perpendicular cross-ticks in red/blue,
      centerline only, avoiding crossings and tight turns
- [ ] Calibration walkthrough covering board placement, the preview overlay, and how to tell it went wrong
- [ ] One runnable agent example for each of the five activities:
  - [ ] Drive once around the track and stop
  - [ ] Stop at stop signs for 5 seconds, then proceed
  - [ ] Stop at obstacles until the obstacle is removed
  - [ ] Drive around obstacles
  - [ ] Stop at a numbered address until commanded to continue
- [ ] Examples run against `MOCK` / `IMAGE_LIST` in CI, not only on hardware
- [ ] Security posture documented: bind address, `TransportSecuritySettings`, and the bearer token

---

# Risks worth designing against

## The one that will bite hardest — agent latency vs. vehicle speed

At `THROTTLE_MIN = 0.15` and a 20 Hz loop, a 1–3 second agent round trip means the car travels a meaningful
distance uncommanded — plausibly a full 3-foot segment. An agent that decides to stop when it *sees* a stop
sign has already passed it.

Three mitigations, all cheap if built in from the start:

- **A watchdog in `MCPBridge`** that zeroes throttle when no agent command has arrived within
  `MCP_COMMAND_TIMEOUT_S` (default ~2 s). Agent silence then fails safe rather than fast-and-forward.
- **Keep the split of responsibilities:** the agent sets slow-changing intent, the CV controller steers at
  loop rate. Never put the agent in the steering path.
- **`measure_ground_point` is a safety feature, not a nicety.** Braking early requires knowing distance.

## Security

A socket server that can make a vehicle move needs a deliberate posture, even on a home network.

- **Bind narrowly.** The default is `127.0.0.1`; widen to the car's LAN address, never `0.0.0.0`.
- **Keep DNS-rebinding protection on.** `TransportSecuritySettings` has
  `enable_dns_rebinding_protection=True` by default — set `allowed_hosts` and `allowed_origins` explicitly
  rather than disabling it to make a client connect.
- **Add a token.** The constructor exposes `token_verifier` and `auth`. This token is the only thing between
  a guest on the WiFi and the throttle.

---

# Testing without a car

Almost all of this is verifiable on a laptop, which matters because the alternative is debugging a moving
vehicle.

- `CAMERA_TYPE='MOCK'` or `'IMAGE_LIST'` with `DRIVE_TRAIN_TYPE='None'` and a bounded `MAX_LOOPS` exercises
  the whole pipeline headlessly — the pattern is already in `donkeycar/tests/test_template.py:17`.
- `IMAGE_LIST` plus a recorded tub of real track footage gives deterministic, repeatable lane-offset and
  calibration tests against genuine imagery.
- Tool handlers test against a synthetic state object with no `Vehicle` at all, following
  `donkeycar/tests/test_web_controller.py`.
- `cv_control.py` already supports `add_simulator()`, so end-to-end agent loops can run against Gym before
  touching hardware — though the simulator has no tape line, so it validates plumbing and lifecycle, not
  line following.

---

*Grounded in the working tree on branch `mcp-server` at `ba25266b`. SDK behavior verified against
`mcp` 2.1.1, ruff 0.16.5, and OpenCV 4.11 as installed.*
