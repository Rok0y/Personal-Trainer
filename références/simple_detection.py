import cv2
import mediapipe as mp
import numpy as np

cv2.namedWindow('Mediapipe Feed', cv2.WINDOW_NORMAL)

# VIDEO FEED
cap = cv2.VideoCapture(0)
while cap.isOpened():
    ret, frame = cap.read()
    cv2.imshow('Mediapipe Feed', frame)

    image = frame.copy()
    
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()