# Distance and speed from a known object — Plan

An agent that can see a stop sign wants to know how far away it is, and how fast the car is
closing on it. The ground-plane calibration (`cv_calibration.json`) cannot answer the first from
an object's size: it holds a floor homography but no focal length, and recovering one from it
on Ed's car gave two estimates 40% apart (224 px and 162 px), because the wide-angle lens is
distorted and the board covers a small patch of floor.

This plan adds an **optional full OpenCV camera calibration** (focal length, principal point and
lens distortion) captured with `donkey calibrate-cv`, and two MCP tools that use it:
`measure_object_distance` and `estimate_speed_from_object`. The ground-plane calibration stays
as it is, and anyone who only wants lane offsets and `measure_ground_point` never needs the new
capture. Without a camera calibration, both new tools answer "unknown".

**Branch:** `mcp-server`

---

## Progress — 6 of 7

- [x] **O1** — Camera intrinsics: model, solver and `camera_intrinsics.json`
- [x] **O2** — `donkey calibrate-cv --intrinsics`: capture page and headless `--from-images`
- [x] **O3** — Bridge loads the intrinsics; `get_calibration` reports them
- [x] **O4** — `measure_object_distance` tool
- [x] **O5** — `estimate_speed_from_object` tool
- [x] **O6** — Docs, the published user manual, and the agent instructions
- [ ] **O7** — Record the hardware check on the car

Each box is ticked in the commit that does the work. Ruff, mypy and the full test suite pass on
every commit.

---

## Decisions

All settled with Ed on 2026-10-22, before O1 started.

| # | Question | Proposal | Why |
| --- | --- | --- | --- |
| D1 | Where the camera calibration lives | **A separate file, `camera_intrinsics.json`**, beside `cv_calibration.json` | Focal length and distortion belong to the camera, lens and resolution, not to how the camera is mounted. Re-doing the floor calibration after bumping the mount must not throw them away, and vice versa. |
| D2 | When the intrinsics are stale | When `IMAGE_W`, `IMAGE_H` or `CAMERA_TYPE` differs from the capture | Same rule as the ground calibration. Changing resolution changes the focal length in pixels. A swapped lens on the same camera type cannot be detected, and the docs say so. |
| D3 | How the capture works | **Board held up at many angles**, the opposite of the ground capture. "Add view" collects a view whenever the corners are found; "Solve" runs `cv2.calibrateCamera` once there are at least **12** views | OpenCV recommends 10–20 views that tilt the board and fill the frame, corners included, so the distortion near the edges is constrained. 12 is a floor, not a target. |
| D4 | Distortion model | OpenCV's standard 5 coefficients (k1, k2, p1, p2, k3). **No fisheye model** | The Pi camera's wide lens is within what the standard model handles at 320×240. Fisheye is a separate model with its own calibration call; it can be added if the standard one leaves large errors at the edges. |
| D5 | A capture that is not good enough | **Refused**, not saved, when the RMS reprojection error is over **1.0 px** or the views leave a frame quadrant empty | A bad camera calibration produces confident wrong distances. Refusing with the reason ("add views near the top-left") is more useful. |
| D6 | What the tools return without a camera calibration | **`"known": false`**, every value `null`, and a `reason` naming `donkey calibrate-cv --intrinsics`. Not an error | Asked for by Ed. "Unknown" is an answer the agent can act on (fall back to `measure_ground_point`); an error reads like a broken tool. |
| D7 | The object's size | `width_inches` and/or `height_inches`; at least one is required | Some signs are known by height, cones by width. With both, the tool reports both estimates and how far apart they are, which shows the agent when the box is poor. |
| D8 | What "distance" means | **`range_inches`**: straight-line distance from the camera to the object's centre. When a ground calibration is also present, **`forward_inches` / `lateral_inches`** on the floor as well | Range needs only the intrinsics. A floor position also needs the camera's height and tilt, which come from combining the intrinsics with the ground homography. |
| D9 | How `estimate_speed_from_object` takes its images | **Two or more observations**, each a bounding box plus the `timestamp` that `get_vehicle_state` returned with that frame. The tool does not store frames | Stateless, like the rest of the tools. The agent already has each frame's timestamp, and the server's own timestamp is better than one the agent makes up. |
| D10 | How speed is computed | A **least-squares fit of range against time**, reported as **closing speed** (positive means getting closer) with an uncertainty | Two frames give a slope; more frames give a better one. The object is assumed to be stationary, so the speed is the car's. |
| D11 | Observations too close in time to mean anything | **Answered with the uncertainty and a warning**, not refused, when the uncertainty is bigger than the speed | The agent can decide what to do with a noisy answer; refusing would hide how noisy it is. |
| D12 | Uncertainty | Propagated from **±1 px on each box edge**, stated in the payload | Bounding boxes from a language model are often several pixels off. Saying what was assumed lets the agent widen it. |
| D13 | Keeping the calibration views | **Saved.** Each capture writes every view added, including any the solve rejected, to its own timestamped folder, `<car>/camera_calibration_views/<YYYY-MM-DDTHH-MM-SS>/view_NN.png`, with a `views.json` recording which views were used and each one's reprojection error. **Nothing deletes old folders** | `--from-images` can re-solve without the car (a different model or threshold later); the frames show why a bad solve went wrong (blur, board half out of frame, corners never covered); and real frames from the car's lens make better test data than synthetic ones. A 20-view capture is about 2–3 MB, and clean-up stays the user's call. |

---

## O1 — Camera intrinsics

**Files:** `donkeycar/parts/camera_intrinsics.py` (new), `donkeycar/tests/test_camera_intrinsics.py` (new).

- `CameraIntrinsics` dataclass: `fx`, `fy`, `cx`, `cy`, `distortion` (5 floats), `image_w`,
  `image_h`, `camera_type`, `rms_error_px`, `view_count`, `captured_at`, `loaded_from`
  (reported, never saved, as in `Calibration`).
- `solve_intrinsics(corner_sets, pattern, square_inches, image_size)` wraps
  `cv2.calibrateCamera` and applies the D5 checks.
- `save` / `load` with strict validation (unknown or missing fields refused), `stale_reasons(cfg)`
  (D2), and `undistort_points(points)` returning normalised image coordinates.
- `load_intrinsics(car_dir, cfg)` finds `camera_intrinsics.json` in the car directory.

**Acceptance**

- [x] From board corners projected through a known camera (focal length, centre and distortion
      chosen in the test), the solver recovers the focal length within 1% and the centre within
      2 px.
- [x] A capture with fewer than 12 views, an empty quadrant, or RMS over 1.0 px is refused,
      naming the reason.
- [x] Save then load round-trips; `loaded_from` is never written to the file.
- [x] A file with an unknown or missing field is refused, naming it.
- [x] Changing `IMAGE_W`, `IMAGE_H` or `CAMERA_TYPE` makes it stale.
- [x] `undistort_points` inverts the distortion applied in the test to within 0.1 px.

## O2 — Capture

**Files:** `donkeycar/management/calibrate_cv.py`, its tests.

- `--intrinsics` switches the preview page to camera-calibration mode. The page says to hold the
  board up and tilt it, shows the views collected so far and a coverage grid of the frame, and
  has **Add view** and **Solve** buttons. Solve writes `camera_intrinsics.json` and shows the
  focal length, RMS error and view count, or the D5 refusal.
- Each view is written to the capture's folder as it is added, and `views.json` is written on
  Solve, refused or not (D13). The page shows the folder's path.
- `--from-images "<glob>"` solves from saved frames without a camera or page, for a laptop or
  for re-running on a folder kept from an earlier capture. It writes no new views folder.
- The ground-plane capture (the default) is unchanged and does not touch `camera_intrinsics.json`.

**Acceptance**

- [x] `--from-images` on synthetic board images writes a file that loads.
- [x] Add view with no board visible is refused and adds nothing.
- [x] Solve before 12 views is refused, saying how many more are needed.
- [x] The default ground capture still writes only `cv_calibration.json`.
- [x] Every view added is saved as a PNG in a new timestamped folder under
      `camera_calibration_views/`, including views the solve rejects.
- [x] `views.json` lists every view with whether it was used and its reprojection error, and is
      written for a refused solve as well as a successful one.
- [x] A second capture writes a second folder and leaves the first untouched.
- [x] `--from-images` pointed at a saved folder reproduces that capture's focal length and
      RMS error.

## O3 — Bridge and `get_calibration`

**Files:** `donkeycar/parts/mcp_server.py`, `donkeycar/parts/mcp_tools.py`, their tests.

- The bridge loads the intrinsics beside the ground calibration, and re-reads them on `start`.
  A malformed file refuses to start, like a malformed `cv_calibration.json`.
- `get_calibration` gains a `camera` section: the intrinsics, `stale`, `stale_reasons` and
  `loaded_from`, or `{"calibrated": false, "reason": ...}` when there is no file.

**Acceptance**

- [x] With no `camera_intrinsics.json`, `get_calibration` reports `camera.calibrated: false` and
      the rest of the payload is unchanged.
- [x] With one, the `camera` section carries the values and its `loaded_from` path.
- [x] Editing the file and calling `stop` then `start` reports the new values.

## O4 — `measure_object_distance`

**Files:** `donkeycar/parts/object_distance.py` (new), `donkeycar/parts/mcp_server.py`,
`donkeycar/parts/mcp_tools.py`, their tests.

- Input: `box` (`x_min`, `y_min`, `x_max`, `y_max` in pixels of the camera frame) and
  `width_inches` and/or `height_inches` (D7).
- Method: undistort the midpoints of the box's edges into rays, and take the range at which the
  known size subtends the angle between opposite rays. With both sizes, the two ranges are
  combined weighted by their uncertainty. With a ground calibration too, the camera's height and
  tilt come from the homography and the intrinsics (`solvePnP` on floor points the homography
  knows), and give `forward_inches` / `lateral_inches` (D8).
- *Changed while building O4:* the plan first said "depth along the optical axis", a span on the
  image plane. Prototyping showed that is off by up to 6% for an upright sign when the camera is
  pitched 20° down, because the image plane is tilted and the sign is not. The angle between rays
  does not depend on the pitch, so it is used instead.
- Output: `known`, `range_inches`, `range_from_width_inches`, `range_from_height_inches`, their
  disagreement as a fraction, `range_uncertainty_inches` (D12), the floor position when
  available, and a note: the object should be upright and roughly facing the camera, the box
  tight, and accuracy falls toward the frame edges.
- Without intrinsics, or with stale ones: `known: false` and the reason (D6).

**Acceptance**

- [x] A synthetic object of known size rendered at 24, 60 and 120 inches through a known camera
      measures within 3%, with and without distortion. *Changed while building O4:* within 3% at
      60 and 120 inches, and **5% at 24 inches**, for a sign turned toward a camera pitched 10°
      down, centred or 6 inches to the side. Close up, an axis-aligned box cannot say which row of
      the tilted sign set its width; at 24 inches the width estimate is off by up to 4%.
- [x] Width-only, height-only and both give consistent answers; both report the disagreement.
- [x] Neither size given is refused, naming the two fields.
- [x] A box outside the frame, or with zero width or height, is refused.
- [x] No intrinsics: `known: false`, values `null`, the reason names `calibrate-cv --intrinsics`.
- [x] With a ground calibration as well, the floor position agrees with `measure_ground_point`
      at the object's base within 5%.

## O5 — `estimate_speed_from_object`

**Files:** `donkeycar/parts/object_distance.py`, `donkeycar/parts/mcp_server.py`,
`donkeycar/parts/mcp_tools.py`, their tests.

- Input: the object's `width_inches` and/or `height_inches`, and `observations`: two or more
  `{timestamp, box}` (D9).
- Each observation goes through the O4 range calculation; a least-squares line through range
  against time gives `closing_speed_inches_per_s` and its uncertainty (D10, D12).
- Output: `known`, the speed and uncertainty, `span_s`, each observation's range, and a warning
  when the uncertainty is larger than the speed (D11). It says the object is assumed stationary.
- *Changed while building O5:* the warning fires when the frames span **under 0.5 s**, or when
  the uncertainty is **more than half** the speed. "Uncertainty larger than the speed" alone
  missed two in three of the cases it was meant for: on a short span, box noise inflates the
  measured speed as much as its uncertainty, so the two look consistent while both are wrong
  (frames 0.1 s apart with 2 px noise: 34% warned under the old rule, 100% under the new; frames
  0.5 s apart, seven of them, 1 px noise: 0% under both). With three or more frames, the
  uncertainty is also widened when the points scatter more than 1 px per edge explains.
- Without intrinsics: `known: false` and the reason (D6).

**Acceptance**

- [x] Synthetic observations of an approaching object at a known speed give that speed within 5%.
- [x] A receding object gives a negative closing speed; a stationary one gives about zero.
- [x] Fewer than two observations, or two with the same timestamp, is refused.
- [x] Observations 0.1 s apart with ±2 px box noise return a speed with the noise warning
      (checked over 20 noise seeds, every one warned).
- [x] Observations out of time order give the same answer as the sorted ones.
- [x] No intrinsics: `known: false`, the reason names `calibrate-cv --intrinsics`.

## O6 — Docs

**Files:** `docs/mcp-server.md`, `docs/mcp-server-manual.html`, the server `INSTRUCTIONS` in
`donkeycar/parts/mcp_tools.py`.

- Calibration section: the two calibrations, what each one enables, and that the camera one is
  optional. How to run `--intrinsics`: print the board, hold it up, tilt it, fill the corners of
  the frame, and what a good RMS looks like.
- Tool table: the two new tools, and the `camera` section of `get_calibration`.
- `INSTRUCTIONS` tell the agent: prefer `measure_object_distance` for an object of known size,
  fall back to `measure_ground_point` at the object's base when the answer is unknown, and use
  observations at least half a second apart for speed.

## O7 — Hardware check

Run on the car by Ed, with Claude driving the MCP calls from the Mac. The steps below assume no
other context. The commit records the results and any fixes.

**The car:** `murmurpi64.local`, user `ed`, car directory `~/mycar`, donkeycar checkout
`~/projects/donkeycar`. It was at `10.0.0.32` on 2026-10-21; run `hostname -I` on the car to
check, and use whatever it prints wherever `10.0.0.32` appears below. **Keep the ESC unpowered
throughout**: nothing here needs the motor, and the car is rolled by hand.

### You will need

- The checkerboard, `assets/checkerboard/calibration-checkerboard-9x6-1in-letter.pdf`, printed
  at **100% / actual size** (not "fit to page"). Check with a ruler that one square is exactly
  1 inch. Tape it flat to something rigid: a clipboard, foam board or a book cover. It has 10×7
  squares, which is 9×6 inner corners, the tool's default.
- The large stop sign, `assets/track-cards/stop-sign-large.pdf`: one Letter sheet, printed at
  100%, folded in half on the dashed line, and stood **upright** in a card stand, the kind used
  for trading cards, fold at the top. Its octagon is 4.5 inches across. The 3-inch track card's
  octagon (2 1/16 inches) is about 5 px across at 120 inches at 640×480, too small for a
  one-pixel box error not to dominate; it can still be used at 12, 24 and 48 inches. Check by eye from the side that it is vertical, not leaning back.
  **Measure the octagon's width and its height across its flat sides with a ruler**, and write
  both down: these are the `width_inches` and `height_inches` used below. Also measure the height
  of the octagon's centre above the floor, in the stand. (A folded tent would lean back, which
  makes the sign look shorter to the camera than it is; the stand avoids that, so both sizes can
  be used.)
- A tape measure, a stopwatch (a phone is fine), and masking tape to mark the floor.
- A laptop or phone browser on the same network as the car.

### Step 1 — Deploy

1. On the Mac, push `mcp-server` (or ask Claude to).
2. On the car: `cd ~/projects/donkeycar && git pull --ff-only`. Check `git log --oneline -1`
   shows the commit that ticked O6 or later.
3. If a `donkey mcp` server is running, stop it with Ctrl-C. The calibration in step 2 needs the
   camera to itself.

### Step 2 — Capture the camera calibration

1. On the car: `cd ~/mycar && donkey calibrate-cv --car ~/mycar --intrinsics`
2. In the browser, open `http://10.0.0.32:8892`. The page should say "Camera calibration" and
   show the live camera. Use the car's address, not `localhost`, even though the command's
   startup message prints `http://localhost:8892`: on the laptop, `localhost` is the laptop.

   **If the browser says `ERR_ADDRESS_UNREACHABLE`** (Chrome) or cannot connect, first check the
   command is still running in the SSH session; if it exited, the terminal says why. If it is
   running, the browser is probably being blocked by macOS. Since macOS 15, each app needs
   **Local Network** permission to reach devices on the local network, and without it every
   local address fails this way, while Terminal and `curl` still connect. To fix it, open
   **System Settings → Privacy & Security → Local Network**, turn on the browser, quit it
   completely (Cmd-Q), and reopen it. If the browser is not listed, try Safari. Seen on
   2026-10-23 on Ed's Mac: Chrome was ticked, but listed **twice**, and still could not connect
   while Firefox, Terminal and `curl` could. A duplicate usually means a stale entry left by a
   Chrome update, and the permission that counts can be on the other one: turn both entries off
   and back on, then quit Chrome with Cmd-Q, since closing its windows can leave it running.
   Firefox is a fine alternative for the whole check. On a laptop
   other than the Mac, check it is on the same network as the car, not a guest network or a
   VPN: `curl -I http://10.0.0.32:8892/` from its terminal shows whether it can reach the car
   at all. This applies to every page on the car, including the MCP server on port 8891.
3. Hold the board up in front of the camera, 1–3 feet away, and keep it still. When the corners
   are drawn on the preview, press **Add view**. If it says "No 9x6 board found", move the board
   closer or into better light and try again.
4. Repeat until there are at least 15 views, changing something each time: move the board to the
   left, right, top and bottom of the frame and into all four corners; tilt it left, right,
   forward and back by about 30°; hold it near and far. The grid under the buttons shows how many
   views reach each quadrant of the frame. Every square needs at least 3.
5. Press **Solve**. A good result shows `"ok": true` and `rms_error_px` under 0.5. If it is
   refused, the message says what to fix; add the views it asks for and press Solve again.
6. Stop the page with Ctrl-C.

**Record:** `fx`, `fy`, `cx`, `cy`, the five `distortion` values, `rms_error_px`, `view_count`,
and the views folder's path. Check by eye that `fx` and `fy` agree within about 2%, and that `cx`
and `cy` are within about 20 px of 160 and 120.

### Step 3 — Start the server

On the car, from `~/mycar`:

```
PYTHONUNBUFFERED=1 donkey mcp --car ~/mycar --host 10.0.0.32 --port 8891 2>&1 | tee -ia ~/mcp.log
```

Claude then calls `cv_control-get_calibration`. **Record:** whether the `camera` section shows
`calibrated: true`, `stale: false`, and a `loaded_from` of `/home/ed/mycar/camera_intrinsics.json`.

### Step 4 — Distance at three ranges

1. Put the car on the floor where it can see down a clear stretch. Mark the floor directly
   below the camera lens with tape. Measure the lens's height above the floor and write it down.
2. Stand the stop sign straight ahead of the car, facing it, with the front of its base on a
   tape mark at **24 inches** from the mark under the lens, measured along the floor.
3. Tell Claude it is in place. Claude calls `start`, takes a frame with
   `cv_control-get_vehicle_state`, finds the sign's box, calls `measure_object_distance` with
   your `width_inches` and `height_inches`, and then calls `stop`. The car stays still: the
   throttle stays 0.
4. Repeat at **60 inches** and **120 inches**.
5. Repeat at 60 inches with the sign about 12 inches to the left of straight ahead, still facing
   the car.

Claude boxes the sign two ways each time: by colour (a red mask on the saved frame, which is
pixel-tight), and by eye from the image (rough, the way an agent would). This separates the
tool's accuracy from the box's.

**Record, for each placement:** the floor distance; the true range, which Claude works out from
the floor distance, the lens height and the sign's centre height; `range_inches`,
`range_uncertainty_inches`, `range_from_width_inches`, `range_from_height_inches` and
`size_disagreement` for both boxes; and the percentage error. **Pass:** the colour-box
range within 5% at 60 and 120 inches and within 8% at 24 inches, and the true range inside about
twice `range_uncertainty_inches`, and `size_disagreement` under 0.1 for the colour box. The
real lens and a printed card are rougher than the synthetic
tests, so these targets are looser than O4's; a miss beyond them is a finding to fix, not a fail
to wave through.

### Step 5 — Speed, rolled by hand

1. Stand the sign at the 24-inch mark again. Mark the floor at **120 inches** and **48 inches**
   from the sign: a 72-inch run.
2. Put the car at the 120-inch mark, pointing at the sign. Tell Claude, who calls `start` and
   begins taking frames with their timestamps, about every half second.
3. Start the stopwatch and push the car steadily and straight toward the sign. Stop it at the
   48-inch mark and stop the stopwatch. Aim for 3–5 seconds over the run. Tell Claude the time.
4. Claude calls `estimate_speed_from_object` on the frames from the run, then `stop`.
5. Repeat twice: once with every frame, and once with only two frames about a second apart. Then
   leave the car still for 3 seconds and estimate again.

**Record:** the stopwatch speed (72 inches ÷ seconds); `closing_speed_inches_per_s`, its
uncertainty, `span_s` and any `warning` for each estimate; and the stationary estimate.
**Pass:** the all-frames speed within 15% of the stopwatch speed (hand-pushing is not steady,
and a stopwatch is good to about 0.2 s), the stationary estimate within its own uncertainty of
zero, and no `warning` on the full run.

### Step 6 — Wrap up

1. Stop the server with Ctrl-C.
2. Keep the views folder: it is the first real-lens test data. Claude asks before copying any of
   it into the repository.
3. Claude writes the results into this section, ticks O7, and commits. Any failure gets a fix,
   or a note here on why it is accepted.

### Results

**Resolution.** Ed changed the camera to **640×480** (`IMAGE_W`/`IMAGE_H` in `myconfig.py`)
before the check, so the step 2 rules of thumb scale up: the principal point near (320, 240)
rather than (160, 120), and RMS errors in pixels about twice the 320×240 figures. The floor
calibration in `~/mycar/cv_calibration.json` was captured at 320×240 and is now stale; it needs
recapturing at 640×480 before anything that uses it (lane offsets, `measure_ground_point`, the
floor position from `measure_object_distance`).

**Step 2, 2026-10-23.** Passed. 22 views, all used; folder
`~/mycar/camera_calibration_views/2026-10-23T17-21-34/`.

| Value | Result | Check |
| --- | --- | --- |
| `fx`, `fy` | 315.34, 314.71 px | agree within 0.2% (target 2%) |
| `cx`, `cy` | 311.81, 226.46 px | 8 and 14 px from the frame centre (target about 20 at 320×240, so 40 here) |
| distortion | k1 −0.348, k2 0.157, p1 −0.0001, p2 0.0010, k3 −0.038 | strong barrel distortion, as expected of a wide lens |
| `rms_error_px` | 0.185 | well under 0.5 |
| per-view error | 0.140–0.219 px, median 0.189 | no outlier view |

A focal length of 315 px at 640 px wide is a horizontal field of view of about 91°. For
comparison, the two estimates recovered from the floor homography at 320×240 (224 and 162 px,
which would be 448 and 324 px at this size) were 42% and 3% off: this is why the size-based
tools needed a real camera calibration.

**Before step 3, 2026-10-23 and 24: the floor calibration and line-follower settings for
640×480.** The floor calibration was recaptured twice. The first recapture, at `SCAN_Y = 100`,
went in with `--lateral-inches 4` for a centred board, when that flag wanted left as negative.
That put the straight-ahead column 8 inches right of the centreline, and led to renaming the flag
`--left-inches` (positive to the left). The line follower's pixel settings in `~/mycar/myconfig.py`
were then scaled for 640×480: `SCAN_Y` 100→200, `SCAN_HEIGHT` 80→160, `TARGET_PIXEL` 160→320,
`TARGET_THRESHOLD` 20→40, `PID_P` −0.01→−0.005, `PID_D` −0.0001→−0.00005, and the two PID step
sizes halved. They are not yet checked on a drive. The second recapture, at `SCAN_Y = 200`, left the
left offset out, because the old flag name had stopped working; `origin_lateral_inches` was set to
−4.0 by hand for the centred board, putting the straight-ahead column at 0 lateral. The old flag
name now says what replaced it. Saved capture: `~/mycar/cv_calibration_captures/2026-10-24T11-58-44/`.

**Step 3, 2026-10-24.** Passed. `cv_control-get_calibration` on the running server:

| | Floor | Camera |
| --- | --- | --- |
| `calibrated` / `stale` | true / false | true / false |
| `loaded_from` | `/home/ed/mycar/cv_calibration.json` | `/home/ed/mycar/camera_intrinsics.json` |
| Size | 640×480 | 640×480 |
| Values | 8.135 px/in at `SCAN_Y` 200; origin 8.625 in forward, −4.0 lateral | `fx` 315.34, `fy` 314.71, centre (311.81, 226.46) |
| Quality | 0.089 px fit; `can_measure_points` true | 0.185 px RMS over 22 views |

**Step 4 set-up, 2026-10-24.** The large stop sign, octagon measured at **4.5 in** across the
flats both ways, stands in a card stand with its bottom 5/8 in, its top 5 1/8 in and its centre **2 7/8 in** above
the floor. The camera lens is **7.5 in** above the floor (a standard Donkeycar on the Exceed
Magnet chassis), so the lens is 4 5/8 in above the sign's centre, and the true range is
√(floor distance² + 4.625²): 24.44 in at 24, 60.18 at 60, 120.09 at 120, and 61.36 at 60 with
the sign 12 in to the left.

**Step 4, 24 inches, 2026-10-24.** The sign's face was at 24 in from the lens mark (Ed placed
the sign itself, not the base, on the mark); true range 24.44 in. The floor calibration alone
put the card's base 24.14 in ahead and 0.3 in right, which checks it independently.

| Box | Range | Error | Width / height ranges | Disagreement | Floor (fwd, lat) |
| --- | --- | --- | --- | --- | --- |
| Edge (outer edge of the dark border, from the card-to-border brightness step) | 25.71 ± 0.46 | +5.2% | 25.44 / 26.01 | 0.022 | 24.66, +0.31 |
| By eye | 25.48 ± 0.45 | +4.3% | 25.30 / 25.68 | 0.015 | 24.42, +0.38 |
| Colour mask | 27.41 ± 0.52 | +12.2% | 26.74 / 28.26 | 0.055 | 26.33, +0.47 |

The colour mask first boxed a red object on a shelf (the largest red blob), then, once restricted
to the octagon, left out the dark red border, which is too dark in room light to count as red:
3 px small and +12%. This is what led to `TRACK_CARDS_CV_PLAN.md`. The edge and eye boxes pass
the 8% target at 24 in and the disagreement target, but miss the "true range within twice the
uncertainty" target: both read 4–5% long, in width and height alike, so the error is systematic.
Placement is ruled out. The candidates are a focal length a few percent off, or box edges a pixel
or two inside the true edge; the 60 and 120 in placements separate them, since a focal-length
error is the same fraction at every range and a fixed pixel error grows as the sign shrinks.

**Lens mark corrected, 2026-10-24.** Ed re-measured the lens position (the bumper had been in the
way): the floor calibration's reference corner is **9 1/16 in** ahead of the lens, not 8 5/8
(first reported as 8 15/16, then corrected). `origin_forward_inches` in the car's
`cv_calibration.json` is now 9.0625 (backups kept). The lens is 7/16 in further back than the
mark used for the 24 in placement above, so that sign was about 24 7/16 in from the lens (true
range about 24.87 in), which accounts for about 1.8 points of the +5.2%. The 24 in placement is
to be redone, measured from the corrected mark, with the reprinted red-to-the-edge sign.

**Step 4, 60 inches, 2026-10-24.** The reprinted sign, measured from the corrected lens mark;
true range 60.18 in. The room was dark and the card brightly lit, so it came out cyan and the
red octagon purple-blue (OpenCV hue 115–125). No red mask finds it in that light. Boxed instead
where the hue crosses halfway from the card (about 93) to the octagon (about 118):

| Box | Range | Error | Width / height ranges | Disagreement | Floor (fwd, lat) |
| --- | --- | --- | --- | --- | --- |
| Hue halfway, 23 × 23 px | 61.69 ± 2.57 | +2.5% | 61.88 / 61.50 | 0.006 | 60.94, +1.78 |
| Hue core only, 20 × 20 px | 70.95 ± 3.38 | +17.9% | 71.17 / 70.73 | 0.006 | 70.12, +1.97 |

The halfway box passes all three targets. At 23 px a 1 px box error is 4% of range, so the
box rule matters as much as the optics.

`measure_ground_point` at the card's base read about 42.5 in, not about 60. solvePnP on the
chessboard in this frame and in the floor capture's saved frame shows why: the lens is
7.36 in up now and 7.41 in then, but its axis is **12.5°** below level now and **14.7°** then.
The car had been moved since the floor capture. A 2.2° change in pitch is a few pixels near the
car, but at 60 in it moves the floor reading by 18 in. The angular range doesn't depend on
pitch, so it is unaffected.

---

## Out of scope

- Using the intrinsics to undistort the ground-plane capture. It would improve
  `measure_ground_point` near the frame edges, but it changes an existing calibration's numbers
  and deserves its own change once the camera calibration has been proven on the car.
- A fisheye distortion model (D4).
- Detecting objects. The agent supplies the bounding box; the server only measures it.
- Car directories such as `~/mycar` are never committed; the new file lives there once captured.
