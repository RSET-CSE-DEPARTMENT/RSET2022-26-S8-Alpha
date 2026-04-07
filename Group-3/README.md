# Personalized Anomaly Detection in Financial Transactions

### Account-GANomaly: A Hybrid GAN + XGBoost Framework

---

## Overview

Fraud detection systems often fail because they treat all users the same.
This project introduces a **personalized anomaly detection framework** that learns **individual user behavior** and detects deviations specific to each user.

We combine:
* **User-conditioned GANomaly (Deep Learning)**
* **XGBoost (Supervised Learning)**
to build a **hybrid fraud detection system** that improves accuracy and reduces false positives.

---

## Key Idea

Instead of asking:
“Is this transaction suspicious?”

We ask:
“Is this transaction suspicious for THIS specific user?”

---

## Architecture

### 1. Data Preprocessing
* Feature engineering
* Sequence construction (short-term behavior)
* Long-term statistical profiling
* Normalization

### 2. Hybrid User Encoder
* **LSTM** → captures short-term behavior
* **MLP** → captures long-term patterns
* **History-gated mechanism** → handles cold-start users

### 3. User-Conditioned GANomaly
* Learns personalized “normal” behavior
* Uses:
  * Encoder
  * Generator
  * Discriminator
* Outputs:
  * Reconstruction error
  * Latent space difference

### 4. Anomaly Scoring
Score is computed as:

```
Score = α × Reconstruction Error + (1 − α) × Latent Difference
```

### 5. XGBoost Decision Layer
* Final classification: **Fraud / Normal**
* Learns complex non-linear patterns from anomaly features

---

## Results

### Performance Highlights

* **AUC ≈ 0.81 (XGBoost layer)**
* Improved fraud detection over standalone models
* Better handling of:
  * Cold-start users
  * Sparse data
  * Behavioral anomalies

### Key Insights

* Personalization reduces false positives
* Model adapts to user-specific spending habits
* Works well on both real-world and synthetic datasets

---

## Datasets Used

Due to size limitations, datasets are not included in this repository.

### 1. IEEE-CIS Fraud Detection Dataset
- IEEE-CIS Dataset: https://www.kaggle.com/c/ieee-fraud-detection
* ~590K transactions
* Highly imbalanced (≈3.5% fraud)
* 430+ anonymized features

### 2. Synthetic Dataset

* ~2.5M transactions
* Explicit user behavior modeling
* Designed for sequential anomaly detection

---

## Tech Stack

* **Python 3.8+**
* **PyTorch** → GAN + LSTM models
* **XGBoost** → Classification layer
* **NumPy / Pandas** → Data processing
* **Matplotlib / Seaborn** → Visualization

---

## How to Run

### 1. Clone repository

```
git clone https://github.com/aaronjames09/account-ganomaly.git
cd account-ganomaly
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Run notebook

Open:

```
Final_Account_Ganomaly.ipynb
```

Run all cells.

---

## Challenges Addressed

* **Cold-start problem** → handled using history-gated encoder
* **Data sparsity** → personalized embeddings
* **Adversarial instability** → tuned GAN training
* **Concept drift** → adaptable user profiles

---

## Future Improvements

* Real-time fraud detection API
* Deployment using Flask/FastAPI
* Online learning for evolving behavior
* Integration with banking systems

---

## Why This Project Stands Out

* Combines **unsupervised + supervised learning**
* Focuses on **user-level personalization**
* Solves **real-world fraud detection limitations**
* Strong foundation for **startup or product development**

---

---
