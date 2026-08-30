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

A lane offset says where **the car** should sit: positive is right of the centreline,
the way a person would describe it. The controller works in the opposite frame &mdash;
it steers the *tape* to a column in the image, and putting the car right of the line is
the same as putting the line left of centre &mdash; but converting between the two is
the server's job, not yours. Fill this file in as a person sees the track.

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

### Where to put the board

Two things decide whether the numbers are worth having.

**Big enough to find.** At donkeycar's stock 320&times;240 a 10&times;7 inch board lying
where the scan line falls is about 8 pixels per square, which is below what the corner
detector resolves &mdash; it reports no board at all on a frame where the board is
plainly visible, flat, sharp and well lit. The detector retries on an upscaled copy for
exactly this case and usually succeeds anyway. If the preview still says NO BOARD, the
answer is almost always to move the board closer, not to change the lighting.

**As close to the scan row as you can manage.** `pixels_per_inch` is evaluated at
`SCAN_Y`, and a homography fitted from corners that all sit well below that row is
extrapolating to reach it. On one car the board covered image rows 128&ndash;142 while
`SCAN_Y` was 100, roughly 37 inches further out; perturbing the corners by a third of a
pixel moved the answer by 5% at the scan row, against 0.4% at rows the board actually
covered. Straddle the scan line if the board can still be found there. If it cannot, 5%
is usually tolerable &mdash; a 6 inch lane offset still lands within a pixel &mdash; but
that is the weakest number in the calibration and worth knowing about.

**Lateral zero is the board's corner, not the car's centreline.** Unless you pass
`--lateral-inches`, `measure_ground_point` reports lateral distance from wherever the
board's first corner happened to be, so the middle of the frame will not read zero: on
one capture it read &minus;2.8 inches. Scale is unaffected, so lane offsets are right
either way; only absolute positions shift.

**No printer?** Lay two strips of the follow-tape a known distance apart:

```
donkey calibrate-cv --car ~/mycar --tape-separation-inches 10
```

That gives the scale but no homography, so lane changes work and distance
measurement does not.

### Tuning the line colour

The follower finds the tape by thresholding hue, saturation and value, and the
default window is wide: hue 0&ndash;50 from saturation 50 up. That admits skin,
denim, ceiling lights and pale flooring, so a person walking past can capture the
histogram peak and swing the steering to full lock.

Save a few frames from your own car in your own lighting, then:

```
donkey calibrate-color --images "~/frames/*.jpg" --compare
```

It measures the tape's actual colour, proposes a window around it, and &mdash; the
part that matters &mdash; checks that window against every frame you gave it:

```
  frame-102058.jpg   peak col 150  coverage  1.7%  concentration 100.0%
  frame-102304.jpg   peak col 150  coverage  1.4%  concentration 100.0%
```

**Concentration is the number to watch**, not coverage. A wide window matches
more of the band but spreads it, and the histogram peak then lands wherever the
lighting is brightest. A tight window matches less and clusters it on the tape.

Point `--region X,Y,W,H` at the tape if the automatic search picks the wrong
thing, or `--pick` to drag a box.

Capture the frames with `OVERLAY_IMAGE = False`. With it on, the scan band in the
saved image is the follower's own mask rather than the scene, and calibrating
from that measures the previous answer. The command detects and excludes such
rows, and says so, but a clean frame is better.

### CONFIDENCE_THRESHOLD changed meaning

It is now the **fraction of the scan column** that must match the tape colour,
0.0 to 1.0, defaulting to 0.15.

It was previously compared against a raw sum of mask values &mdash; 255 per matching
pixel &mdash; while being documented as a fraction with a default of 0.0015. One
matching pixel scored 255 and cleared it, so **the gate could never reject
anything**. On a real track a ten-pixel speck at the edge of the frame counted as
a confident line detection: the follower chased it, steering saturated, and the
car drove off the course.

Measured on that track: tape genuinely in view scores 0.28&ndash;0.44, and the speck
that caused the crash scored 0.125.

**Dashed tape can never fill the band.** Confidence is lit rows over `SCAN_HEIGHT`, so
a track laid in dashes only ever scores what a single dash covers. On one course with
`SCAN_HEIGHT = 80` a dash lit 10&ndash;25 rows, putting confidence between 0.12 and 0.31
&mdash; straddling the 0.15 default, which reads as the line flickering in and out while
the car is in fact tracking it perfectly well. Either lower the gate or shorten
`SCAN_HEIGHT` so a dash covers more of it, but check real frames before deciding: the
same change also raises what a reflection scores, and that is what the gate is for.

If your config still has a value near 0.0015, the gate stays effectively open and
you keep the behaviour you had &mdash; nothing breaks on upgrade. Raise it to around
0.15 to actually get the protection.

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

### Upgrading a car that already exists

Pulling new code onto the Pi is only the first step. A car directory holds
*copies* of `manage.py` and `config.py` taken when it was created, and the
supervisor prefers the car's own `manage.py` so that local changes survive. A
template change therefore does not reach an existing car on its own, and the
failure is silent &mdash; the car keeps running, just without the new behaviour.

**1. Pull the code.**

```zsh
cd ~/projects/donkeycar && git pull
```

**2. Refresh the car's copies.** Run it *from inside the car directory*, and
name the template &mdash; without `--template` it defaults to `complete` and you
will get the wrong car app:

```zsh
cd ~/mycar
donkey update --template cv_control
```

That rewrites `manage.py` and `config.py` from the template and leaves
`myconfig.py` alone. Back up `manage.py` first if you have edited it.

**3. Check `myconfig.py` for overrides of anything that changed.** `myconfig.py`
wins over `config.py`, so a stale value there survives step 2. The one that
bites is `CV_CONTROLLER_OUTPUTS`: a car created earlier has

```python
CV_CONTROLLER_OUTPUTS = ['pilot/steering', 'pilot/throttle', 'cv/image_array']
```

`Memory.put` assigns by position, so extra values the controller returns are
simply dropped. That is deliberate &mdash; it is what keeps old configs working &mdash;
but it means new outputs never arrive, and everything downstream reads `None`
with no error anywhere. The current list is:

```python
CV_CONTROLLER_OUTPUTS = ['pilot/steering', 'pilot/throttle', 'cv/image_array',
                         'cv/confidence', 'cv/line_detected']
```

**4. Restart the server, not just the vehicle.**

```zsh
pkill -f "donkey mcp"
donkey mcp --car ~/mycar --host <the car's LAN address>
```

`start` re-reads the *config*, but the builder module is imported once when the
process starts, so a changed `manage.py` needs a real restart. As a rule: config
values reload, code does not.

### Reading a run that went wrong

Several failure modes look like something else entirely:

| What you see | What it usually is |
| --- | --- |
| `line_detected` true on ~100% of samples, steering barely varying | **The car is not moving.** An unpowered ESC produces a flawless-looking trace, because a stationary camera sees the same tape in every frame. Genuine driving on this course held the line about 86% of the time. Vary-free perfection is the tell. |
| No line for the first several seconds after `start`, then it appears | The camera's auto-exposure is still settling. Measured on one car, confidence climbed from 0.07 to 0.36 over a few seconds while nothing moved. Wait for the line rather than judging placement from the first frames. |
| The car drives for two seconds and stops | The command watchdog. See **Commands expire**. |
| Steering pinned at full lock | Check `line_detected` first. The follower decays steering toward centre while blind, so a hard steering value means something completely different depending on whether the line is in view. |
| The tape looks badly off-centre at the scan row | Not necessarily a placement problem. `SCAN_Y` looks tens of inches ahead &mdash; about 37 on one car &mdash; so the tape's column there mixes lateral offset with the car's heading and with the track's curvature over that distance. On a bend a correctly placed car reads as badly offset. |

### Tuning without restarting

`start` re-reads the car's config, so the loop is:

1. edit `myconfig.py` (thresholds, `SCAN_Y`, `SCAN_HEIGHT`, lane offsets)
2. call `stop`, then `start`
3. look at the next `get_vehicle_state` frame

A config that will not parse fails the `start` and leaves the previous one in
place, so a typo does not take the server down with it. `MCP_SERVER_HOST` and
`MCP_SERVER_PORT` are the exception: the socket is already bound, so changing
those needs a real restart, and the server logs a warning saying so. Pass
`--no-reload` to keep the config fixed for the life of the process.

## 5. The tools

| Tool | What it does |
| --- | --- |
| `get_track_config` | Segment geometry, how many, loop or dead-end, and the named lanes. Call once. |
| `get_vehicle_state` | Camera frame plus throttle, steering, lane, mode. `live` says whether the vehicle loop is still writing; when it is false the car-derived fields are null and there is no frame, so a stopped car cannot look like a running one. `loop_count` rises every loop. |
| `set_control` | Set throttle and/or lane. Give `lane` by name, or `lane_offset_inches` for finer control. |
| `measure_ground_point` | Turn a pixel into a position on the ground, in inches. This is how you know when to brake. |
| `start` / `stop` | Begin and end driving. `start` re-reads `config.py` and `myconfig.py` first, so tuning is edit &rarr; stop &rarr; start &rarr; look, with no server restart. |
| `emergency_stop` | Zero the throttle now, without touching the lifecycle. |
| `get_calibration` | Scale, homography, and whether either has gone stale. |

`get_vehicle_state` also reports `line_detected` and `line_confidence`. Watch
them: a hard steering value means something entirely different depending on
whether the autopilot can see the line. Following a bend and driving blind at the
lock it last held look identical otherwise &mdash; on a real track that difference
put a car off the course. When the line is lost the payload carries a `warning`
and the follower decays steering back toward centre, but it keeps moving until
you set the throttle to 0.

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

Reading state does **not** reset the timer &mdash; only a command does. So the obvious
driving loop, command once and then poll `get_vehicle_state` to watch what happens,
gives you a car that moves for two seconds and parks, while the state you are reading
goes on reporting the throttle you asked for. `watchdog_tripped` in the state payload
says when this has happened, and sending the same values again is the normal way to
hold a speed.

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

## 8. A worked example

These are the settings one car ended up with after a session of tuning on a real
indoor track. **The numbers are that car's, not yours** &mdash; they depend on its
ESC, its servo, its camera mount and the lighting in that room. What transfers is
the *method*: every value below was measured rather than guessed, and the
measurement is given so you can repeat it.

```python
# colour, from `donkey calibrate-color` on five clean frames
COLOR_THRESHOLD_LOW  = (17, 103, 104)
COLOR_THRESHOLD_HIGH = (37, 255, 255)
CONFIDENCE_THRESHOLD = 0.15

# where and how much to look
SCAN_Y      = 100
SCAN_HEIGHT = 80

# pin the reference column; see below
TARGET_PIXEL = 160

# when to treat it as a corner
TARGET_THRESHOLD = 20

# speed
THROTTLE_MIN = 0.25
THROTTLE_MAX = 0.3

PWM_STEERING_THROTTLE = {
    "STEERING_RIGHT_PWM":   300,
    "STEERING_LEFT_PWM":    440,
    "THROTTLE_STOPPED_PWM": 370,
    "THROTTLE_FORWARD_PWM": 450,
    ...
}
```

### How each one was arrived at

**Colour and confidence.** `donkey calibrate-color` measured the tape at hue
24&ndash;31, saturation 123+, value 135+, and proposed a window with margin. Tape
genuinely in view scored 0.28&ndash;0.44 on the confidence scale; a ten-pixel speck at
the frame edge that had sent the car off course scored 0.125. 0.15 sits between.

**`THROTTLE_FORWARD_PWM`.** The car would not move at all. Converting to
microseconds showed why: at the original 400, full throttle was only +122&nbsp;&micro;s
above neutral, and 0.3 throttle just +37&nbsp;&micro;s &mdash; inside the ESC's deadband.
Ramping the commanded throttle found the car first moved at about **+72&nbsp;&micro;s**.
450 puts 0.3 throttle at +98&nbsp;&micro;s, comfortably past it.

**`THROTTLE_MIN`.** At 0.15 the ESC sees +49&nbsp;&micro;s &mdash; enough to keep rolling,
since rolling friction is lower than stiction, but not to start again. The car
slowed for a corner, stopped, and could not restart. 0.25 gives +81&nbsp;&micro;s, just
above the measured threshold.

**Steering PWM.** The original 345&ndash;415 is &plusmn;142&nbsp;&micro;s, about a third of a
typical RC servo's travel. The symptom was the PID winding to full lock and the
car never recovering. 300&ndash;440 is &plusmn;285&nbsp;&micro;s, and corners then entered *and
exited* &mdash; steering peaked around 0.5 and came back rather than pinning at 1.0.

**`TARGET_THRESHOLD`.** Steering is `Kp` times the pixel error, so with
`PID_P = -0.01` the pixel error is roughly `steering * 100`. Logging a real run
gave a median error of 19&nbsp;px, which meant the stock threshold of 10 classified
83% of the run as cornering and the car almost never reached `THROTTLE_MAX`.
Raising it to 20 took mean throttle up 41% and time-at-maximum from 4% to 48%.

**`THROTTLE_MAX`.** 0.4 was tried and reverted: on a tight section it produced
four lost-line events against zero at 0.3.

**`SCAN_Y`.** 60, 100 and 140 were all tried. 100 was best. Looking nearer (140)
meant the car could not see where the line was going; looking further (60) made
the tape thinner in frame, so confidence fell and the gate rejected it.

**`TARGET_PIXEL = 160`** &mdash; the image centre, pinned rather than left at `None`.

Left unset, the follower latches its reference from the first frame containing a line,
and a lane offset is then measured from wherever the tape happened to be in that one
frame rather than from the car's centreline. "Six inches right" only means six inches
right if the car started square on the line. Pinning it to the middle of the image makes
the offset mean the same thing on every run.

It also removes a failure mode worth knowing about even if you leave it unset. The
latch used to happen before the confidence gate, so a car started while looking away
from the tape anchored itself to the argmax of an empty scan band &mdash; on this car a
reflection at column 18, scored 0.087 against a threshold of 0.15, became the place it
spent the rest of the run steering toward. The latch now waits for a frame that clears
the gate.

### The general lesson

Three of these were the same bug in different clothes: **a control range too
narrow to do anything with**. Throttle spanned 30 PWM counts, steering 70, and in
both cases the software was working perfectly and commanding values the hardware
could not act on. If a car will not move, or will not turn, convert the PWM
numbers to microseconds before touching anything else.

## 9. Testing without a car

Everything above is exercisable on a laptop.

```
CAMERA_TYPE = 'MOCK'         # or 'IMAGE_LIST' with recorded track footage
DRIVE_TRAIN_TYPE = 'None'
```

`IMAGE_LIST` plus a recorded tub gives deterministic replays against real footage.
The test suite drives all five activities against a real vehicle loop this way, with
scripted perception standing in for the vision model.
