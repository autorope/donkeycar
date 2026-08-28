"""
The shipped calibration board has to match what the calibration code expects.

A board with the wrong number of corners is not a subtle failure -- detection
just returns nothing -- but it would be discovered by someone standing over a
car with a printed sheet, which is a bad time to find out.
"""

import importlib.util
import os
import re
import sys

import cv2
import numpy as np
import pytest

import donkeycar
from donkeycar.parts.cv_calibration import (
    DEFAULT_PATTERN,
    DEFAULT_SQUARE_INCHES,
    detect_board,
    solve_homography,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(donkeycar.__file__)))
ASSETS = os.path.join(REPO_ROOT, "assets")
PDFS = [
    "calibration-checkerboard-9x6-1in-letter.pdf",
    "calibration-checkerboard-9x6-1in-a4.pdf",
]


def load_generator():
    path = os.path.join(ASSETS, "generate_checkerboard.py")
    spec = importlib.util.spec_from_file_location("generate_checkerboard", path)
    module = importlib.util.module_from_spec(spec)
    # Register before executing: @dataclass resolves annotations through
    # sys.modules[cls.__module__], which is None for an unregistered module.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", PDFS)
def test_shipped_pdf_exists_and_is_a_pdf(name):
    path = os.path.join(ASSETS, name)
    assert os.path.exists(path), f"{name} is missing from assets/"
    with open(path, "rb") as handle:
        head = handle.read(8)
    assert head.startswith(b"%PDF-"), head


@pytest.mark.parametrize("name", PDFS)
def test_shipped_pdf_matches_the_expected_pattern(name):
    """
    The PDF records its own geometry, so drift between the board and
    DEFAULT_PATTERN is caught here rather than on the workshop floor.
    """
    with open(os.path.join(ASSETS, name), "rb") as handle:
        raw = handle.read().decode("latin-1")
    match = re.search(r"/Subject \(pattern=(\d+)x(\d+) inner corners; square=([\d.]+)in\)", raw)
    assert match, "the PDF does not record its pattern"

    cols, rows, square = int(match.group(1)), int(match.group(2)), float(match.group(3))
    assert (cols, rows) == DEFAULT_PATTERN
    assert square == DEFAULT_SQUARE_INCHES


def test_generator_defaults_track_the_calibration_defaults():
    board = load_generator().Board()
    assert (board.cols, board.rows) == DEFAULT_PATTERN
    assert board.square_inches == DEFAULT_SQUARE_INCHES


def test_board_geometry_is_squares_not_corners():
    """A 9x6-inner-corner board is 10x7 squares, so 10 x 7 inches."""
    board = load_generator().Board()
    assert (board.squares_across, board.squares_down) == (10, 7)
    assert (board.width_inches, board.height_inches) == (10.0, 7.0)


def test_board_must_fit_the_paper():
    generator = load_generator()
    huge = generator.Board(cols=30, rows=20)
    with pytest.raises(ValueError, match="does not fit"):
        generator.build_pdf(huge, "letter")


def test_unknown_paper_is_rejected():
    generator = load_generator()
    with pytest.raises(ValueError, match="Unknown paper"):
        generator.build_pdf(generator.Board(), "foolscap")


def test_generated_board_is_detectable():
    """
    Render the same geometry the PDF describes and put it through the real
    detector, flat and through a camera-like perspective. This is the property
    the printed sheet exists for.
    """
    generator = load_generator()
    board = generator.Board()

    # Raster the board at print-like resolution: squares of `square_px`.
    square_px = 40
    width = board.squares_across * square_px
    height = board.squares_down * square_px
    page = np.full((height + 80, width + 80, 3), 255, np.uint8)
    for col in range(board.squares_across):
        for row in range(board.squares_down):
            if (col + row) % 2 == 0:
                x0, y0 = 40 + col * square_px, 40 + row * square_px
                page[y0 : y0 + square_px, x0 : x0 + square_px] = 0

    flat = detect_board(page, DEFAULT_PATTERN)
    assert flat is not None
    assert flat.shape[0] == DEFAULT_PATTERN[0] * DEFAULT_PATTERN[1]

    h, w = page.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[w * 0.28, h * 0.08], [w * 0.72, h * 0.08], [w * 1.05, h * 0.97], [w * -0.05, h * 0.97]])
    warped = cv2.warpPerspective(page, cv2.getPerspectiveTransform(src, dst), (w, h), borderValue=(255, 255, 255))
    camera = cv2.resize(warped, (320, 240))

    corners = detect_board(camera, DEFAULT_PATTERN)
    assert corners is not None, "the shipped board is not detectable at camera resolution"
    _matrix, error = solve_homography(corners, DEFAULT_PATTERN, DEFAULT_SQUARE_INCHES)
    assert error < 0.1, error
