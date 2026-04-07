import torch
import numpy as np
import cv2
from api.config import DEVICE

class EfficientNetGradCAM:
    """Grad-CAM for EfficientNet (CNN)"""
    def __init__(self, model):
        self.model = model
        self.model.eval()
        self.gradients = None
        self.activations = None
        self._register_hooks()
    
    def _get_target_layer(self):
        """Find the last convolutional layer"""
        target_layer = None
        layer_name = ""
        
        # Search for conv layers
        for name, module in self.model.named_modules():
            if isinstance(module, torch.nn.Conv2d):
                target_layer = module
                layer_name = name
        
        print(f"  Using layer for Grad-CAM: {layer_name}")
        return target_layer
    
    def _register_hooks(self):
        target_layer = self._get_target_layer()
        
        if target_layer is None:
            print("    Could not find conv layer, using fallback")
            return
        
        def forward_hook(module, input, output):
            self.activations = output.detach()
        
        def backward_hook(module, grad_input, grad_output):
            if grad_output[0] is not None:
                self.gradients = grad_output[0].detach()
        
        target_layer.register_forward_hook(forward_hook)
        target_layer.register_full_backward_hook(backward_hook)
    
    def compute_cam(self, input_tensor, target_class_idx):
        """Compute Grad-CAM for specific class"""
        self.model.zero_grad()
        
        # Forward pass
        input_copy = input_tensor.clone().requires_grad_(True)
        output = self.model(input_copy)
        
        # Backward pass for target class
        target = output[0, target_class_idx]
        target.backward(retain_graph=True)
        
        if self.gradients is None or self.activations is None:
            print("    Gradients not captured, using input gradients")
            grad = input_copy.grad[0].cpu().numpy()
            grad_magnitude = np.abs(grad).sum(axis=0)
            cam = cv2.resize(grad_magnitude, (224, 224))
        else:
            # Compute Grad-CAM
            gradients = self.gradients.cpu().numpy()[0]
            activations = self.activations.cpu().numpy()[0]
            
            # Global average pooling of gradients
            weights = np.mean(gradients, axis=(1, 2))
            
            # Weighted combination
            cam = np.zeros(activations.shape[1:], dtype=np.float32)
            for i, w in enumerate(weights):
                cam += w * activations[i]
            
            # Apply ReLU
            cam = np.maximum(cam, 0)
            
            # Resize
            cam = cv2.resize(cam, (224, 224))
        
        # Normalize
        cam_min, cam_max = cam.min(), cam.max()
        if cam_max - cam_min > 1e-8:
            cam = (cam - cam_min) / (cam_max - cam_min)
        else:
            cam = np.ones_like(cam) * 0.5
        
        # Smooth
        cam = cv2.GaussianBlur(cam, (11, 11), 0)
        
        return cam


class ViTVisualizer:
    """Professional ViT patch importance visualization"""
    def __init__(self, model):
        self.model = model
        self.model.eval()
    
    def get_patch_importance_with_features(self, image_tensor, target_class_idx):
        """Get patch importance with proper normalization and feature analysis"""
        # Forward pass with gradient tracking
        input_copy = image_tensor.clone().requires_grad_(True)
        output = self.model(input_copy)
        
        # Backward pass
        target = output[0, target_class_idx]
        target.backward()
        
        # Get gradient from input
        grad = input_copy.grad[0].cpu().numpy()
        
        # ViT uses 14x14 patches for 224x224 image
        patch_size = 16
        grid_size = 14
        
        # Create patch importance grid
        patch_importance = np.zeros((grid_size, grid_size))
        patch_features = []
        
        # Get the original image for patch analysis
        img_array = (image_tensor[0].cpu().numpy().transpose(1, 2, 0) * 0.5 + 0.5) * 255
        img_array = img_array.astype(np.uint8)
        
        # Calculate importance for each patch
        for i in range(grid_size):
            row_features = []
            for j in range(grid_size):
                # Extract patch region
                y_start = i * patch_size
                y_end = y_start + patch_size
                x_start = j * patch_size
                x_end = x_start + patch_size
                
                # Compute importance as gradient magnitude in patch
                patch_grad = grad[:, y_start:y_end, x_start:x_end]
                importance = np.abs(patch_grad).mean()
                patch_importance[i, j] = importance
                
                # Analyze patch content
                patch_img = img_array[y_start:y_end, x_start:x_end]
                features = self.analyze_patch_features(patch_img)
                row_features.append(features)
            
            patch_features.append(row_features)
        
        # PROFESSIONAL NORMALIZATION:
        # 1. First normalize to 0-1
        imp_min, imp_max = patch_importance.min(), patch_importance.max()
        if imp_max - imp_min > 1e-8:
            patch_importance = (patch_importance - imp_min) / (imp_max - imp_min)
        
        # 2. Apply soft scaling to show gradual importance
        # This makes the top patches stand out while still showing relative importance
        patch_importance = np.power(patch_importance, 0.7)  # Gamma correction
        
        # 3. Ensure at least the top 20% are visible, but not overwhelming
        threshold = np.percentile(patch_importance, 60)  # Top 40% will be visible
        patch_importance = np.where(patch_importance > threshold, patch_importance, patch_importance * 0.3)
        
        # 4. Renormalize
        imp_min, imp_max = patch_importance.min(), patch_importance.max()
        if imp_max - imp_min > 1e-8:
            patch_importance = (patch_importance - imp_min) / (imp_max - imp_min)
        
        return patch_importance, patch_features, grid_size, patch_size
    
    def analyze_patch_features(self, patch_img):
        """Analyze features in a single patch"""
        features = {}
        
        # Convert to grayscale for edge detection
        gray_patch = cv2.cvtColor(patch_img, cv2.COLOR_RGB2GRAY)
        
        # Edge detection
        edges = cv2.Canny(gray_patch, 50, 150)
        edge_density = np.sum(edges > 0) / (16 * 16)
        
        # Color analysis
        hsv_patch = cv2.cvtColor(patch_img, cv2.COLOR_RGB2HSV)
        color_variance = np.std(hsv_patch[:, :, 0])
        
        # Texture analysis
        texture_variance = np.var(gray_patch)
        
        # Detect if patch contains specific patterns
        is_smooth = texture_variance < 100
        has_edges = edge_density > 0.1
        
        features.update({
            'edge_density': edge_density,
            'color_variance': color_variance,
            'texture_variance': texture_variance,
            'is_smooth': is_smooth,
            'has_edges': has_edges,
            'brightness': np.mean(gray_patch)
        })
        
        return features