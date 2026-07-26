import time
import state

# VISION
import cv2
from vision.detector import PoseDetector
from vision.dessin import dessiner_squelette

# POSITIONS

from mouvements.positions import (
    bras_droit_leve,
    bras_gauche_leve,
    bras_en_x
)

# COMPTEUR

from mouvements.compteur import CompteurMouvement

# MAINTIEN

from mouvements.outils import HoldPosition

# SITE WEB
import threading
import webbrowser
from web.app import lancer_site, ouvrir_navigateur


# CIRCUIT

from seance.seance_test import seance


# ==========================================
# LANCEMENT DU SITE
# ==========================================

threading.Thread(
    target=lancer_site,
    daemon=True
).start()

def ouvrir_navigateur():
    time.sleep(1)  # laisse le temps à Flask de démarrer
    webbrowser.open("http://127.0.0.1:5000")

threading.Thread(
    target=ouvrir_navigateur,
    daemon=True
).start()

# ==========================================
# DETECTEUR
# ==========================================

detector = PoseDetector()


# ==========================================
# CAMERA
# ==========================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Impossible d'ouvrir la caméra.")
    detector.close()
    raise SystemExit


# ==========================================
# COMPTEUR DE MOUVEMENT
# ==========================================

compteur = CompteurMouvement()


# ==========================================
# MAINTIEN BRAS EN X
# ==========================================

hold_bras_x = HoldPosition(
    bras_en_x,
    1.5
)


# ==========================================
# BOUCLE PRINCIPALE
# ==========================================

try:

    while True:

        # ======================================
        # LECTURE DE LA CAMERA
        # ======================================

        ret, frame = cap.read()

        if not ret:
            print("Impossible de lire la caméra.")
            break


        # ======================================
        # DETECTION DU CORPS
        # ======================================

        corps = detector.detect(frame)


        if corps is not None:

            # ==================================
            # POSITIONS
            # ==================================

            if bras_droit_leve(corps):

                state.position_actuelle = (
                    "Bras droit levé"
                )

            elif bras_gauche_leve(corps):

                state.position_actuelle = (
                    "Bras gauche levé"
                )

            elif bras_en_x(corps):

                state.position_actuelle = (
                    "Bras en X"
                )

            else:

                state.position_actuelle = (
                    "Aucune"
                )


            # ==================================
            # MAINTIEN BRAS EN X
            # ==================================

            progression, termine = (
                hold_bras_x.update(corps)
            )

            state.progression_maintien = progression
            state.maintien_termine = termine


            # ==================================
            # RESET DES REPETITIONS
            # ==================================

            if termine:

                compteur.reset()

                state.repetitions = 0


            # ==================================
            # MACHINE DU CIRCUIT
            # ==================================

            seance.update()


            # ==================================
            # INFORMATIONS DU CIRCUIT
            # ==================================

            state.phase = seance.phase

            state.serie_actuelle = (
                seance.serie_actuelle
            )

            state.nombre_series = (
                seance.nombre_series
            )

            state.repetitions_cibles = (
                seance.repetitions_cibles
            )

            state.temps_restant = (
                seance.temps_restant
            )


            # ==================================
            # EXERCICE EN COURS
            # ==================================

            if seance.phase == "exercice":

                exercice = seance.exercice_actuel


                # ----------------------------------
                # NOM DE L'EXERCICE
                # ----------------------------------

                if exercice.__name__ == "curl_biceps_droit":

                    state.exercice_actuel = (
                        "Curl biceps droit"
                    )

                elif exercice.__name__ == "curl_biceps_gauche":

                    state.exercice_actuel = (
                        "Curl biceps gauche"
                    )

                else:

                    state.exercice_actuel = (
                        exercice.__name__
                    )


                # ----------------------------------
                # DETECTION DU MOUVEMENT
                # ----------------------------------

                stage_detecte = exercice(corps)


                # ----------------------------------
                # COMPTEUR
                # ----------------------------------

                stage, repetitions = (
                    compteur.mettre_a_jour(
                        stage_detecte
                    )
                )

                state.stage = stage
                state.repetitions = repetitions


                # ----------------------------------
                # SERIE TERMINEE
                # ----------------------------------

                if (
                    repetitions
                    >= seance.repetitions_cibles
                ):

                    seance.terminer_serie()

                    compteur.reset()

                    state.repetitions = 0


            # ==================================
            # RECUPERATION ENTRE SERIES
            # ==================================

            elif (
                seance.phase
                == "recuperation_serie"
            ):

                state.stage = "Récupération"


            # ==================================
            # REPOS ENTRE EXERCICES
            # ==================================

            elif (
                seance.phase
                == "repos_exercice"
            ):

                state.stage = "Repos"


            # ==================================
            # FIN DE SEANCE
            # ==================================

            elif (
                seance.phase
                == "termine"
            ):

                state.exercice_actuel = (
                    "Séance terminée"
                )

                state.stage = "Terminé"


            # ==================================
            # DESSIN DU SQUELETTE
            # ==================================

            frame = dessiner_squelette(frame,)

        # ==========================================
        # ENCODAGE POUR LE FEED WEB
        # ==========================================

        succes, buffer = cv2.imencode(".jpg",frame)

        if succes:
            state.latest_frame = buffer.tobytes()


        


# ==========================================
# ARRET PROPRE
# ==========================================

except KeyboardInterrupt:

    print("Arrêt du programme...")


finally:

    cap.release()

    detector.close()

    print("Caméra arrêtée.")