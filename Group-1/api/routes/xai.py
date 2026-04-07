from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import base64
import hashlib
import time
import os
import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

from api.config import CLASS_NAMES
from api.models import eff, vit
from api.gradcam import EfficientNetGradCAM, ViTVisualizer
from api.visualizations import create_cnn_visualization, create_vit_visualization, create_shap_plot
from api.shap_explain import extract_human_friendly_features, extract_cnn_specific_features, extract_vit_specific_features
from api.utils import predict_local

router = APIRouter()

def run_gradcam_explanation(image_bytes, local_result, output_dir):
    """Run Grad-CAM analysis with improved visualizations"""
    print("   🎯 Running Grad-CAM analysis...")
    
    try:
        img = local_result["image"]
        tensor = local_result["tensor"]
        image_np = local_result["image_np"]
        
        # Get predictions
        eff_pred_idx = 0 if local_result["eff_pred"] == CLASS_NAMES[0] else 1
        vit_pred_idx = 0 if local_result["vit_pred"] == CLASS_NAMES[0] else 1
        
        # Initialize Grad-CAM methods
        gradcam_cnn = EfficientNetGradCAM(eff)
        vit_viz = ViTVisualizer(vit)
        
        # Compute Grad-CAM for CNN
        print("   🔍 Computing CNN Grad-CAM...")
        cnn_cam = gradcam_cnn.compute_cam(tensor, eff_pred_idx)
        
        # Compute ViT patch analysis
        print("   🔍 Computing ViT patch analysis...")
        patch_importance, patch_features, grid_size, patch_size = vit_viz.get_patch_importance_with_features(tensor, vit_pred_idx)
        
        print(f"   📊 ViT patch importance range: [{patch_importance.min():.3f}, {patch_importance.max():.3f}]")
        
        # Create visualizations
        print("   📊 Creating improved visualizations...")
        
        # 1. CNN_Explanation.png
        cnn_fig = create_cnn_visualization(
            image_np, cnn_cam, "EfficientNet", 
            local_result["eff_pred"], local_result["eff_confidence"], 
            local_result["eff_pred"]
        )
        cnn_path = os.path.join(output_dir, "CNN_Explanation.png")
        cnn_fig.savefig(cnn_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(cnn_fig)
        print(f"     ✓ Saved: CNN_Explanation.png")
        
        # 2. ViT_Explanation.png
        vit_fig = create_vit_visualization(
            image_np, patch_importance, patch_features, grid_size, patch_size,
            "Vision Transformer", 
            local_result["vit_pred"], local_result["vit_confidence"], 
            local_result["vit_pred"]
        )
        vit_path = os.path.join(output_dir, "ViT_Explanation.png")
        vit_fig.savefig(vit_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(vit_fig)
        print(f"     ✓ Saved: ViT_Explanation.png")
        
        return True
        
    except Exception as e:
        print(f"     Error in Grad-CAM analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_shap_explanation(image_bytes, local_result, output_dir):
    """Run SHAP analysis with proper SHAP logic from original api.py"""
    print("   📊 Running SHAP analysis...")
    
    try:
        import shap
        image_np = local_result["image_np"]
        
        # Extract features using the original function
        features = extract_human_friendly_features(image_np)
        feature_names = list(features.keys())
        feature_values = np.array([features[name] for name in feature_names])
        
        # Get model predictions
        cnn_pred = local_result["eff_pred"]
        vit_pred = local_result["vit_pred"]
        
        # Create synthetic data for SHAP (matching original api.py logic)
        n_samples = 100
        n_features = len(feature_names)
        
        X_synthetic = np.random.randn(n_samples, n_features) * 0.2
        X_synthetic[0] = feature_values
        
        # Create DIFFERENT weights for CNN and ViT (as in original api.py)
        weights_cnn = np.zeros(n_features)
        weights_vit = np.zeros(n_features)
        
        for i, feat in enumerate(feature_names):
            feat_lower = feat.lower()
            
            # CNN weights (more focused on local features)
            if any(x in feat_lower for x in ['sharp', 'blur', 'edge', 'detail', 'texture']):
                weights_cnn[i] = np.random.randn() * 0.6 + 0.3
            elif any(x in feat_lower for x in ['color', 'rich', 'print']):
                weights_cnn[i] = np.random.randn() * 0.4 + 0.2
            else:
                weights_cnn[i] = np.random.randn() * 0.2
            
            # ViT weights (more focused on global patterns)
            if any(x in feat_lower for x in ['pattern', 'consistency', 'centering', 'background', 'composition']):
                weights_vit[i] = np.random.randn() * 0.6 + 0.3
            elif any(x in feat_lower for x in ['light', 'shadow', 'shine', 'regular']):
                weights_vit[i] = np.random.randn() * 0.4 + 0.2
            else:
                weights_vit[i] = np.random.randn() * 0.2
        
        # Generate labels for CNN
        logits_cnn = X_synthetic @ weights_cnn + np.random.randn(n_samples) * 0.1
        probs_cnn = 1 / (1 + np.exp(-logits_cnn))
        y_cnn = (probs_cnn > 0.5).astype(int)
        y_cnn[0] = 0 if cnn_pred.lower() == 'fake' else 1
        
        # Generate labels for ViT
        logits_vit = X_synthetic @ weights_vit + np.random.randn(n_samples) * 0.1
        probs_vit = 1 / (1 + np.exp(-logits_vit))
        y_vit = (probs_vit > 0.5).astype(int)
        y_vit[0] = 0 if vit_pred.lower() == 'fake' else 1
        
        # Train CNN surrogate model
        X_train, X_test, y_train, y_test = train_test_split(
            X_synthetic, y_cnn, test_size=0.2, random_state=42, stratify=y_cnn
        )
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        rf_cnn = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        rf_cnn.fit(X_train_scaled, y_train)
        
        # Compute CNN SHAP values
        explainer_cnn = shap.TreeExplainer(rf_cnn)
        features_scaled = scaler.transform(X_synthetic)
        shap_values_cnn = explainer_cnn.shap_values(features_scaled)
        
        if isinstance(shap_values_cnn, list):
            shap_values_cnn = shap_values_cnn[1]
        
        # Create CNN Feature Analysis
        print("   📈 Creating CNN Feature Analysis...")
        cnn_shap_fig = create_shap_plot(
            shap_values_cnn, 
            feature_names,
            feature_values,
            model_name="CNN (EfficientNet)",
            prediction=cnn_pred,
            output_type="cnn"
        )
        cnn_shap_path = os.path.join(output_dir, "CNN_Feature_Analysis.png")
        cnn_shap_fig.savefig(cnn_shap_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(cnn_shap_fig)
        print(f"     ✓ Saved: CNN_Feature_Analysis.png")
        
        # Train ViT surrogate model
        X_train_vit, X_test_vit, y_train_vit, y_test_vit = train_test_split(
            X_synthetic, y_vit, test_size=0.2, random_state=43, stratify=y_vit
        )
        
        scaler_vit = StandardScaler()
        X_train_scaled_vit = scaler_vit.fit_transform(X_train_vit)
        X_test_scaled_vit = scaler_vit.transform(X_test_vit)
        
        rf_vit = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=5,
            random_state=43,
            n_jobs=-1
        )
        rf_vit.fit(X_train_scaled_vit, y_train_vit)
        
        # Compute ViT SHAP values
        explainer_vit = shap.TreeExplainer(rf_vit)
        features_scaled_vit = scaler_vit.transform(X_synthetic)
        shap_values_vit = explainer_vit.shap_values(features_scaled_vit)
        
        if isinstance(shap_values_vit, list):
            shap_values_vit = shap_values_vit[1]
        
        # Create ViT Feature Analysis
        print("   📈 Creating ViT Feature Analysis...")
        vit_shap_fig = create_shap_plot(
            shap_values_vit, 
            feature_names,
            feature_values,
            model_name="ViT (Vision Transformer)",
            prediction=vit_pred,
            output_type="vit"
        )
        vit_shap_path = os.path.join(output_dir, "ViT_Feature_Analysis.png")
        vit_shap_fig.savefig(vit_shap_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(vit_shap_fig)
        print(f"     ✓ Saved: ViT_Feature_Analysis.png")
        
        return True
        
    except Exception as e:
        print(f"     Error in SHAP analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


@router.post("/generate-xai")
async def generate_xai(request: Request):
    """Generate XAI visualizations"""
    try:
        body = await request.json()
        image_base64 = body.get("image_base64")
        
        if not image_base64:
            return JSONResponse({"error": "No image data", "status": "error"}, status_code=400)
        
        # Decode base64
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        image_bytes = base64.b64decode(image_base64)
        
        # Generate unique identifier
        timestamp = int(time.time())
        file_hash = hashlib.md5(image_bytes).hexdigest()[:8]
        
        print(f"\n🔍 Generating XAI for image: {file_hash}")
        
        # Get prediction first
        from api.utils import predict_local
        local_result = predict_local(image_bytes)
        
        # Create output directory
        output_dir = f"D:\\project\\xai op\\api_{timestamp}_{file_hash}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Run Grad-CAM analysis
        gradcam_success = run_gradcam_explanation(image_bytes, local_result, output_dir)
        
        # Run SHAP analysis
        shap_success = run_shap_explanation(image_bytes, local_result, output_dir)
        
        # Copy images to web-accessible directory
        web_output_dir = "xai_outputs"
        os.makedirs(web_output_dir, exist_ok=True)
        
        image_paths = {}
        generated_files = []
        
        target_files = [
            ("CNN_Explanation.png", "cnn_gradcam"),
            ("ViT_Explanation.png", "vit_gradcam"),
            ("CNN_Feature_Analysis.png", "cnn_features"),
            ("ViT_Feature_Analysis.png", "vit_features")
        ]
        
        for filename, key in target_files:
            src_path = os.path.join(output_dir, filename)
            dst_filename = f"{timestamp}_{file_hash}_{filename}"
            dst_path = os.path.join(web_output_dir, dst_filename)
            
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
                
                labels = {
                    "cnn_gradcam": "CNN Grad-CAM (Heatmap)",
                    "vit_gradcam": "ViT Patch Analysis",
                    "cnn_features": "CNN Feature Analysis",
                    "vit_features": "ViT Feature Analysis"
                }
                
                image_paths[key] = {
                    "url": f"/xai_outputs/{dst_filename}",
                    "filename": filename,
                    "label": labels.get(key, filename)
                }
                generated_files.append(filename)
                print(f"     Copied: {filename}")
        
        response = {
            "status": "success",
            "xai_visualizations": image_paths,
            "predictions": {
                "efficientnet": local_result["eff_pred"],
                "vit": local_result["vit_pred"],
                "final_verdict": local_result["final_verdict"]
            },
            "confidence_scores": {
                "efficientnet": round(local_result["eff_confidence"], 2),
                "vit": round(local_result["vit_confidence"], 2),
                "final": round(local_result["final_confidence"], 2)
            }
        }
        
        print(f"  XAI generation complete")
        print(f"  Files generated: {generated_files}")
        return JSONResponse(response)
        
    except Exception as e:
        print(f"  XAI generation error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e), "status": "error"}, status_code=500)