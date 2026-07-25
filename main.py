import cv2

from vision.detector import PoseDetector


detector = PoseDetector()


cap = cv2.VideoCapture(0)


while True:

    ret, frame = cap.read()

    if not ret:
        break


    pose = detector.detect(frame)


    if pose:

        print("--------------------")

        print(
            "Poignet gauche :",
            pose[15]
        )

        print(
            "Épaule gauche :",
            pose[11]
        )


    cv2.imshow(
        "Pose detector",
        frame
    )


    if cv2.waitKey(10) & 0xFF == ord("q"):
        break



cap.release()
cv2.destroyAllWindows()

detector.close()