# Tous les imports
import time
import state
import cv2
import ctypes
from session.moteur import executer_mode, decrire_prochaine_etape, mettre_a_jour_prochain_exercice
from historique.database import initialiser, enregistrer_seance
from audio.lecteur import jouer
from vision.detector import PoseDetector
from vision.dessin import dessiner_squelette
from mouvements.compteur import CompteurMouvement
from mouvements.outils import HoldPosition
import threading
from web.app import lancer_site, ouvrir_navigateur, controleur
from audio.coach import coach, annoncer_prochaine_etape,annoncer_temps_repos
import session.seances
from mouvements.positions import (
    bras_droit_leve,
    bras_gauche_leve,
    bras_en_x,
    deux_bras_leves,
)

# Définition des variables
cap = cv2.VideoCapture(0)
compteur = CompteurMouvement()
hold_bras_x = HoldPosition(bras_en_x, 3)
hold_deux_bras_leves = HoldPosition(deux_bras_leves, 3)
preparation = HoldPosition(bras_en_x, 1.5)
detection = PoseDetector()
ancienne_phase = None
derniere_rep = 0
fin_preparation = None 
DELAI_AVANT_EXERCICE = 3


def empecher_veille():
    if hasattr(ctypes, "windll"):
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001 | 0x00000002)


def autoriser_veille():
    if hasattr(ctypes, "windll"):
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


controleur.definir_reset_progression(lambda: compteur.reset())
seance = controleur.selectionner("upper_push")
"""La séance active est partagée avec l'API web."""

state.prochaine_etape = decrire_prochaine_etape(
    seance.bloc_actuel,
    seance.nombre_series
)


# Initialisation de la base de données
initialiser()

# Lancement du site
threading.Thread(target=lancer_site, daemon=True).start()
threading.Thread(target=ouvrir_navigateur, daemon=True).start()


if not cap.isOpened():
    print("Impossible d'ouvrir la caméra.")
    detection.close()
    raise SystemExit

# ==========================================
# BOUCLE PRINCIPALE
# ==========================================

coach("debut")

try:

    while True:

        # LECTURE DE LA CAMERA
        ret, frame = cap.read()

        if not ret:
            print("Impossible de lire la caméra.")
            break

        seance = controleur.seance
        if controleur.statut in ("running", "paused"):
            empecher_veille()
        else:
            autoriser_veille()

        # DETECTION DU CORPS
        corps = detection.detect(frame) if controleur.statut == "running" else None
        if corps is None:
            state.erreur = None
        """cette variable dit si il y a un corps à l'écran ou non"""

        if seance is not None and controleur.statut == "running" and corps is None:
            seance.update()
            mettre_a_jour_prochain_exercice(seance, state)

        if controleur.statut == "paused":
            state.phase = "pause"
            state.stage = "En pause"
            corps = None
        if corps is not None:
            """soit si il détecte un corps à l'écran"""

            # Détection des positions de controle
            if deux_bras_leves(corps):
                state.position_actuelle = "Deux bras levés"
            elif bras_droit_leve(corps):
                state.position_actuelle = "Bras droit levé"
            elif bras_gauche_leve(corps):
                state.position_actuelle = "Bras gauche levé"
            elif bras_en_x(corps):
                state.position_actuelle = "Bras en X"
            else:
                state.position_actuelle = "Aucune"

            # Bras en X valide une série uniquement pendant l'exercice.
            progression_x, termine_x = hold_bras_x.update(corps)
            state.progression_maintien = progression_x
            state.maintien_termine = termine_x

            # Deux bras levés réinitialisent la série sans valider le résultat.
            _, reset = hold_deux_bras_leves.update(corps)
            if reset and seance.phase == "exercice":
                compteur.reset()
                state.repetitions = 0
                derniere_rep = 0

            if termine_x and seance.phase == "exercice":
                seance.terminer_serie_manuellement(
                    repetitions=state.repetitions,
                    duree=state.temps_maintien or state.temps_chrono,
                )
                compteur.reset()
                state.repetitions = 0
                derniere_rep = 0

            # ==================================
            # MACHINE DU CIRCUIT
            # ==================================
            seance.update()
            mettre_a_jour_prochain_exercice(seance, state)

            # ==================================
            # Le coach (une seule fois par changement de phase)
            # ==================================
                        
            if seance.phase != ancienne_phase:

                if seance.phase == "preparation":
                    coach("preparation")


                elif seance.phase == "exercice":

                    if ancienne_phase in (
                        "recuperation_serie",
                        "repos_exercice"
                    ):
                        coach("debut_serie")

                    seance.repos_restant_precedent = None


                elif seance.phase == "recuperation_serie":

                    coach("repos")

                    seance.repos_restant_precedent = int(
                        seance.temps_restant
                    )


                elif seance.phase == "repos_exercice":

                    coach("repos")

                    annoncer_prochaine_etape(
                        state.prochaine_etape,
                        "changement_exercice"
                    )

                    seance.repos_restant_precedent = int(
                        seance.temps_restant
                    )


                elif seance.phase == "termine":

                    coach("fin_seance")


            ancienne_phase = seance.phase

            if seance.phase == "recuperation_serie":
                annoncer_temps_repos(
                    seance,
                    state,
                    annoncer_exercice=False
                )


            elif seance.phase == "repos_exercice":

                annoncer_temps_repos(
                    seance,
                    state,
                    annoncer_exercice=False
                )        
            # ==================================
            # SEANCE TERMINEE
            # ==================================

            if seance.phase in ("termine", "abandonne"):

                controleur.marquer_terminee()

                state.phase = seance.phase
                state.serie_actuelle = 0
                state.nombre_series = 0
                state.repetitions_cibles = 0
                state.temps_repos_restant = 0
                state.poids = 0
                state.exercice_actuel = "Séance terminée"
                state.stage = "Terminé"

                if not seance.historique_enregistre and seance.a_des_resultats():
                    print(">>> ENREGISTREMENT HISTORIQUE <<<")

                    enregistrer_seance(
                        duree=seance.duree_totale,
                        exercices=seance.exporter_resultats(),
                        nom_seance=controleur.nom_selectionne,
                        statut="abandoned" if seance.phase == "abandonne" else "finished",
                    )

                    seance.historique_enregistre = True

            # ==================================
            # SEANCE EN COURS
            # ==================================

            else:

                state.phase = seance.phase
                state.serie_actuelle = seance.serie_actuelle
                state.nombre_series = seance.nombre_series
                state.repetitions_cibles = seance.repetitions_cibles
                state.temps_repos_restant = seance.temps_restant
                state.poids = seance.poids

                # ----------------------------------
                # PREPARATION (doit tourner à CHAQUE frame
                # tant qu'on est en phase "preparation", pour
                # accumuler le temps de maintien du bras en X)
                # ----------------------------------
                if seance.phase == "preparation":

                    if fin_preparation is None:
                        # Étape 1 : on attend que le maintien bras en X soit validé
                        progression, termine = preparation.update(corps)
                        state.progression_preparation = progression
                        state.stage = "Préparation"

                        if termine:
                            annoncer_prochaine_etape(
                                state.prochaine_etape,
                                "debut_serie"
                            )
                            fin_preparation = time.time()

                    else:
                        # Étape 2 : compte à rebours avant de vraiment démarrer
                        temps_ecoule = time.time() - fin_preparation
                        state.progression_preparation = 100
                        state.stage = "Prêt ! Redescendez les bras..."

                        if temps_ecoule >= DELAI_AVANT_EXERCICE:
                            coach("debut_serie")
                            seance.commencer_exercice()
                            fin_preparation = None

                # ----------------------------------
                # EXERCICE EN COURS
                # ----------------------------------
                if seance.phase == "exercice":
                    exercice = seance.exercice_actuel

                    if exercice is not None:

                        # NOM DE L'EXERCICE
                        state.exercice_actuel = exercice.nom

                        # DETECTION DU MOUVEMENT
                        stage_detecte = exercice.detection(corps)

                        # Execution du moteur d'exo
                        derniere_rep, repetitions, serie_terminee = executer_mode(
                            seance=seance,
                            corps=corps,
                            compteur=compteur,
                            state=state,
                            coach=coach,
                            derniere_rep=derniere_rep
                        )

                        # SERIE TERMINEE
                        if serie_terminee:
                            continue

                # ----------------------------------
                # RECUPERATION ENTRE SERIES
                # ----------------------------------

                elif seance.phase == "recuperation_serie":
                    state.exercice_actuel = "Récupération"
                    state.stage = "Récupération"

                # ----------------------------------
                # REPOS ENTRE EXERCICES
                # ----------------------------------

                elif seance.phase == "repos_exercice":
                    state.exercice_actuel = "Repos"
                    state.stage = "Repos"

            # ==================================
            # DESSIN DU SQUELETTE
            # ==================================

            frame = dessiner_squelette(frame, corps)

        # La fin doit être publiée même si la pose disparaît à la dernière frame.
        if seance is not None and seance.phase == "termine":
            controleur.marquer_terminee()
            state.phase = "termine"
            state.serie_actuelle = 0
            state.nombre_series = 0
            state.repetitions_cibles = 0
            state.temps_repos_restant = 0
            state.poids = 0
            state.exercice_actuel = "Séance terminée"
            state.stage = "Terminé"

        # ==========================================
        # ENCODAGE POUR LE FEED WEB
        # ==========================================

        succes, buffer = cv2.imencode(".jpg", frame)

        if succes:
            state.latest_frame = buffer.tobytes()


# ==========================================
# ARRET PROPRE
# ==========================================

except KeyboardInterrupt:

    print("Arrêt du programme...")

finally:

    cap.release()

    detection.close()
    autoriser_veille()

    print("Caméra arrêtée.")