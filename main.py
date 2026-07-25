"""
Curl Counter avec MediaPipe - API Tasks, utilisant les utilitaires de dessin
intégrés à mediapipe.tasks.python.vision (drawing_utils / drawing_styles).
Cette version n'importe PAS mediapipe.framework ni mp.solutions.
"""

import os
import time
import urllib.request

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils,drawing_styles
import fonctions

# ---------------------------------------------------------------------------
# 0. Télécharger le modèle si besoin
# ---------------------------------------------------------------------------
MODEL_PATH = "pose_landmarker_lite.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)

if not os.path.exists(MODEL_PATH):
    print("Téléchargement du modèle...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

# ---------------------------------------------------------------------------
# 1. Configurer le PoseLandmarker
# ---------------------------------------------------------------------------
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    min_pose_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)
landmarker = vision.PoseLandmarker.create_from_options(options)

# Indices des landmarks
LEFT_SHOULDER = 11
LEFT_ELBOW = 13
LEFT_WRIST = 15

# ---------------------------------------------------------------------------
# Curl Counter avec webcam
# ---------------------------------------------------------------------------
cv2.namedWindow('Mediapipe Feed (Tasks API)', cv2.WINDOW_NORMAL)

cap = cv2.VideoCapture(0)

counter = 0
stage = None

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    timestamp_ms = int(time.time() * 1000)
    detection_result = landmarker.detect_for_video(mp_image, timestamp_ms)

    image = frame.copy()

    try:
        landmarks = detection_result.pose_landmarks[0]

        shoulder = [landmarks[LEFT_SHOULDER].x, landmarks[LEFT_SHOULDER].y]
        elbow = [landmarks[LEFT_ELBOW].x, landmarks[LEFT_ELBOW].y]
        wrist = [landmarks[LEFT_WRIST].x, landmarks[LEFT_WRIST].y]

        angle = fonctions.calculate_angle(shoulder, elbow, wrist)

        cv2.putText(
            image,
            str(int(angle)),
            tuple(np.multiply(elbow, [640, 480]).astype(int)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        if angle > 160:
            stage = "down"
        if angle < 30 and stage == "down":
            stage = "up"
            counter += 1
            print(counter)

    except IndexError:
        pass

    cv2.rectangle(image, (0, 0), (225, 73), (245, 117, 16), -1)
    cv2.putText(image, "REPS", (15, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(image, str(counter), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(image, "STAGE", (65, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(image, str(stage), (60, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    result_image = fonctions.draw_landmarks_on_image(image_rgb, detection_result)
    result_image_bgr = cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR)

    cv2.imshow("Mediapipe Feed (Tasks API)", result_image_bgr)

    if cv2.waitKey(10) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
landmarker.close()