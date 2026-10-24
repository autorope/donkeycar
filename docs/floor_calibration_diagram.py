"""
Draw docs/floor-calibration-measurements.png: what to measure for
`donkey calibrate-cv --forward-inches ... --left-inches ...`, seen from above.

    python docs/floor_calibration_diagram.py docs/floor-calibration-measurements.png

Drawn with OpenCV because the project already depends on it. Re-run it if the
flags or the reference corner change.
"""

import sys

import cv2
import numpy as np
from PIL import Image

SC = 26  # pixels per inch in the drawing
W, H = 1180, 1150
CX, BASE = 470, 770  # where the lens mark (0, 0) is drawn
img = np.full((H, W, 3), 255, np.uint8)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def P(x: float, y: float) -> tuple[int, int]:
    """Inches on the floor (x right, y forward) to pixels in the drawing."""
    return round(CX + x * SC), round(BASE - y * SC)


def text(
    s: str,
    x: float,
    y: float,
    scale: float = 0.62,
    color: tuple[int, int, int] = (40, 40, 40),
    thick: int = 1,
    px: bool = False,
) -> None:
    pos = (round(x), round(y)) if px else P(x, y)
    cv2.putText(img, s, pos, FONT, scale, color, thick, cv2.LINE_AA)


def arrow(a: tuple[float, float], b: tuple[float, float], color: tuple[int, int, int], thick: int = 2) -> None:
    cv2.arrowedLine(img, P(*a), P(*b), color, thick, cv2.LINE_AA, tipLength=0.04)
    cv2.arrowedLine(img, P(*b), P(*a), color, thick, cv2.LINE_AA, tipLength=0.04)


# Car, seen from above, pointing up the page
cv2.rectangle(img, P(-3.75, 1.0), P(3.75, -11.0), (225, 225, 225), -1)
cv2.rectangle(img, P(-3.75, 1.0), P(3.75, -11.0), (90, 90, 90), 2)
for wx in (-4.6, 3.6):
    for wy in (-1.5, -9.5):
        cv2.rectangle(img, P(wx, wy + 1.2), P(wx + 1.0, wy - 1.2), (60, 60, 60), -1)
text("CAR (from above)", -2.6, -6.0, 0.6)
text("front", -0.9, -1.6, 0.5, (90, 90, 90))
# Camera lens and the tape mark on the floor directly under it
cv2.circle(img, P(0, 0), 9, (0, 140, 0), -1)
cv2.circle(img, P(0, 0), 9, (0, 0, 0), 1)
text("camera lens: put a tape mark on", 4.6, -2.2, 0.55, (0, 110, 0))
text("the floor directly below it", 4.6, -3.1, 0.55, (0, 110, 0))
cv2.line(img, P(4.4, -2.4), P(0.3, -0.3), (0, 110, 0), 1, cv2.LINE_AA)

# Car centreline, straight ahead from the lens
for y0 in np.arange(1.5, 21, 1.0):
    cv2.line(img, P(0, y0), P(0, y0 + 0.5), (150, 150, 150), 1, cv2.LINE_AA)
text("car's centreline", 0.4, 11.0, 0.5, (120, 120, 120))
text("(straight ahead)", 0.4, 10.2, 0.5, (120, 120, 120))

# The board: 10 x 7 one-inch squares lying flat, long side across, near edge 14 in ahead
near_edge, cols_sq, rows_sq = 14.0, 10, 7
left_edge = -cols_sq / 2
for i in range(cols_sq):
    for j in range(rows_sq):
        x0, y0 = left_edge + i, near_edge + j
        color = (30, 30, 30) if (i + j) % 2 == 0 else (250, 250, 250)
        cv2.rectangle(img, P(x0, y0 + 1), P(x0 + 1, y0), color, -1)
cv2.rectangle(img, P(left_edge, near_edge + rows_sq), P(-left_edge, near_edge), (0, 0, 0), 1)
text("CHECKERBOARD, flat on the floor", -5.0, near_edge + rows_sq + 1.4, 0.6)
text("(10 x 7 squares, 1 inch each)", -5.0, near_edge + rows_sq + 0.5, 0.5, (90, 90, 90))

# Inner corners: where four squares meet. Mark them all lightly, the reference one strongly.
for i in range(1, cols_sq):
    for j in range(1, rows_sq):
        cv2.circle(img, P(left_edge + i, near_edge + j), 3, (200, 120, 0), -1)
corner = (left_edge + 1, near_edge + 1)  # near-left inner corner: (-4, 15)
cv2.circle(img, P(*corner), 13, (0, 0, 220), 3, cv2.LINE_AA)
cv2.line(img, P(corner[0] - 0.6, corner[1] - 0.6), (P(-9.2, 13.2)[0], P(-9.2, 13.2)[1]), (0, 0, 220), 2, cv2.LINE_AA)
text("REFERENCE CORNER", -16.8, 12.9, 0.62, (0, 0, 220), 2)
text("the inner corner (where four", -16.8, 12.0, 0.5, (0, 0, 220))
text("squares meet) NEAREST the", -16.8, 11.2, 0.5, (0, 0, 220))
text("car and furthest LEFT", -16.8, 10.4, 0.5, (0, 0, 220))
text("(not the board's outer corner)", -16.8, 9.6, 0.5, (0, 0, 220))

# Measurement A: forward, along the centreline, from the lens mark to the reference corner's row
cv2.line(img, P(corner[0], corner[1]), P(0.0, corner[1]), (220, 0, 160), 1, cv2.LINE_AA)
arrow((6.2, 0.0), (6.2, corner[1]), (220, 0, 160), 2)
cv2.line(img, P(0.3, 0.0), P(6.6, 0.0), (220, 0, 160), 1, cv2.LINE_AA)
cv2.line(img, P(5.2, corner[1]), P(6.6, corner[1]), (220, 0, 160), 1, cv2.LINE_AA)
text("A: --forward-inches", 6.7, 8.2, 0.65, (220, 0, 160), 2)
text("straight ahead, parallel to the", 6.7, 7.3, 0.5, (220, 0, 160))
text("centreline, from the lens mark", 6.7, 6.5, 0.5, (220, 0, 160))
text("to the reference corner's row", 6.7, 5.7, 0.5, (220, 0, 160))
text("(15 in this drawing)", 6.7, 4.9, 0.5, (220, 0, 160))

# Measurement B: lateral, from the centreline sideways to the reference corner
arrow((0.0, corner[1] - 1.4), (corner[0], corner[1] - 1.4), (200, 90, 0), 2)
cv2.line(img, P(corner[0], corner[1]), P(corner[0], corner[1] - 1.8), (200, 90, 0), 1, cv2.LINE_AA)
text("B: --left-inches", -16.8, 6.9, 0.65, (200, 90, 0), 2)
text("how far the reference corner", -16.8, 6.0, 0.5, (200, 90, 0))
text("is to the LEFT of the car's", -16.8, 5.2, 0.5, (200, 90, 0))
text("centreline: a positive number", -16.8, 4.4, 0.5, (200, 90, 0))
text("(4 in this drawing: a centred", -16.8, 3.6, 0.5, (200, 90, 0))
text("board puts it 4 in left)", -16.8, 2.8, 0.5, (200, 90, 0))
cv2.line(img, P(-9.0, 4.6), P(-2.4, corner[1] - 1.4), (200, 90, 0), 1, cv2.LINE_AA)

text("Floor calibration: what to measure", 30, 40, 0.75, (0, 0, 0), 2, px=True)
text("Top-down view. The car points up the page. Distances are examples.", 30, 72, 0.55, (90, 90, 90), px=True)
text("For this drawing:", 30, H - 48, 0.55, (40, 40, 40), px=True)
text("donkey calibrate-cv --car ~/mycar --forward-inches 15 --left-inches 4", 30, H - 22, 0.6, (0, 0, 0), 1, px=True)
# Saved with a 64-colour palette: the drawing has only a few colours, and the
# user manual embeds it, so 25 KB beats 175 KB. Fewer colours turn the green
# lens marker grey.
out = sys.argv[1] if len(sys.argv) > 1 else "floor-calibration-measurements.png"
Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).quantize(colors=64).save(out, optimize=True)
