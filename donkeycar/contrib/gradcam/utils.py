"""
Utility functions for Grad-CAM visualization.

This module provides helper functions for generating Grad-CAM visualizations
for DonkeyCar neural networks.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import cv2
import tensorflow as tf


def find_last_conv_layer(model):
    """Find the name of the last convolutional layer in the model."""
    print("Searching for last convolutional layer")

    # Try to find the last convolutional layer
    last_conv_layer = None
    for layer in model.layers:
        if 'conv' in layer.name.lower():
            last_conv_layer = layer.name
            print(f"Found convolutional layer: {layer.name}")

    if last_conv_layer:
        print(f"Using {last_conv_layer} as the last convolutional layer")
        return last_conv_layer

    # Fallback logic for alternative layer types
    print("No layer with 'conv' in name found, looking for alternatives")
    for layer in model.layers:
        # Try to find layers that might be convolutional but named differently
        if hasattr(layer, 'kernel_size'):
            last_conv_layer = layer.name
            print(f"Found alternative convolutional layer: {layer.name}")
            break

    if not last_conv_layer:
        print("WARNING - No convolutional layer found in model!")
        if len(model.layers) > 1:
            # Try second-to-last layer as fallback
            last_conv_layer = model.layers[-2].name
            print(f"Using {last_conv_layer} as fallback layer")
        else:
            # Last resort
            last_conv_layer = model.layers[0].name
            print(f"Using first layer {last_conv_layer} as last resort")

    return last_conv_layer


def make_gradcam_heatmap(
        img_array,
        model,
        last_conv_layer_name,
        pred_index=None):
    """
    Generate Grad-CAM heatmap.

    Args:
        img_array: Input image array (preprocessed)
        model: Keras model
        last_conv_layer_name: Name of the last conv layer
        pred_index: Index for prediction (None for regression models)

    Returns:
        heatmap: Generated heatmap
    """
    try:
        # Create a model for extracting features from the last conv layer
        grad_model = tf.keras.models.Model(
            inputs=model.inputs, outputs=[
                model.get_layer(last_conv_layer_name).output, model.output])

        # Compute gradients with respect to the last conv layer
        with tf.GradientTape() as tape:
            last_conv_layer_output, preds = grad_model(img_array)

            # Handle different prediction formats (multiple outputs)
            if isinstance(preds, list):
                # Use the first output (steering angle)
                target_output = preds[0]
                # Steering is usually a single value
                if len(target_output.shape) > 1:
                    target_output = target_output[:, 0]
            else:
                target_output = preds
                # Classification models might need an index
                if pred_index is not None and len(target_output.shape) > 1:
                    target_output = target_output[:, pred_index]

        # Calculate gradients
        grads = tape.gradient(target_output, last_conv_layer_output)

        # Take the mean gradient over batch dimension
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        # Multiply each channel by its importance weight
        last_conv_layer_output = last_conv_layer_output.numpy()[0]
        pooled_grads = pooled_grads.numpy()

        for i in range(pooled_grads.shape[-1]):
            last_conv_layer_output[:, :, i] *= pooled_grads[i]

        # Average over channels to get the heatmap
        heatmap = np.mean(last_conv_layer_output, axis=-1)

        # Apply ReLU to the heatmap (only keep positive contributions)
        heatmap = np.maximum(heatmap, 0)

        # Normalize between 0 and 1 if the heatmap has a maximum
        if np.max(heatmap) > 0:
            heatmap = heatmap / np.max(heatmap)

        return heatmap

    except Exception as e:
        print(f"ERROR in make_gradcam_heatmap: {str(e)}")
        import traceback
        traceback.print_exc()

        # Create a blank heatmap as fallback
        h, w = img_array.shape[1:3]
        print(f"Creating blank heatmap of shape ({h}, {w})")
        return np.zeros((h, w))


def create_gradcam_visualization(img, heatmap, alpha=0.5, prediction=None,
                                 exclude_regions=None):
    """
    Create visualization with Grad-CAM heatmap overlay.

    Args:
        img: Original RGB image
        heatmap: Generated Grad-CAM heatmap
        alpha: Transparency of the heatmap overlay
        prediction: Prediction text to display (e.g. steering angle)
        exclude_regions: List of regions to exclude from heatmap visualization,
                        each as [x1, y1, x2, y2]

    Returns:
        superimposed_img: Image with heatmap overlay
    """
    # Resize heatmap to match image dimensions
    heatmap = cv2.resize(heatmap, (img.shape[1], img.shape[0]))

    # Convert to RGB
    heatmap = np.uint8(255 * heatmap)

    # Apply colormap
    heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

    # Superimpose heatmap on original image
    superimposed_img = cv2.addWeighted(
        cv2.cvtColor(img, cv2.COLOR_RGB2BGR),
        1.0 - alpha,
        heatmap,
        alpha,
        0
    )

    # Convert back to RGB
    superimposed_img = cv2.cvtColor(superimposed_img, cv2.COLOR_BGR2RGB)

    # Restore original image in excluded regions
    if exclude_regions:
        for region in exclude_regions:
            x1, y1, x2, y2 = region
            # Make sure coordinates are within image boundaries
            x1 = max(0, min(x1, img.shape[1] - 1))
            y1 = max(0, min(y1, img.shape[0] - 1))
            x2 = max(0, min(x2, img.shape[1]))
            y2 = max(0, min(y2, img.shape[0]))

            # Copy original image to the excluded region
            superimposed_img[y1:y2, x1:x2] = img[y1:y2, x1:x2]

    # Add prediction text if provided
    if prediction is not None:
        # Convert back to BGR for OpenCV text drawing
        draw_img = cv2.cvtColor(superimposed_img, cv2.COLOR_RGB2BGR)
        cv2.putText(
            draw_img,
            str(prediction),
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )
        # Convert back to RGB
        superimposed_img = cv2.cvtColor(draw_img, cv2.COLOR_BGR2RGB)

    return superimposed_img


def parse_exclude_regions(regions_str):
    """
    Parse the exclude_regions string format into a list of region coordinates.

    Args:
        regions_str: String with format "x1,y1,x2,y2;x1,y1,x2,y2;..."

    Returns:
        List of regions as [x1, y1, x2, y2] lists
    """
    if not regions_str:
        return None

    regions = []
    try:
        region_strs = regions_str.split(';')
        for region_str in region_strs:
            coords = [int(x) for x in region_str.split(',')]
            if len(coords) == 4:
                regions.append(coords)
    except Exception as e:
        print(f"Error parsing exclude_regions: {e}")
        return None

    return regions


def create_video(frames, output_path, fps=30):
    """
    Create a video from a list of frames.

    Args:
        frames: List of image frames
        output_path: Path to save the output video
        fps: Frames per second

    Returns:
        True if successful, False otherwise
    """
    if not frames:
        print("No frames to create video from!")
        return False

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Get dimensions from first frame
    h, w = frames[0].shape[:2]

    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    if not out.isOpened():
        print(f"Failed to open video writer for {output_path}")
        return False

    # Write frames to video
    for i, frame in enumerate(frames):
        out.write(frame)
        if (i + 1) % 20 == 0 or i == 0 or i == len(frames) - 1:
            print(f"Saved frame {i+1}/{len(frames)} to video")

    # Release the video writer
    out.release()
    print(f"Video saved to {output_path}")
    return True
