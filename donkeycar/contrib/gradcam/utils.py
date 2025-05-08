"""
Utility functions for Grad-CAM visualization.
"""

import os
import cv2
import numpy as np
import tensorflow as tf


def find_last_conv_layer(model):
    """Find the name of the last convolutional layer in the model."""
    for layer in reversed(model.layers):
        # Check if the layer is a convolutional layer
        if isinstance(layer, tf.keras.layers.Conv2D) or 'conv' in layer.name.lower():
            return layer.name
    
    # If no conv layer is found, return None
    return None


def make_gradcam_heatmap(img_array, model, last_conv_layer_name, pred_index=None):
    """
    Generate a Grad-CAM heatmap for a specific prediction index.
    
    Args:
        img_array: Input image as a preprocessed array
        model: The model to analyze
        last_conv_layer_name: Name of the last convolutional layer
        pred_index: Index of the prediction to visualize (for multi-output models)
        
    Returns:
        The generated heatmap as a 2D numpy array
    """
    # Create a model that maps the input image to the activations of the last conv layer
    # and the output predictions
    grad_model = tf.keras.models.Model(
        inputs=model.inputs,
        outputs=[model.get_layer(last_conv_layer_name).output, model.output]
    )
    
    # Compute the gradient of the output with respect to the last conv layer
    with tf.GradientTape() as tape:
        last_conv_layer_output, preds = grad_model(img_array)
        
        # Handle different prediction formats (multiple outputs, etc.)
        if isinstance(preds, list):
            # Use the first output (steering angle)
            target_output = preds[0]
            if len(target_output.shape) > 1:
                target_output = target_output[:, 0] if pred_index is None else target_output[:, pred_index]
        else:
            target_output = preds
            if len(target_output.shape) > 1 and pred_index is not None:
                target_output = target_output[:, pred_index]
    
    # Gradient of the predicted output with respect to the last conv layer output
    grads = tape.gradient(target_output, last_conv_layer_output)
    
    # Global average pooling of the gradients
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    
    # Weight the channels by their importance and create the heatmap
    last_conv_layer_output = last_conv_layer_output.numpy()[0]
    pooled_grads = pooled_grads.numpy()
    
    for i in range(pooled_grads.shape[-1]):
        last_conv_layer_output[:, :, i] *= pooled_grads[i]
        
    # Average over all channels to get the heatmap
    heatmap = np.mean(last_conv_layer_output, axis=-1)
    
    # Apply ReLU to the heatmap (only keep positive contributions)
    heatmap = np.maximum(heatmap, 0)
    
    # Normalize between 0 and 1 if the heatmap has a non-zero maximum
    if np.max(heatmap) > 0:
        heatmap = heatmap / np.max(heatmap)
    
    return heatmap


def create_gradcam_visualization(img, heatmap, alpha=0.5, prediction=None, exclude_regions=None):
    """
    Create visualization with Grad-CAM heatmap overlay.
    
    Args:
        img: Original RGB image
        heatmap: Generated Grad-CAM heatmap
        alpha: Transparency of the heatmap overlay
        prediction: Prediction text to display (e.g. steering angle)
        exclude_regions: List of regions to exclude from heatmap visualization,
                        each as [x1, y1, x2, y2] where x1,y1 is top-left and
                        x2,y2 is bottom-right corner
                        
    Returns:
        Visualization image with heatmap overlay
    """
    # Ensure img is in the right format
    if img.dtype != np.uint8:
        if np.max(img) <= 1.0:
            img = (img * 255).astype(np.uint8)
        else:
            img = img.astype(np.uint8)
    
    # Resize heatmap to match image size
    heatmap_resized = cv2.resize(heatmap, (img.shape[1], img.shape[0]))
    
    # Apply colormap to the heatmap
    heatmap_colored = np.uint8(255 * heatmap_resized)
    heatmap_colored = cv2.applyColorMap(heatmap_colored, cv2.COLORMAP_JET)
    
    # Overlay the heatmap on the original image
    superimposed_img = cv2.addWeighted(img, 1.0, heatmap_colored, alpha, 0)
    
    # Apply excluded regions if provided
    if exclude_regions is not None and len(exclude_regions) > 0:
        for region in exclude_regions:
            x1, y1, x2, y2 = region
            # Ensure coordinates are within image boundaries
            x1 = max(0, min(x1, img.shape[1]-1))
            y1 = max(0, min(y1, img.shape[0]-1))
            x2 = max(0, min(x2, img.shape[1]))
            y2 = max(0, min(y2, img.shape[0]))
            
            # Copy original image to the excluded region
            superimposed_img[y1:y2, x1:x2] = img[y1:y2, x1:x2]
    
    # Add prediction text if provided
    if prediction is not None:
        # Convert prediction to string if it's not already
        if not isinstance(prediction, str):
            if isinstance(prediction, (list, np.ndarray)) and len(prediction) > 0:
                # Handle array-like predictions
                if isinstance(prediction[0], (list, np.ndarray)) and len(prediction[0]) > 0:
                    pred_value = prediction[0][0]
                else:
                    pred_value = prediction[0]
                prediction_text = f"Steering: {pred_value:.4f}"
            else:
                prediction_text = f"Steering: {prediction:.4f}"
        else:
            prediction_text = prediction
        
        # Add text to the image
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            superimposed_img,
            prediction_text,
            (10, 30),
            font,
            0.8,
            (255, 255, 255),
            2
        )
    
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
        if (i+1) % 20 == 0 or i == 0 or i == len(frames)-1:
            print(f"Saved frame {i+1}/{len(frames)} to video")
    
    # Release the video writer
    out.release()
    print(f"Video saved to {output_path}")
    return True 