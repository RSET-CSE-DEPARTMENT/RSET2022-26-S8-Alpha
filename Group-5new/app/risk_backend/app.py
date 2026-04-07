from journal_generator import generate_journal
from flask import Flask, request, jsonify
import joblib
import numpy as np

app = Flask(__name__)

# Load trained model
model = joblib.load("risk_model.pkl")

@app.route("/predict", methods=["POST"])
def predict():
    data = request.json

    features = np.array([[ 
        data["avg_screen_time"],
        data["social_media_hours"],
        data["gaming_hours"],
        data["night_usage"],
        
        data["phone_checks_per_day"],
        data["entertainment_ratio"],
        data["night_usage_ratio"],
        data["engagement_intensity"],
        data["gaming_ratio"],
        data["social_ratio"]
    ]])

    prediction = model.predict(features)

    return jsonify({
        "risk_level": int(prediction[0])
    })
@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json

    # Step 1: Predict risk
    features = np.array([[
        data["avg_screen_time"],
        data["social_media_hours"],
        data["gaming_hours"],
        data["night_usage"],
        data["phone_checks_per_day"],
        data["entertainment_ratio"],
        data["night_usage_ratio"],
        data["engagement_intensity"],
        data["gaming_ratio"],
        data["social_ratio"]
    ]])

    prediction = model.predict(features)
    risk = int(prediction[0])

    # Step 2: Add risk to data
    data["risk_level"] = risk

    # Step 3: Generate AI journal
    journal = generate_journal(data)

    return jsonify({
        "risk_level": risk,
        "journal": journal
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)  