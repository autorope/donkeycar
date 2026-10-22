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

## Progress — 2 of 7

- [x] **O1** — Camera intrinsics: model, solver and `camera_intrinsics.json`
- [x] **O2** — `donkey calibrate-cv --intrinsics`: capture page and headless `--from-images`
- [ ] **O3** — Bridge loads the intrinsics; `get_calibration` reports them
- [ ] **O4** — `measure_object_distance` tool
- [ ] **O5** — `estimate_speed_from_object` tool
- [ ] **O6** — Docs, the published user manual, and the agent instructions
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

- [ ] With no `camera_intrinsics.json`, `get_calibration` reports `camera.calibrated: false` and
      the rest of the payload is unchanged.
- [ ] With one, the `camera` section carries the values and its `loaded_from` path.
- [ ] Editing the file and calling `stop` then `start` reports the new values.

## O4 — `measure_object_distance`

**Files:** `donkeycar/parts/object_distance.py` (new), `donkeycar/parts/mcp_server.py`,
`donkeycar/parts/mcp_tools.py`, their tests.

- Input: `box` (`x_min`, `y_min`, `x_max`, `y_max` in pixels of the camera frame) and
  `width_inches` and/or `height_inches` (D7).
- Method: undistort the box corners, take depth along the optical axis from each known size,
  and turn depth into `range_inches` through the box centre's direction. With a ground
  calibration too, the camera's height and tilt come from the homography and the intrinsics, and
  give `forward_inches` / `lateral_inches` (D8).
- Output: `known`, `range_inches`, `range_from_width_inches`, `range_from_height_inches`, their
  disagreement as a fraction, `range_uncertainty_inches` (D12), the floor position when
  available, and a note: the object should be upright and roughly facing the camera, the box
  tight, and accuracy falls toward the frame edges.
- Without intrinsics, or with stale ones: `known: false` and the reason (D6).

**Acceptance**

- [ ] A synthetic object of known size rendered at 24, 60 and 120 inches through a known camera
      measures within 3%, with and without distortion.
- [ ] Width-only, height-only and both give consistent answers; both report the disagreement.
- [ ] Neither size given is refused, naming the two fields.
- [ ] A box outside the frame, or with zero width or height, is refused.
- [ ] No intrinsics: `known: false`, values `null`, the reason names `calibrate-cv --intrinsics`.
- [ ] With a ground calibration as well, the floor position agrees with `measure_ground_point`
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
- Without intrinsics: `known: false` and the reason (D6).

**Acceptance**

- [ ] Synthetic observations of an approaching object at a known speed give that speed within 5%.
- [ ] A receding object gives a negative closing speed; a stationary one gives about zero.
- [ ] Fewer than two observations, or two with the same timestamp, is refused.
- [ ] Observations 0.1 s apart with ±2 px box noise return a speed with the noise warning.
- [ ] Observations out of time order give the same answer as the sorted ones.
- [ ] No intrinsics: `known: false`, the reason names `calibrate-cv --intrinsics`.

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

Run on the car by Ed, with the steps written into this plan before he starts so they need no
other context: capture the intrinsics, then measure a stop sign card at three tape-measured
distances and compare, then roll the car toward it by hand and compare the speed with a
stopwatch. The commit records the results and any fixes.

---

## Out of scope

- Using the intrinsics to undistort the ground-plane capture. It would improve
  `measure_ground_point` near the frame edges, but it changes an existing calibration's numbers
  and deserves its own change once the camera calibration has been proven on the car.
- A fisheye distortion model (D4).
- Detecting objects. The agent supplies the bounding box; the server only measures it.
- Car directories such as `~/mycar` are never committed; the new file lives there once captured.
