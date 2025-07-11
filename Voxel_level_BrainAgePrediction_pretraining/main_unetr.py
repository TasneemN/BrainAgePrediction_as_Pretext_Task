"""
main_unetr.py

Entry point for voxel-level brain age prediction training using the UNETR architecture.

Main features:
- Sets up the environment, device, and Weights & Biases (wandb) experiment tracking.
- Initializes the 3D UNETR model for brain age prediction.
- Loads training, validation, and test datasets and dataloaders.
- Configures optimizer and learning rate scheduler.
- Supports resuming training from the last saved checkpoint.
- Runs the full training loop and evaluates the model on the test set.

Functions:
    main():
        Initializes all components, runs training, and performs final testing.
"""

import os
import torch
import wandb
from monai.config import print_config
from monai.networks.nets import UNETR

from transforms import *
from load_data import *
from loss import *
from train import *
from testfunction import *
from testfunction import test
from config import (
    UNETR_OUTPUT_DIR, UNETR_PROJECT_NAME,
    FULL_DATA_CSV, TEST_CSV,
    UNETR_OPTIMIZER_CLASS, UNETR_OPTIMIZER_PARAMS,
    UNETR_SCHEDULER_CLASS, UNETR_SCHEDULER_PARAMS,
    UNETR_MAX_EPOCHS
)   

print_config()
# Set the PYTORCH_CUDA_ALLOC_CONF to avoid memory fragmentation
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

# Set up Weights & Biases
if wandb.run is None:
    wandb.init(project=UNETR_PROJECT_NAME, settings=wandb.Settings(start_method="fork", _service_wait=300))
    wandb.run.name = 'x'

# Set CUDA launch blocking to help with debugging
torch.backends.cudnn.benchmark = True
#CUDA_LAUNCH_BLOCKING = 1
os.environ['TORCH_USE_CUDA_DSA'] = '1'
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def main():
    """
    Main function to initialize the model, load data, and run training and testing phases.

    Returns:
        None
    """
    # Specify the name of the directory to save models and logs
    directory_name = UNETR_OUTPUT_DIR
    os.makedirs(directory_name, exist_ok=True)

    # Initialize the UNet model for 3D input of size (128, 160, 128)
    model = UNETR(
        spatial_dims=3,  # 3D input for dimensions (128, 160, 128)
        in_channels=1,   # Number of input channels
        out_channels=1,  # Number of output channels
        img_size=(128, 160, 128)  # Input image size
    )


    # Use DataParallel if multiple GPUs are available
    model = torch.nn.DataParallel(model).to(device)
    # Initialize optimizer and scheduler from config
    optimizer = UNETR_OPTIMIZER_CLASS(model.parameters(), **UNETR_OPTIMIZER_PARAMS)
    scheduler = UNETR_SCHEDULER_CLASS(optimizer, **UNETR_SCHEDULER_PARAMS)
    max_epochs = UNETR_MAX_EPOCHS
    # Load the last model weights (if available)
    model, optimizer, scheduler, start_epoch, last_val_loss, best_val_loss = load_last_model(model, optimizer, scheduler, directory_name)

   # Call the load_data function to create datasets and dataloaders
    ds_train, train_loader, ds_val, val_loader, ds_test, test_loader = load_data(test_set_path=TEST_CSV, full_data_path=FULL_DATA_CSV)

    # Start training
    train(train_loader, val_loader, model, optimizer, scheduler, max_epochs, directory_name, start_epoch=start_epoch)

    # Test the trained model
    test(test_loader, model, directory_name, TEST_CSV)

if __name__ == "__main__":
    if torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
        print("CUDA is not available. Using CPU.")
    
    main()
