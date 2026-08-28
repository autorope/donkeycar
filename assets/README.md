# Assets

Printable material for setting a car up.

## Calibration checkerboard

| File | Paper |
| --- | --- |
| `calibration-checkerboard-9x6-1in-letter.pdf` | US Letter, landscape |
| `calibration-checkerboard-9x6-1in-a4.pdf` | A4, landscape |

Both are the same board: **10 x 7 squares of exactly 1 inch**, which gives the
**9 x 6 inner corners** that `donkey calibrate-cv` looks for by default. They are
vector PDFs, so the geometry is exact at any print resolution — provided the printer
is not allowed to resize it.

### Printing

**Print at 100% / actual size.** Turn off "Fit to Page", "Shrink to Fit" and "Scale
to Fit". This is the one thing that quietly ruins a calibration: a board printed at
96% produces a confident, wrong answer rather than an error.

Then check it with a ruler before you use it:

- 10 squares across should measure **10 inches**
- the outline should be **10 x 7 inches**

If it is off, fix the print settings rather than compensating with
`--square-inches` — a scaled print is usually also slightly non-uniform.

### Using it

Glue or tape it to something rigid — foam board, stiff card, a clipboard. A curled
sheet is a curved plane, and the calibration assumes a flat one.

Lay it **flat on the floor** in front of the car, then:

```
donkey calibrate-cv --car ~/mycar
```

and open `http://localhost:8892`. Slide the board until the blue scan band crosses it
and the corners light up green, then press Capture. Full walkthrough in
[`docs/mcp-server.md`](../docs/mcp-server.md).

### A different board

Any checkerboard works if you tell the tool its shape:

```
donkey calibrate-cv --car ~/mycar --cols 7 --rows 5 --square-inches 1.5
```

`--cols` and `--rows` are **inner corners**, not squares: a 10 x 7 square board has
9 x 6 inner corners. To generate a matching PDF:

```
python assets/generate_checkerboard.py --cols 7 --rows 5 --square-inches 1.5
```

A bigger board measured from further away gives a better homography, so use the
largest one that fits comfortably in frame.
