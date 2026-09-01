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
"""

import cv2

from mouvements.positions import bras_droit_leve, bras_en_x, bras_gauche_leve
from vision.dessin import dessiner_squelette
from vision.detector import PoseDetector

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

finally:
    cap.release()
    cv2.destroyAllWindows()
    detection.close()
    print("Script de test arrete.")
