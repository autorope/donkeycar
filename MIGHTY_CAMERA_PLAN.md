# MightyCamera as an image camera (`CAMERA_TYPE = "MIGHTY"`)

**Progress: 0 / 9 commits verified**

Branch: `zlite/mighty-camera-gps`. Today the Mighty camera only feeds poses to
`path_follow` (`HAVE_MIGHTY`), and its images are ignored. This plan adds a
`MightyCamera` part that publishes `cam/image_array` like `PICAM`, `WEBCAM` and
`CVCAM`. You select it in any template's `myconfig.py` with
`CAMERA_TYPE = "MIGHTY"`.

## How the work proceeds

- **One commit at a time.** Each commit is made, then verified. Only after
  that is its box ticked, with a note saying how it was verified. Work then
  stops until Ed says to start the next commit.
- **Verification** means the checks listed under the commit pass:
  - `pytest` for the Mighty and template tests in the Mac's `.venv`;
  - the same tests on the car (`~/env`, `~/projects/donkeycar`), after Ed
    pushes and the car pulls;
  - any hardware check the commit names.
- **Ticking.** The tick and its note are a small follow-up commit
  (`Tick plan: commit N verified`), since verification on the car can only
  happen after the work is pushed.
- **Recording what we learn.** Anything learned along the way goes under
  **Findings**. Any choice made goes under **Decisions**, with its date and
  who made it.

## Decisions

| # | Date | Decision | By | Status |
|---|------|----------|----|--------|
| D1 | 2026-11-14 | Plan before code; one commit per template; strict type hints; tests pass on every commit. | Ed | Decided |
| D2 | 2026-11-14 | Go one commit at a time; tick each box only once that commit is verified. | Ed | Decided |
| D3 | 2026-11-14 | Plans carry a Decisions section and a Findings section. | Ed | Decided |
| D4 | 2026-11-14 | `MightyCamera` lives in `donkeycar/parts/mighty.py`, beside `MightyPose`. | Claude | Proposed |
| D5 | 2026-11-14 | Pose and camera share one SDK connection per URL (`MightyLink`), which means changing `MightyPose` in commit 3. Ed: "Here we are explicitly changing the python code in donkeycar, so it is ok to edit MightyPose or other parts or the templates." | Ed | Decided |
| D6 | 2026-11-14 | Resize by stretching to `IMAGE_W`×`IMAGE_H`; the docs suggest `IMAGE_H = 100` to keep 16:10. No crop or undistort option for now. | Ed | **Open** |
| D7 | 2026-11-14 | Decode in the part's own thread. The SDK callback only stores the newest frame's bytes, so a JPEG decode never delays pose packets. | Claude | Proposed |
| D8 | 2026-11-14 | Fail fast like `CvCam`: raise `CameraError` if no frame arrives within `MIGHTY_CAMERA_WARMUP_SECS` (default 5.0). After that, return the last frame and log one warning once frames stop arriving for longer than 1 s. | Claude | Proposed |
| D9 | 2026-11-14 | Reuse `MIGHTY_URL`. Add only `MIGHTY_CAMERA_WARMUP_SECS`. | Claude | Proposed |

## Findings

| # | Date | Finding | Source |
|---|------|---------|--------|
| F1 | 2026-11-14 | SDK `mighty-protocol 0.1.0` and firmware `Mighty v.2026-10-01-e2aac61`, reached at `http://192.168.7.1` over USB Ethernet. | Probe on murmurpi64 |
| F2 | 2026-11-14 | Images arrive as `kind='jpg'`, `channel='cam0'`, 640×400, about 18.7 KB each, at about 18 fps. The sensor is mono: all three channels decode identical. The lens is a wide fisheye. | Probe on murmurpi64, one frame saved and viewed |
| F3 | 2026-11-14 | Images stream with VIO off (state 0). The camera works without pose tracking. | Probe on murmurpi64 |
| F4 | 2026-11-14 | Two `MightyClient` streams can run at once, but each got about 13 fps instead of 18. | Probe on murmurpi64 |
| F5 | 2026-11-14 | On the Pi, PIL JPEG decoding plus a resize to 160×120 takes about 9 ms per frame. | Probe on murmurpi64, mean of 20 runs |
| F6 | 2026-11-14 | The SDK skips JPEG handling when no image listener is registered, so a pose-only setup costs nothing extra. | `mighty_sdk/client.py` |
| F7 | 2026-11-14 | `templates/path_follow.py` has an unused `from distutils.log import debug`. It stops `test_path_follow_mighty.py` from importing on the Mac's Python 3.12+ venv. The test passes on the car (15 passed) only because setuptools provides a `distutils` shim. | `pytest` on Mac and car |

## Design

- **`MightyCamera`** (D4, D7, D8) is a threaded part with the usual `update`,
  `run_threaded`, `run` and `shutdown`.
  - It uses the SDK's `select_primary_image` / `image_to_raw`. It accepts
    `jpg`, the `stereo_*` primary (`cam0`/left) and raw `GRAY8`, `RGB24` and
    `BGR24`.
  - Each decode takes only the newest frame; older frames are dropped and
    never queued.
  - Output is `IMAGE_W`×`IMAGE_H`. With `IMAGE_DEPTH=3` it is RGB `uint8`
    (H, W, 3), with the grey copied into all channels. With `IMAGE_DEPTH=1` it
    is (H, W). This follows `PiCamera` and `Webcam`.
  - A missing SDK raises the same install hint `MightyPose` gives.
- **`MightyLink`** (D5) is a small reference-counted holder, one per URL, that
  owns a single `MightyClient`.
  - The first `acquire()` connects and the last `release()` disconnects.
  - `MightyPose` still owns `start_vio` and the high-rate pose command.
- **Config** (D9): set `CAMERA_TYPE = "MIGHTY"`. The comment listing camera
  types in each `cfg_*.py` gains `MIGHTY`.

## Commits

Each box is ticked only after the checks listed under it pass (D2).

- [ ] **1. Add this plan.**
  - *Verify:* Ed reviews the plan and settles D5 and D6.
- [ ] **2. Remove the stray `distutils` import in `templates/path_follow.py`
  (F7).**
  - *Verify:* `test_mighty*.py` and `test_path_follow_mighty.py` pass on the
    Mac and on the car.
- [ ] **3. Add the `MightyLink` shared connection, and switch `MightyPose` to
  it (D5).**
  - *Verify:* new tests pass: the first acquire connects, the last release
    disconnects, and the same URL returns the same client.
  - *Verify:* all existing Mighty tests pass on the Mac and on the car.
  - *Verify:* on the car, a short pose-only run of the existing
    `HAVE_MIGHTY` setup still logs `Mighty pose stream: fresh`.
- [ ] **4. Add the `MightyCamera` part, unit tests, and a `snapshot` CLI.**
  - The CLI runs as
    `python -m donkeycar.parts.mighty snapshot --url ... --out frame.jpg --seconds 5`.
    It saves one frame and prints the measured fps.
  - The unit tests use a fake client fed with PIL-generated JPEGs. They cover
    depth 1 and 3, output size, newest frame wins, the warm-up timeout raising
    `CameraError`, stereo/raw selection, shutdown releasing the link, and the
    missing-SDK message.
  - *Verify:* the tests pass on the Mac and on the car.
  - *Verify:* the CLI on the car saves a viewable frame and reports about
    18 fps (F2).
- [ ] **5. `complete` template.** Adds a `MIGHTY` branch to `get_camera()` in
  `templates/complete.py`, and updates `cfg_complete.py`.
  - *Verify:* a test that `get_camera` builds a `MightyCamera` from config,
    with the SDK mocked.
- [ ] **6. `path_follow` template.** Updates `cfg_path_follow.py`: the camera
  types list and the warm-up setting. `MIGHTY_URL` is already there.
  - *Verify:* `test_path_follow_mighty.py` gains a case with `HAVE_MIGHTY` and
    `CAMERA_TYPE="MIGHTY"` set, checking that both parts share one client.
- [ ] **7. `cv_control` template.** Updates `cfg_cv_control.py`; the template
  already goes through `add_camera`.
  - *Verify:* a template test with `CAMERA_TYPE="MIGHTY"`.
- [ ] **8. `basic` template.** Adds a `MIGHTY` branch to the camera chain in
  `templates/basic.py`, and updates `cfg_basic.py`.
  - *Verify:* a template test with `CAMERA_TYPE="MIGHTY"`.
- [ ] **9. Docs.** Adds a camera section to `docs/mighty.md` covering config,
  image format and aspect ratio, sharing the connection, and a
  self-contained hardware runbook.
  - *Verify:* Claude runs the runbook as written on murmurpi64.
  - *Verify:* Ed sets `CAMERA_TYPE = "MIGHTY"` in a car directory of his own
    and sees the live image in the web UI at `http://murmurpi64.local:8887`.
  - *Verify:* with `HAVE_MIGHTY = True` also set, the image and
    `Mighty pose stream: fresh` appear together.

## Not in this plan

- Crop or undistort options for the fisheye (D6).
- Publishing depth (`DPT `), stereo pairs or the right camera.
- Changes to the pose transform, gates or look-ahead controller.
- Editing any car directory (`~/mycar*`). Ed makes those config changes.
