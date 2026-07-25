import time
import cv2
import mediapipe as mp
import urllib.request
import os
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from vision.body import Body, LandmarkPoint
from vision.landmarks import LANDMARKS

MODEL_PATH = "pose_landmarker_lite.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)

if not os.path.exists(MODEL_PATH):
    print("Téléchargement du modèle...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)



class PoseDetector:

    def __init__(self):

        base_options = python.BaseOptions(
            model_asset_path=MODEL_PATH
        )

        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            min_pose_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self.landmarker = vision.PoseLandmarker.create_from_options(
            options
        )


    def detect(self, frame):
        """Entrée : frame OpenCV (BGR)
        Sortie : dictionnaire contenant les landmarks"""

        rgb = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb)
        timestamp = int(time.time() * 1000)
        result = self.landmarker.detect_for_video(mp_image,timestamp)
        if not result.pose_landmarks:
            return None
        
        landmarks = result.pose_landmarks[0]
        points = {}
        for nom, index in LANDMARKS.items():
            point = landmarks[index]
            points[nom] = LandmarkPoint(
                point.x,
                point.y,
                point.z,
                point.visibility)
        return Body(points)


    def close(self):
        self.landmarker.close()

print("Detector chargé")
print(PoseDetector)