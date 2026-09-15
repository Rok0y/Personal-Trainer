"""
Script de TEST — squelette + positions uniquement
====================================================
But : isoler juste la partie caméra / détection de pose / dessin du
squelette, sans la machine à séances, le coach vocal ou le site web.
Sert à tester rapidement de nouvelles fonctions de position pendant
qu'on ajoute des exercices.

Touches :
  q  -> quitter
  p  -> afficher les coordonnées brutes du corps détecté dans la console
        (pratique pour écrire une nouvelle fonction de position)

Il répond aussi à la question **« l'image est-elle en miroir ? »**, qui décide
de tout l'étiquetage droite/gauche et qu'aucun œil ne tranche de façon fiable :
on est habitué à se voir retourné, donc une image miroir passe pour normale.
Voir `CLAUDE.md` — le miroir de ce poste ne vient pas du code, il n'y a aucun
`flip` dans le projet, il vient entièrement de la source (Camo).
"""

import cv2

from mouvements.positions import bras_droit_leve, bras_en_x, bras_gauche_leve
from vision.dessin import dessiner_squelette
from vision.detector import PoseDetector

#: Écart horizontal minimal entre les deux épaules, en largeurs d'image, pour
#: que le verdict miroir ait un sens. De profil ou de dos elles se superposent
#: et le test ne dit plus rien : mieux vaut se taire que de trancher à pile ou
#: face sur une pose qui ne porte pas l'information.
ECART_EPAULES_MINIMAL = 0.08


def verdict_miroir(corps):
    """L'image reçue est-elle retournée ? Rend (message, couleur BGR).

    **MediaPipe étiquette les membres du point de vue du sujet**, en supposant
    une image non retournée : quelqu'un qui fait face à l'objectif a donc son
    épaule *droite* dans la moitié *gauche* de l'image. Si l'inverse est vrai,
    c'est que la source retourne l'image — et le modèle, qui ne peut pas le
    savoir, appelle « droit » ce qui est le bras gauche. « Curl biceps droit »
    compte alors l'autre bras, sans que rien ne le signale.

    C'est une **mesure et non un jugement**, et c'est tout l'intérêt : on ne
    demande pas à quelqu'un de dire s'il se voit en miroir, puisque c'est
    précisément ce dont l'habitude nous rend mauvais juges.
    """
    epaule_droite = corps.epaule_droite
    epaule_gauche = corps.epaule_gauche
    ecart = epaule_gauche.x - epaule_droite.x

    if abs(ecart) < ECART_EPAULES_MINIMAL:
        return "Mets-toi FACE a la camera (epaules superposees)", (0, 200, 255)
    if ecart > 0:
        return "Image NON miroir - etiquetage droite/gauche fiable", (0, 255, 0)
    return "IMAGE EN MIROIR - droite et gauche sont INVERSEES", (0, 0, 255)

# ------------------------------------------------------------------
# Ajoute ici tes nouvelles fonctions de position à tester, par ex :
# from mouvements.positions import squat_bas
# ------------------------------------------------------------------

# Liste (nom affiché, fonction) -> pour tester plusieurs positions
# d'un coup sans dupliquer le code d'affichage.
POSITIONS_A_TESTER = [
    ("Bras droit leve", bras_droit_leve),
    ("Bras gauche leve", bras_gauche_leve),
    ("Bras en X", bras_en_x),
    # ("Squat bas", squat_bas),
]

cap = cv2.VideoCapture(0)
detection = PoseDetector()

if not cap.isOpened():
    print("Impossible d'ouvrir la camera.")
    detection.close()
    raise SystemExit

print("Script de test lance. 'q' pour quitter, 'p' pour afficher le corps detecte.")

try:
    while True:

        ret, frame = cap.read()
        if not ret:
            print("Impossible de lire la camera.")
            break

        corps = detection.detect(frame)

        if corps is not None:

            frame = dessiner_squelette(frame, corps)

            # ------------------------------------------------
            # Test de chaque position et affichage à l'écran
            # ------------------------------------------------
            position_detectee = "Aucune"
            for nom, fonction_test in POSITIONS_A_TESTER:
                if fonction_test(corps):
                    position_detectee = nom
                    break

            cv2.putText(
                frame,
                f"Position : {position_detectee}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
            )

            message_miroir, couleur_miroir = verdict_miroir(corps)
            cv2.putText(
                frame,
                message_miroir,
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                couleur_miroir,
                2,
            )

        else:
            cv2.putText(
                frame,
                "Aucun corps detecte",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                2,
            )

        cv2.imshow("Test positions", frame)

        touche = cv2.waitKey(1) & 0xFF

        if touche == ord("q"):
            break

        elif touche == ord("p") and corps is not None:
            print("Corps detecte :", corps)
            print("Epaule droite x =", round(corps.epaule_droite.x, 3))
            print("Epaule gauche x =", round(corps.epaule_gauche.x, 3))
            print(verdict_miroir(corps)[0])

finally:
    cap.release()
    cv2.destroyAllWindows()
    detection.close()
    print("Script de test arrete.")
