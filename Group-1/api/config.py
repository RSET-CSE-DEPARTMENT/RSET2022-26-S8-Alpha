import os
import torch
from torchvision import transforms, datasets

# ================== PATHS ==================
EFFICIENTNET_PTH = r"D:\project\efficientnet_model_final.pth"
VIT_PTH = r"D:\project\vit_model_final.pth"
TRAIN_DATASET_PATH = r"D:\project\data\cnn_dataset\train"
CORRECTED_IMAGES_PATH = r"D:\project\corrected_images"

# ================== DEVICE ==================
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ================== GET CLASS MAPPING ==================
def get_class_mapping():
    """Get actual class mapping used during training"""
    temp_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
    ])
    
    train_dataset = datasets.ImageFolder(root=TRAIN_DATASET_PATH, transform=temp_transform)
    print(f"✓ Training class mapping: {train_dataset.class_to_idx}")
    print(f"✓ Class names: {train_dataset.classes}")
    return train_dataset.class_to_idx, train_dataset.classes

CLASS_MAPPING, CLASS_NAMES = get_class_mapping()

# FAKE class is at index 0, REAL at index 1
FAKE_IDX = 0
REAL_IDX = 1

# ================== IMAGE TRANSFORMS ==================
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])