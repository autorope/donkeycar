import pytorch_lightning as pl
import torchvision.models as models
import torch.nn as nn
import torch.nn.functional as F
import torch
import numpy as np
import torch.optim as optim
from donkeycar.parts.pytorch.torch_data import get_default_transform


def load_resnet18(num_classes=2):
    # Load the pre-trained model (on ImageNet)
    model = models.resnet18(pretrained=True)

    # Don't allow model feature extraction layers to be modified
    for layer in model.parameters():
        layer.requires_grad = False

    # Change the classifier layer
    model.fc = nn.Linear(512, 2)

    for param in model.fc.parameters():
        param.requires_grad = True

    return model


class ResNet18(pl.LightningModule):
    def __init__(self, input_shape=(128, 3, 224, 224), output_size=(2,)):
        super().__init__()

        # Used by PyTorch Lightning to print an example model summary
        self.example_input_array = torch.rand(input_shape)

        # Metrics
        self.train_mse = pl.metrics.MeanSquaredError()
        self.valid_mse = pl.metrics.MeanSquaredError()

        self.model = load_resnet18(num_classes=output_size[0])

        self.inference_transform = get_default_transform(for_inference=True)

        # Keep track of the loss history. This is useful for writing tests
        self.loss_history = []

    def forward(self, x):
        # Forward defines the prediction/inference action
        return self.model(x)

    def training_step(self, batch, batch_idx):
        x, y = batch
        logits = self.model(x)

        loss = F.l1_loss(logits, y)
        self.loss_history.append(loss)
        self.log("train_loss", loss)

        # Log Metrics
        self.train_mse(logits, y)
        self.log("train_mse", self.train_mse, on_step=False, on_epoch=True)

        return loss

    def validation_step(self, batch, batch_idx):
        x, y = batch
        logits = self.forward(x)
        loss = F.l1_loss(logits, y)

        self.log("val_loss", loss)

        # Log Metrics
        self.valid_mse(logits, y)
        self.log("valid_mse", self.valid_mse, on_step=False, on_epoch=True)

    def configure_optimizers(self):
        optimizer = optim.Adam(self.model.parameters(), lr=0.0001, weight_decay=0.0005)
        return optimizer

    def run(self, img_arr: np.ndarray, other_arr: np.ndarray = None):
        """
        Donkeycar parts interface to run the part in the loop.

        :param img_arr:     uint8 [0,255] numpy array with image data
        :param other_arr:   numpy array of additional data to be used in the
                            pilot, like IMU array for the IMU model or a
                            state vector in the Behavioural model
        :return:            tuple of (angle, throttle)
        """
        from PIL import Image

        pil_image = Image.fromarray(img_arr)
        tensor_image = self.inference_transform(pil_image)
        tensor_image = tensor_image.unsqueeze(0)

        # Result is (1, 2)
        result = self.forward(tensor_image)

        # Resize to (2,)
        result = result.reshape(-1)

        # Convert from being normalized between [0, 1] to being between [-1, 1]
        result = result * 2 - 1
        print("ResNet18 result: {}".format(result))
        return result
