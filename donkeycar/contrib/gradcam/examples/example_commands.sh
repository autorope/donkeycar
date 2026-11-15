#!/bin/bash
# Example commands for using DonkeyCar Grad-CAM visualization

# Basic usage - Generate Grad-CAM visualizations for a model and dataset
python -m gradcam.cli gradcam \
  --model_path /path/to/your/model.h5 \
  --data_path /path/to/your/data \
  --output_dir gradcam_output

# Exclude top half of the image (e.g., to ignore the sky) - 160x120 images
python -m gradcam.cli gradcam \
  --model_path /path/to/your/model.h5 \
  --data_path /path/to/your/data \
  --exclude_regions "0,0,160,60" \
  --output_dir gradcam_output_top_excluded

# Exclude top half of the image - 640x480 images
python -m gradcam.cli gradcam \
  --model_path /path/to/your/model.h5 \
  --data_path /path/to/your/data \
  --exclude_regions "0,0,640,240" \
  --output_dir gradcam_output_top_excluded

# Process only the first 150 frames at 20 FPS
python -m gradcam.cli gradcam \
  --model_path /path/to/your/model.h5 \
  --data_path /path/to/your/data \
  --max_frames 150 \
  --fps 20 \
  --output_dir gradcam_output

# Fix video glitches if they occur
python -m gradcam.cli fix \
  --frames_dir gradcam_output/grad_cam_visualization_frames \
  --output_path gradcam_output/fixed_grad_cam.avi \
  --fps 20

# Using the original scripts directly
python true_gradcam.py \
  --model_path /path/to/your/model.h5 \
  --data_path /path/to/your/data \
  --output_dir gradcam_output

# Fix glitches using the better_fix_gradcam.py script
python better_fix_gradcam.py \
  --frames_dir gradcam_output/grad_cam_visualization_frames \
  --output_path gradcam_output/robust_fixed_grad_cam.avi 