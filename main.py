import cv2
import threading

import state

from web.app import lancer_site

from vision.detector import PoseDetector

from mouvements.positions import (
    bras_droit_leve,
    bras_gauche_leve,
    bras_en_x
)


# -----------------------------
# Lancer le serveur web
# -----------------------------

threading.Thread(
    target=lancer_site,
    daemon=True
).start()


# -----------------------------
# Initialisation
# -----------------------------

detector = PoseDetector()

cap = cv2.VideoCapture(0)


# -----------------------------
# Boucle principale
# -----------------------------

while True:

    ret, frame = cap.read()

    if not ret:
        break


    # -------------------------
    # Détection du corps
    # -------------------------

    corps = detector.detect(frame)


    if corps:

        if bras_droit_leve(corps):

            state.position_actuelle = "Bras droit levé"


        elif bras_gauche_leve(corps):

            state.position_actuelle = "Bras gauche levé"


        elif bras_en_x(corps):

            state.position_actuelle = "Bras en X"


        else:

            state.position_actuelle = "Aucune"


    else:

        state.position_actuelle = "Aucun corps détecté"


    # -------------------------
    # Transformer l'image en JPEG
    # -------------------------

    succes, buffer = cv2.imencode(
        ".jpg",
        frame
    )


    if succes:

        state.frame_actuelle = buffer.tobytes()


# -----------------------------
# Fermeture
# -----------------------------

cap.release()

detector.close()