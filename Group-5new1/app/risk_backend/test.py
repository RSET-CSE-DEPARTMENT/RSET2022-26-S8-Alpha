import requests

data = {
    "avg_screen_time": 8,
    "social_media_hours": 3,
    "gaming_hours": 3,
    "night_usage": 2,
    "phone_checks_per_day": 140,
    "entertainment_ratio": 0.75,
    "night_usage_ratio": 0.25,
    "engagement_intensity": 1120,
    "gaming_ratio": 0.375,
    "social_ratio": 0.375
}

response = requests.post("http://127.0.0.1:5000/analyze", json=data)
print(response.json())
