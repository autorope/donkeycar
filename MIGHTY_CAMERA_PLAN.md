# MightyCamera as an image camera (`CAMERA_TYPE = "MIGHTY"`)

**Progress: 5 / 9 commits verified**

Branch: `mighty-camera-image`, branched from `zlite/mighty-camera-gps`
(`a0c3b63e`). When the work is done it is opened as a PR into
`zlite/mighty-camera-gps`, so Chris, the author of that branch, can review and
merge it (D11). Today the Mighty camera only feeds poses to
`path_follow` (`HAVE_MIGHTY`), and its images are ignored. This plan adds a
`MightyCamera` part that publishes `cam/image_array` like `PICAM`, `WEBCAM` and
`CVCAM`. You select it in any template's `myconfig.py` with
`CAMERA_TYPE = "MIGHTY"`.

## How the work proceeds

- **One commit at a time** (D10):
  1. Claude makes one commit's worth of changes in Ed's Mac checkout, runs
     the Mac tests, commits, and stops.
  2. Ed reviews and pushes.
  3. The car pulls with `git pull --ff-only` in `~/projects/donkeycar`. The
     first time, it switches with
     `git fetch origin && git switch mighty-camera-image`.
- **Verification** means the checks listed under the commit pass:
  - `pytest` for the Mighty and template tests in the Mac's `.venv`;
  - the same tests on the car (`~/env`, `~/projects/donkeycar`), after the
    pull;
  - any hardware check the commit names.
- **Ticking.** Once a commit is verified, Claude ticks its box with a note
  saying how it was verified. The tick lands in the next commit. Work then stops until Ed says to start the next
  commit.
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
| D6 | 2026-11-14 | **Never stretch.** Ed: "it should not be stretched. I would check that the image size can be returned by the camera and if it cannot, then fail with a clear error message that includes how to modify myconfig.py to make it work and suggest an image size as close to what was requested as possible." There is no resolution setting to query (F8), so "can be returned" means the shape the camera sends: `IMAGE_W`×`IMAGE_H` must have exactly the same aspect ratio as the frames, and be no larger. Those sizes are scaled down without distortion. Any other size raises `CameraError` (D12). This replaces an earlier entry that allowed stretching. | Ed | Decided |
| D7 | 2026-11-14 | Decode in the part's own thread. The SDK callback only stores the newest frame's bytes, so a JPEG decode never delays pose packets. | Claude | Proposed |
| D8 | 2026-11-14 | Fail fast like `CvCam`: raise `CameraError` if no frame arrives within `MIGHTY_CAMERA_WARMUP_SECS` (default 5.0). After that, return the last frame and log one warning once frames stop arriving for longer than 1 s. | Claude | Proposed |
| D9 | 2026-11-14 | Reuse `MIGHTY_URL`. Add only `MIGHTY_CAMERA_WARMUP_SECS`. | Claude | Proposed |
| D10 | 2026-11-14 | Claude edits code on the Mac and commits each step. Ed reviews and pushes, then the car pulls for testing. Ed first asked to commit himself, then said: "you should create the commits before I push". | Ed | Decided |
| D12 | 2026-11-14 | How a size is checked, and what the error says (implements D6). The camera's size comes from the first frame received during warm-up. With 640×400, the valid sizes are 8k×5k for k = 1…80 (e.g. 80×50, 160×100, 320×200, 640×400). A requested size is invalid if it is non-positive, if its aspect ratio differs (`IMAGE_W * native_h != IMAGE_H * native_w`), or if it is larger than the frames. **Suggested size** (Ed, 2026-11-14: "choose the one with the most pixels that fits one or both requested dimensions… and also suggest full frame"): there are two candidates. One is the largest valid size whose width is ≤ `IMAGE_W`, which equals `IMAGE_W` when it can. The other is the largest valid size whose height is ≤ `IMAGE_H`. Both are capped at the camera's size, and a dimension with no valid size below it gives no candidate; if neither gives one, the smallest valid size is suggested. The suggestion is the candidate with more pixels; on a tie, the width-based one wins. The full frame is always offered as well, unless it is the suggestion itself. The error names the request, the camera's size and shape, and gives both as lines to paste into `myconfig.py`. As implemented in commit 4, the message for the default 160×120 reads: *"MightyCamera cannot return IMAGE_W=160, IMAGE_H=120 without stretching: the camera sends 640x400 (16:10). In myconfig.py set IMAGE_W = 192 and IMAGE_H = 120 (keeps your height), or IMAGE_W = 640 and IMAGE_H = 400 (the full frame). Any 16:10 size up to 640x400 works."* The labels are "keeps your width/height", "the largest that fits your width/height", "the smallest size" and "the full frame". If the camera's size changes mid-run, those frames are dropped, with one logged error, and are never stretched. | Claude | Proposed |
| D13 | 2026-11-14 | `get_camera` hands `CAMERA_TYPE = "MIGHTY"` to a helper, `get_mighty_camera(cfg)`, in `templates/complete.py`. The `path_follow` and `cv_control` templates reach the same helper through `add_camera`. The helper reads `MIGHTY_URL` and `MIGHTY_CAMERA_WARMUP_SECS` with `getattr` defaults (`http://192.168.7.1`, 5.0). A car directory created before these settings existed still works, so commits 6–8 only add the settings and comments to each `cfg_*.py`. | Claude | Proposed |
| D11 | 2026-11-14 | All work goes on `mighty-camera-image`, branched from `zlite/mighty-camera-gps`. It ends with a PR into `zlite/mighty-camera-gps` for Chris to review and merge. `c740dab4` moved onto this branch, and the local `zlite/mighty-camera-gps` was reset to match origin (`a0c3b63e`). | Ed | Decided |

## Findings

| # | Date | Finding | Source |
|---|------|---------|--------|
| F1 | 2026-11-14 | SDK `mighty-protocol 0.1.0` and firmware `Mighty v.2026-10-01-e2aac61`, reached at `http://192.168.7.1` over USB Ethernet. | Probe on murmurpi64 |
| F2 | 2026-11-14 | Images arrive as `kind='jpg'`, `channel='cam0'`, 640×400, about 18.7 KB each, at about 18 fps. The sensor is mono: all three channels decode identical. The lens is a wide fisheye. | Probe on murmurpi64, one frame saved and viewed |
| F3 | 2026-11-14 | Images stream with VIO off (state 0). The camera works without pose tracking. | Probe on murmurpi64 |
| F4 | 2026-11-14 | Two `MightyClient` streams can run at once, but each got about 13 fps instead of 18. | Probe on murmurpi64 |
| F5 | 2026-11-14 | On the Pi, PIL JPEG decoding plus a resize to 160×120 takes about 9 ms per frame. | Probe on murmurpi64, mean of 20 runs |
| F6 | 2026-11-14 | The SDK skips JPEG handling when no image listener is registered, so a pose-only setup costs nothing extra. | `mighty_sdk/client.py` |
| F8 | 2026-11-14 | The SDK has no resolution setting. `config_get` and `config_set` take free-form keys, and none is listed for image size. Only the frames themselves carry `width` and `height` (and, for JPEG, the encoded size). The camera's size must therefore be read from a received frame. | `mighty_sdk/client.py`, `mighty_protocol.py` |
| F9 | 2026-11-14 | `test_scripts.py::test_bad_command_fails` fails on the Mac with or without this branch's changes. It is not related to Mighty, and this plan leaves it alone. | `pytest` on Mac, with changes stashed and restored |
| F10 | 2026-11-14 | Standing still on the bench, VIO went OFF → INITIALIZING → TRACKING (confidence 0.66, 183 features) within about 2 s of `start_vio`. About 1 s later it dropped to DEGRADED (state 3, flag `LOW_TRANSLATION_OBSERVABILITY`) and stayed there for the remaining 35 s, while poses kept arriving. `MightyPose` accepts only state 2, so `mighty/valid` was False from then on. This behaviour predates this plan, which leaves it unchanged. It means a parked car shows `fresh` only briefly; the camera has to move to show sustained tracking. | 40 s `path_follow` run on murmurpi64, `logs/mighty-timing-*.jsonl` |
| F11 | 2026-11-14 | The camera's frame rate depends on VIO. With VIO off it streamed about 18 fps (F2). With VIO left running in DEGRADED after the commit 3 drive, the camera reported `fps_current` 15–16, and a plain SDK client received 14.0 fps. Over three runs `MightyCamera` received 13.4–15.3 fps; one earlier first run gave 11.6. So the part costs no measurable rate. | Snapshot CLI and plain SDK client on murmurpi64 |
| F7 | 2026-11-14 | `templates/path_follow.py` has an unused `from distutils.log import debug`. It stops `test_path_follow_mighty.py` from importing on the Mac's Python 3.12+ venv. The test passes on the car (15 passed) only because setuptools provides a `distutils` shim. | `pytest` on Mac and car |

## Design

- **`MightyCamera`** (D4, D7, D8) is a threaded part with the usual `update`,
  `run_threaded`, `run` and `shutdown`.
  - It accepts `jpg`, the `stereo_*` primary (`cam0`/left) and raw `GRAY8`,
    `RGB24` and `BGR24`. Frame selection copies the SDK's
    `select_primary_image` rules: dropped frames and reference JPEGs are
    skipped. Decoding uses PIL directly instead of the SDK's `image_to_raw`,
    which can only decode JPEG to `gray8`, `rgb24` or `rgba32` and re-imports
    PIL on every call. Doing it here also keeps the part testable with the SDK
    mocked.
  - Each decode takes only the newest frame; older frames are dropped and
    never queued.
  - It checks the configured size against the first frame (D6, D12). An
    invalid size raises `CameraError` with the `myconfig.py` fix. A valid
    size is downscaled with area interpolation; the aspect ratio is never
    changed.
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

- [x] **1. Add this plan.**
  - *Verify:* Ed reviews the plan and settles D5 and D6.
  - *Verified 2026-11-14:* Ed reviewed the plan, decided D5, accepted D6 by
    saying "Proceed", and pushed `c740dab4` to `origin/mighty-camera-image`.
- [x] **2. Remove the stray `distutils` import in `templates/path_follow.py`
  (F7).**
  - *Verify:* `test_mighty*.py` and `test_path_follow_mighty.py` pass on the
    Mac and on the car.
  - *Verified 2026-11-14:* the Mac run passed (29 passed). Ed ruled the change
    trivial and declared it verified without a car run.
- [x] **3. Add the `MightyLink` shared connection, and switch `MightyPose` to
  it (D5).**
  - *Verify:* new tests pass: the first acquire connects, the last release
    disconnects, and the same URL returns the same client.
  - *Verify:* all existing Mighty tests pass on the Mac and on the car.
  - *Verify:* on the car, a short pose-only run of the existing
    `HAVE_MIGHTY` setup still logs `Mighty pose stream: fresh`.
  - *Mac, 2026-11-14:*
    - The Mighty, timing, `path_follow` and look-ahead tests pass: 36 passed,
      7 of them new link tests.
    - `mypy` is clean on `parts/mighty.py`.
    - The full `donkeycar/tests` run gives 154 passed and 1 failed. The
      failure is `test_scripts.py::test_bad_command_fails`, which also fails
      without these changes (F9).
  - *Verified 2026-11-14 on murmurpi64 at `d133510b`:*
    - The same tests passed on the car: 36 passed.
    - Claude ran `manage.py drive` for 40 s in `~/mycar_mighty_path_follow`,
      with Ed's permission, after setting `HAVE_MIGHTY = True` and
      `CAMERA_TYPE = "MOCK"`. The car has no USB webcam for its `CVCAM`
      setting. The original file is backed up as `myconfig.py.bak-2026-11-14`.
    - Through the shared link, the run connected, ran the high-rate command
      and `start_vio` (`started`), and received 2110 poses and both camera
      resets.
    - It logged `Mighty pose stream: fresh` with `valid=True`.
    - Shutdown was clean: no traceback, and no process left running.
    - Tracking then degraded with the camera standing still (F10).
- [x] **4. Add the `MightyCamera` part, unit tests, and a `snapshot` CLI.**
  - The CLI runs as
    `python -m donkeycar.parts.mighty snapshot --url ... --out frame.jpg --seconds 5`.
    It saves one frame and prints the measured fps.
  - The unit tests use a fake client fed with PIL-generated JPEGs. They cover
    depth 1 and 3, output size, newest frame wins, the warm-up timeout raising
    `CameraError`, stereo/raw selection, shutdown releasing the link, and the
    missing-SDK message.
  - Size-check tests (D12):
    - 160×100, 320×200 and 640×400 are accepted with no distortion.
    - 160×120 is rejected; the message suggests 192×120, then the full frame
      640×400.
    - Each candidate rule is exercised:
      - 200×100: the width candidate is 200×125 and the height candidate is
        160×100. It suggests 200×125, which keeps the width.
      - 170×110 is not a multiple, so each candidate rounds down: 168×105
        and 176×110. It suggests 176×110.
      - 1000×120: the width candidate caps at 640×400 and is suggested. The
        full frame is not listed a second time.
      - 4×2 has no valid size below either dimension, so it suggests the
        smallest, 8×5, plus the full frame.
    - Larger than the frames is rejected, as are zero and negative sizes.
    - A mid-run size change drops the frame and logs one error.
  - *Verify:* the tests pass on the Mac and on the car.
  - *Verify:* the CLI on the car saves a viewable frame and reports roughly
    the same fps as a plain SDK client measured at the same time. This
    replaces "about 18 fps": the camera's own rate depends on VIO (F11).
  - *Verify:* on the car, the CLI given `--width 160 --height 120` prints the
    D12 error. Given `--width 160 --height 100`, it saves an undistorted
    frame.
  - *Mac, 2026-11-14:*
    - The new `test_mighty_camera.py` has 25 tests, all passing.
    - All Mighty, timing, `path_follow` and look-ahead tests pass: 61 passed.
    - `mypy --check-untyped-defs` is clean on `parts/mighty.py`.
    - The full suite gives 179 passed, plus the same unrelated F9 failure.
  - *Car pre-check, 2026-11-14 (before commit):* the uncommitted `mighty.py`
    ran from a throwaway copy in `/tmp`, with the car's checkout untouched.
    - With no size given, the CLI saved a 640×400 frame.
    - At 160×100 it saved an undistorted frame (viewed).
    - At 160×120 it printed the D12 message exactly and exited 1.
    - Over three runs it received 13.4–15.3 fps, against 14.0 fps for a
      plain SDK client with VIO running.
  - *Verified 2026-11-14 on murmurpi64 at `47f71e0b`:* Ed pushed, and the
    car pulled.
    - The tests passed on the car: 61 passed.
    - `snapshot --width 160 --height 120` printed the D12 message and exited
      1.
    - At 160×100 it saved a frame and received 14.9 fps.
    - With no size given, it saved a 640×400 RGB frame and received 15.0 fps.
    - A plain SDK client measured 14.8 fps right afterwards, with VIO still
      DEGRADED.
- [x] **5. `complete` template.** Adds a `MIGHTY` branch to `get_camera()` in
  `templates/complete.py`, and updates `cfg_complete.py`.
  - *Verify:* a test that `get_camera` builds a `MightyCamera` from config,
    with the SDK mocked.
  - *Mac, 2026-11-14:* the new `test_mighty_templates.py` has 6 tests for
    `complete`, all passing. They use a car directory created by
    `donkey createcar`, with the SDK mocked, and cover:
    - the config has the new settings;
    - `get_camera` builds a camera with the configured URL, size and depth;
    - a config missing the `MIGHTY_*` settings falls back to defaults;
    - the default 160×120 fails with the fix;
    - `add_camera` publishes a threaded `cam/image_array`;
    - a 10-loop `complete.drive()` connects, then unsubscribes and
      disconnects at shutdown.

    The full suite gives 185 passed, plus the same unrelated F9 failure.
  - *Verified 2026-11-14 on murmurpi64 at `de143d3e`:* the Mighty, template
    and look-ahead tests, including `test_template.py`, passed on the car: 70
    passed.
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
  image format, the allowed sizes and the size error (D12), sharing the connection, and a
  self-contained hardware runbook.
  - *Verify:* Claude runs the runbook as written on murmurpi64.
  - *Verify:* Ed sets `CAMERA_TYPE = "MIGHTY"` in a car directory of his own
    and sees the live image in the web UI at `http://murmurpi64.local:8887`.
  - *Verify:* with `HAVE_MIGHTY = True` also set, the image and
    `Mighty pose stream: fresh` appear together.

## Not in this plan

- Crop, letterbox or undistort options for the fisheye. D6 rejects sizes
  that don't match the camera's shape rather than reshaping the image.
- Publishing depth (`DPT `), stereo pairs or the right camera.
- Changes to the pose transform, gates or look-ahead controller.
- Editing any car directory (`~/mycar*`). Ed makes those config changes.
