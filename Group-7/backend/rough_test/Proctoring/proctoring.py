import cv2
import mediapipe as mp
import numpy as np
from datetime import datetime

# ----------------------------------------
# Logging Setup
# ----------------------------------------
LOG_FILE = "proctoring_log.txt"

def log_event(message):
    with open(LOG_FILE, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")

print(f"Logging to {LOG_FILE}")

previous_status = None

# ----------------------------------------
# MediaPipe setup
# ----------------------------------------
mp_face = mp.solutions.face_detection
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

face_detector = mp_face.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.6
)

hand_detector = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# ----------------------------------------
# Background Subtractor
# ----------------------------------------
bg_subtractor = cv2.createBackgroundSubtractorMOG2(
    history=200,
    varThreshold=50,
    detectShadows=True
)

# ----------------------------------------
# Webcam
# ----------------------------------------
cap = cv2.VideoCapture(0)
print("Press 'q' to quit")

hand_near_face_frames = 0
HAND_FACE_THRESHOLD = 15

# ----------------------------------------
# Background object persistence
# ----------------------------------------
background_object_active = False
no_object_frames = 0
CLEAR_THRESHOLD = 20

# ----------------------------------------
# Main Loop
# ----------------------------------------
while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # ----------------------------------------
    # FACE DETECTION
    # ----------------------------------------
    faces = []
    face_results = face_detector.process(rgb)

    if face_results.detections:
        for det in face_results.detections:
            box = det.location_data.relative_bounding_box
            x = int(box.xmin * w)
            y = int(box.ymin * h)
            fw = int(box.width * w)
            fh = int(box.height * h)

            faces.append((x, y, fw, fh))

            cv2.rectangle(frame, (x, y), (x + fw, y + fh),
                          (255, 0, 0), 2)

    # ----------------------------------------
    # HAND DETECTION
    # ----------------------------------------
    hand_results = hand_detector.process(rgb)

    if hand_results.multi_hand_landmarks:
        for hand_landmarks in hand_results.multi_hand_landmarks:
            mp_draw.draw_landmarks(
                frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
            )

            palm_x = int(hand_landmarks.landmark[9].x * w)
            palm_y = int(hand_landmarks.landmark[9].y * h)

            for (fx, fy, fw, fh) in faces:
                if fx < palm_x < fx + fw and fy < palm_y < fy + fh:
                    hand_near_face_frames += 1
                    break
    else:
        hand_near_face_frames = max(0, hand_near_face_frames - 1)

    # ----------------------------------------
    # BACKGROUND OBJECT DETECTION
    # ----------------------------------------
    fg_mask = bg_subtractor.apply(frame)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
    fg_mask = cv2.dilate(fg_mask, kernel, iterations=2)

    contours, _ = cv2.findContours(
        fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    detected_this_frame = False

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 4000:
            continue

        x, y, w2, h2 = cv2.boundingRect(cnt)

        ignore = False
        for (fx, fy, fw, fh) in faces:
            if x < fx + fw and x + w2 > fx and y < fy + fh and y + h2 > fy:
                ignore = True
                break

        if ignore:
            continue

        detected_this_frame = True

        cv2.rectangle(frame, (x, y), (x + w2, y + h2),
                      (0, 255, 255), 2)
        cv2.putText(frame, "BACKGROUND OBJECT",
                    (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 255), 2)

    # ----------------------------------------
    # PERSISTENCE LOGIC
    # ----------------------------------------
    if detected_this_frame:
        background_object_active = True
        no_object_frames = 0
    else:
        if background_object_active:
            no_object_frames += 1
            if no_object_frames >= CLEAR_THRESHOLD:
                background_object_active = False
                no_object_frames = 0

    # ----------------------------------------
    # FINAL DECISION
    # ----------------------------------------
    if len(faces) == 0:
        status = "Face not detected"
    elif len(faces) > 1:
        status = "Multiple faces detected"
    elif background_object_active:
        status = "Background object detected"
    elif hand_near_face_frames > HAND_FACE_THRESHOLD:
        status = "Suspicious behavior detected"
    else:
        status = "Candidate OK"

    # ----------------------------------------
    # LOGGING + SCREENSHOT
    # ----------------------------------------
    if status != previous_status:
        log_event(status)

        if status != "Candidate OK":
            filename = f"violation_{datetime.now().strftime('%H%M%S')}.jpg"
            cv2.imwrite(filename, frame)

        previous_status = status

    # ----------------------------------------
    # DISPLAY STATUS
    # ----------------------------------------
    cv2.putText(frame, status, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1,
                (0, 255, 0) if status == "Candidate OK" else (0, 0, 255), 2)

    cv2.imshow("AI Interview Proctoring", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
