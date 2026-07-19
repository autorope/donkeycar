#!/usr/bin/env python3
"""
Static side-by-side preview tool for the DonkeyCar lighting augmentations
(GAMMA, NOISE, improved BRIGHTNESS, existing SHADOW, and the combined
"All Conditions" profile).

This is a review/inspection tool only:
  - It does not start a server or web app.
  - It does not modify, move, or delete any training data.
  - It only reads real images from a tub folder and writes new PNG files
    to the chosen output folder.

It loads a handful of real images from a DonkeyCar tub, applies each
augmentation individually (with its probability forced to 1.0 so the
effect is always visible in the preview), builds a side-by-side
comparison grid for each image, and saves the grid as a PNG.

Usage:
    python tools/preview_augmentations.py \\
        --data path/to/tub_folder \\
        --output augmentation_previews \\
        --num-samples 6 \\
        --clean-output

--data should point at a DonkeyCar tub directory (v2 format), i.e. a
folder containing an "images/" subfolder of .jpg files. You can also
point --data directly at a plain folder of .jpg/.png images.

Rerun behavior:
  - Preview files are named preview_<source_image_basename>.png, so
    rerunning with the same --data/--seed/--num-samples overwrites the
    same files in place.
  - By default the output folder is never cleared, so previews from a
    different --seed/--num-samples/--data (i.e. different source images)
    just accumulate alongside older ones.
  - Pass --clean-output to delete old preview_*.png files directly inside
    --output before generating, so the folder only ever reflects the most
    recent run. This never touches --data, never touches anything outside
    --output, and refuses to run if --output points at your tub folder.
"""
import argparse
import glob
import os
import random
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageDraw

# Make the repo root importable when this script is run directly, e.g.
# `python tools/preview_augmentations.py` from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from donkeycar.pipeline.augmentations import ImageAugmentation  # noqa: E402


# ---------------------------------------------------------------------------
# Augmentation settings used for this preview. These mirror the defaults in
# donkeycar/templates/cfg_complete.py, with AUG_GAMMA_RANGE widened to
# (60, 160) to match the recommended "all_conditions" training profile
# (see donkeycar/templates/myconfig.py).
#
# Every probability below is forced to 1.0 in build_config(). That does
# NOT match real per-image training probability (defaults there are
# BRIGHTNESS 0.5, SHADOW 0.3, GAMMA 0.5, NOISE 0.3) - it's a deliberate
# "always on" view so every column always shows its effect, which makes it
# easier to judge maximum strength/realism, including whether stacking
# every effect at once in "All Conditions" looks unrealistic.
SETTINGS = {
    'AUG_BRIGHTNESS_RANGE': 0.2,
    'AUG_CONTRAST_RANGE': 0.2,
    'AUG_BLUR_RANGE': (0, 3),
    'AUG_GAMMA_RANGE': (60, 160),
    'AUG_NOISE_STD_RANGE': (0.05, 0.15),
    'AUG_NOISE_MEAN_RANGE': (0.0, 0.0),
    'AUG_SHADOW_DARKNESS_RANGE': (0.4, 0.7),
    'AUG_SHADOW_COUNT_RANGE': (1, 2),
    'AUG_SHADOW_DIMENSION': 5,
    'AUG_SHADOW_ROI': (0.0, 0.3, 1.0, 1.0),
    'AUG_SHADOW_BLUR_KSIZE': 21,
}

COLUMNS = ['Original', 'Brightness', 'Gamma', 'Shadow', 'Noise',
          'All Conditions']

ALL_CONDITIONS_LIST = ['BRIGHTNESS', 'BLUR', 'SHADOW', 'GAMMA', 'NOISE']


def build_config(aug_list):
    """Minimal config object for ImageAugmentation with every augmentation
    probability forced to 1.0, so previewed effects are always visible."""
    cfg = SimpleNamespace(AUGMENTATIONS=aug_list, **SETTINGS)
    cfg.AUG_GAMMA_PROBABILITY = 1.0
    cfg.AUG_NOISE_PROBABILITY = 1.0
    cfg.AUG_SHADOW_PROBABILITY = 1.0
    return cfg


def find_images(data_path, num_samples, seed):
    """Locate .jpg/.jpeg/.png images under a tub folder's images/
    subfolder (DonkeyCar tub v2 layout), or directly under data_path if
    it's just a plain folder of images. Returns a deterministic sample
    of up to num_samples paths."""
    search_folders = []
    images_subfolder = os.path.join(data_path, 'images')
    if os.path.isdir(images_subfolder):
        search_folders.append(images_subfolder)
    search_folders.append(data_path)

    image_paths = []
    for folder in search_folders:
        for ext in ('*.jpg', '*.jpeg', '*.png'):
            image_paths.extend(glob.glob(os.path.join(folder, ext)))
        if image_paths:
            break

    if not image_paths:
        raise FileNotFoundError(
            f"No .jpg/.jpeg/.png images found under '{data_path}' or "
            f"'{images_subfolder}'. Point --data at a DonkeyCar tub folder "
            f"(one containing an images/ subfolder) or a plain folder of "
            f"images.")

    image_paths = sorted(image_paths)
    random.Random(seed).shuffle(image_paths)
    return image_paths[:num_samples]


def clean_output_folder(output_dir, data_path):
    """Deletes only this tool's own generated preview PNGs - files
    directly inside output_dir matching the 'preview_*.png' naming
    convention used by build_grid(). Never recurses into subfolders,
    never touches anything outside output_dir.

    As a safety guard, refuses to clean if output_dir resolves to the
    same folder as --data (or its images/ subfolder), so a mistaken
    --output value can never delete source tub images. Returns the
    number of files removed.
    """
    output_abs = os.path.abspath(output_dir)
    data_abs = os.path.abspath(data_path)
    images_abs = os.path.abspath(os.path.join(data_path, 'images'))
    if output_abs in (data_abs, images_abs):
        raise ValueError(
            f"Refusing --clean-output: the output folder ('{output_abs}') "
            f"is the same as your --data folder (or its images/ "
            f"subfolder). Choose a separate --output folder so cleaning "
            f"can never touch source tub data.")

    if not os.path.isdir(output_dir):
        return 0

    removed = 0
    for f in glob.glob(os.path.join(output_dir, 'preview_*.png')):
        if os.path.isfile(f):
            os.remove(f)
            removed += 1
    return removed


def apply_single(name, img):
    cfg = build_config([name])
    aug = ImageAugmentation.create(name, cfg, prob=1.0)
    return aug(image=img)['image']


def apply_all_conditions(img):
    cfg = build_config(ALL_CONDITIONS_LIST)
    pipeline = ImageAugmentation(cfg, 'AUGMENTATIONS')
    return pipeline.run(img)


def label_panel(img_arr, text, pad=24):
    """Returns a PIL Image with a dark title bar (with text) above img_arr."""
    h, w = img_arr.shape[:2]
    panel = Image.new('RGB', (w, h + pad), color=(30, 30, 30))
    draw = ImageDraw.Draw(panel)
    draw.text((6, 5), text, fill=(255, 255, 255))
    panel.paste(Image.fromarray(img_arr), (0, pad))
    return panel


def build_grid(image_path, out_path):
    """Builds and saves one side-by-side comparison PNG for image_path.
    Returns the dict of column-name -> augmented np.ndarray for validation.
    """
    orig = np.array(Image.open(image_path).convert('RGB'))

    columns = {
        'Original': orig,
        'Brightness': apply_single('BRIGHTNESS', orig),
        'Gamma': apply_single('GAMMA', orig),
        'Shadow': apply_single('SHADOW', orig),
        'Noise': apply_single('NOISE', orig),
        'All Conditions': apply_all_conditions(orig),
    }

    # Sanity check: every augmentation must preserve shape and dtype.
    for name, arr in columns.items():
        assert arr.shape == orig.shape, f'{name} changed shape: {arr.shape}'
        assert arr.dtype == orig.dtype, f'{name} changed dtype: {arr.dtype}'

    panels = [label_panel(columns[c], c) for c in COLUMNS]
    gap = 4
    total_w = sum(p.width for p in panels) + gap * (len(panels) - 1)
    max_h = max(p.height for p in panels)
    grid = Image.new('RGB', (total_w, max_h), color=(255, 255, 255))
    x = 0
    for p in panels:
        grid.paste(p, (x, 0))
        x += p.width + gap
    grid.save(out_path)
    return columns


def main():
    parser = argparse.ArgumentParser(
        description='Generate static side-by-side PNG previews of the '
                     'DonkeyCar lighting augmentations (Brightness, Gamma, '
                     'Shadow, Noise, All Conditions) on real tub images.')
    parser.add_argument('--data', required=True,
                        help='Path to a DonkeyCar tub folder (containing '
                             'an images/ subfolder) or a plain folder of '
                             '.jpg/.png images.')
    parser.add_argument('--output', default='augmentation_previews',
                        help='Output folder for preview PNGs '
                             '(default: augmentation_previews)')
    parser.add_argument('--num-samples', type=int, default=6,
                        help='Number of sample images to preview '
                             '(default: 6)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed used to pick which images are '
                             'sampled, for reproducible previews '
                             '(default: 42)')
    parser.add_argument('--clean-output', action='store_true',
                        help='Before generating, delete old preview PNGs '
                             '(files matching preview_*.png) directly '
                             'inside --output. Only ever removes files '
                             "this tool generated, only inside --output. "
                             'Never touches tub/source data. Off by '
                             'default, so reruns are additive/overwrite '
                             'unless you pass this flag.')
    args = parser.parse_args()

    # Seed both random and numpy's global RNG so that re-running with the
    # same --seed reproduces identical previews (both which images are
    # sampled and the randomized augmentation strength/placement drawn for
    # each one). Useful for comparing "before vs after" tweaks to the
    # augmentation settings.
    random.seed(args.seed)
    np.random.seed(args.seed)

    cleaned_count = 0
    if args.clean_output:
        cleaned_count = clean_output_folder(args.output, args.data)

    os.makedirs(args.output, exist_ok=True)
    image_paths = find_images(args.data, args.num_samples, args.seed)

    print(f'Found images under: {args.data}')
    if args.clean_output:
        print(f'Cleaned {cleaned_count} old preview_*.png file(s) from '
             f'{os.path.abspath(args.output)} before generating.')
    print(f'Previewing {len(image_paths)} image(s), saving to: '
         f'{os.path.abspath(args.output)}\n')

    generated = []
    for path in image_paths:
        base = os.path.splitext(os.path.basename(path))[0]
        out_path = os.path.join(args.output, f'preview_{base}.png')
        build_grid(path, out_path)
        generated.append(out_path)
        print(f'  {path}  ->  {out_path}')

    rerun_cmd = (f'python tools/preview_augmentations.py --data {args.data} '
                f'--output {args.output} --num-samples {args.num_samples}')
    if args.clean_output:
        rerun_cmd += ' --clean-output'

    print('\n--- Summary ---')
    print(f'Preview files generated this run: {len(generated)}')
    print(f'Saved to: {os.path.abspath(args.output)}')
    if args.clean_output:
        print(f'Old previews cleaned first: yes '
             f'({cleaned_count} old file(s) removed)')
    else:
        print('Old previews cleaned first: no (existing preview_*.png '
             'files for the same source images were overwritten; '
             'previews for images not in this run, if any, were left '
             'in place - pass --clean-output to remove them)')
    print(f'Rerun command: {rerun_cmd}')
    print('\nDone.')


if __name__ == '__main__':
    main()
