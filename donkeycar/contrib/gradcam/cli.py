"""
Command-line interface for Grad-CAM visualization tool.

This module provides a command-line interface for generating Grad-CAM
visualizations for DonkeyCar neural networks.
"""

import os
import sys
import glob
import json
import argparse
import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras.models import load_model

from .utils import (
    find_last_conv_layer,
    make_gradcam_heatmap,
    create_gradcam_visualization
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate Grad-CAM visualizations for DonkeyCar models'
    )

    # Required arguments
    parser.add_argument(
        '--model_path',
        required=True,
        help='Path to the trained model (.h5 file)'
    )

    parser.add_argument(
        '--data_path',
        required=True,
        help='Path to the dataset directory containing images'
    )

    # Optional arguments
    parser.add_argument(
        '--output_dir',
        default='gradcam_output',
        help='Directory to save output visualizations'
    )

    parser.add_argument(
        '--video_name',
        default='grad_cam_visualization',
        help='Name for the output video file'
    )

    parser.add_argument(
        '--fps',
        type=int,
        default=20,
        help='Frames per second for the output video'
    )

    parser.add_argument(
        '--stride',
        type=int,
        default=1,
        help='Process every Nth frame'
    )

    parser.add_argument(
        '--max_frames',
        type=int,
        default=None,
        help='Maximum number of frames to process'
    )

    parser.add_argument(
        '--alpha',
        type=float,
        default=0.4,
        help='Transparency of the heatmap overlay (0.0-1.0)'
    )

    parser.add_argument(
        '--exclude_regions',
        type=str,
        default=None,
        help='Regions to exclude from heatmap (x1,y1,x2,y2|x1,y1,x2,y2|...)'
    )

    return parser.parse_args()


def load_model_safely(model_path):
    """
    Load a Keras model with appropriate error handling.

    Args:
        model_path: Path to the model file

    Returns:
        Loaded Keras model
    """
    print(f"Loading model from {model_path}")

    try:
        # Try to load the model with custom objects to handle loss functions
        custom_objects = {
            'mse': tf.keras.losses.mean_squared_error,
            'mean_squared_error': tf.keras.losses.mean_squared_error
        }
        model = load_model(model_path, custom_objects=custom_objects)
        print("Model loaded successfully with custom objects")
        return model
    except Exception as e:
        print(f"Error loading model with custom objects: {e}")

        try:
            # Alternative loading method with compile=False
            model = load_model(model_path, compile=False)
            print("Model loaded successfully with compile=False")
            return model
        except Exception as e2:
            print(f"Fatal error loading model: {e2}")
            sys.exit(1)


def find_images(data_path):
    """
    Find image files in the data directory.

    Args:
        data_path: Path to the data directory

    Returns:
        List of image file paths
    """
    print(f"Searching for images in {data_path}")

    # Different image patterns to try
    patterns = [
        os.path.join(data_path, "images/*.jpg"),
        os.path.join(data_path, "**/images/*.jpg"),
        os.path.join(data_path, "*.jpg"),
        os.path.join(data_path, "**/*.jpg")
    ]

    for pattern in patterns:
        print(f"Trying pattern {pattern}")
        image_paths = sorted(glob.glob(pattern, recursive=True))
        if image_paths:
            print(f"Found {len(image_paths)} images with pattern {pattern}")
            return image_paths

    print("No images found with any pattern")
    return []


def load_metadata(data_path):
    """
    Load metadata for images if available.

    Args:
        data_path: Path to the data directory

    Returns:
        Dictionary mapping image paths to their metadata
    """
    metadata = {}

    # Check for catalog.json
    catalog_path = os.path.join(data_path, 'catalog.json')
    if os.path.exists(catalog_path):
        print(f"Found catalog.json at {catalog_path}")
        try:
            with open(catalog_path, 'r') as f:
                catalog = json.load(f)

            for record in catalog:
                if 'image_path' in record:
                    img_path = os.path.join(data_path, record['image_path'])
                    metadata[img_path] = {
                        'steering': record.get('steering'),
                        'throttle': record.get('throttle')
                    }
            print(f"Loaded metadata for {len(metadata)} images from catalog")
        except Exception as e:
            print(f"Error loading catalog.json: {e}")

    # If no catalog or few entries, look for individual JSON files
    if len(metadata) == 0:
        print("Looking for individual JSON files")
        json_files = glob.glob(os.path.join(data_path, "**/*.json"),
                               recursive=True)

        for json_path in json_files:
            try:
                img_path = os.path.splitext(json_path)[0] + '.jpg'
                if os.path.exists(img_path):
                    with open(json_path, 'r') as f:
                        metadata[img_path] = json.load(f)
            except Exception as e:
                print(f"Error reading {json_path}: {e}")

        print(f"Found {len(metadata)} JSON files with metadata")

    return metadata


def process_images(image_paths, model, last_conv_layer_name, metadata={},
                   stride=1, max_frames=None, alpha=0.4, exclude_regions=None):
    """
    Process images and generate Grad-CAM visualizations.

    Args:
        image_paths: List of image file paths
        model: Loaded Keras model
        last_conv_layer_name: Name of the last convolutional layer
        metadata: Dictionary of image metadata
        stride: Process every Nth frame
        max_frames: Maximum number of frames to process
        alpha: Transparency of the heatmap overlay
        exclude_regions: Regions to exclude from the heatmap

    Returns:
        List of visualization frames
    """
    # Apply stride and limit
    image_paths = image_paths[::stride]
    if max_frames is not None and max_frames > 0:
        image_paths = image_paths[:max_frames]

    print(f"Processing {len(image_paths)} images")

    # Sort images numerically if they follow a numeric naming pattern
    try:
        def extract_number(filename):
            base = os.path.basename(filename)
            parts = base.split('_')
            if parts and parts[0].isdigit():
                return int(parts[0])
            return filename

        image_paths = sorted(image_paths, key=extract_number)
        numbers = [extract_number(path) for path in image_paths]
        print(f"Frame sequence: first={numbers[0]}, last={numbers[-1]}")
        print(f"Sample sequence: {numbers[:10]} ...")
    except Exception as e:
        print(f"Could not sort images numerically: {e}")

    # Process images
    frames = []
    for i, img_path in enumerate(image_paths):
        print(f"Processing image {i+1}/{len(image_paths)}: {img_path}")

        # Load image
        img = cv2.imread(img_path)
        if img is None:
            print(f"Warning: Unable to read image {img_path}")
            continue

        # Convert to RGB for visualization
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Get input shape for the model
        input_shape = model.input_shape[1:3]  # Height, width

        # Preprocess image for model input
        img_resized = cv2.resize(img_rgb, (input_shape[1], input_shape[0]))
        img_array = np.asarray(img_resized, dtype=np.float32) / 255.0
        img_batch = np.expand_dims(img_array, axis=0)

        # Generate Grad-CAM heatmap
        heatmap = make_gradcam_heatmap(img_batch, model, last_conv_layer_name)

        # Get metadata for this image if available
        prediction = None
        if img_path in metadata:
            md = metadata[img_path]
            if isinstance(md, dict) and 'steering' in md:
                prediction = f"Steering: {md['steering']:.4f}"
                if 'throttle' in md:
                    prediction += f" Throttle: {md['throttle']:.4f}"

        # Create visualization
        vis_img = create_gradcam_visualization(
            img_rgb,
            heatmap,
            alpha=alpha,
            prediction=prediction,
            exclude_regions=exclude_regions
        )

        frames.append(vis_img)

    return frames


def create_video(frames, output_path, fps=20):
    """
    Create a video from a list of frames.

    Args:
        frames: List of frames (numpy arrays)
        output_path: Path to save the video
        fps: Frames per second

    Returns:
        Path to the created video
    """
    if not frames:
        print("No frames to create video")
        return None

    # Get dimensions from the first frame
    height, width = frames[0].shape[:2]

    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Write frames
    for frame in frames:
        # Convert to BGR for OpenCV
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        out.write(frame_bgr)

    out.release()
    print(f"Video saved to {output_path}")

    return output_path


def save_frames(frames, output_dir):
    """
    Save individual frames to disk.

    Args:
        frames: List of frames (numpy arrays)
        output_dir: Directory to save frames

    Returns:
        Path to the frames directory
    """
    os.makedirs(output_dir, exist_ok=True)

    for i, frame in enumerate(frames):
        # Convert to BGR for OpenCV
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Save frame
        frame_path = os.path.join(output_dir, f"frame_{i:04d}.jpg")
        cv2.imwrite(frame_path, frame_bgr)

    print(f"Individual frames saved to {output_dir}")

    return output_dir


def main():
    """Main function for the CLI."""
    # Parse command line arguments
    args = parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Load model
    model = load_model_safely(args.model_path)
    model.summary()

    # Find the last convolutional layer
    last_conv_layer_name = find_last_conv_layer(model)
    if not last_conv_layer_name:
        print("Could not find a convolutional layer in the model.")
        return

    print(f"Using last convolutional layer: {last_conv_layer_name}")

    # Find images
    image_paths = find_images(args.data_path)
    if not image_paths:
        print(f"No images found in {args.data_path}")
        return

    # Load metadata
    metadata = load_metadata(args.data_path)

    # Parse exclude regions if provided
    exclude_regions = None
    if args.exclude_regions:
        exclude_regions = []
        for region_str in args.exclude_regions.split('|'):
            coords = [int(x) for x in region_str.split(',')]
            if len(coords) == 4:
                exclude_regions.append(coords)

    # Process images
    frames = process_images(
        image_paths=image_paths,
        model=model,
        last_conv_layer_name=last_conv_layer_name,
        metadata=metadata,
        stride=args.stride,
        max_frames=args.max_frames,
        alpha=args.alpha,
        exclude_regions=exclude_regions
    )

    if not frames:
        print("No frames were processed successfully.")
        return

    # Create and save the video
    video_path = os.path.join(args.output_dir, f"{args.video_name}.mp4")
    backup_path = os.path.join(
        args.output_dir,
        f"{args.video_name}_backup.mp4")

    create_video(frames, video_path, fps=args.fps)
    create_video(frames, backup_path, fps=args.fps)

    # Save individual frames
    frames_dir = os.path.join(args.output_dir, f"{args.video_name}_frames")
    save_frames(frames, frames_dir)

    print("Grad-CAM visualization complete!")


if __name__ == "__main__":
    main()
