import cv2
import threading

import state

from web.app import lancer_site

from vision.detector import PoseDetector
from vision.dessin import dessiner_squelette

from mouvements.positions import (
    bras_droit_leve,
    bras_gauche_leve,
    bras_en_x
)

from mouvements.exercices import (
    curl_biceps_droit
)

from mouvements.compteur import (
    CompteurMouvement
)


# ==========================================================
# SERVEUR WEB
# ==========================================================

threading.Thread(
    target=lancer_site,
    daemon=True
).start()


# ==========================================================
# INITIALISATION
# ==========================================================

detector = PoseDetector()

cap = cv2.VideoCapture(0)

# Compteur du curl biceps droit
compteur_curl = CompteurMouvement()


# ==========================================================
# BOUCLE PRINCIPALE
# ==========================================================

while True:

    ret, frame = cap.read()

    if not ret:
        break


    # ------------------------------------------------------
    # DÉTECTION DU CORPS
    # ------------------------------------------------------

    corps = detector.detect(frame)


    if corps:

        # ==================================================
        # POSITIONS
        # ==================================================

        if bras_droit_leve(corps):

            state.position_actuelle = "Bras droit levé"


        elif bras_gauche_leve(corps):

            state.position_actuelle = "Bras gauche levé"


        elif bras_en_x(corps):

            state.position_actuelle = "Bras en X"


        else:

            state.position_actuelle = "Aucune"


        # ==================================================
        # EXERCICE : CURL BICEPS DROIT
        # ==================================================

        state.exercice_actuel = "Curl biceps droit"


        # Détection de la phase du mouvement
        stage_detecte = curl_biceps_droit(corps)


        # Mise à jour de la machine d'état
        stage, repetitions = compteur_curl.mettre_a_jour(
            stage_detecte
        )


        # Envoi des informations vers state.py
        state.stage = stage
        state.repetitions = repetitions


        # ==================================================
        # DESSIN DU SQUELETTE
        # ==================================================

        frame = dessiner_squelette(
            frame,
            corps
        )


    else:

        # ==================================================
        # AUCUN CORPS DÉTECTÉ
        # ==================================================

        state.position_actuelle = "Aucun corps détecté"

        state.exercice_actuel = "Aucun"

        state.stage = "Aucune"


    # ======================================================
    # ENCODAGE DE LA VIDÉO
    # ======================================================

    succes, buffer = cv2.imencode(
        ".jpg",
        frame
    )


    if succes:

        state.frame_actuelle = buffer.tobytes()


# ==========================================================
# FERMETURE
# ==========================================================

cap.release()

detector.close()

cv2.destroyAllWindows()