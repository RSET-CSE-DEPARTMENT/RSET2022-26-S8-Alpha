"""
services/proctoring_service.py

Live video proctoring service using OpenCV and MediaPipe.
MediaPipe imports are lazy to avoid crashing the server if
mediapipe/tensorflow have compatibility issues on certain setups.
"""

import base64
import cv2
import numpy as np

# Lazy-loaded mediapipe references
_mp_face = None
_mp_hands = None
_mp_available = None


def _ensure_mediapipe():
    """Try to import mediapipe; return True if available."""
    global _mp_face, _mp_hands, _mp_available
    if _mp_available is not None:
        return _mp_available
    try:
        import mediapipe as mp
        _mp_face = mp.solutions.face_detection
        _mp_hands = mp.solutions.hands
        _mp_available = True
        print("[Proctoring] MediaPipe loaded successfully.")
    except Exception as e:
        _mp_available = False
        print(f"[Proctoring] WARNING: MediaPipe unavailable ({e}). "
              "Proctoring will use OpenCV-only fallback.")
    return _mp_available


class ProctoringSession:
    def __init__(self):
        self.use_mediapipe = _ensure_mediapipe()

        if self.use_mediapipe:
            self.face_detector = _mp_face.FaceDetection(
                model_selection=0,
                min_detection_confidence=0.6
            )
            self.hand_detector = _mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6
            )
        else:
            self.face_detector = None
            self.hand_detector = None
            # OpenCV Haar cascade fallback
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=200,
            varThreshold=50,
            detectShadows=True
        )
        
        self.hand_near_face_frames = 0
        
        # We assume slower frame rate over WS (e.g. 1-2 fps), so lower thresholds
        self.HAND_FACE_THRESHOLD = 3
        self.CLEAR_THRESHOLD = 5
        
        self.background_object_active = False
        self.no_object_frames = 0
        
        self.previous_status = "Candidate OK"

    def process_frame(self, base64_image_data: str) -> str | None:
        """
        Processes a single base64-encoded JPEG/PNG frame.
        Returns the new status string if the status has changed, otherwise None.
        """
        try:
            if base64_image_data.startswith('data:image'):
                base64_image_data = base64_image_data.split(',')[1]

            image_bytes = base64.b64decode(base64_image_data)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return None
        except Exception as e:
            print(f"[Proctoring] Frame decode error: {e}")
            return None

        h, w, _ = frame.shape

        # ----------------------------------------
        # 1. FACE DETECTION
        # ----------------------------------------
        faces = []

        if self.use_mediapipe:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_results = self.face_detector.process(rgb)
            if face_results.detections:
                for det in face_results.detections:
                    box = det.location_data.relative_bounding_box
                    x = int(box.xmin * w)
                    y = int(box.ymin * h)
                    fw = int(box.width * w)
                    fh = int(box.height * h)
                    faces.append((x, y, fw, fh))
        else:
            # OpenCV Haar cascade fallback
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )
            for (x, y, fw, fh) in detected:
                faces.append((int(x), int(y), int(fw), int(fh)))

        # ----------------------------------------
        # 2. HAND DETECTION (mediapipe only)
        # ----------------------------------------
        if self.use_mediapipe:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hand_results = self.hand_detector.process(rgb)
            if hand_results.multi_hand_landmarks:
                for hand_landmarks in hand_results.multi_hand_landmarks:
                    palm_x = int(hand_landmarks.landmark[9].x * w)
                    palm_y = int(hand_landmarks.landmark[9].y * h)
                    for (fx, fy, fw, fh) in faces:
                        padding_x = int(fw * 0.3)
                        padding_y = int(fh * 0.3)
                        if (fx - padding_x) < palm_x < (fx + fw + padding_x) and \
                           (fy - padding_y) < palm_y < (fy + fh + padding_y):
                            self.hand_near_face_frames += 1
                            break
            else:
                self.hand_near_face_frames = max(0, self.hand_near_face_frames - 1)
        else:
            # No hand detection in fallback mode
            self.hand_near_face_frames = max(0, self.hand_near_face_frames - 1)

        # ----------------------------------------
        # 3. BACKGROUND OBJECT DETECTION
        # ----------------------------------------
        fg_mask = self.bg_subtractor.apply(frame)

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
            break

        # ----------------------------------------
        # PERSISTENCE LOGIC
        # ----------------------------------------
        if detected_this_frame:
            self.background_object_active = True
            self.no_object_frames = 0
        else:
            if self.background_object_active:
                self.no_object_frames += 1
                if self.no_object_frames >= self.CLEAR_THRESHOLD:
                    self.background_object_active = False
                    self.no_object_frames = 0

        # ----------------------------------------
        # FINAL DECISION
        # ----------------------------------------
        if len(faces) == 0:
            status = "Face not detected"
        elif len(faces) > 1:
            status = "Multiple faces detected"
        elif self.background_object_active:
            status = "Background object detected"
        elif self.hand_near_face_frames > self.HAND_FACE_THRESHOLD:
            status = "Suspicious behavior detected"
        else:
            status = "Candidate OK"

        if status != self.previous_status:
            self.previous_status = status
            return status

        return None

    def close(self):
        """Clean up MediaPipe resources."""
        if self.use_mediapipe:
            if hasattr(self, 'face_detector') and self.face_detector:
                self.face_detector.close()
            if hasattr(self, 'hand_detector') and self.hand_detector:
                self.hand_detector.close()
