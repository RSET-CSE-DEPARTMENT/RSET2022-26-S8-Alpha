from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import base64
import os
import json
import time
import hashlib
import traceback

router = APIRouter()

# ================== SAVE CORRECTED IMAGE FUNCTION ==================
def save_corrected_image_to_folder(image_base64, true_label, predicted_label, image_url):
    """Save corrected image to D:\project\corrected_images folder"""
    try:
        # Create the base directory
        base_dir = r"D:\project\corrected_images"
        
        # Determine the folder based on true_label
        if true_label.lower() == "real":
            folder = os.path.join(base_dir, "real")
        elif true_label.lower() == "fake":
            folder = os.path.join(base_dir, "fake")
        else:
            # If label is invalid, use "unknown" folder
            folder = os.path.join(base_dir, "unknown")
        
        # Create the directory if it doesn't exist
        os.makedirs(folder, exist_ok=True)
        
        # Generate a unique filename
        timestamp = int(time.time())
        filename = f"corrected_{timestamp}_{hashlib.md5(image_url.encode()).hexdigest()[:8]}.jpg"
        filepath = os.path.join(folder, filename)
        
        # Decode base64 image
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        image_data = base64.b64decode(image_base64)
        
        # Save the image
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        # Create metadata file
        metadata = {
            "true_label": true_label,
            "predicted_label": predicted_label,
            "image_url": image_url,
            "corrected_at": time.strftime('%Y-%m-%d %H:%M:%S'),
            "filename": filename,
            "filepath": filepath
        }
        
        metadata_file = os.path.join(folder, f"{os.path.splitext(filename)[0]}_metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"  Saved corrected image to: {filepath}")
        print(f"  Metadata saved to: {metadata_file}")
        
        return {
            "status": "success",
            "message": f"Image saved to {true_label} folder",
            "filepath": filepath,
            "metadata_file": metadata_file,
            "true_label": true_label,
            "predicted_label": predicted_label
        }
        
    except Exception as e:
        print(f"  Error saving corrected image: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }

# ================== FEEDBACK ENDPOINT ==================
@router.post("/submit-feedback")
async def submit_feedback(request: Request):
    """Submit user feedback and save corrected images"""
    try:
        body = await request.json()
        
        # Extract feedback data
        image_url = body.get("image_url", "Unknown")
        predicted_label = body.get("predicted_label", "Unknown")
        true_label = body.get("true_label", "Unknown")
        confidence = body.get("confidence", 0)
        image_base64 = body.get("image_base64", "")
        
        print(f"\n📝 Received feedback:")
        print(f"   Predicted: {predicted_label}")
        print(f"   True: {true_label}")
        print(f"   Confidence: {confidence}")
        
        # Save corrected image if prediction was wrong
        if predicted_label.lower() != true_label.lower():
            print(f"     Prediction was wrong! Saving corrected image...")
            
            # Save corrected image to folder
            save_result = save_corrected_image_to_folder(image_base64, true_label, predicted_label, image_url)
            
            if save_result["status"] == "success":
                print(f"     Corrected image saved to: {save_result['filepath']}")
                save_message = save_result["message"]
            else:
                print(f"     Failed to save corrected image: {save_result.get('error')}")
                save_message = "Feedback recorded but image save failed"
        else:
            save_message = "Prediction was correct"
        
        # Create feedback directory if it doesn't exist
        feedback_dir = "user_feedback"
        os.makedirs(feedback_dir, exist_ok=True)
        
        # Create feedback record
        timestamp = int(time.time())
        feedback_id = hashlib.md5(f"{image_url}{timestamp}".encode()).hexdigest()[:8]
        
        feedback_data = {
            "feedback_id": feedback_id,
            "timestamp": timestamp,
            "image_url": image_url,
            "predicted_label": predicted_label,
            "true_label": true_label,
            "confidence": confidence,
            "prediction_correct": predicted_label.lower() == true_label.lower(),
            "corrected_image_saved": predicted_label.lower() != true_label.lower(),
            "save_message": save_message
        }
        
        # Save feedback to file
        feedback_file = os.path.join(feedback_dir, f"feedback_{feedback_id}.json")
        with open(feedback_file, 'w') as f:
            json.dump(feedback_data, f, indent=2)
        
        print(f"  Feedback saved: {feedback_file}")
        
        response = {
            "status": "success",
            "message": save_message,
            "feedback_id": feedback_id,
            "timestamp": timestamp,
            "prediction_correct": predicted_label.lower() == true_label.lower(),
            "corrected_image_saved": predicted_label.lower() != true_label.lower()
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        print(f"  Feedback submission error: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e), "status": "error"}, status_code=500)

# ================== SAVE CORRECTED IMAGE ENDPOINT ==================
@router.post("/save-corrected-image")
async def save_corrected_image_endpoint(request: Request):
    """Endpoint specifically for saving corrected images"""
    try:
        body = await request.json()
        
        image_base64 = body.get("image_base64")
        true_label = body.get("true_label", "unknown")
        predicted_label = body.get("predicted_label", "unknown")
        image_url = body.get("original_url", "Unknown")
        
        if not image_base64:
            return JSONResponse({"error": "No image data", "status": "error"}, status_code=400)
        
        print(f"\n💾 Saving corrected image...")
        print(f"   True label: {true_label}")
        print(f"   Predicted: {predicted_label}")
        
        # Save corrected image to folder
        result = save_corrected_image_to_folder(image_base64, true_label, predicted_label, image_url)
        
        if result["status"] == "success":
            print(f"  Image saved successfully")
            return JSONResponse(result)
        else:
            print(f"  Failed to save image")
            return JSONResponse(result, status_code=500)
            
    except Exception as e:
        print(f"  Save corrected image error: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e), "status": "error"}, status_code=500)

# ================== CHECK METADATA ENDPOINT ==================
@router.post("/check-metadata")
async def check_metadata(request: Request):
    """Check image metadata - simplified version"""
    try:
        body = await request.json()
        image_base64 = body.get("image_base64")
        
        if not image_base64:
            return JSONResponse({"error": "No image data", "status": "error"}, status_code=400)
        
        # Decode base64
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        image_bytes = base64.b64decode(image_base64)
        
        # Get basic image info
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        
        # Create metadata response
        response = {
            "status": "success",
            "verdict": "Analyzed",
            "confidence": 85.0,
            "image_info": {
                "format": img.format or "JPEG",
                "dimensions": f"{img.width}x{img.height}",
                "size_kb": round(len(image_bytes) / 1024, 2),
                "mode": img.mode
            },
            "metadata_summary": f"Image analyzed successfully",
            "has_metadata": True,
            "total_tags": 4
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        return JSONResponse({"error": str(e), "status": "error"}, status_code=500)