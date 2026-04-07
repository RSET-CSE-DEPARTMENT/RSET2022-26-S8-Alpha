# ImageGuard

ImageGuard is a deep learning–based system for detecting fake or manipulated images in online marketplaces.  
It combines convolutional neural networks, vision transformers, explainable AI techniques, and image–text mismatch analysis, and is deployed using a FastAPI backend with a Chrome browser extension for real-time usage.

The goal of ImageGuard is not only to classify images as real or fake, but also to explain why a decision was made and to identify inconsistencies between product images and their descriptions.

---

## Key Features

- Fake vs Real image classification using EfficientNet (CNN) and Vision Transformer (ViT)
- Explainable AI using Grad-CAM (CNN) and feature-attribution visualizations
- Image–text mismatch detection using CLIP and YOLO
- Metadata analysis for detecting suspicious image properties
- Human-interpretable quality, texture, lighting, and background analysis
- FastAPI backend for inference and explanations
- Chrome browser extension for real-time detection on web pages

---

## System Architecture

### Backend
- Python + FastAPI
- Modular structure using api/ folder
- Handles image inference, XAI generation, metadata analysis, and mismatch detection

### Models
- EfficientNet-B2
- Vision Transformer (ViT-Base)
- YOLO
- CLIP

### Frontend
- Chrome Extension (Manifest V3)

---

## Project Structure

ImageGuard/
├── api/
├── extension/
├── training/
├── xai/
├── imageguard_group.pdf
├── README.md

---

## Installation

git clone https://github.com/Anand-Basil/ImageGuard.git  
cd ImageGuard  
pip install -r requirements.txt  

---

## Run Backend

uvicorn api.main:app --reload  

---

## Project Report

[Project Report](./imageguard_group.pdf)

---

## License

MIT License