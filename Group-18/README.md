# 🕵️‍♂️ Smart Forensic AI Sketching

**Smart Forensic AI Sketching** is a multimodal, AI-driven system designed to revolutionize criminal investigations by replacing traditional, slow, and expert-dependent manual sketching methods. The system empowers law enforcement to generate forensic face sketches feature-by-feature, directly from voice or natural language descriptions, ensuring an incremental and highly controlled reconstruction workflow.

-----

## 🎯 Project Objectives

  * **Component-Wise Datasets:** Construct highly specialized datasets by isolating individual facial parts (eyes, nose, mouth, hair, etc.) from existing large-scale face databases.
  * **Attribute-Driven Generation:** Synthesize realistic human facial features strictly based on specific attributes described by the user.
  * **Incremental Fine-Tuning:** Implement a step-by-step editing interface that allows investigators to modify and refine individual facial features iteratively until the composite matches the witness's memory.
  * **Interactive Multimodal UI:** Develop an integrated dashboard supporting both voice and text inputs to guide the facial reconstruction process and produce a final, standardized sketch for investigative use.

-----

## 🏗️ System Architecture & Module Breakdown

The architecture is divided into four highly specialized modules to handle the end-to-end pipeline from witness testimony to final sketch validation.

### 1\. User Input & Text Processing

  * **Multimodal Capture:** Captures the witness description via voice or text input.
  * **Speech-to-Text Integration:** Utilizes Whisper Automatic Speech Recognition (ASR) to convert spoken descriptions into accurate text transcripts.
  * **NLP & Attribute Extraction:** Passes the text through an LLM-based Token Mapper to extract explicit facial attributes and encode them into standardized, structured feature vectors for the generative engines.

### 2\. Dataset Collection and Preprocessing

  * **Data Source:** Built upon front-facing images from the CelebA dataset.
  * **Feature Engineering & Segmentation:** Performs 5-point facial landmark detection to segment the face into distinct regions (Mouth, Nose, Eyes & Eyebrows, Ears, Hair, Cheeks).
  * **Forensic Standardization:** Prepares the isolated components for training by applying image masking, explicit attribute extraction (saved to CSVs), and image-to-sketch conversion to ensure the output mimics professional forensic drawings.

### 3\. Generative Sketch Synthesis

  * **Model Selection:** Evaluated multiple architectures (Conditional GANs, ResNet, PatchGAN) to assign the best-performing model for each specific facial feature.
  * **Component Synthesis:** Deploys trained "specialist" models to generate individual facial components (e.g., generating a mouth at 256x256 resolution, upscaled to 512x512) based on the standardized vectors passed from the input module.
  * **Training & Loss Optimization:** Generator and Discriminator loss metrics were tracked over 100 epochs to ensure high-fidelity outputs for complex textures like hair and subtle features like noses.

### 4\. Integration, Validation & User Interface

  * **Component Assembly:** The Integration Module spatially maps and blends the independently generated features onto a standardized facial template.
  * **Harmonization Layer:** Applies OpenCV-based blending to ensure the transitions between features (e.g., nose to cheeks) are anatomically correct and visually seamless.
  * **Automated Quality Check:** A Validation Module utilizes attribute verification (VQA/Classifier) and confidence thresholding to automatically reject inconsistent combinations, prompting the user for refinement.
  * **Forensic Workspace:** An interactive dashboard where users can view the chat narrative, adjust specific parameters (e.g., "make nose higher"), execute smart GAN resynthesis, and secure the final case record.

-----

## 🛠️ Hardware & Software Requirements

**Hardware:**

  * Multi-core processor with a minimum of 8 GB RAM.
  * Dedicated GPU support (essential for GAN training and rapid inference).
  * Adequate local storage for CelebA datasets and heavy PyTorch model weights.
  * Microphone (for Whisper voice input processing) and display system.

**Software Stack:**

  * **Backend:** Python 3.10+, Flask Framework.
  * **AI & Machine Learning:** OpenRouter (for LLM access), Whisper (ASR), and generative libraries (PyTorch/TensorFlow).
  * **Computer Vision:** OpenCV and PIL (Python Imaging Library) for image processing, masking, and sketch conversion.
  * **Frontend:** Modern web browser to run the interactive React/Vite user interface.

-----

## ⚠️ Assumptions, Risks & Challenges

**System Assumptions:**

1.  **Mono-lingual Input:** The current ASR and NLP pipeline assumes English-only voice and text processing.
2.  **Rational Testimony:** Assumes the witness provides objective, accurate descriptions of the suspect.
3.  **Structured Delivery:** Assumes a workflow that defines the global face shape first, followed by individual feature refinement.

**Known Risks & Challenges:**

  * **Ambiguity:** Natural language descriptions from witnesses can be highly ambiguous or subjective (e.g., "he had a weird nose").
  * **Dataset Limitations:** The diversity of generated features is inherently bound by the demographic scope of the CelebA training dataset.
  * **Computational Load:** Running multiple generative models concurrently requires high computational overhead.
  * **Blending Consistency:** Maintaining seamless lighting and structural consistency when stitching together components generated by different models.

-----

## 👥 Team Details

**Group 18**

  * **Arun Vijo Tharakan (U2203052):** Validation, User Interface & Integration
  * **Anagha Shiji (U2203038):** Text Processing & Attribute Extraction
  * **Alphy Geevarghese (U2203031):** Dataset Collection, Preprocessing & Generative Sketch Synthesis
  * **Alen Thomas John (U2203029):** Dataset Collection, Preprocessing & Generative Sketch Synthesis

**Guided By:** Dr. Jisha G
*Department of Computer Science, Rajagiri School of Engineering and Technology (RSET)*