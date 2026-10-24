# Track cards for the camera — Plan

The track cards (`assets/track-cards/`) were drawn to look good to a person: a cream background,
pastels, and a stop sign in crimson with a dark red border. On the car they are harder to read than
they need to be. In the O7 hardware check (`OBJECT_DISTANCE_PLAN.md`), under ordinary room
light at 640×480, the large stop sign's dark red border came out too dark for a red colour mask,
so the mask boxed the octagon 3 px small and `measure_object_distance` read 12% long. The
crimson also landed at OpenCV hue 165–177, toward the purple that the venue's decorations share
(see the field notes), and a red object on a shelf was a bigger "red" blob than the sign.

This plan redraws the cards so a camera, not just a person, can pick each one out and measure it:
plain white backgrounds, strong outlines, saturated colours chosen to be far apart in hue from
each other and from the track, and no detail too small to survive 320×240.

**Branch:** `mcp-server`

---

## Progress — 1 of 5

- [x] **C1** — Legibility check: a script that scores every card as the camera would see it
- [ ] **C2** — Stop signs: the track card and the large sign
- [ ] **C3** — Traffic lights
- [ ] **C4** — People, dog, vehicles and houses
- [ ] **C5** — PDFs, README and the docs

Each box is ticked in the commit that does the work. Ruff, mypy and the full test suite pass on
every commit.

---

## Decisions

| # | Question | Proposal | Why |
| --- | --- | --- | --- |
| D1 | Background | **Pure white**, `#ffffff`, on every card face | The cream (`#fdf7ee`) lowers contrast against every colour on the card and tints the white a camera white-balances against. White paper is as bright as print gets. |
| D2 | Outlines | Every figure gets a **black outline**, at least 8 of the card's 300 units (0.08 in on a 3 in card) | An object's edge is where a box is drawn and a size is measured. Black against white is the strongest edge print can make, whatever the colour inside it. |
| D3 | Stop sign colours | **Signal red to the edge** (`#e3170a`, OpenCV hue 2) on the white card, with **no dark or black rim**; **white** inner ring and lettering. D2's black outline does not apply to the stop sign. *Changed by Ed, 2026-10-24, from "black outer border", after C1's comparison* | The dark red border was the part the camera lost, and C1 showed a black one is worse still for a colour mask: a rim that is not red is not in a red mask. Red to the edge boxes best by colour and by edge. A red nearer orange moves the face away from the purple at the venue and the magenta the crimson drifted toward. |
| D4 | Hues across the set | One hue family per kind of thing, chosen to be **at least 25° apart** in hue from each other and from the track's **yellow** centreline, plus white for side tape | So a colour mask for one prop does not catch another, or the track. The palette, with OpenCV hue values, is fixed in C1 before any card is redrawn. |
| D5 | Saturation and brightness | Colour fills at **saturation ≥ 70%**, and no fill within 15% brightness of the white background | Pastels (the light blues, tans and greens now used) wash out under room light and auto-exposure. |
| D6 | Fine detail | Nothing narrower than **6 of 300 units** (about 2 px at 320×240 from 2 ft); text at least **40 units** tall, heavy weight | Detail below a couple of pixels turns to noise, or vanishes in JPEG. |
| D7 | Recognisability for a person | Kept: each card still reads at a glance as what it is | The agent is a vision model and reasons the way a person would; a card that stops looking like a stop sign is worse for it, not better. |
| D8 | Sizes | **Unchanged**: 3 in faces, the same tent geometry; the large sign's octagon stays 4.5 in | The O7 measurements and the docs' reference dimensions stay valid; only the artwork changes. |
| D9 | How "better" is checked | A script (C1) renders each card, then simulates the camera: dim light, auto-exposure, blur and JPEG at 320×240 and 640×480. It reports contrast, hue and the size a colour-plus-edge box measures, against fixed targets | Judging by eye on a monitor is what produced the current cards. A number that improves is a check; "looks punchier" is not. |
| D10 | When the O7 check uses them | ~~O7 finishes with the sign already printed~~ **Changed by Ed, 2026-10-24: the new sign and cards come first**, and O7's 24 in placement is redone with the new large sign | Ed's call, after re-measuring the lens mark: the 24 in placement is being redone anyway. |

---

## Palette

Fixed in C1 (D4, D5). OpenCV hue is 0–179; the car's yellow tape window is 17–37
(`COLOR_THRESHOLD_LOW/HIGH` in `~/mycar/myconfig.py`). Red, amber and green are reserved for the
stop sign and the lamps, so a colour mask for one cannot catch another prop.

| Colour | Hex | Hue | Use |
| --- | --- | --- | --- |
| White | `#ffffff` | — | backgrounds, lettering, number panels |
| Black | `#111111` | — | outlines, lettering, housings |
| Dark grey | `#3c3c3c` | — | unlit lamps, tyres, shadows |
| Mid grey | `#7a7a7a` | — | roads, posts, details |
| Signal red | `#e3170a` | 2 | **reserved**: stop sign, red lamp |
| Amber | `#ff7000` | 13 | **reserved**: yellow lamp |
| Green | `#00b050` | 74 | **reserved**: green lamp |
| Blue | `#1e5bd6` | 110 | car, clothing |
| Teal | `#009a9a` | 90 | truck, clothing |
| Brown | `#7b3f12` | 13 | hair, dog, wood |
| Skin | `#e0a070` | 12 | skin |

Two exceptions, on purpose. **Amber** sits 4 below the tape window, not 25° clear (D4): a yellow
lamp has to look yellow, and every yellow is in the tape window. It is small, ringed by a black
housing, and only ever lit on its own. **Skin** is under the 70% saturation floor (D5): skin has
to look like skin, and a person is told apart by shape, not by a colour mask.

## C1 — Legibility check

**Files:** `assets/track-cards/check_legibility.py` (new), `donkeycar/tests/test_track_cards.py` (new).

- Renders each card face from `track-cards.html` and `stop-sign-large.html` with headless Chrome,
  or from the SVG directly, to a known pixel size.
- Simulates the camera: brightness scaled to 50% and 30%, a 1 px blur, JPEG quality 75, at
  320×240 and 640×480 for a 3 in face at 2 ft and 4 ft.
- Reports per card: contrast ratio of the figure's outline against the background; the hue and
  saturation of each main colour after the simulation; for the stop signs, the box a red mask
  followed by an edge refinement finds, against the octagon's true size in pixels.
- Fixes the palette for D4 and D5 as a table in this plan, with OpenCV hue values.

*As built:* the drawing rules are checked from each card's SVG source (background, palette,
translucency, black outline, stroke and text sizes), so they need no rendering. The stop signs and
lamps, which are only polygons, circles and rectangles, are drawn directly with OpenCV rather than
through a browser, so the check runs anywhere, including CI. The camera's colour response is
**fitted to the O7 frame** of the printed large sign at 24 in, rather than assumed: per BGR channel
in linear light, `out = flare + gain × printed`, matched to that frame's white card (blue: gray
153, hue 101, saturation 96 of 255), crimson face (hue 172) and dark red border (hue 110–160,
saturation 61–85). A first, assumed response kept the border red and did not reproduce the field
result. `donkeycar/tests/test_track_cards.py` tests the checker on cards written in the test, not
on the real cards.

*Finding, for C2 (D3):* the checker compared three stop sign designs before any was drawn. Error in
px of the box against the true octagon, over both resolutions, both distances and both light
levels:

| Design | Large sign, colour box (worst) | Large sign, edge box (worst) | 3 in card, colour (worst) | 3 in card, edge (worst) |
| --- | --- | --- | --- | --- |
| Current: crimson, dark red rim | −5.7 (−9.0) | +0.9 (+1.3) | −4.6 (−7.0) | +0.5 (+1.1) |
| A: signal red, **black rim** 12 units (D3 as written) | −9.3 (−16.8) | +1.5 (+1.8) | −5.3 (−7.8) | +1.2 (+1.6) |
| B: signal red **to the edge**, no dark rim | **−2.4 (−5.5)** | **+0.7 (+0.9)** | **−2.6 (−4.0)** | **+0.4 (+0.9)** |

A black rim is the worst of the three for a colour mask, for the same reason the dark red one
failed in the field: a rim that is not red is not in a red mask. It does not sharpen the edge box
either. **Proposed change to D3, for Ed to decide:** design B, red to the edge on white, with the
white ring and lettering, and no black or dark rim; D2's black outline applies to the other cards
but not to the stop sign.

**Acceptance**

- [x] Run on the current cards, it reproduces the field result: the stop sign's colour-mask box
      is at least 2 px small at 640×480 at 2 ft under 50% brightness. *(As built, the light levels
      are the fitted "room" response and "dim" at 60% of it: −2.1 px for the large sign and
      −7.0 px for the 3 in card at 640×480, 24 in, room light.)*
- [x] It prints a per-card table and exits non-zero when any card misses a target, so C2–C4 can
      be checked by running it. *(On the current cards: 35 misses, and all 14 fail the drawing
      rules.)*

## C2 — Stop signs

**Files:** `assets/track-cards/track-cards.html`, `assets/track-cards/stop-sign-large.html`.

- Both signs redrawn per D2, D3 and D6: black outer border, signal red face, white ring and
  lettering, white background. The large sign shares the same artwork.
- `measure_object_distance` takes the octagon's size across the flats including the black
  border, as before.

*As built:* both signs are signal red `#e3170a` to the edge (the octagon's stroke is the face
colour, so its outer edge still spans 47–253 and the sizes are unchanged), white ring and
lettering, white background. The track card's post is mid grey with a 6-unit black outline. Both
stop signs are exempt from the black-outline rule (D3). `stop-sign-large.pdf` is regenerated here,
so the new large sign can be printed for O7; `track-cards.pdf` waits for C5. Orange-leaning reds
(`#ee2200`, `#f02800`, `#e83a00`) kept the face further from purple but lost up to 0.8 px of edge
accuracy on the 3 in card at 320×240; darker ones (`#c81e00`–`#dc2400`) kept the edge but not the
hue. `#e3170a` was the best of both.

**Acceptance**

- [x] Under the C1 simulation, the colour-plus-edge box is within 1 px of the true octagon at
      both resolutions and both distances, at 50% and 30% brightness. *(Worst +1.0 px over all 16
      cases; the "room" and "dim" responses stand for the two light levels.)*
- [x] The face's hue is outside the 140–170 OpenCV range (purple and magenta) after simulation.
      *(172–177 throughout. Changed while building C2: not checked for octagons under 10 px, where
      a dozen coloured pixels are mostly noise; that is only the 3 in card at 320×240 from 4 ft,
      6.8 px, which read 163 in dim light.)*
- [ ] A person shown the card without context calls it a stop sign. *(For Ed.)*

## C3 — Traffic lights

**Files:** `assets/track-cards/track-cards.html`.

- Red, yellow and green lights redrawn per D2–D6: a black housing with a white outline, so the
  housing's edge shows against white; the lit lamp in a saturated colour from the D4 palette; the
  unlit lamps dark grey, not tinted.
- The lit lamp's colour is the one thing that tells the three apart, so their hues are the
  furthest apart in the palette; the yellow is kept distinguishable from the yellow centreline by
  shape and housing, since a yellow light must be yellow.

**Acceptance**

- [ ] Under simulation, each lit lamp is classified as its own colour and no other, by hue alone.
- [ ] Each card's housing passes the outline contrast target.

## C4 — People, dog, vehicles and houses

**Files:** `assets/track-cards/track-cards.html`.

- Each figure redrawn per D2, D5 and D6: black outlines, the pastels replaced by saturated fills
  from the palette, small details (faces, wheels' spokes, window frames) simplified or thickened
  to D6.
- Vehicles and houses keep a colour family each (D4). House numbers: black, heavy, at least 40
  units tall, on a white panel.

**Acceptance**

- [ ] Every card passes the C1 outline contrast and minimum-detail targets.
- [ ] House numbers are readable by OCR (Tesseract, if installed; otherwise by the vision model
      the agent uses) at 640×480 from 2 ft.

## C5 — PDFs and docs

**Files:** `assets/track-cards/track-cards.pdf`, `assets/track-cards/stop-sign-large.pdf`,
`assets/track-cards/README.md`, `docs/mcp-server.md`, `docs/mcp-server-manual.html`.

- Both PDFs regenerated with headless Chrome and checked by rendering, as the README describes.
- The README gains the design rules (D1–D6) and how to run the legibility check, so a new card
  can be held to the same standard.
- The docs' reference dimensions say the stop sign's border is black.

**Acceptance**

- [ ] Both PDFs are one Letter page per sheet at 100% and match the HTML.
- [ ] `check_legibility.py` passes on every card.

---

## Out of scope

- Changing card sizes or the tent geometry (D8).
- Teaching the server to detect props itself. The agent still finds and boxes them.
- Reprinting: Ed prints the new sheets; the check in C2 is on the render, and on the car once
  printed.
