"""
Command-line interface for DonkeyCar Grad-CAM visualization.
"""

import os
import sys
import argparse
import tensorflow as tf

from gradcam.utils import (
    find_last_conv_layer,
    make_gradcam_heatmap,
    create_gradcam_visualization,
    parse_exclude_regions,
    create_video
)


def load_model(model_path):
    """Load a TensorFlow/Keras model from file."""
    print(f"Loading model from {model_path}")
    try:
        model = tf.keras.models.load_model(model_path)
        model.summary()
        return model
    except Exception as e:
        print(f"Error loading model: {e}")
        return None


def find_images(data_path):
    """Find image files in the data directory."""
    import glob
    
    print(f"Searching for images in {data_path}")
    
    # Different image patterns to try
    patterns = [
        os.path.join(data_path, "**/images/*.jpg"),
        os.path.join(data_path, "*.jpg"),
        os.path.join(data_path, "**/*.jpg"),
        os.path.join(data_path, "**/images/*.jpeg"),
        os.path.join(data_path, "*.jpeg"),
        os.path.join(data_path, "**/*.jpeg"),
        os.path.join(data_path, "**/images/*.png"),
        os.path.join(data_path, "*.png"),
        os.path.join(data_path, "**/*.png")
    ]
    
    for pattern in patterns:
        image_paths = sorted(glob.glob(pattern, recursive=True))
        if image_paths:
            print(f"Found {len(image_paths)} images with pattern {pattern}")
            return image_paths
    
    print("No images found with any pattern")
    return []


def load_and_preprocess_image(image_path, input_width=160, input_height=120):
    """Load and preprocess an image for model prediction."""
    import cv2
    import numpy as np
    
    try:
        # Read image using OpenCV
        img = cv2.imread(image_path)
        if img is None:
            print(f"Could not read image {image_path}")
            return None, None
        
        # Store the original image for visualization
        original_img = img.copy()
        
        # Convert BGR to RGB for TensorFlow
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Resize image to the input size expected by the model
        img_rgb_resized = cv2.resize(img_rgb, (input_width, input_height))
        
        # Normalize image for model
        img_array = np.asarray(img_rgb_resized, dtype=np.float32) / 255.0
        
        # Expand dimensions to create a batch of size 1
        img_batch = np.expand_dims(img_array, axis=0)
        
        # For visualization, we'll keep the original image but convert to RGB
        original_img_rgb = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
        
        return original_img_rgb, img_batch
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None, None


def process_images_for_video(image_paths, model, stride=1, max_frames=None, exclude_regions=None, verbose=True):
    """Process a sequence of images and return frames for video."""
    # Limit the number of frames if specified
    if max_frames:
        print(f"Limiting to {max_frames} frames out of {len(image_paths)} available images")
        image_paths = image_paths[:max_frames]
    
    # Apply frame stride
    if stride > 1:
        image_paths = image_paths[::stride]
        print(f"Applied stride of {stride}, processing {len(image_paths)} frames")
    
    # Find the last convolutional layer
    last_conv_layer_name = find_last_conv_layer(model)
    if not last_conv_layer_name:
        print("Error: Could not find a convolutional layer in the model.")
        return []
    
    print(f"Using last convolutional layer: {last_conv_layer_name}")
    
    # Process images and compile frames for the video
    processed_frames = []
    
    for i, image_path in enumerate(image_paths):
        if verbose:
            print(f"Processing image {i+1}/{len(image_paths)}: {os.path.basename(image_path)}")
        
        # Load and preprocess the image
        original_img, img_preprocessed = load_and_preprocess_image(image_path)
        
        if original_img is None or img_preprocessed is None:
            print(f"Skipping image {i+1} due to processing error")
            continue
        
        # Get model predictions
        try:
            predictions = model.predict(img_preprocessed, verbose=0)
            
            # Different models may have different output formats
            if isinstance(predictions, list):
                steering = float(predictions[0][0][0])  # Extract steering prediction
                throttle = float(predictions[1][0][0]) if len(predictions) > 1 else 0.0
                prediction_text = f"Angle: {steering:.2f}, Throttle: {throttle:.2f}"
            else:
                steering = float(predictions[0][0])
                prediction_text = f"Angle: {steering:.2f}"
            
            # Generate Grad-CAM heatmap
            heatmap = make_gradcam_heatmap(img_preprocessed, model, last_conv_layer_name)
            
            # Create visualization
            visualization = create_gradcam_visualization(
                original_img, 
                heatmap, 
                alpha=0.6, 
                prediction=prediction_text,
                exclude_regions=exclude_regions
            )
            
            # Add the visualized frame to our collection
            processed_frames.append(visualization)
            
        except Exception as e:
            print(f"Error processing image {i+1}: {str(e)}")
    
    return processed_frames


def gradcam_visualization(args):
    """Main function for Grad-CAM visualization."""
    # Parse exclude regions if provided
    exclude_regions = parse_exclude_regions(args.exclude_regions)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Create frames directory
    frames_dir = os.path.join(args.output_dir, f"{args.video_name}_frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    # Load the model
    model = load_model(args.model_path)
    if model is None:
        return
    
    # Find images in the dataset
    image_paths = find_images(args.data_path)
    if not image_paths:
        return
    
    # Process images for video
    frames = process_images_for_video(
        image_paths, 
        model, 
        stride=args.stride, 
        max_frames=args.max_frames,
        exclude_regions=exclude_regions
    )
    
    if not frames:
        print("No frames were processed successfully.")
        return
    
    # Save individual frames
    for i, frame in enumerate(frames):
        frame_path = os.path.join(frames_dir, f"frame_{i:04d}.jpg")
        import cv2
        cv2.imwrite(frame_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        if (i+1) % 50 == 0 or i == 0 or i == len(frames)-1:
            print(f"Saved frame {i+1}/{len(frames)} as image")
    
    # Create the video
    output_video_path = os.path.join(args.output_dir, f"{args.video_name}.mp4")
    create_video(
        [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in frames],
        output_video_path,
        args.fps
    )
    
    print(f"All {len(frames)} frames saved to {frames_dir}")
    print(f"Video saved to {output_video_path}")


def fix_video_glitches(args):
    """Fix glitches in a Grad-CAM visualization video."""
    from collections import defaultdict
    import cv2
    import numpy as np
    import glob
    
    # Find all frame files
    frame_files = sorted(glob.glob(os.path.join(args.frames_dir, "frame_*.jpg")))
    if not frame_files:
        print(f"No frames found in {args.frames_dir}")
        return
    
    print(f"Analyzing {len(frame_files)} frames to detect scene changes...")
    
    # Take sample frames to identify potential different scenes
    samples = [0, len(frame_files)//3, 2*len(frame_files)//3, len(frame_files)-1]
    sample_frames = []
    
    for idx in samples:
        frame = cv2.imread(frame_files[idx])
        if frame is not None:
            # Convert to grayscale for simpler comparison
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Resize to very small for quick comparison
            small = cv2.resize(gray, (16, 12))
            sample_frames.append((small, frame_files[idx]))
    
    # Group frames into clusters
    clusters = defaultdict(list)
    reference_samples = [s[0] for s in sample_frames]
    
    # Analyze each frame
    for i, frame_path in enumerate(frame_files):
        if i % 10 == 0:
            print(f"Analyzing frame {i+1}/{len(frame_files)}")
            
        frame = cv2.imread(frame_path)
        if frame is None:
            continue
            
        # Find closest sample
        min_diff = float('inf')
        closest_idx = 0
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (16, 12))
        
        for j, ref in enumerate(reference_samples):
            diff = np.sum(np.abs(small.astype(float) - ref.astype(float)))
            if diff < min_diff:
                min_diff = diff
                closest_idx = j
        
        # Very high diff indicates a glitch or different scene
        if diff > 500000:
            clusters['glitch'].append((frame_path, diff))
        else:
            clusters[closest_idx].append((frame_path, diff))
    
    # Identify the main scene (most common cluster)
    main_cluster = max(clusters.items(), key=lambda x: len(x[1]) if x[0] != 'glitch' else 0)[0]
    
    print(f"Found {len(clusters)} frame clusters")
    for cluster, frames in clusters.items():
        if cluster == 'glitch':
            print(f"  Glitch frames: {len(frames)}")
        else:
            print(f"  Cluster {cluster}: {len(frames)} frames")
    
    print(f"Main scene is cluster {main_cluster} with {len(clusters[main_cluster])} frames")
    
    # Sort the main cluster frames by original frame index
    main_frames = sorted(clusters[main_cluster], 
                         key=lambda x: int(os.path.basename(x[0]).split('_')[1].split('.')[0]))
    
    if not main_frames:
        print("No frames in main cluster!")
        return
    
    # Get dimensions from first frame
    first_frame = cv2.imread(main_frames[0][0])
    height, width = first_frame.shape[:2]
    
    # Create video from main frames
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(args.output_path, fourcc, args.fps, (width, height))
    
    for i, (frame_path, _) in enumerate(main_frames):
        frame = cv2.imread(frame_path)
        out.write(frame)
        if (i+1) % 10 == 0 or i == 0 or i == len(main_frames)-1:
            print(f"Added frame {i+1}/{len(main_frames)} to video")
    
    out.release()
    print(f"Fixed video saved to {args.output_path}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description='DonkeyCar Grad-CAM Visualization')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Parser for gradcam command
    gradcam_parser = subparsers.add_parser('gradcam', help='Generate Grad-CAM visualizations')
    gradcam_parser.add_argument('--model_path', type=str, required=True, 
                              help='Path to the model file (.h5)')
    gradcam_parser.add_argument('--data_path', type=str, required=True, 
                              help='Path to the data directory containing images')
    gradcam_parser.add_argument('--output_dir', type=str, default='gradcam_output', 
                              help='Directory to save output files')
    gradcam_parser.add_argument('--max_frames', type=int, default=None, 
                              help='Maximum number of frames to process (default: all)')
    gradcam_parser.add_argument('--fps', type=int, default=20, 
                              help='Frames per second for output video')
    gradcam_parser.add_argument('--stride', type=int, default=1, 
                              help='Stride for processing images (1 = every image)')
    gradcam_parser.add_argument('--video_name', type=str, default='grad_cam_visualization', 
                              help='Base name for output video')
    gradcam_parser.add_argument('--exclude_regions', type=str, default=None, 
                              help='Regions to exclude from heatmap in format "x1,y1,x2,y2;x1,y1,x2,y2;..."')
    
    # Parser for fix command
    fix_parser = subparsers.add_parser('fix', help='Fix glitches in Grad-CAM visualization videos')
    fix_parser.add_argument('--frames_dir', type=str, required=True,
                          help='Directory containing the individual frames')
    fix_parser.add_argument('--output_path', type=str, required=True,
                          help='Path for the fixed output video')
    fix_parser.add_argument('--fps', type=int, default=20,
                          help='Frames per second for output video')
    
    args = parser.parse_args()
    
    if args.command == 'gradcam':
        gradcam_visualization(args)
    elif args.command == 'fix':
        fix_video_glitches(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 