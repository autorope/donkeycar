#!/usr/bin/env python3
"""
Run and view offline explainability analysis (Grad-CAM attention/uncertainty,
feature-space novelty, and pixel-gradient saliency maps) for a recorded
drive, entirely from the browser -- no need to remember the underlying
`python -m donkeycar.parts.gradcam_uncertainty` command-line flags.

Usage:
    python run_gradcam_analysis.py [--port 8890] [--host 127.0.0.1]

Then open the printed URL. Pick a tub and model (autodiscovered from data/
and models/ in this directory, or type any path), choose which frames to
analyse, and click Run -- the page shows live progress and switches to the
viewer automatically when the analysis finishes.

To view a previously-generated analysis directly (skipping the form), pass
its directory:
    python run_gradcam_analysis.py --analysis data/mytub/gradcam_analysis
"""
from donkeycar.parts.uncertainty_viewer import main

if __name__ == '__main__':
    main()
