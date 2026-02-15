# DonkeyCar Grad-CAM Visualization

A visualization tool for understanding and debugging DonkeyCar neural networks using Gradient-weighted Class Activation Mapping (Grad-CAM).

![Grad-CAM Example](docs/Screenshot%202025-05-08%20at%201.22.18%20PM.png)

## What is Grad-CAM?

Grad-CAM is a technique that produces visual explanations for decisions made by convolutional neural networks. It helps us understand which regions of an input image are important for the model's predictions.

For DonkeyCar models, this helps visualize:
- Which parts of the track the model is focusing on when making steering decisions
- Whether the model is looking at relevant features (lane lines, track edges) versus distractions
- How model attention changes in different driving scenarios

## Features

- Generate heatmap visualizations of model attention for any DonkeyCar TensorFlow model
- Selectively exclude regions of the image (sky, dashboard, etc.) to focus visualization
- Automatically create videos from image sequences to visualize model attention over time
- Support for different model architectures and input sizes
- Frame-consistency algorithms to prevent glitches in output videos

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/donkeycar-gradcam.git
cd donkeycar-gradcam

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```bash
# Basic usage
python true_gradcam.py --model_path /path/to/model.h5 --data_path /path/to/data --output_dir output

# Exclude top half of the image (e.g., to ignore the sky)
python true_gradcam.py --model_path /path/to/model.h5 --data_path /path/to/data --exclude_regions "0,0,160,60" --output_dir output

# Process only the first 150 frames at 20 FPS
python true_gradcam.py --model_path /path/to/model.h5 --data_path /path/to/data --max_frames 150 --fps 20 --output_dir output
```

## Command Line Arguments

### true_gradcam.py

- `--model_path`: Path to the trained model (.h5 file)
- `--data_path`: Path to the dataset directory containing images
- `--output_dir`: Directory to save visualization outputs
- `--max_frames`: Maximum number of frames to process (default: all)
- `--fps`: Frames per second for output video (default: 30)
- `--stride`: Process every Nth frame (default: 1)
- `--exclude_regions`: Regions to exclude from heatmap in format "x1,y1,x2,y2;x1,y1,x2,y2;..." (multiple regions separated by semicolons)
- `--video_name`: Base name for output video (default: "grad_cam_visualization")

## Common Use Cases

### Analyzing Track Following

Visualize where your model is focusing when following the track:

```bash
python true_gradcam.py --model_path models/track_following.h5 --data_path data/track_following --output_dir track_analysis
```

### Ignoring Irrelevant Sky Area

Exclude the top portion of the image to focus on the track:

```bash
# For 160x120 images (common in DonkeyCar)
python true_gradcam.py --model_path models/model.h5 --data_path data/images --exclude_regions "0,0,160,60" --output_dir track_focus

# For 640x480 images
python true_gradcam.py --model_path models/model.h5 --data_path data/images --exclude_regions "0,0,640,240" --output_dir track_focus
```

## How It Works

1. The script loads a trained DonkeyCar model
2. It processes images from your dataset one by one
3. For each image:
   - The model makes a prediction (steering angle, throttle)
   - Grad-CAM calculates gradients of the prediction with respect to the last convolutional layer
   - A heatmap is generated showing which regions influenced the prediction most
   - The heatmap is overlaid on the original image
4. All processed frames are combined into a video

## Integrating With Your Workflow

This tool can be integrated at different stages of your DonkeyCar development:

- **During training**: Periodically check model attention to ensure it's focusing on relevant features
- **After training**: Compare different models to see which ones focus better on the track
- **Debugging**: When your car behaves unexpectedly, visualize what it was "looking at"
- **Data cleaning**: Identify and remove problematic training data where attention is on irrelevant features

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 