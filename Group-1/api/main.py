from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# Import routes
from api.routes import detection, xai, mismatch, feedback
from api.config import CLASS_NAMES, DEVICE

app = FastAPI(title="ImageGuard AI Detection with Enhanced XAI & Mismatch Detection")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
os.makedirs("temp_images", exist_ok=True)
os.makedirs("xai_outputs", exist_ok=True)
os.makedirs("user_feedback", exist_ok=True)
os.makedirs(r"D:\project\corrected_images\real", exist_ok=True)
os.makedirs(r"D:\project\corrected_images\fake", exist_ok=True)

# Mount static directories
app.mount("/xai_outputs", StaticFiles(directory="xai_outputs"), name="xai_outputs")
app.mount("/user_feedback", StaticFiles(directory="user_feedback"), name="user_feedback")

# Include routers
app.include_router(detection.router)
app.include_router(xai.router)
app.include_router(mismatch.router)
app.include_router(feedback.router)

@app.get("/")
async def root():
    return {"message": "ImageGuard API is running", "status": "ok"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "models": ["EfficientNet-B2", "Vision Transformer (ViT-Base)", "CLIP", "YOLO"],
        "xai_methods": ["Grad-CAM", "Feature Analysis"],
        "mismatch_detection": True,
        "class_names": CLASS_NAMES,
        "device": str(DEVICE)
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("  ImageGuard AI Detection API (IMPROVED XAI VISUALIZATIONS)")
    print("=" * 70)
    print(f" Class names: {CLASS_NAMES}")
    print(f" Models: EfficientNet-B2 + Vision Transformer")
    print(f" XAI: Grad-CAM + Feature Analysis (IMPROVED)")
    print(f"   - CNN: Single heatmap with text legend (no colorbar)")
    print(f"   - ViT: Colored borders (NO heatmap overlay)")
    print(f"   - SHAP: Single-color professional graphs")
    print(f" Device: {DEVICE}")
    print("\n  API Running at: http://127.0.0.1:8000")
    print("=" * 70)
    
    uvicorn.run(app, host="127.0.0.1", port=8000)