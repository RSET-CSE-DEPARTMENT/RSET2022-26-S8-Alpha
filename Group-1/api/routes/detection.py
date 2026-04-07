from fastapi import APIRouter, File, UploadFile, Request
from fastapi.responses import JSONResponse
import base64
from api.utils import predict_local

router = APIRouter()

@router.post("/detect")
async def detect(file: UploadFile = File(...)):
    """Main detection endpoint - accepts file upload"""
    try:
        image_bytes = await file.read()
        
        # Get predictions
        local_result = predict_local(image_bytes)
        
        response = {
            "verdict": local_result["final_verdict"],
            "confidence": round(local_result["final_confidence"], 2),
            "status": "success",
            "needs_explanation": True,
            
            # Model details
            "efficientnet_prediction": local_result["eff_pred"],
            "efficientnet_confidence": round(local_result["eff_confidence"], 2),
            "vit_prediction": local_result["vit_pred"],
            "vit_confidence": round(local_result["vit_confidence"], 2),
            
            # Final decision
            "final_fake_probability": round(local_result["avg_fake_prob"], 2),
            "models_agree": local_result["models_agree"],
            "disagreement": local_result["disagreement"]
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        return JSONResponse({"error": str(e), "status": "error"}, status_code=500)

@router.post("/detect-base64")
async def detect_base64(request: Request):
    """Detection endpoint that accepts base64"""
    try:
        body = await request.json()
        image_base64 = body.get("image_base64")
        
        if not image_base64:
            return JSONResponse({"error": "No image data", "status": "error"}, status_code=400)
        
        # Decode base64
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        image_bytes = base64.b64decode(image_base64)
        
        # Get predictions
        local_result = predict_local(image_bytes)
        
        response = {
            "verdict": local_result["final_verdict"],
            "confidence": round(local_result["final_confidence"], 2),
            "status": "success",
            "needs_explanation": True,
            
            # Model details
            "efficientnet_prediction": local_result["eff_pred"],
            "efficientnet_confidence": round(local_result["eff_confidence"], 2),
            "vit_prediction": local_result["vit_pred"],
            "vit_confidence": round(local_result["vit_confidence"], 2),
            
            # Final decision
            "final_fake_probability": round(local_result["avg_fake_prob"], 2),
            "models_agree": local_result["models_agree"],
            "disagreement": local_result["disagreement"]
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        return JSONResponse({"error": str(e), "status": "error"}, status_code=500)