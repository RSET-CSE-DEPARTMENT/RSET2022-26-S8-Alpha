"""
Flask web application for the Case Scraper Admin Dashboard.
Connects to MongoDB to list cases and triggers scraping.
"""
import os
from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
from bson import ObjectId
from scraper import ScrapeJob
import firebase_admin
from firebase_admin import credentials, messaging

app = Flask(__name__)

# --- MongoDB Connection ---
MONGO_URI = "mongodb+srv://lawyer_user:12341234@casedata.trucxkk.mongodb.net/?appName=CaseData"
client = MongoClient(MONGO_URI)
db = client["Case"]
cases_collection = db["CaseDetails"]

# --- Firebase Admin SDK Init ---
# Set GOOGLE_APPLICATION_CREDENTIALS env var OR provide path to your service account JSON
FCM_SERVICE_ACCOUNT_PATH = os.environ.get("FCM_SERVICE_ACCOUNT", "firebase-service-account.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(FCM_SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)

# FCM topic to push case updates to (mobile devices subscribe to this topic)
FCM_TOPIC = "case_updates"

# --- Global Scrape Job ---
scrape_job = ScrapeJob()


def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict."""
    doc["_id"] = str(doc["_id"])
    return doc


def send_fcm_topic_notification(cnr_number: str, next_list: str, latest_proceedings: str):
    """
    Send a push notification to the FCM topic with case update details.
    Only sends CNR Number, Next List date, and the latest Proceedings.
    """
    try:
        # Build a concise data payload (works on both Android & iOS background)
        data_payload = {
            "cnr_number": cnr_number or "",
            "next_list": next_list or "",
            "latest_proceedings": latest_proceedings or "",
        }

        # Human-readable notification for foreground display
        notification_title = f"Case Update: {cnr_number}"
        notification_body = latest_proceedings or "Case details updated."

        message = messaging.Message(
            topic=FCM_TOPIC,
            notification=messaging.Notification(
                title=notification_title,
                body=notification_body,
            ),
            data=data_payload,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    click_action="OPEN_CASE_DETAIL",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound="default",
                        badge=1,
                    )
                )
            ),
        )

        response = messaging.send(message)
        print(f"[FCM] Notification sent to topic '{FCM_TOPIC}': {response}")
        return True, response

    except Exception as e:
        print(f"[FCM] Failed to send notification: {e}")
        return False, str(e)


def extract_fcm_fields(scraped_data: dict) -> tuple:
    """
    Extract Next List date and the latest Proceedings from scraped data.
    Returns (next_list, latest_proceedings).
    """
    case_details = scraped_data.get("Case Details", {})
    next_list = case_details.get("Next List", "") if isinstance(case_details, dict) else ""

    # Get Proceedings from the first (most recent) entry in Case History
    history = scraped_data.get("Case History", [])
    latest_proceedings = ""
    if isinstance(history, list) and len(history) > 0:
        latest = history[0]  # first entry is the most recent hearing
        if isinstance(latest, dict):
            latest_proceedings = latest.get("Proceedings", "")

    return next_list, latest_proceedings



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/cases", methods=["GET"])
def get_cases():
    """Fetch all cases from MongoDB with optional search."""
    search = request.args.get("search", "").strip()
    query = {}
    if search:
        query = {
            "$or": [
                {"cnr_number": {"$regex": search, "$options": "i"}},
                {"case_status": {"$regex": search, "$options": "i"}},
                {"district": {"$regex": search, "$options": "i"}},
                {"court": {"$regex": search, "$options": "i"}},
            ]
        }
    try:
        docs = list(cases_collection.find(query))
        cases = [serialize_doc(d) for d in docs]
        return jsonify({"success": True, "cases": cases})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/cases", methods=["POST"])
def add_case():
    """Add a new case to MongoDB."""
    data = request.get_json()
    cnr = data.get("cnr_number", "").strip()
    district = data.get("district", "").strip()
    court = data.get("court", "").strip()

    if not cnr or not district or not court:
        return jsonify({"success": False, "error": "CNR, District, and Court are required."}), 400

    existing = cases_collection.find_one({"cnr_number": cnr})
    if existing:
        cases_collection.update_one(
            {"cnr_number": cnr},
            {"$set": {"district": district, "court": court}}
        )
        return jsonify({"success": True, "message": "Case updated with district/court."})

    new_case = {
        "cnr_number": cnr,
        "district": district,
        "court": court,
        "case_status": "",
        "next_hearing_date": "",
    }
    cases_collection.insert_one(new_case)
    return jsonify({"success": True, "message": "Case added successfully."})


@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    """Trigger scraping for a specific case."""
    if scrape_job.status in ("running", "waiting_captcha"):
        return jsonify({"success": False, "error": "A scrape is already in progress."}), 409

    data = request.get_json()
    district = data.get("district", "").strip()
    court = data.get("court", "").strip()
    cnr_number = data.get("cnr_number", "").strip()

    if not district or not court or not cnr_number:
        return jsonify({"success": False, "error": "District, Court, and CNR Number are required."}), 400

    scrape_job.run(district, court, cnr_number)
    return jsonify({"success": True, "message": "Scraping started."})


@app.route("/api/scrape-status", methods=["GET"])
def scrape_status():
    """Get current scrape job status."""
    response = {
        "status": scrape_job.status,
        "message": scrape_job.message,
    }
    if scrape_job.status == "waiting_captcha" and scrape_job.captcha_image_b64:
        response["captcha_image"] = scrape_job.captcha_image_b64
    if scrape_job.status == "completed" and scrape_job.result:
        response["result"] = scrape_job.result
    if scrape_job.status == "error" and scrape_job.error:
        response["error"] = scrape_job.error
    return jsonify(response)


@app.route("/api/captcha", methods=["POST"])
def submit_captcha():
    """Submit captcha answer from the web UI."""
    if scrape_job.status != "waiting_captcha":
        return jsonify({"success": False, "error": "No captcha pending."}), 400

    data = request.get_json()
    answer = data.get("answer", "").strip()
    if not answer:
        return jsonify({"success": False, "error": "Captcha answer is required."}), 400

    scrape_job.captcha_answer = answer
    scrape_job.captcha_event.set()
    return jsonify({"success": True, "message": "Captcha submitted."})


@app.route("/api/save-result", methods=["POST"])
def save_result():
    """Save scraped result back to the case in MongoDB and push FCM notification."""
    data = request.get_json()
    cnr = data.get("cnr_number", "").strip()
    result = data.get("result")

    if not cnr or not result:
        return jsonify({"success": False, "error": "CNR and result required."}), 400

    # Extract useful info from scraped data
    scraped = result.get("scraped_data", {})
    case_details = scraped.get("Case Details", {})
    update_fields = {"scraped_data": scraped}

    next_hearing = ""
    if isinstance(case_details, dict):
        if case_details.get("Case Status"):
            update_fields["case_status"] = case_details["Case Status"]
        if case_details.get("Next Hearing Date"):
            next_hearing = case_details["Next Hearing Date"]
            update_fields["next_hearing_date"] = next_hearing

    # Also store network data if available
    network = result.get("network_data")
    if network:
        update_fields["network_data"] = network

    cases_collection.update_one(
        {"cnr_number": cnr},
        {"$set": update_fields}
    )

    # --- FCM Push Notification ---
    next_list, latest_proceedings = extract_fcm_fields(scraped)
    fcm_sent, fcm_response = send_fcm_topic_notification(cnr, next_list, latest_proceedings)

    return jsonify({
        "success": True,
        "message": "Result saved to MongoDB.",
        "fcm_sent": fcm_sent,
        "fcm_response": fcm_response if fcm_sent else str(fcm_response),
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)