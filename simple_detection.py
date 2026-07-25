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
      cv2.putText(image, "REPS", (15, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
cap.release()
cv2.destroyAllWindows()