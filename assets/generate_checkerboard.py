#!/usr/bin/env python3
"""
Generate the calibration checkerboard as a vector PDF.

Vector, not raster, because the whole point of the board is that its squares are
exactly one inch. A PDF is measured in points at 72 to the inch, so the geometry
here is exact and stays exact at any print resolution -- as long as the printer
is not allowed to scale it.

The board matches DEFAULT_PATTERN and DEFAULT_SQUARE_INCHES in
donkeycar/parts/cv_calibration.py: 9x6 inner corners, which is 10x7 squares of
one inch, so 10 x 7 inches of board. That fits US Letter and A4 in landscape
with room for the printing instructions.

    python assets/generate_checkerboard.py

Regenerate it if the pattern in cv_calibration.py ever changes; a test checks
the two agree.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

POINTS_PER_INCH = 72.0

# Paper sizes in points, landscape.
PAPERS: dict[str, tuple[float, float]] = {
    "letter": (11.0 * POINTS_PER_INCH, 8.5 * POINTS_PER_INCH),
    "a4": (11.69 * POINTS_PER_INCH, 8.27 * POINTS_PER_INCH),
}


@dataclass(frozen=True)
class Board:
    """A checkerboard described the way OpenCV describes it: inner corners."""

    cols: int = 9  # inner corners across
    rows: int = 6  # inner corners down
    square_inches: float = 1.0

    @property
    def squares_across(self) -> int:
        return self.cols + 1

    @property
    def squares_down(self) -> int:
        return self.rows + 1

    @property
    def width_inches(self) -> float:
        return self.squares_across * self.square_inches

    @property
    def height_inches(self) -> float:
        return self.squares_down * self.square_inches


def _escape(text: str) -> str:
    """Escape a string for a PDF literal."""
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _content_stream(board: Board, page_w: float, page_h: float) -> str:
    """Draw the squares, the title and the printing instructions."""
    square = board.square_inches * POINTS_PER_INCH
    board_w = board.width_inches * POINTS_PER_INCH
    board_h = board.height_inches * POINTS_PER_INCH

    left = (page_w - board_w) / 2.0
    # Sit the board above the instructions, leaving a little more room below
    # than above so the text has somewhere to go.
    bottom = (page_h - board_h) / 2.0 + 6.0

    parts: list[str] = ["q", "0 0 0 rg"]
    for col in range(board.squares_across):
        for row in range(board.squares_down):
            # Top-left square black, so the board looks conventional.
            if (col + row) % 2 == 0:
                x = left + col * square
                y = bottom + (board.squares_down - 1 - row) * square
                parts.append(f"{x:.4f} {y:.4f} {square:.4f} {square:.4f} re f")

    # A hairline box around the whole board: it is the thing to measure against,
    # and it makes a scaled print obvious.
    parts += [
        "0.5 w",
        f"{left:.4f} {bottom:.4f} {board_w:.4f} {board_h:.4f} re S",
        "Q",
    ]

    title = (
        f"Donkeycar CV calibration board - {board.cols}x{board.rows} inner corners, "
        f"{board.square_inches:g} inch squares"
    )
    warn = "PRINT AT 100% / ACTUAL SIZE. Do not use Fit to Page, Shrink to Fit, or Scale to Fit."
    check = (
        f"Check before use: any {board.squares_across} squares across must measure "
        f"{board.width_inches:g} inches, and the outline {board.width_inches:g} x "
        f"{board.height_inches:g} inches."
    )
    lay = "Lay it FLAT on the floor in front of the car. Held upright it gives meaningless numbers."

    text_top = bottom + board_h + 14.0
    parts += [
        "BT",
        "/F1 11 Tf",
        f"1 0 0 1 {left:.4f} {text_top:.4f} Tm",
        f"({_escape(title)}) Tj",
        "ET",
        "BT",
        "/F2 10 Tf",
        f"1 0 0 1 {left:.4f} {bottom - 20.0:.4f} Tm",
        f"({_escape(warn)}) Tj",
        "ET",
        "BT",
        "/F1 9 Tf",
        f"1 0 0 1 {left:.4f} {bottom - 33.0:.4f} Tm",
        f"({_escape(check)}) Tj",
        "ET",
        "BT",
        "/F1 9 Tf",
        f"1 0 0 1 {left:.4f} {bottom - 45.0:.4f} Tm",
        f"({_escape(lay)}) Tj",
        "ET",
    ]
    return "\n".join(parts)


def build_pdf(board: Board, paper: str = "letter") -> bytes:
    """Assemble a single-page PDF. Written by hand to avoid a new dependency."""
    try:
        page_w, page_h = PAPERS[paper]
    except KeyError:
        raise ValueError(f"Unknown paper {paper!r}. Known: {sorted(PAPERS)}") from None

    if board.width_inches * POINTS_PER_INCH > page_w or board.height_inches * POINTS_PER_INCH > page_h:
        raise ValueError(f"A {board.width_inches:g}x{board.height_inches:g} inch board does not fit {paper} landscape")

    content = _content_stream(board, page_w, page_h).encode("ascii")
    # Recorded so a test can prove the shipped PDF still matches the pattern the
    # calibration code expects.
    subject = f"pattern={board.cols}x{board.rows} inner corners; square={board.square_inches:g}in"

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_w:.4f} {page_h:.4f}] "
            f"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>"
        ).encode("ascii"),
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        (
            f"<< /Title (Donkeycar CV calibration board) /Subject ({_escape(subject)}) "
            f"/Creator (donkeycar assets/generate_checkerboard.py) >>"
        ).encode("ascii"),
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {len(objects)} 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode("ascii")
    return bytes(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cols", type=int, default=9, help="inner corners across")
    parser.add_argument("--rows", type=int, default=6, help="inner corners down")
    parser.add_argument("--square-inches", type=float, default=1.0)
    parser.add_argument("--paper", choices=sorted(PAPERS), default="letter")
    parser.add_argument("--out", default=None, help="output path")
    args = parser.parse_args(argv)

    board = Board(cols=args.cols, rows=args.rows, square_inches=args.square_inches)
    out = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"calibration-checkerboard-{board.cols}x{board.rows}-{board.square_inches:g}in-{args.paper}.pdf",
    )
    with open(out, "wb") as handle:
        handle.write(build_pdf(board, args.paper))
    print(f"Wrote {out}: {board.squares_across}x{board.squares_down} squares, {board.square_inches:g} in each")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
