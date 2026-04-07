import torch
import timm
import torch.nn as nn
import clip
import os
from ultralytics import YOLO
from api.config import DEVICE, EFFICIENTNET_PTH, VIT_PTH, CLASS_NAMES

print("🔧 Loading models...")

# ================== LOAD EFFICIENTNET ==================
print("\nLoading EfficientNet-B2 model...")
eff = timm.create_model('efficientnet_b2', pretrained=True)

# Freeze early layers
for param in eff.parameters():
    param.requires_grad = False

# Unfreeze last few layers
for param in eff.blocks[-3:].parameters():
    param.requires_grad = True

# Replace classifier
num_ftrs_eff = eff.classifier.in_features
eff.classifier = nn.Sequential(
    nn.Dropout(0.3),
    nn.Linear(num_ftrs_eff, 512),
    nn.ReLU(),
    nn.BatchNorm1d(512),
    nn.Dropout(0.2),
    nn.Linear(512, 256),
    nn.ReLU(),
    nn.BatchNorm1d(256),
    nn.Dropout(0.1),
    nn.Linear(256, 2)
)

# ================== LOAD VIT ==================
print("\nLoading Vision Transformer (ViT-Base) model...")
vit = timm.create_model('vit_base_patch16_224', pretrained=True)

# Freeze early layers
for param in vit.parameters():
    param.requires_grad = False

# Unfreeze last transformer blocks
for param in vit.blocks[-4:].parameters():
    param.requires_grad = True

# Replace classifier
num_ftrs_vit = vit.head.in_features
vit.head = nn.Sequential(
    nn.LayerNorm(num_ftrs_vit),
    nn.Dropout(0.5),
    nn.Linear(num_ftrs_vit, 512),
    nn.GELU(),
    nn.LayerNorm(512),
    nn.Dropout(0.3),
    nn.Linear(512, 256),
    nn.GELU(),
    nn.LayerNorm(256),
    nn.Dropout(0.2),
    nn.Linear(256, 2)
)

# Load model weights
try:
    eff_checkpoint = torch.load(EFFICIENTNET_PTH, map_location=DEVICE, weights_only=False)
    vit_checkpoint = torch.load(VIT_PTH, map_location=DEVICE, weights_only=False)
    
    if 'model_state_dict' in eff_checkpoint:
        eff.load_state_dict(eff_checkpoint['model_state_dict'])
    else:
        eff.load_state_dict(eff_checkpoint)
    
    if 'model_state_dict' in vit_checkpoint:
        vit.load_state_dict(vit_checkpoint['model_state_dict'])
    else:
        vit.load_state_dict(vit_checkpoint)
    
    print(f"✓ EfficientNet-B2 loaded successfully")
    print(f"✓ ViT model loaded successfully")
except Exception as e:
    print(f"Error loading models: {e}")
    exit(1)

eff.to(DEVICE).eval()
vit.to(DEVICE).eval()

# ================== LOAD MISMATCH DETECTION MODELS ==================
print("\nLoading Mismatch Detection models...")

# Load CLIP
clip_model, clip_preprocess = None, None
try:
    clip_model, clip_preprocess = clip.load("ViT-B/32", device=DEVICE)
    clip_model.eval()
    print("✓ CLIP loaded successfully")
except Exception as e:
    print(f" CLIP loading error: {e}")

# Load YOLO
yolo_model = None
try:
    yolo_model_path = r"D:\project\runs\classify\shoe_watch_final\weights\best.pt"
    if os.path.exists(yolo_model_path):
        yolo_model = YOLO(yolo_model_path)
        print(f"✓ YOLO loaded successfully: {os.path.basename(yolo_model_path)}")
    else:
        print(f"  YOLO model not found at: {yolo_model_path}")
except Exception as e:
    print(f"  YOLO loading error: {e}")

print("  All models loaded successfully")