from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import base64
import numpy as np
from PIL import Image
import io
import cv2
import re
import os
import time
from collections import Counter
from sklearn.cluster import KMeans
import traceback

from api.config import DEVICE
from api.models import yolo_model

router = APIRouter()

# ================== COMPLETELY REWRITTEN - ACCURATE COLOR ANALYSIS ==================
# Uses FULL SIZE image, NOT resized!

# Comprehensive color database with RGB values
COLORS_RGB = {
    'Red': (255, 0, 0),
    'Orange': (255, 165, 0),
    'Yellow': (255, 255, 0),
    'Lime': (50, 205, 50),
    'Green': (0, 128, 0),
    'Teal': (0, 128, 128),
    'Cyan': (0, 255, 255),
    'Blue': (0, 0, 255),
    'Navy': (0, 0, 128),
    'Purple': (128, 0, 128),
    'Magenta': (255, 0, 255),
    'Pink': (255, 192, 203),
    'HotPink': (255, 105, 180),
    'Brown': (139, 69, 19),
    'Tan': (210, 180, 140),
    'Beige': (245, 245, 220),
    'Black': (0, 0, 0),
    'Charcoal': (54, 69, 79),
    'DarkGray': (64, 64, 64),
    'Gray': (128, 128, 128),
    'Silver': (192, 192, 192),
    'LightGray': (211, 211, 211),
    'White': (255, 255, 255),
    'Gold': (255, 215, 0),
    'Coral': (255, 127, 80),
    'Salmon': (250, 128, 114),
    'Peach': (255, 218, 185),
    'Khaki': (240, 230, 140),
    'Olive': (128, 128, 0),
    'Mint': (189, 252, 201),
    'Lavender': (230, 230, 250),
    'Maroon': (128, 0, 0),
    'Burgundy': (128, 0, 32),
    'Nude': (242, 226, 210),
}

# Color grouping for merging similar colors
COLOR_GROUPS = {
    'Red': ['Red', 'Maroon', 'Burgundy', 'Crimson', 'Scarlet'],
    'Orange': ['Orange', 'Coral', 'Salmon', 'Peach', 'Tangerine', 'Apricot', 'Rust'],
    'Yellow': ['Yellow', 'Gold', 'Mustard', 'Lemon', 'Khaki'],
    'Green': ['Green', 'Lime', 'Olive', 'Mint', 'Sage', 'Emerald', 'Forest'],
    'Teal': ['Teal', 'Cyan', 'Turquoise', 'Aqua'],
    'Blue': ['Blue', 'Navy', 'Royal', 'Cobalt', 'Sapphire', 'Azure'],
    'Purple': ['Purple', 'Magenta', 'Lavender', 'Violet', 'Plum'],
    'Pink': ['Pink', 'HotPink', 'Rose', 'Blush', 'Fuchsia'],
    'Brown': ['Brown', 'Tan', 'Beige', 'Khaki', 'Camel', 'Chocolate', 'Coffee', 'Nude'],
    'Black': ['Black', 'Charcoal', 'Onyx', 'Ebony', 'Jet'],
    'Gray': ['Gray', 'DarkGray', 'Silver', 'LightGray', 'Slate'],
    'White': ['White', 'Cream', 'Ivory', 'Snow', 'Pearl']
}

# Build KD-tree for fast color matching
from scipy.spatial import KDTree
color_rgb_list = list(COLORS_RGB.values())
color_name_list = list(COLORS_RGB.keys())
color_tree = KDTree(color_rgb_list)


def rgb_to_color_name(rgb):
    """Find closest color name using Euclidean distance"""
    r, g, b = rgb
    distance, idx = color_tree.query([r, g, b])
    return color_name_list[idx]


def group_color_name(color_name):
    """Map to main color group"""
    for group, members in COLOR_GROUPS.items():
        if color_name in members:
            return group
        for member in members:
            if member.lower() in color_name.lower() or color_name.lower() in member.lower():
                return group
    return color_name


def professional_color_analysis(image_np):
    """
    ACCURATE color analysis - works on FULL SIZE image
    """
    try:
        print(f"  🎨 Starting accurate color analysis...")
        
        # Convert to uint8 (0-255)
        if image_np.max() <= 1.0:
            img_uint8 = (image_np * 255).astype(np.uint8)
        else:
            img_uint8 = image_np.astype(np.uint8)
        
        # Ensure RGB format
        if len(img_uint8.shape) == 3 and img_uint8.shape[2] == 3:
            # Check if it's BGR (OpenCV format) or RGB
            # Try to detect: if first pixel has high blue, might be BGR
            if img_uint8[0, 0, 0] > img_uint8[0, 0, 2]:
                img_rgb = cv2.cvtColor(img_uint8, cv2.COLOR_BGR2RGB)
            else:
                img_rgb = img_uint8
        else:
            img_rgb = img_uint8
        
        print(f"  📐 Image size: {img_rgb.shape[1]}x{img_rgb.shape[0]}")
        
        # Use more pixels for better accuracy - sample 100,000 pixels
        pixels = img_rgb.reshape(-1, 3)
        sample_size = min(100000, len(pixels))
        
        # Stratified sampling - take from all areas
        if len(pixels) > sample_size:
            indices = np.linspace(0, len(pixels) - 1, sample_size, dtype=int)
            pixels = pixels[indices]
        
        print(f"  📊 Analyzing {len(pixels)} pixels...")
        
        # Use 12 clusters for better color separation
        n_colors = 12
        kmeans = KMeans(n_clusters=n_colors, n_init=10, random_state=42, max_iter=500)
        kmeans.fit(pixels)
        
        # Get color labels and counts
        labels = kmeans.labels_
        counts = Counter(labels)
        total = sum(counts.values())
        
        # Get colors with accurate names
        colors_with_percentages = []
        for i in range(n_colors):
            rgb = kmeans.cluster_centers_[i].astype(int)
            color_name = rgb_to_color_name(rgb)
            percentage = (counts[i] / total) * 100
            
            # Only include colors with > 0.5% presence
            if percentage > 0.5:
                colors_with_percentages.append({
                    "name": color_name,
                    "percentage": round(percentage, 1),
                    "rgb": rgb.tolist()
                })
        
        # Sort by percentage
        colors_with_percentages.sort(key=lambda x: x["percentage"], reverse=True)
        
        # Merge similar colors into groups
        grouped_colors = {}
        for color in colors_with_percentages:
            group = group_color_name(color["name"])
            if group not in grouped_colors:
                grouped_colors[group] = {
                    "name": group,
                    "percentage": 0,
                    "rgb": color["rgb"],
                    "colors_in_group": [color["name"]]
                }
            grouped_colors[group]["percentage"] += color["percentage"]
            grouped_colors[group]["rgb"] = color["rgb"]  # Keep the most prominent RGB
        
        # Convert back to list
        merged_colors = []
        for group, data in grouped_colors.items():
            merged_colors.append({
                "name": data["name"],
                "percentage": round(data["percentage"], 1),
                "rgb": data["rgb"],
                "components": data["colors_in_group"]
            })
        
        # Sort by percentage
        merged_colors.sort(key=lambda x: x["percentage"], reverse=True)
        
        # Keep top 5 colors
        merged_colors = merged_colors[:5]
        
        # Renormalize percentages to sum to 100
        total_percentage = sum(c["percentage"] for c in merged_colors)
        if total_percentage > 0:
            for color in merged_colors:
                color["percentage"] = round((color["percentage"] / total_percentage) * 100, 1)
        
        # Get hex colors
        def rgb_to_hex(rgb):
            return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
        
        for color in merged_colors:
            color["hex"] = rgb_to_hex(color["rgb"])
        
        # Generate analysis text
        if merged_colors:
            primary = merged_colors[0]
            if len(merged_colors) == 1:
                analysis = f"{primary['name']} ({primary['percentage']}%)"
            elif len(merged_colors) == 2:
                secondary = merged_colors[1]
                analysis = f"{primary['name']} ({primary['percentage']}%), {secondary['name']} ({secondary['percentage']}%)"
            else:
                color_list = ", ".join([f"{c['name']} ({c['percentage']}%)" for c in merged_colors[:3]])
                analysis = color_list
        else:
            analysis = "Unknown"
        
        print(f"  🎨 Final colors: {analysis}")
        
        return {
            "colors": [{"name": c["name"], "percentage": c["percentage"], "hex": c["hex"], "rgb": c["rgb"]} for c in merged_colors],
            "primary_color": merged_colors[0]["name"] if merged_colors else "Unknown",
            "primary_percentage": merged_colors[0]["percentage"] if merged_colors else 0,
            "primary_hex": merged_colors[0]["hex"] if merged_colors else "#808080",
            "color_count": len(merged_colors),
            "analysis": analysis,
            "all_colors_detected": len(merged_colors) > 0
        }
        
    except Exception as e:
        print(f"  ❌ Color analysis error: {e}")
        traceback.print_exc()
        return {
            "colors": [],
            "primary_color": "Unknown",
            "primary_percentage": 0,
            "primary_hex": "#808080",
            "color_count": 0,
            "analysis": "Unknown",
            "all_colors_detected": False
        }


def improved_color_analysis(image_np):
    """Compatibility wrapper"""
    result = professional_color_analysis(image_np)
    return result


# ================== QUALITY METRICS ==================

def improved_quality_metrics(image_np):
    """Quality metrics for e-commerce product images"""
    try:
        img_uint8 = (image_np * 255).astype(np.uint8)
        gray = cv2.cvtColor(img_uint8, cv2.COLOR_BGR2GRAY)
        
        height, width = gray.shape
        
        # Sharpness
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness_raw = np.var(laplacian)
        
        if sharpness_raw > 2000:
            sharpness_score = 100
        elif sharpness_raw > 1000:
            sharpness_score = 80 + ((sharpness_raw - 1000) / 1000) * 20
        elif sharpness_raw > 500:
            sharpness_score = 60 + ((sharpness_raw - 500) / 500) * 20
        elif sharpness_raw > 200:
            sharpness_score = 40 + ((sharpness_raw - 200) / 300) * 20
        else:
            sharpness_score = max(0, (sharpness_raw / 200) * 40)
        
        sharpness_score = min(100, max(0, sharpness_score))
        
        # Contrast
        contrast_raw = np.std(gray)
        contrast_score = min(100, (contrast_raw / 80) * 100)
        
        # Brightness
        brightness_raw = np.mean(gray)
        if brightness_raw < 80:
            brightness_score = (brightness_raw / 80) * 50
        elif brightness_raw > 200:
            brightness_score = 100 - ((brightness_raw - 200) / 55) * 50
        else:
            brightness_score = 100
        brightness_score = min(100, max(0, brightness_score))
        
        # Noise level
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        noise_raw = np.std(gray - blurred)
        
        if noise_raw < 5:
            noise_level = "Very Low"
            noise_score = 100
        elif noise_raw < 10:
            noise_level = "Low"
            noise_score = 80
        elif noise_raw < 15:
            noise_level = "Medium"
            noise_score = 60
        elif noise_raw < 20:
            noise_level = "High"
            noise_score = 40
        else:
            noise_level = "Very High"
            noise_score = 20
        
        # Overall quality score
        quality_score = (
            (sharpness_score * 0.35) +
            (contrast_score * 0.20) +
            (brightness_score * 0.20) +
            (noise_score * 0.25)
        )
        
        quality_score = max(0, min(100, quality_score))
        
        if quality_score >= 80:
            quality_rating = "Excellent"
            quality_description = "Excellent quality image"
        elif quality_score >= 65:
            quality_rating = "Good"
            quality_description = "Good quality image"
        elif quality_score >= 50:
            quality_rating = "Fair"
            quality_description = "Fair quality image"
        elif quality_score >= 35:
            quality_rating = "Poor"
            quality_description = "Poor quality image"
        else:
            quality_rating = "Very Poor"
            quality_description = "Very poor quality image"
        
        return {
            "quality_score": round(float(quality_score), 1),
            "quality_rating": quality_rating,
            "quality_description": quality_description,
            "sharpness_score": round(sharpness_score, 1),
            "contrast_score": round(contrast_score, 1),
            "brightness_score": round(brightness_score, 1),
            "noise_level": noise_level,
            "resolution": f"{width}x{height}"
        }
        
    except Exception as e:
        print(f"  Quality metrics error: {e}")
        return {
            "quality_score": 0,
            "quality_rating": "Unknown",
            "quality_description": "Analysis failed",
            "resolution": "Unknown"
        }


# ================== BACKGROUND ANALYSIS ==================

def analyze_simple_background(image_np):
    """Analyze image background"""
    try:
        img_uint8 = (image_np * 255).astype(np.uint8)
        gray = cv2.cvtColor(img_uint8, cv2.COLOR_BGR2GRAY)
        
        height, width = gray.shape
        
        # Check if product is centered
        edges = cv2.Canny(gray, 50, 150)
        edge_points = np.where(edges > 0)
        
        if len(edge_points[0]) > 0:
            center_x, center_y = width // 2, height // 2
            edge_center_x = np.mean(edge_points[1])
            edge_center_y = np.mean(edge_points[0])
            
            distance = np.sqrt((center_x - edge_center_x)**2 + (center_y - edge_center_y)**2)
            max_distance = np.sqrt(center_x**2 + center_y**2)
            centered_score = 1.0 - (distance / max_distance)
        else:
            centered_score = 0.5
        
        # Background simplicity
        border_width = min(30, width // 8, height // 8)
        
        if border_width > 0:
            top_border = gray[:border_width, :]
            bottom_border = gray[-border_width:, :]
            left_border = gray[:, :border_width]
            right_border = gray[:, -border_width:]
            
            border_variances = [
                np.std(top_border) if top_border.size > 0 else 0,
                np.std(bottom_border) if bottom_border.size > 0 else 0,
                np.std(left_border) if left_border.size > 0 else 0,
                np.std(right_border) if right_border.size > 0 else 0
            ]
            
            avg_variance = np.mean(border_variances)
            
            if avg_variance < 10:
                background_type = "Simple"
                is_simple = True
            elif avg_variance < 30:
                background_type = "Moderate"
                is_simple = True
            else:
                background_type = "Complex"
                is_simple = False
        else:
            background_type = "Unknown"
            is_simple = False
            avg_variance = 0
        
        # Check for white/plain background
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        white_percentage = np.sum(binary == 255) / binary.size
        
        is_product_photo = white_percentage > 0.3 or (centered_score > 0.7 and is_simple)
        
        if is_product_photo and centered_score > 0.7:
            assessment = "Professional product photo"
        elif is_simple and centered_score > 0.6:
            assessment = "Good product photo"
        elif not is_simple:
            assessment = "Natural/personal photo"
        else:
            assessment = "Average quality photo"
        
        return {
            "background_type": background_type,
            "is_product_photo": bool(is_product_photo),
            "product_centered_score": round(float(centered_score * 100), 1),
            "white_background_percentage": round(float(white_percentage * 100), 1),
            "assessment": assessment
        }
        
    except Exception as e:
        print(f"  Background analysis error: {e}")
        return {
            "background_type": "Unknown",
            "is_product_photo": False,
            "product_centered_score": 0,
            "white_background_percentage": 0,
            "assessment": "Analysis failed"
        }


# ================== TEXT FEATURE EXTRACTION ==================

def extract_text_features(description):
    """Extract product features from description text"""
    text_lower = description.lower()
    
    features = {
        "product_type": None,
        "color": None,
        "brand": None,
        "condition": None,
        "size": None,
        "price": None,
        "has_price": False,
        "is_shoe": False,
        "is_watch": False,
        "summary": ""
    }
    
    # Product type detection
    shoe_keywords = ['shoe', 'shoes', 'sneaker', 'sneakers', 'boot', 'boots', 'footwear', 'running', 'basketball', 'tennis', 'soccer', 'football']
    watch_keywords = ['watch', 'watches', 'wristwatch', 'timepiece', 'smartwatch', 'chronograph']
    
    for keyword in watch_keywords:
        if keyword in text_lower:
            features["product_type"] = "watch"
            features["is_watch"] = True
            break
    
    if not features["product_type"]:
        for keyword in shoe_keywords:
            if keyword in text_lower:
                features["product_type"] = "shoe"
                features["is_shoe"] = True
                break
    
    # Color detection
    color_map = {
        "Black": ['black', 'charcoal', 'graphite'],
        "White": ['white', 'ivory', 'cream', 'pearl'],
        "Red": ['red', 'burgundy', 'maroon', 'crimson'],
        "Orange": ['orange', 'coral', 'peach', 'apricot', 'rust', 'tangerine'],
        "Yellow": ['yellow', 'gold', 'mustard', 'lemon'],
        "Green": ['green', 'olive', 'mint', 'sage', 'emerald', 'forest'],
        "Blue": ['blue', 'navy', 'royal', 'cobalt', 'sapphire', 'azure'],
        "Purple": ['purple', 'violet', 'lavender', 'plum'],
        "Pink": ['pink', 'rose', 'blush', 'fuchsia', 'magenta'],
        "Brown": ['brown', 'tan', 'beige', 'khaki', 'camel', 'chocolate', 'coffee'],
        "Gray": ['gray', 'grey', 'silver', 'slate']
    }
    
    for color_name, color_words in color_map.items():
        for word in color_words:
            if word in text_lower:
                features["color"] = color_name
                break
        if features["color"]:
            break
    
    # Brand detection
    brand_map = {
        "Nike": ['nike', 'air jordan', 'jordan'],
        "Adidas": ['adidas', 'yeezy', 'ultraboost'],
        "Puma": ['puma'],
        "Converse": ['converse', 'chuck taylor'],
        "Vans": ['vans'],
        "New Balance": ['new balance'],
        "Timberland": ['timberland'],
        "Rolex": ['rolex'],
        "Omega": ['omega'],
        "Apple": ['apple watch'],
        "Samsung": ['samsung watch'],
        "Casio": ['casio', 'g-shock'],
        "Seiko": ['seiko'],
        "Citizen": ['citizen']
    }
    
    for brand_name, brand_words in brand_map.items():
        for word in brand_words:
            if word in text_lower:
                features["brand"] = brand_name
                break
        if features["brand"]:
            break
    
    # Size detection
    size_match = re.search(r'size[:\s]*(\d+(?:\.\d+)?)', text_lower)
    if size_match:
        features["size"] = size_match.group(1)
    
    # Price detection
    price_match = re.search(r'[₹$€£]\s*([\d,]+(?:\.\d{2})?)', description)
    if price_match:
        features["has_price"] = True
        features["price"] = price_match.group(0)
    
    # Condition detection
    if 'new' in text_lower:
        features["condition"] = "New"
    elif 'used' in text_lower or 'pre-owned' in text_lower:
        features["condition"] = "Used"
    elif 'refurbished' in text_lower:
        features["condition"] = "Refurbished"
    
    # Build summary
    parts = []
    if features["brand"]:
        parts.append(features["brand"])
    if features["product_type"]:
        parts.append(features["product_type"].title())
    if features["color"]:
        parts.append(features["color"])
    if features["size"]:
        parts.append(f"Size {features['size']}")
    if features["condition"]:
        parts.append(features["condition"])
    
    features["summary"] = " • ".join(parts) if parts else "Product details extracted"
    
    return features


# ================== YOLO PRODUCT DETECTION ==================

def detect_product_with_yolo(image_np):
    """Detect product type using YOLO"""
    try:
        if yolo_model is None:
            return {
                "product_type": "unknown",
                "confidence": 0,
                "display_name": "Unknown",
                "detected": False
            }
        
        # Save image temporarily
        temp_dir = "temp_images"
        os.makedirs(temp_dir, exist_ok=True)
        temp_image_path = f"{temp_dir}/yolo_{int(time.time())}.jpg"
        
        img_uint8 = (image_np * 255).astype(np.uint8)
        cv2.imwrite(temp_image_path, cv2.cvtColor(img_uint8, cv2.COLOR_RGB2BGR))
        
        # Run YOLO prediction
        results = yolo_model.predict(temp_image_path)
        result = results[0]
        
        # Get top prediction
        if hasattr(result, 'probs') and result.probs is not None:
            top1_idx = result.probs.top1
            top1_conf = result.probs.top1conf.item()
            
            if hasattr(result, 'names'):
                product_type = result.names[top1_idx]
            else:
                product_type = "unknown"
            
            # Clean up
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            
            # Determine display name
            product_lower = product_type.lower()
            if "shoe" in product_lower or "sneaker" in product_lower:
                display_name = "👟 Shoes/Footwear"
            elif "watch" in product_lower:
                display_name = "⌚ Watch/Timepiece"
            else:
                display_name = product_type.title()
            
            return {
                "product_type": product_type.lower(),
                "confidence": float(top1_conf * 100),
                "display_name": display_name,
                "detected": True
            }
        else:
            return {
                "product_type": "unknown",
                "confidence": 0,
                "display_name": "Unknown",
                "detected": False
            }
            
    except Exception as e:
        print(f"  YOLO detection error: {e}")
        return {
            "product_type": "unknown",
            "confidence": 0,
            "display_name": "Unknown",
            "detected": False
        }


# ================== MATCH SCORE CALCULATION ==================

def calculate_match_score(text_features, image_features):
    """Calculate match score based on product features"""
    score = 0.5
    reasons = []
    
    # Product type match (40% weight)
    if text_features["product_type"] and image_features["product_type"] and image_features["product_type"] != "unknown":
        text_type = text_features["product_type"]
        image_type = image_features["product_type"]
        
        if (text_type == "shoe" and "shoe" in image_type) or (text_type == "watch" and "watch" in image_type):
            score += 0.3
            reasons.append("✓ Product type matches")
        else:
            score -= 0.2
            reasons.append("✗ Product type mismatch")
    
    # Color match (30% weight)
    if text_features["color"] and image_features["color_analysis"]["primary_color"] != "Unknown":
        text_color = text_features["color"].lower()
        image_color = image_features["color_analysis"]["primary_color"].lower()
        
        if text_color == image_color:
            score += 0.25
            reasons.append(f"✓ Color matches: {text_features['color']}")
        elif (text_color == "orange" and image_color in ["coral", "peach", "tangerine"]) or \
             (text_color == "red" and image_color in ["burgundy", "maroon"]) or \
             (text_color == "blue" and image_color in ["navy", "royal"]) or \
             (text_color == "black" and image_color in ["charcoal", "darkgray"]):
            score += 0.15
            reasons.append(f"⚠️ Color similar: {text_features['color']} → {image_features['color_analysis']['primary_color']}")
        else:
            score -= 0.15
            reasons.append(f"✗ Color mismatch: expected {text_features['color']}, found {image_features['color_analysis']['primary_color']}")
    
    # Brand presence (10% weight)
    if text_features["brand"]:
        score += 0.1
        reasons.append("ℹ️ Brand specified")
    
    # Price presence (10% weight)
    if text_features["has_price"]:
        score += 0.1
        reasons.append("ℹ️ Price included")
    
    # Size/Condition (10% weight)
    if text_features["size"] or text_features["condition"]:
        score += 0.05
        reasons.append("ℹ️ Details specified")
    
    score = max(0, min(1, score))
    return score, reasons


def get_match_explanation(score):
    """Get user-friendly explanation for match score"""
    if score >= 0.8:
        return {"rating": "Excellent Match", "description": "The product matches the description very well.", "color": "#2ecc71"}
    elif score >= 0.6:
        return {"rating": "Good Match", "description": "The product generally matches the description.", "color": "#27ae60"}
    elif score >= 0.4:
        return {"rating": "Moderate Match", "description": "Some elements match, but there are differences.", "color": "#f39c12"}
    elif score >= 0.2:
        return {"rating": "Poor Match", "description": "The product shows significant differences from the description.", "color": "#e67e22"}
    else:
        return {"rating": "Very Poor Match", "description": "The product does not match the description at all.", "color": "#e74c3c"}


# ================== MISMATCH DETECTION ENDPOINT ==================

@router.post("/detect-mismatch")
async def detect_mismatch(request: Request):
    """Mismatch detection with accurate color analysis on FULL SIZE image"""
    try:
        body = await request.json()
        image_base64 = body.get("image_base64")
        description = body.get("description", "")
        
        if not image_base64:
            return JSONResponse({"error": "No image data", "status": "error"}, status_code=400)
        
        print(f"\n" + "="*60)
        print(f"🔍 MISMATCH DETECTION STARTED")
        print(f"="*60)
        print(f"📝 Description: {description[:100]}...")
        
        # Decode base64
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        image_bytes = base64.b64decode(image_base64)
        
        # Load FULL SIZE image for color analysis (DO NOT RESIZE for color!)
        img_full = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        print(f"📐 Original image size: {img_full.size[0]}x{img_full.size[1]}")
        
        # Convert to numpy for color analysis (FULL SIZE)
        image_np_full = np.array(img_full) / 255.0
        
        # For YOLO and quality, resize to 224x224 (acceptable)
        img_resized = img_full.resize((224, 224))
        image_np_resized = np.array(img_resized) / 255.0
        
        # Extract text features
        text_features = extract_text_features(description)
        print(f"📝 Text features: {text_features['summary']}")
        
        # Detect product from image using YOLO (on resized)
        image_product = detect_product_with_yolo(image_np_resized)
        print(f"🖼️ YOLO detection: {image_product['display_name']} ({image_product['confidence']:.1f}%)")
        
        # COLOR ANALYSIS ON FULL SIZE IMAGE (THIS IS THE KEY FIX!)
        color_analysis = professional_color_analysis(image_np_full)
        print(f"🎨 Color analysis result: {color_analysis['analysis']}")
        
        # Quality metrics (on resized)
        quality_metrics = improved_quality_metrics(image_np_resized)
        print(f"📊 Quality: {quality_metrics['quality_rating']} ({quality_metrics['quality_score']:.1f}%)")
        
        # Background analysis
        background_analysis = analyze_simple_background(image_np_resized)
        print(f"🖼️ Background: {background_analysis['background_type']}")
        
        # Calculate match score
        match_score, match_reasons = calculate_match_score(text_features, {
            "product_type": image_product["product_type"],
            "color_analysis": color_analysis
        })
        match_explanation = get_match_explanation(match_score)
        print(f"📊 Match score: {match_score:.2f} - {match_explanation['rating']}")
        
        # Calculate risk score
        risk_score = 0
        mismatches = []
        warnings = []
        
        # Product type check
        if text_features["product_type"] and image_product["detected"] and image_product["product_type"] != "unknown":
            text_type = text_features["product_type"]
            image_type = image_product["product_type"]
            
            is_match = (text_type == "shoe" and "shoe" in image_type) or (text_type == "watch" and "watch" in image_type)
            
            if not is_match:
                mismatches.append(f"Product type mismatch: Description says '{text_type}', image shows {image_product['display_name']}")
                risk_score += 35
                print(f"  ⚠️ Product type mismatch!")
            else:
                print(f"  ✅ Product type matches")
        
        # Color check
        if text_features["color"] and color_analysis["primary_color"] != "Unknown":
            text_color = text_features["color"].lower()
            image_color = color_analysis["primary_color"].lower()
            
            if text_color != image_color:
                mismatches.append(f"Color mismatch: Description says '{text_features['color']}', image shows '{color_analysis['primary_color']}'")
                risk_score += 25
                print(f"  ⚠️ Color mismatch: {text_features['color']} vs {color_analysis['primary_color']}")
            else:
                print(f"  ✅ Color matches: {text_features['color']}")
        
        # Price check warning
        if not text_features["has_price"]:
            warnings.append("No price mentioned in description")
            risk_score += 5
            print(f"  ⚠️ No price mentioned")
        
        # Cap risk score
        risk_score = min(risk_score, 100)
        
        # Final verdict
        if risk_score >= 60:
            verdict = "HIGH RISK - POTENTIAL SCAM"
            risk_level = "high"
        elif risk_score >= 35:
            verdict = "MEDIUM RISK - VERIFY CAREFULLY"
            risk_level = "medium"
        elif risk_score >= 15:
            verdict = "LOW RISK - MINOR CONCERNS"
            risk_level = "low"
        else:
            verdict = "LOW RISK - LIKELY LEGITIMATE"
            risk_level = "very_low"
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"  Risk Score: {risk_score}/100 ({risk_level})")
        print(f"  Verdict: {verdict}")
        print(f"  Match Score: {match_score:.2f}")
        print("="*60 + "\n")
        
        response = {
            "status": "success",
            "verdict": verdict,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "match_score": round(match_score, 3),
            "match_explanation": match_explanation,
            "match_reasons": match_reasons,
            "mismatches": mismatches,
            "warnings": warnings,
            "text_features": {
                "product_type": text_features.get("product_type"),
                "product_display": "Shoe" if text_features.get("is_shoe") else "Watch" if text_features.get("is_watch") else None,
                "color": text_features.get("color"),
                "brand": text_features.get("brand"),
                "condition": text_features.get("condition"),
                "size": text_features.get("size"),
                "price": text_features.get("price"),
                "has_price": text_features.get("has_price", False),
                "summary": text_features.get("summary")
            },
            "image_features": {
                "product_type": image_product.get("product_type"),
                "product_display": image_product.get("display_name"),
                "product_confidence": image_product.get("confidence"),
                "color_analysis": color_analysis,
                "quality_metrics": quality_metrics,
                "background_analysis": background_analysis,
                "detected": image_product.get("detected", False)
            }
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        print(f"❌ Mismatch detection error: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e), "status": "error"}, status_code=500)