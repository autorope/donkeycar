# Driving a donkeycar with an AI agent

An MCP server that lets an LLM agent read the car's state and set its intent while
the computer-vision autopilot follows a taped line. The autopilot steers at 20 Hz;
the agent decides how fast to go and which lane to hold.

The agent is never in the steering path. That is deliberate: an agent round trip
takes a second or more, and at that cadence a car following a line would be a
segment behind the road.

---

## 1. Build a track

The track is **1 inch yellow tape**, laid as a centreline in segments. Each segment
is a "T":

- a **3 foot stem** along the direction of travel, and
- a **1 foot cross** of red or blue tape at the end of the stem.

```
        ══════════            <- 1 ft cross tape (red or blue)
             │
             │                <- 3 ft stem, 1 in yellow tape
             │
        ══════════
```

Rules of thumb:

- Join segments end to end. Avoid crossings, and keep turns gentle — the follower
  loses the line on tight ones.
- There are no track edges to lay. The centreline is the whole track, which is what
  makes one quick to build.
- Start with a straight line that dead-ends, then close it into a loop.

### Traffic features

Print [`assets/track-cards/track-cards.pdf`](../assets/track-cards/track-cards.pdf) —
7 sheets giving 13 fold-over tents, each showing the same image on both faces so the
car reads it the same whichever way it approaches:

- **Signs** — stop sign, and a traffic light in red, yellow and green
- **Obstacles to wait out** — child chasing a ball, adult with a stroller, elderly
  man with a cane, dog
- **Obstacles to drive around** — car, truck
- **Addresses** — houses numbered 123, 456 and 789

Print at 100%, on matte stock — **not glossy**. These exist to be read by a camera,
and under overhead lights a glossy stop sign throws a specular highlight that blows
out exactly the region a vision model needs. Assembly, paper weights and printer
settings are in [`assets/track-cards/README.md`](../assets/track-cards/README.md).

Put a feature at the cross-tape end of a segment to begin with, so the follower has an
obvious place to stop.

**Features are not configured anywhere.** The agent finds them in the camera image.
That is the point of the exercise, and it means you can move a sign or drop an
obstacle in the road without editing a file.

## 2. Describe the track

`donkey createcar` puts a `track.yml` in the car directory. Edit it to match what
you built:

```yaml
segment_length_inches: 36.0
cross_length_inches: 12.0
segment_count: 4
continuous: false          # true once you close the loop

lanes:                     # offsets from the centreline, inches
  left: -12.0
  center: 0.0
  right: 12.0
```

Validation is strict and unknown fields are rejected, so a typo fails loudly rather
than reading as "never set". A silently wrong lane width is a car in the wall.

## 3. Calibrate the camera

A lane offset given in inches has to become a pixel offset, so the car needs to know
how many pixels an inch is worth on the ground.

Print the board first: [`assets/checkerboard/calibration-checkerboard-9x6-1in-letter.pdf`](../assets/checkerboard/calibration-checkerboard-9x6-1in-letter.pdf)
(or the A4 version). **Print at 100% / actual size** — "Fit to Page" silently shrinks
it, and a board printed at 96% gives a confident, wrong calibration rather than an
error. Check with a ruler that 10 squares measure 10 inches, then mount it on
something rigid: a curled sheet is a curved plane, and the maths assumes a flat one.

```
donkey calibrate-cv --car ~/mycar
```

Then open `http://localhost:8892`:

1. Lay the board **flat on the floor** in front of the car. Held upright it gives
   meaningless numbers.
2. Slide it until the blue band crosses the board and the corners turn green. The
   blue band is the strip the follower actually samples.
3. Press **Capture**. It writes `cv_calibration.json` beside your config.

The same corners also solve a ground homography, which is what lets the agent ask
"how far ahead is that?". Without it the only cue is apparent size, guessed over a
network round trip while the car keeps moving.

To get answers in car coordinates rather than the board's own frame, say where the
board was:

```
donkey calibrate-cv --car ~/mycar --forward-inches 24 --lateral-inches 0
```

**No printer?** Lay two strips of the follow-tape a known distance apart:

```
donkey calibrate-cv --car ~/mycar --tape-separation-inches 10
```

That gives the scale but no homography, so lane changes work and distance
measurement does not.

**Recalibrate whenever the camera moves.** The calibration records the `SCAN_Y`,
image size and camera type it was taken with, and `get_calibration` reports when
those no longer match — but it cannot tell that someone knocked the camera.

## 4. Run the server

First install the `mcp` extra. It is optional, so no platform extra pulls it in
and a normal car install will not have it:

```zsh
uv pip install -e ".[pi,dev,mcp]"     # on the car, from a clone
uv pip install "donkeycar[pi,mcp]"    # on the car, from PyPI
```

Swap `pi` for `pc` or `macos` off the car. Without it both commands below stop
and tell you to install it.

Two ways to run, depending on who should own the process.

**Alongside a normally launched car.** The car runs as usual and serves MCP from
inside the drive loop:

```
python manage.py drive --mcp
```

`start` and `stop` arm and disarm the car here; they cannot restart the loop,
because returning from the drive loop ends the program.

**Server owns the vehicle.** Real lifecycle control — `stop` tears the loop down and
`start` builds a new one:

```
donkey mcp --car ~/mycar
```

Either way the tools are at `http://<host>:8891/mcp`. Nothing is running until the
agent calls `start`, and the car does not move until it also sets a throttle.

## 5. The tools

| Tool | What it does |
| --- | --- |
| `get_track_config` | Segment geometry, how many, loop or dead-end, and the named lanes. Call once. |
| `get_vehicle_state` | Camera frame plus throttle, steering, lane, mode. `live` says whether the vehicle loop is still writing; when it is false the car-derived fields are null and there is no frame, so a stopped car cannot look like a running one. `loop_count` rises every loop. |
| `set_control` | Set throttle and/or lane. Give `lane` by name, or `lane_offset_inches` for finer control. |
| `measure_ground_point` | Turn a pixel into a position on the ground, in inches. This is how you know when to brake. |
| `start` / `stop` | Begin and end driving. |
| `emergency_stop` | Zero the throttle now, without touching the lifecycle. |
| `get_calibration` | Scale, homography, and whether either has gone stale. |

### Throttle is a ceiling, not a command

`set_control(throttle=0.8)` does **not** drive at 0.8. The autopilot computes its own
throttle and slows itself in corners; your value caps it. So:

- A high value does not make the car corner faster.
- A low value does slow it down.
- `0` always stops it.

This keeps the autopilot's cornering behaviour intact while leaving you able to slow
and stop. There is no way to override it from the tool surface, on purpose.

### Commands expire

If no command arrives for `MCP_COMMAND_TIMEOUT_S` (2 seconds by default) the throttle
goes to zero. Agent silence — a crash, a dropped connection, a long think — stops the
car rather than letting it continue blind. **Keep calling `set_control` while you want
the car to move.**

## 6. The activities

A progression, each building on the last. Reference implementations are in
`donkeycar/mcp_agent/policies.py`.

1. **`lap`** — drive once around the track and stop.
2. **`stop-signs`** — also stop 5 seconds at every stop sign.
3. **`obstacle-halt`** — also wait at obstacles until they are removed.
4. **`obstacle-avoid`** — drive around the obstacles that can be passed. Which ones
   those are is your judgement from the image, not something the track file declares.
5. **`address`** — stop at a numbered address and wait to be told to continue.

The policies handle throttle, lanes and braking distance. What they do **not** do is
see: `Perception.observe(frame, state) -> list[Sighting]` is the seam where your
vision model goes.

```python
from donkeycar.mcp_agent import McpSession, build_policy

class MyEyes:
    def observe(self, frame, state):
        # ask your model what is in `frame`
        return [...]

policy = build_policy("stop-signs", McpSession(client), MyEyes())
policy.begin()
while not policy.finished:
    policy.step()
policy.end()
```

To watch the loop work without a vision model, replay scripted sightings:

```
python -m donkeycar.mcp_agent.runner --activity lap --demo-script sightings.json
```

## 7. Security

The server can make a vehicle move, so treat the port as a control surface.

- **Bind narrowly.** The default is `127.0.0.1`. Set `MCP_SERVER_HOST` to the car's
  LAN address to reach it from a laptop — never `0.0.0.0`.
- **Keep DNS-rebinding protection on.** It is on by default. Set the allowed hosts
  and origins explicitly rather than turning it off to make a client connect.
- **Add a token** if the network is shared. The server accepts a token verifier, and
  that token is the only thing between a guest on the WiFi and the throttle.

## 8. Testing without a car

Everything above is exercisable on a laptop.

```
CAMERA_TYPE = 'MOCK'         # or 'IMAGE_LIST' with recorded track footage
DRIVE_TRAIN_TYPE = 'None'
```

`IMAGE_LIST` plus a recorded tub gives deterministic replays against real footage.
The test suite drives all five activities against a real vehicle loop this way, with
scripted perception standing in for the vision model.
