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

from mouvements.outils import HoldPosition


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

# Maintien des bras en X pendant 1,5 seconde
hold_bras_x = HoldPosition(
    bras_en_x,
    1.5
)


# ==========================================================
# BOUCLE PRINCIPALE
# ==========================================================

while True:

    ret, frame = cap.read()

    if not ret:
        break


    # ======================================================
    # DÉTECTION DU CORPS
    # ======================================================

    corps = detector.detect(frame)


    if corps:

        # ==================================================
        # POSITIONS
        # ==================================================

        bras_x = bras_en_x(corps)


        if bras_droit_leve(corps):

            state.position_actuelle = "Bras droit levé"


        elif bras_gauche_leve(corps):

            state.position_actuelle = "Bras gauche levé"


        elif bras_x:

            state.position_actuelle = "Bras en X"


        else:

            state.position_actuelle = "Aucune"


        # ==================================================
        # EXERCICE : CURL BICEPS DROIT
        # ==================================================

        state.exercice_actuel = "Curl biceps droit"

        stage_detecte = curl_biceps_droit(corps)


        # Mise à jour du compteur
        stage, repetitions = compteur_curl.mettre_a_jour(
            stage_detecte
        )

        state.stage = stage
        state.repetitions = repetitions


        # ==================================================
        # MAINTIEN DES BRAS EN X
        # ==================================================

        progression, maintien_termine = hold_bras_x.update(
            corps
        )

        state.progression_maintien = progression
        state.maintien_termine = maintien_termine


        # ==================================================
        # RESET DES RÉPÉTITIONS
        # ==================================================

        if maintien_termine:

            compteur_curl.reset()

            state.repetitions = 0


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

        state.progression_maintien = 0

        state.maintien_termine = False


    # ======================================================
    # ENCODAGE DE LA VIDÉO POUR LE SITE
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