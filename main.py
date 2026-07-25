import cv2

from vision.detector import PoseDetector


detector = PoseDetector()


cap = cv2.VideoCapture(0)


while True:

    ret, frame = cap.read()

    if not ret:
        break


    corps = detector.detect(frame)


    print("Y du poignet gauche :")
    print(corps.poignet_gauche.x)

    print("Y de l'épaule gauche :")
    print(corps.epaule_gauche.x)

    if corps.poignet_gauche.y < corps.epaule_gauche.y:
        print("MAIN GAUCHE EN HAUT")

    cv2.namedWindow('Test Body', cv2.WINDOW_NORMAL)

    cv2.imshow(
        "Test Body",
        frame
    )


    if cv2.waitKey(10) & 0xFF == ord("q"):
        break



cap.release()
cv2.destroyAllWindows()

detector.close()