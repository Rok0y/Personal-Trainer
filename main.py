import cv2

from vision.detector import PoseDetector
from mouvements.positions import bras_droit_leve,bras_gauche_leve,bras_en_x


detector = PoseDetector()


cap = cv2.VideoCapture(0)


while True:

    ret, frame = cap.read()

    if not ret:
        break


    corps = detector.detect(frame)

    if bras_droit_leve(corps):
        print("Bras droit leve")
    if bras_gauche_leve(corps):
        print("Bras gauche leve")
    if bras_en_x(corps):
        print("Bras en X")

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