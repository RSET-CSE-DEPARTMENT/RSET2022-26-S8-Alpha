import torch
import numpy as np
from PIL import Image
import io
from api.config import transform, DEVICE, CLASS_NAMES
from api.models import eff, vit

def predict_local(image_bytes):
    """Predict using your models with CONSISTENT decision logic"""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = transform(img).unsqueeze(0).to(DEVICE)
    
    with torch.no_grad():
        eff_output = eff(tensor)
        vit_output = vit(tensor)
        
        eff_probs = torch.softmax(eff_output, 1)[0]
        vit_probs = torch.softmax(vit_output, 1)[0]
        
        eff_pred_idx = eff_output.argmax(dim=1).item()
        vit_pred_idx = vit_output.argmax(dim=1).item()
        
        eff_class = CLASS_NAMES[eff_pred_idx]
        vit_class = CLASS_NAMES[vit_pred_idx]
        
        # Get confidence
        eff_confidence = eff_probs[eff_pred_idx].item() * 100
        vit_confidence = vit_probs[vit_pred_idx].item() * 100
        
        # Get fake probability for both models (FAKE is index 0, REAL is index 1)
        fake_class_idx = 0  # Assuming FAKE is at index 0
        real_class_idx = 1  # Assuming REAL is at index 1
        
        eff_fake_prob = eff_probs[fake_class_idx].item() * 100
        vit_fake_prob = vit_probs[fake_class_idx].item() * 100
        
        # Weighted average
        weighted_fake_prob = (eff_fake_prob * 0.6) + (vit_fake_prob * 0.4)
        
        # Determine final verdict
        if weighted_fake_prob > 50:
            verdict = "FAKE"
            confidence = weighted_fake_prob
        else:
            verdict = "REAL"
            confidence = 100 - weighted_fake_prob
        
        # Check if models agree
        models_agree = eff_class == vit_class
        
        return {
            "image": img,
            "tensor": tensor,
            "image_np": np.array(img.resize((224, 224))) / 255.0,
            "eff_pred": eff_class,
            "eff_confidence": eff_confidence,
            "eff_fake_prob": eff_fake_prob,
            "vit_pred": vit_class,
            "vit_confidence": vit_confidence,
            "vit_fake_prob": vit_fake_prob,
            "avg_fake_prob": weighted_fake_prob,
            "final_verdict": verdict,
            "final_confidence": confidence,
            "models_agree": models_agree,
            "disagreement": not models_agree
        }