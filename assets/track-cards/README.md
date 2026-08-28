# Donkeycar LLM Track

Materials for driving a [Donkeycar](https://docs.donkeycar.com/) around a taped
track under the control of an LLM agent — the track design itself, plus printable
props the car has to recognize and react to.

## What's in here

| File | What it is |
| --- | --- |
| `track-cards.html` | Source for the printable props. Self-contained — inline SVG, no external assets, no build step. Open it in a browser to see setup instructions and a preview. |
| `track-cards.pdf` | Print this. 7 sheets, US Letter, generated from the HTML. |

The track layout, the CV autopilot, the MCP server the agent drives through and the
progression of activities are all in [`docs/mcp-server.md`](../../docs/mcp-server.md).
The implementation plan, with acceptance criteria per milestone, is in
[`MCP_SERVER_PLAN.md`](../../MCP_SERVER_PLAN.md).

## The props

13 self-standing tents, each with a 3″ × 3″ face on both sides:

- **Signs** — stop sign; traffic light showing red, yellow, green
- **Obstacles that must be waited out** — child chasing a ball, mother pushing a
  stroller, elderly man with a cane, dog
- **Obstacles to drive around** — car, truck
- **Addresses** — houses numbered 123, 456, 789

Each tent shows the *same* image on both faces, so the car reads it identically
whichever direction it approaches from.

## Printing and assembly

1. **Print `track-cards.pdf` at 100% / "Actual size."** Turn *off* "fit to page" —
   scaling makes the 3″ face wrong. Card stock stands far better than paper —
   see [Paper](#paper).
2. **Cut** along the solid outline of each 3″ × 9″ strip.
3. **Fold down** on the darker dashed line marked `APEX FOLD`, printed side out.
   That crease becomes the top of the tent.
4. **Fold both 1.5″ tabs outward** on their dashed lines so they lie flat like
   feet, and tape them to the table — or tape both tabs to a strip of card stock
   for a portable base.

```
 1.5"  base tab      → folds out as a foot
 3"    image         (prints upside down on the sheet — this is correct)
====== APEX FOLD ======
 3"    image
 1.5"  base tab      → folds out as a foot
```

The two faces print head-to-head because the fold is horizontal; both come out
right-side-up once tented. A 9″ strip only fits twice across a Letter page, hence
2 tents per sheet.

## Paper

Matte, 160–200 gsm, fed one sheet at a time from the rear tray. Glare avoidance
matters more than anything else here: these props exist to be read by the car's
camera.

| Option | Weight | Why |
| --- | --- | --- |
| **Epson Premium Presentation Paper Matte** *(best match)* | 45 lb / 167 gsm | Coated matte formulated for the dye inks in an EcoTank. Deepest blacks, most saturated reds and ambers, no glare. Stiff enough to stand, folds cleanly without scoring. |
| **Generic matte cover stock** | 65–80 lb cover / 176–216 gsm | Cheaper and stands more solidly, but uncoated so colors sit duller and the folds want scoring. Hammermill Premium Color Copy Cover 80 lb or Neenah Exact Index 110 lb both work. |
| **Plain copy paper** | 24 lb / 90 gsm | Test prints only — checking scale and cut lines. Too floppy to stand as a tent. |

**Avoid glossy, semi-gloss, luster, and photo paper.** Under overhead lights a
glossy stop sign throws a specular hotspot into the camera, and a blown-out white
patch is exactly what breaks a vision model's read.

Skip anything above ~216 gsm too. Entry-level EcoTanks rate plain paper around
90 gsm and their own specialty stock up to roughly 190–200 gsm; heavier sheets
risk misfeeds and cracked folds. Check your model's manual for the exact figure.

### Printer settings

- **Paper type: Matte** (or "Thick Paper"). Left on "Plain," matte stock prints washed out.
- **Quality: High/Best.**
- **Scale: 100% / Actual size.** Still the one setting that ruins the job.
- **Rear tray, one sheet at a time** for anything over ~160 gsm — it's the straighter path.
- Roller scuff marks on the printed face? Turn on **Thick Paper** in the printer's
  maintenance menu to widen the platen gap.
- **Let sheets dry 5–10 minutes before folding or stacking.** Dye ink on coated
  matte stays tacky briefly, and creasing a wet sheet transfers ink to the facing panel.

### Two notes specific to these tents

- **No duplex needed.** Both faces print on one side of the sheet — that's what the
  fold buys you. Paper *opacity* is irrelevant; stiffness is the only property that matters.
- **Score the apex fold at 200 gsm and up.** Letter cardstock is usually long-grain
  and the apex fold runs across the grain, so heavy stock cracks along the crease.
  Run an empty ballpoint or a bone folder down the dashed line against a ruler first.

For maximum stability against a car that nudges them, print on the 167 gsm matte
and tape the two base tabs to a scrap of cereal-box chipboard — light, rigid, and
it won't slide.

## Adding a card

### With Claude Code

Just ask — "add a yield sign to the track cards," "make a house numbered 246,"
"the dog is hard to see, make it darker."

> **The `add-track-card` skill is not part of this repository.** If you have it
> installed it loads automatically and carries the SVG conventions, the tent
> geometry and the page packing rules; otherwise the edits below are all by hand,
> and the `build.sh` commands will not be there to run. A newly added skill is not
> picked up until Claude Code restarts.

### By hand

Two edits to `track-cards.html`:

1. A new `<symbol id="art-yourthing" viewBox="0 0 300 300">` in the `<defs>` block
   at the top.
2. A `.strip` block referencing it, inside a `<div class="page">` near the bottom.
   Copy an existing strip — note the **`flip` class on the first panel is
   required**, and a page div holds **exactly two** strips.

Then regenerate the PDF by printing the HTML to PDF from a browser — US Letter,
100% scale, no headers or footers, background graphics on. Chrome headless does the
same thing:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=assets/track-cards/track-cards.pdf \
  assets/track-cards/track-cards.html
```

Look at the result before committing to new artwork — SVG drawn blind is usually
wrong on the first pass in ways only a render reveals.

If you have the `add-track-card` skill installed, its `scripts/build.sh` wraps this
with a contact sheet and per-page previews, and `SKILL.md` carries the drawing
conventions: palette, stroke weights, and the legibility rules for the car's camera.
