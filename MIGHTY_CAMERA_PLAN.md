# MightyCamera as an image camera (`CAMERA_TYPE = "MIGHTY"`)

**Progress: 11 / 12 commits verified**

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
| D13 | 2026-11-14 | `get_camera` hands `CAMERA_TYPE = "MIGHTY"` to a helper, `get_mighty_camera(cfg)`, in `templates/complete.py`. The `path_follow` and `cv_control` templates reach the same helper through `add_camera`. The helper reads `MIGHTY_URL` and `MIGHTY_CAMERA_WARMUP_SECS` with `getattr` defaults (`http://192.168.7.1`, 5.0). A car directory created before these settings existed still works, so commits 8 and 9 only add the settings and comments to each `cfg_*.py`. | Claude | Proposed |
| D14 | 2026-11-14 | **Frame-rate check.** The Mighty sets its own frame rate, and nothing can change it (F12). So `MightyCamera` checks `CAMERA_FRAMERATE` against the rate it actually receives. **Startup:** after the first frame, it counts frames for `MIGHTY_CAMERA_FPS_CHECK_SECS` (default 2.0 s). If `CAMERA_FRAMERATE` is more than 5% above the measured rate, startup fails with a `CameraError`. The message names the measured rate, says that VIO lowers it, and gives the largest whole rate within 5% (floor(measured × 1.05)) as the `myconfig.py` value to use. The rate is measured from the camera's capture timestamps, falling back to frames counted over the window. *Amended after Ed's car run:* the first version rounded the measurement down with no tolerance and timed frames by Pi arrival. It rejected `CAMERA_FRAMERATE = 15` while printing "the camera is sending 15.0 fps" (F14). Below 1 fps it says to check the camera instead. **Lower rates are honoured:** the camera publishes at most `CAMERA_FRAMERATE`, decoding a frame only when at least 0.9 periods have passed. A frame that arrives too early waits rather than being dropped, so camera jitter can't halve the rate. **During a run:** every 5 s it compares the received rate with the same rule. If the rate falls short, which is what happens once `path_follow` starts VIO after the camera's check, it logs one **warning** rather than an error. When the rate recovers, it logs that it has. **No check** when the config has no `CAMERA_FRAMERATE`. Ed accepted the proposal, the extra 2 s of startup, and the warning: "Yes, add it as commit 6; warning is fine". | Ed | Decided |
| D15 | 2026-11-14 | Stop the SDK delivering frames in bursts of three (F15). The fix is to create `MightyWebDevice` in `MightyLink` with a small `read_chunk_size`, rather than patching the SDK. This affects poses as well as images. Ed: "We should add commit 7." The default is 1024 bytes, which gave the steadiest poses at no extra CPU cost (F15, F16). It can be changed with `MIGHTY_READ_CHUNK_BYTES`. | Ed | Decided |
| D16 | 2026-11-15 | **Refuse a depth the camera cannot give.** The Mighty is monochrome. Its SDK README says "Mono camera frames…", and the JPEGs decode with identical channels (F2). So `IMAGE_DEPTH = 3` would be colour-shaped grey, and startup fails with: "set IMAGE_DEPTH = 1". The camera counts as monochrome when the first frame is raw GRAY8, a greyscale JPEG, or has three channels within 2 levels of each other. Raw RGB24/BGR24, or a JPEG whose channels differ, counts as colour, so a future colour camera still works at depth 3. Depth 1 output stays 2-D (H, W), as with `PiCamera`. Ed: "If not we should not start and produce an error that says what the IMAGE_DEPTH setting should be." | Ed | Decided |
| D17 | 2026-11-15 | **One startup error for every configuration problem.** Every template's defaults fail the size, depth and frame-rate checks together (160×120 or 320×240, depth 3, 20 fps). Reporting them one at a time would take three restarts, so `MightyCamera` checks size and depth from the first frame, measures the frame rate anyway, and raises a single `CameraError`. One problem gives the message as before; several are numbered. Ed did not answer this part of the proposal. | Claude | Proposed |
| D18 | 2026-11-15 | **`cv_control` refuses a monochrome camera.** Its default `LineFollower` finds the line by colour (F24) and crashes on 2-D frames (F25). So `cv_control.drive` refuses to start, before connecting, when the controller is that `LineFollower` and the camera is monochrome (`CAMERA_TYPE = "MIGHTY"`) or `IMAGE_DEPTH = 1`. A custom `CV_CONTROLLER_*` is allowed through. A brightness-based line follower is left for later. Ed: "cv_control cannot work with monochrome, so it should just not start if it is monochrome (or we have to change the algorithm, but that would be for later)." | Ed | Decided |
| D19 | 2026-11-15 | **The `basic` template does not support the Mighty camera.** Ed: "The basic template does not need to support the mighty camera. Let's get rid of commit 12 and record that decision." Commit 12 (`d928c7ca`: a `MIGHTY` branch in `basic.py` calling `get_mighty_camera`, a Mighty block in `cfg_basic.py`, and 3 template tests) was written and tested on the Mac but never pushed. It was dropped from the branch with `git reset --hard`, so `basic.py` and `cfg_basic.py` are unchanged from `zlite/mighty-camera-gps`. With `CAMERA_TYPE = "MIGHTY"`, `basic` raises its usual "Unkown camera type". The docs commit is renumbered from 13 to 12. | Ed | Decided |
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
| F7 | 2026-11-14 | `templates/path_follow.py` has an unused `from distutils.log import debug`. It stops `test_path_follow_mighty.py` from importing on the Mac's Python 3.12+ venv. The test passes on the car (15 passed) only because setuptools provides a `distutils` shim. | `pytest` on Mac and car |
| F8 | 2026-11-14 | The SDK has no resolution setting. `config_get` and `config_set` take free-form keys, and none is listed for image size. Only the frames themselves carry `width` and `height` (and, for JPEG, the encoded size). The camera's size must therefore be read from a received frame. | `mighty_sdk/client.py`, `mighty_protocol.py` |
| F9 | 2026-11-14 | `test_scripts.py::test_bad_command_fails` fails on the Mac with or without this branch's changes. It is not related to Mighty, and this plan leaves it alone. | `pytest` on Mac, with changes stashed and restored |
| F10 | 2026-11-14 | Standing still on the bench, VIO went OFF → INITIALIZING → TRACKING (confidence 0.66, 183 features) within about 2 s of `start_vio`. About 1 s later it dropped to DEGRADED (state 3, flag `LOW_TRANSLATION_OBSERVABILITY`) and stayed there for the remaining 35 s, while poses kept arriving. `MightyPose` accepts only state 2, so `mighty/valid` was False from then on. This behaviour predates this plan, which leaves it unchanged. It means a parked car shows `fresh` only briefly; the camera has to move to show sustained tracking. | 40 s `path_follow` run on murmurpi64, `logs/mighty-timing-*.jsonl` |
| F11 | 2026-11-14 | The camera's frame rate depends on VIO. With VIO off it streamed about 18 fps (F2). With VIO left running in DEGRADED after the commit 3 drive, the camera reported `fps_current` 15–16, and a plain SDK client received 14.0 fps. Over three runs `MightyCamera` received 13.4–15.3 fps; one earlier first run gave 11.6. So the part costs no measurable rate. | Snapshot CLI and plain SDK client on murmurpi64 |
| F12 | 2026-11-14 | The camera's frame rate cannot be set or read through config. All 18 likely key names tried with `config_get` (`fps`, `camera_fps`, `preview_fps`, `stream_fps`, `framerate`, `frame_rate`, …) returned "unknown config key". The SDK and its README document no rate control; `calib` and `apriltags` are the only keys they name. The only rate the camera reports is `fps_current` in VIO status. | Read-only `config_get` probe on murmurpi64; `mighty_sdk` source and README |
| F13 | 2026-11-14 | With VIO running, the received rate varies from one 5 s window to the next: 13.4, 14.0, 14.4, 14.5, 14.8, 14.9, 15.0, 15.1 and 15.3 fps were all seen. A `CAMERA_FRAMERATE` equal to the startup suggestion (e.g. 14) can therefore draw the runtime warning once, when a window happens to dip below it. | Snapshot CLI runs on murmurpi64 |
| F14 | 2026-11-14 | **Bug in the first commit 6:** `CAMERA_FRAMERATE = 15` was rejected while the message said "the camera is sending 15.0 fps". The measurement was just under 15, for example 14.98. It printed as 15.0 but rounded down to 14, and the rule allowed no tolerance. | Ed's `complete` run on murmurpi64 |
| F15 | 2026-11-14 | **The SDK hands frames to the Pi in bursts of three.** About every 200 ms, three frames arrive back to back with 0 ms between them, while their capture timestamps are 50–99 ms apart. Pi arrival rates therefore say little about the camera's rate. Worse, `MightyCamera` keeps only the newest frame, so it publishes only about **5 distinct images per second**. The cause is the SDK's `MightyWebDevice`, which reads the stream in 64 KiB blocks (a frame is about 19 KB). This is the transport problem `docs/mighty.md` notes as a hand patch (`read1`). With `read_chunk_size` at 16384, 4096 or 1024, no frames arrived back to back, and the longest gap between poses fell from 238 ms (64 KiB) to 117, 94 and 81 ms. | `read_chunk_size` comparison on murmurpi64 |
| F16 | 2026-11-14 | The SDK client uses most of a Pi core whatever it receives: 88% with only a pose listener, and 94–99% with images, at any chunk size. The time goes in its single `MightyClientLoop` thread, so this is SDK overhead, not this branch's code. Not pursued in this plan. | `time.process_time` around a 4–5 s SDK client run on murmurpi64 |
| F17 | 2026-11-14 | End to end, the bursts of F15 cut `MightyCamera` to about a third of the camera's rate, and 1 KB reads restore it. With `snapshot --framerate 15` over 5 s: at 64 KiB it received 14.5 and 12.4 fps but published only 5.2 and 4.6 distinct images per second; at 1 KB it received 14.7 and 13.2 fps and published 14.9 and 13.4. (Published can slightly exceed received because the two counts start at slightly different moments.) | Commit 7 pre-check on murmurpi64 |
| F18 | 2026-11-14 | Pi arrival times overstate the camera's rate because of the bursts. A draft fix timed first-to-last arrival and measured 15.4–16.8 fps, while 13.9–15.2 fps actually arrived. Over one 6 s window, the same frames gave 15.09 fps from camera timestamps, 15.51 from Pi first-to-last arrival, and 14.67 from a count. This is why D14 measures from camera timestamps. | Draft pre-check and burst probe on murmurpi64 |
| F19 | 2026-11-14 | The camera captures on a 20 Hz grid and skips frames when busy. With VIO running, the gaps between capture timestamps were exactly 50 or 99 ms, giving about 15 fps delivered. With VIO off it reported `fps_current` 20 and delivered about 18 (F2). | Capture timestamps in the burst probe on murmurpi64 |
| F20 | 2026-11-14 | Ed's car pull for commit 6's fix ran before the push reached origin, so the car stayed one commit behind (`c8d31c73` instead of `bfdbff16`). The first verification run there reproduced the old bug: `CAMERA_FRAMERATE = 15` was rejected at 13.5 and 14.0 fps. Before verifying, run `git fetch` and `git status -sb` on the car and check it isn't behind. | Commit 6 verification on murmurpi64 |
| F21 | 2026-11-14 | `MightyLink`'s registry is shared across the whole class, so one test failing before it released its link leaked a link for `http://192.168.7.1`. Every later test then reused it, and about 40 tests failed (camera warm-up timeouts, registry assertions). Test classes now register `MightyLink._links.clear` as a cleanup that runs after the empty-registry assertion. | Commit 7 Mac test run |
| F22 | 2026-11-14 | Giving any parameter of `MightyPose.__init__` a type annotation makes `mypy` check the body. Its attributes initialised to `None` (`latest`, `received_at`, `state`, `last_valid`) then failed on later assignments, so commit 7 gave them `Optional` types. | `mypy --check-untyped-defs` on the Mac |
| F23 | 2026-11-14 | The camera's own rate drifts down over a session. In the evening, with VIO still DEGRADED from the commit 3 drive hours earlier (flag 2, about 146 features), the camera reported `fps_current` 14 (it had reported 15–16 earlier) and delivered 13.2–13.8 fps. Ed's `path_follow` start refused `CAMERA_FRAMERATE = 15` at 12.8–13.8 fps, and 12 started. The drop is on the camera side, not the Pi's, since `fps_current` is the camera's own figure. The cause is unknown; heat, or the long-running VIO session, are guesses. A `CAMERA_FRAMERATE` near the edge can therefore pass on one start and fail on a later one; leaving a few fps of margin avoids that. | VIO status and snapshot runs on murmurpi64; Ed's `path_follow` run |
| F24 | 2026-11-14 | `cv_control`'s default autopilot, `LineFollower`, finds the line by colour. Its pixels must fall in HSV `COLOR_THRESHOLD_LOW` (0, 50, 50) to `COLOR_THRESHOLD_HIGH` (50, 255, 255), so saturation must be at least 50. The Mighty's frames are grey (F2), so their saturation is 0 and the mask is always empty: the default line follower cannot follow tape with `CAMERA_TYPE = "MIGHTY"`. Following tape would need a controller or thresholds based on brightness. This plan only documents it, and leaves the line follower unchanged. | `cfg_cv_control.py`; test `test_mono_frames_never_match_the_default_line_colour`; a real 320×200 frame on murmurpi64: saturation at most 0, 0 mask pixels |
| F25 | 2026-11-15 | `LineFollower.run` crashes on a 2-D (H, W) image with `IndexError: too many indices for array`. Depth 1 output is 2-D, so `cv_control` with any depth 1 camera crashes once autopilot is engaged. | `LineFollower` on a 2-D frame, on murmurpi64 |
| F26 | 2026-11-15 | The Keras autopilot could not be tested at depth 1: building `KerasLinear` fails with `NameError: name 'Input' is not defined` on both the Mac `.venv` and the car's `~/env`, so neither has a working Keras. From the code, a 2-D frame becomes (1, H, W) at inference while a depth 1 model expects (1, H, W, 1). That is a question for donkeycar's depth 1 path generally, not specific to the Mighty, and is not in this plan. | `KerasLinear(input_shape=(100, 160, 1))` on Mac and car |

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
- [x] **6. Frame-rate check (D14).** `MightyCamera` gains `framerate`
  (`CAMERA_FRAMERATE`) and `fps_check_secs` (`MIGHTY_CAMERA_FPS_CHECK_SECS`).
  `get_mighty_camera` passes them, `cfg_complete.py` documents them, and the
  `snapshot` CLI gains `--framerate`.
  - *Verify:* unit tests:
    - the error rule and its message;
    - startup failing with the suggested rate and releasing the link;
    - measuring the rate;
    - publishing at most `CAMERA_FRAMERATE` without dropping frames when the
      camera matches it;
    - the runtime warning appearing once and clearing once the rate recovers;
    - invalid arguments;
    - no check when `CAMERA_FRAMERATE` is absent.
  - *Verify:* template tests, for `complete`: the default
    `CAMERA_FRAMERATE = 20` fails, a supported rate passes, and the rate is
    passed through.
  - *Verify:* the tests pass on the Mac and on the car.
  - *Verify:* on the car, `snapshot --width 160 --height 100 --framerate 20`
    prints the D14 error with the camera's current rate.
    `--framerate` set at or below the suggestion saves a frame.
  - *Mac, 2026-11-14:*
    - `test_mighty_camera.py` gains 13 tests for the rule, startup, pacing,
      the warning and the CLI.
    - `test_mighty_templates.py` gains 2 and updates the rest: those tests
      now fix the measured rate at 17.8 fps and use `CAMERA_FRAMERATE = 15`.
    - All Mighty tests pass: 81 passed.
    - `mypy --check-untyped-defs` is clean.
    - The full suite gives 199 passed, plus the unrelated F9 failure.
  - *Car pre-check, 2026-11-14 (before commit, throwaway copy in `/tmp`):*
    - `--framerate 20` printed *"MightyCamera cannot deliver CAMERA_FRAMERATE
      = 20: the camera is sending 14.5 fps. … In myconfig.py set
      CAMERA_FRAMERATE = 14, or anything lower."* and exited 1.
    - `--framerate 13` saved a frame, receiving 14.4 fps.
  - *Ed on the car, 2026-11-14, at `c8d31c73`:* the `complete` template
    rejected `CAMERA_FRAMERATE = 15` with "the camera is sending 15.0 fps …
    set CAMERA_FRAMERATE = 14" (F14).
  - *Fix commit (still part of commit 6):* adds the 5% tolerance and
    measures from camera timestamps.
    - The Mac tests pass, including a sweep checking that the suggestion
      always passes its own check, a bursty-arrival case and the
      no-timestamp fallback. The full suite gives 203 passed, plus the F9
      failure.
    - Car pre-check from a `/tmp` copy: `--framerate 20` suggests 15, and
      five runs at `--framerate 15` all started, measuring 14.3–15.1 fps.
  - *Verified 2026-11-14 on murmurpi64 at `bfdbff16`:* Ed's pull had run
    before the push landed, so Claude ran `git pull --ff-only` on the car.
    - The Mighty, template and look-ahead tests passed: 88 passed.
    - `snapshot --framerate 20` printed the error, suggesting 16 at 15.9 fps.
    - Five runs at `--framerate 15` all started and saved a frame, measuring
      15.1–15.9 fps.
- [x] **7. Read the SDK stream in small chunks (D15, F15).** `MightyLink`
  creates `MightyWebDevice` with `read_chunk_size` (default 1024 bytes;
  `MIGHTY_READ_CHUNK_BYTES`). `MightyPose`, `MightyCamera`,
  `get_mighty_camera` and `path_follow`'s `add_mighty` pass it through, and
  `cfg_complete.py` documents it. The link keeps the chunk size of its first
  user and warns if a later one asks for a different size. The `snapshot`
  CLI gains `--chunk` and reports *published* (distinct) images per second
  as well as frames received.
  - *Verify:* unit tests for the chunk size reaching `MightyWebDevice`, the
    mismatch warning, the pass-through in both parts and both templates,
    invalid values, and the published count.
  - *Verify:* the tests pass on the Mac and on the car.
  - *Verify:* on the car, `snapshot --chunk 65536` publishes about 5 images
    per second, and the default publishes roughly the camera's rate.
  - *Mac, 2026-11-14:*
    - 10 new tests, covering the link, the camera, the CLI, the `complete`
      template and the `path_follow` template.
    - The test classes now clear the link registry in cleanup. Before this,
      one failing test leaked its link and failed about 40 later tests.
    - `MightyPose`'s attributes gained types, because its typed parameter
      made `mypy` check its body.
    - `mypy --check-untyped-defs` is clean. The full suite gives 212 passed,
      plus the F9 failure.
  - *Car pre-check, 2026-11-14 (before commit, `/tmp` copy, `--framerate 15`,
    5 s runs):*

    | Chunk | Received | Distinct images published |
    |---|---|---|
    | 65536 | 14.5 fps | 5.2 /s |
    | 1024 | 14.7 fps | 14.9 /s |
    | 65536 | 12.4 fps | 4.6 /s |
    | 1024 | 13.2 fps | 13.4 /s |

  - *Verified 2026-11-14 on murmurpi64 at `ae90ab30`:*
    - The car was checked as up to date with origin first (F20).
    - The Mighty, template and look-ahead tests passed: 97 passed.
    - `snapshot --framerate 12` published 5.0 distinct images per second at
      `--chunk 65536` and 12.5 at the 1024 default, with 13.5 fps received
      in both runs.
    - Ed ran `mycar_mighty_path_follow` (640×400, `HAVE_MIGHTY = True`) on
      this code. It started at `CAMERA_FRAMERATE = 12` after 15 was refused
      at 12.8–13.8 fps (F23).
- [x] **8. `path_follow` template.** Updates `cfg_path_follow.py`:
  - `MIGHTY` joins the camera types list;
  - `MIGHTY_READ_CHUNK_BYTES` joins the pose settings, since `add_mighty`
    already reads it from commit 7;
  - a camera block explains the 16:10 size rule, the frame-rate check (the
    template's `CAMERA_FRAMERATE = DRIVE_LOOP_HZ` is 20, more than the camera
    delivers) and sharing with poses, and adds `MIGHTY_CAMERA_WARMUP_SECS`
    and `MIGHTY_CAMERA_FPS_CHECK_SECS`.

  `MIGHTY_URL` is already there.
  - *Verify:* `test_path_follow_mighty.py` gains a case with `HAVE_MIGHTY` and
    `CAMERA_TYPE="MIGHTY"` set, checking that both parts share one client.
  - *Verify:* on the car, a `manage.py drive` run of
    `~/mycar_mighty_path_follow` holds exactly one TCP connection to the
    camera, checked with `ss`.
  - *Mac, 2026-11-14:* `test_path_follow_mighty.py`'s `build()` can now run
    `add_camera` for real against fake SDK clients. 4 new tests:
    - the config documents the camera settings;
    - `HAVE_MIGHTY` plus `CAMERA_TYPE="MIGHTY"` builds one client and one
      `MightyWebDevice` (1024-byte reads) shared by `MightyPose` and
      `MightyCamera`, which publishes a threaded 160×100 `cam/image_array`;
      shutting the camera down keeps the connection, and shutting the pose
      reader down closes it;
    - the camera alone, with no pose reader;
    - the default `CAMERA_FRAMERATE = 20` fails with the rate to use.

    All 11 `path_follow` tests pass. The full suite gives 216 passed, plus
    the F9 failure.
  - *Verified 2026-11-14 on murmurpi64 at `bb0ef25a`:*
    - The car was up to date with origin.
    - The Mighty, template and look-ahead tests passed: 101 passed.
    - Claude ran a 40 s `manage.py drive` in `~/mycar_mighty_path_follow`
      (Ed's settings: `CAMERA_TYPE = "MIGHTY"`, 640×400,
      `CAMERA_FRAMERATE = 12`, `HAVE_MIGHTY = True`). It added
      `MightyPose`, `MightyPoseTransform` and `MightyCamera`.
    - It logged "MightyCamera ready: 640x400 depth 3 … camera at 15.8 fps,
      publishing up to 12 fps", and `start_vio` returned `started`.
    - `ss -tnp` counted exactly 1 TCP connection to `192.168.7.1:80` at
      every 5 s sample from 5 s to 35 s.
    - The run had no tracebacks or camera warnings, and it exited cleanly.
    - The pose stream stayed "waiting for tracking", as expected with the
      camera standing still (F10).
- [x] **9. `cv_control` template.** Updates `cfg_cv_control.py` (the template
  already goes through `add_camera`):
  - `MIGHTY` joins the camera types list;
  - a Mighty block adds `MIGHTY_URL`, the warm-up, frame-rate-check and
    read-chunk settings, and warns that the default `LineFollower` cannot
    see the line in the Mighty's grey frames (F24);
  - it notes that the template's 320×240 must become a 16:10 size such as
    320×200, and that `SCAN_Y` and `TARGET_PIXEL` are in pixels of that
    image.
  - *Verify:* a template test with `CAMERA_TYPE="MIGHTY"`.
  - *Mac, 2026-11-14:* 4 new tests in `test_mighty_templates.py`:
    - the settings are in a `cv_control` car's config;
    - the template's default 320×240 fails, suggesting 384×240 and the full
      frame;
    - a 10-loop `cv_control.drive()` at 320×200 builds the camera on
      `cam/image_array`, connects, and disconnects at shutdown;
    - the camera's grey frames give HSV saturation 0, and the default yellow
      `COLOR_THRESHOLD_*` mask stays empty.

    Each template test now gets its own temporary car directory: a tub left
    by the `complete` tests made `cv_control`'s tub writer fail on its
    different fields. The full suite gives 220 passed, plus the F9 failure.
  - *Verified 2026-11-14 on murmurpi64 at `8739d136`:*
    - The car was up to date with origin.
    - The Mighty, template and look-ahead tests passed: 105 passed.
    - A real 320×200 `snapshot` frame had HSV saturation at most 0 and 0
      pixels in the default yellow mask, which confirms F24 on hardware.
    - `cv_control` itself was not run on the car. `~/mycar` uses that
      template for Ed's MCP server, and the line follower couldn't see tape
      anyway (F24).
- [x] **10. `IMAGE_DEPTH` check and one combined startup error (D16, D17).**
  - `MightyCamera` decides from the first frame whether the camera is
    monochrome, and refuses `IMAGE_DEPTH = 3` if so.
  - Size, depth and frame-rate problems are reported together in one
    `CameraError`.
  - Its `image_d` default and the `snapshot` CLI's `--depth` default become
    1.
  - The comments in `cfg_complete.py`, `cfg_path_follow.py` and
    `cfg_cv_control.py` say `IMAGE_DEPTH` must be 1.
  - *Verify:* unit tests:
    - the monochrome test (GRAY8, grey JPEG, grey RGB, a real colour frame);
    - the depth error and its wording;
    - a colour raw frame still giving RGB at depth 3;
    - one problem reported alone, and several numbered in one error;
    - the frame rate measured even when size or depth are wrong;
    - the CLI default.
  - *Verify:* template tests use `IMAGE_DEPTH = 1`, and the template defaults
    (wrong size, depth 3, 20 fps) give one error naming all three fixes.
  - *Verify:* the tests pass on the Mac and on the car.
  - *Verify:* on the car, `snapshot --depth 3` prints the depth error, and
    `--width 160 --height 120 --depth 3 --framerate 20` prints all three
    fixes in one error.
  - *Mac, 2026-11-15:*
    - New tests cover:
      - monochrome detection (grey, grey RGB, a grey JPEG, JPEG rounding,
        colour);
      - the depth rule;
      - single and numbered errors;
      - depth 3 refused for a grey camera and kept for a colour raw frame;
      - the template defaults giving one error with all three fixes, at the
        camera level and through `complete.get_camera`;
      - `snapshot --depth 3`.
    - Existing tests moved to `IMAGE_DEPTH = 1` and 2-D shapes.
    - The full suite gives 229 passed, plus the F9 failure; `mypy` is clean.
  - *Car pre-check, 2026-11-15 (before commit, `/tmp` copy):*
    - `--depth 3` printed the depth error.
    - `--width 160 --height 120 --depth 3 --framerate 20` printed "cannot
      start: 3 settings in myconfig.py need changing", then the size fix
      (192×120 or 640×400), the depth fix (1), and the rate fix (15, at
      14.8 fps).
    - At depth 1, 160×100 and 12 fps it started, logging "monochrome
      frames", and saved a 160×100 mode `L` image.
  - *Verified 2026-11-15 on murmurpi64 at `e66ed6b9`:*
    - The car was up to date with origin.
    - The Mighty, template and look-ahead tests passed: 114 passed.
    - `snapshot --depth 3` printed the depth error.
    - `--width 160 --height 120 --depth 3 --framerate 20` printed "cannot
      start: 3 settings…" with the size, depth and rate fixes (rate 13.6 fps
      that time).
  - *Car directories:* `~/mycar_mighty_path_follow` and
    `~/mycar_mighty_complete` don't set `IMAGE_DEPTH`, so they get the
    template's 3 and will refuse to start after this commit until Ed adds
    `IMAGE_DEPTH = 1`. On 2026-11-15 they still lacked it. Ed created
    `~/mycar_mighty_cv_control` (`MIGHTY`, 640×400, `IMAGE_DEPTH = 1`,
    `CAMERA_FRAMERATE = 12`); commit 11 will make `cv_control` refuse it.
- [x] **11. `cv_control` refuses a monochrome camera (D18).** `cv_control.drive`
  checks before building any part. With the default colour `LineFollower`,
  `CAMERA_TYPE = "MIGHTY"` or `IMAGE_DEPTH = 1` fails with an error saying
  why, and what to use instead.
  - *Verify:* template tests:
    - `MIGHTY` is refused without connecting to the camera;
    - `IMAGE_DEPTH = 1` is refused;
    - a custom `CV_CONTROLLER_*` is allowed through.
  - *Verify:* the tests pass on the Mac and on the car.
  - *Verify:* on the car, running the committed template from Ed's car
    directory (`cd ~/mycar_mighty_cv_control && python
    ~/projects/donkeycar/donkeycar/templates/cv_control.py drive`) prints
    the refusal and opens no connection to the camera.
  - *Note:* `donkey createcar` copies the template into each car directory
    as `manage.py`. An existing `cv_control` car directory picks up the
    check only after `donkey update --template cv_control`, run inside it.
    That overwrites `manage.py`, `config.py`, `train.py` and `calibrate.py`
    but keeps `myconfig.py`.
  - *Mac, 2026-11-15:*
    - The check is `colour_camera_error(cfg)` in `templates/cv_control.py`,
      called first in `drive()`. `line_follower.py` is unchanged.
    - The `cv_control` drive test was replaced by 4 tests:
      - `MIGHTY` refused with the exact message, with no `Vehicle` and no
        SDK client created;
      - `IMAGE_DEPTH = 1` refused with a `MOCK` camera;
      - a colour camera allowed;
      - a custom greyscale `GreyController` running a 10-loop drive with
        the Mighty camera.
    - `cfg_cv_control.py`'s comment now says it refuses to start.
    - All 17 template tests pass. The full suite gives 232 passed, plus the
      F9 failure.
  - *Verified 2026-11-15 on murmurpi64 at `0a4a59f5`:*
    - The car was up to date with origin.
    - The Mighty, template and look-ahead tests passed: 117 passed.
    - The committed template, run from inside `~/mycar_mighty_cv_control`
      (`MIGHTY`, 640×400, `IMAGE_DEPTH = 1`), raised the `ValueError` with
      the full message and exited 1.
    - `ss` counted 0 connections to `192.168.7.1:80` at each 1 s sample over
      6 s.
    - The car directory's `myconfig.py`, `manage.py` and `config.py` kept
      their checksums: nothing there changed. Its `manage.py` is still the
      old copy until Ed runs `donkey update --template cv_control`.
    - Ed then ran `donkey update --template cv_control` in that directory.
      Its `manage.py` now matches the template byte for byte, and
      `python manage.py drive` refuses with the same error and no camera
      connection. `myconfig.py` kept `MIGHTY` and `IMAGE_DEPTH = 1`.
- [ ] **12. Docs.** Adds a camera section to `docs/mighty.md` covering config,
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
- A line follower that works on brightness, for monochrome cameras (D18).
- Keras autopilots at `IMAGE_DEPTH = 1` (F26).
- The `basic` template (D19).
- Editing any car directory (`~/mycar*`). Ed makes those config changes.
