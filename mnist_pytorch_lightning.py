################################################
# train mnist classifier with lightening pytorch
# Author: David Dov
# Date: 16/6/22
# Credit: https://pytorch-lightning.readthedocs.io/en/latest/starter/introduction.html
###############################################

import os
import torch
from pytorch_lightning import LightningModule, Trainer, LightningDataModule, seed_everything
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, random_split
from torchmetrics import Accuracy
from torchvision import transforms
from torchvision.datasets import MNIST
from pytorch_lightning.callbacks import ModelCheckpoint

### Set seeds for reproductability
seed_everything(0, workers=True) # seeds for torch, numpy, random
# torch.use_deterministic_algorithms() 


params = {}
params['data_path'] = "."
params['AVAIL_GPUS'] = min(0, torch.cuda.device_count())
params['batch_size'] = 64
params['max_epoch'] = 20
params['lr'] = 2e-4


class LitMNIST(LightningModule):
    def __init__(self, params):
        super().__init__()

        self.params = params

        # Hardcoded parameters
        hidden_size = 64
        num_classes = 10
        channels, width, height = (1, 28, 28)
        
        # Define model
        self.model = nn.Sequential(
            nn.Flatten(),
            nn.Linear(channels * width * height, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, num_classes),
        )

        self.val_accuracy = Accuracy()
        self.test_accuracy = Accuracy()

    def forward(self, x):
        x = self.model(x)
        return F.log_softmax(x, dim=1)

    def training_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x) # equivalent to model(x) in pytorch
        loss = F.nll_loss(logits, y)
        self.log("train_loss", loss, prog_bar=True)
        return loss

    def validation_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x) # equivalent to model(x) in pytorch
        loss = F.nll_loss(logits, y)
        preds = torch.argmax(logits, dim=1)
        self.val_accuracy(preds, y)

        # Calling self.log will surface up scalars for you in TensorBoard
        self.log("val_loss", loss, prog_bar=True)
        self.log("val_acc", self.val_accuracy, prog_bar=True)
        return loss

    def test_step(self, batch, batch_idx):
        x, y = batch
        logits = self(x) # equivalent to model(x) in pytorch
        loss = F.nll_loss(logits, y)
        preds = torch.argmax(logits, dim=1)
        self.test_accuracy(preds, y)

        # Calling self.log will surface up scalars for you in TensorBoard
        self.log("test_loss", loss, prog_bar=True)
        self.log("test_acc", self.test_accuracy, prog_bar=True)
        return loss

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=self.params['lr'])
        return optimizer



class MNISTDataModule(LightningDataModule):
    def __init__(self, params):
        super().__init__()
        self.params = params
        self.transform = transforms.Compose([transforms.ToTensor(),
                                             transforms.Normalize((0.1307,), (0.3081,))])
        
    def prepare_data(self): # single core processing
        # download
        MNIST(self.params['data_path'], train=True, download=True)
        MNIST(self.params['data_path'], train=False, download=True)

    def setup(self, stage=None):

        # Assign train/val datasets for use in dataloaders
        if stage == "fit" or stage is None:
            mnist_full = MNIST(self.params['data_path'], train=True, transform=self.transform)
            self.mnist_train, self.mnist_val = random_split(mnist_full, [55000, 5000])

        # Assign test dataset for use in dataloader(s)
        if stage == "test" or stage is None:
            self.mnist_test = MNIST(self.params['data_path'], train=False, transform=self.transform)

    def train_dataloader(self):
        return DataLoader(self.mnist_train, batch_size=params['batch_size'])

    def val_dataloader(self):
        return DataLoader(self.mnist_val, batch_size=params['batch_size'])

    def test_dataloader(self):
        return DataLoader(self.mnist_test, batch_size=params['batch_size'])


if __name__ == "__main__":
    # Initialize the model and datamodule
    model = LitMNIST(params)
    mnist_data_module = MNISTDataModule(params)
    checkpoint_callback = ModelCheckpoint(monitor="val_acc", mode="max")
    # Initialize a trainer
    trainer = Trainer(
        callbacks=[checkpoint_callback],
        deterministic=True,
        gpus=params['AVAIL_GPUS'],
        max_epochs=params['max_epoch'],
        progress_bar_refresh_rate=20,
    )

    # Train the model
    trainer.fit(model, mnist_data_module)

    # Test the model
    trainer.test(model, mnist_data_module)

    print('Done training and evaluating MNIST')

    ### View results in tensorboard:  ######
    # in cmd: activate environment
    # in cmd: tensorboard --logdir=lightning_logs --port=6006 
    # in the web browser: localhost:6006