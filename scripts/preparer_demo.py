"""Prepare la demo statique : catalogue exporte et sons rapatries.

La demo est volontairement **statique** — aucun Flask, aucun profil, aucune
base. Elle peut donc etre deposee telle quelle sur un hebergeur gratuit, avec
une adresse stable, sans que le PC de personne reste allume ; c'est ce qui
rend des testeurs autonomes.

Le catalogue reste pour autant la propriete du Python : il est *exporte* ici,
jamais recopie a la main. Un exercice ajoute a CATALOGUE_EXERCICES apparait
dans la demo a la prochaine execution, avec sa fiche.

    python -m scripts.preparer_demo
"""

import json
import shutil
from pathlib import Path

from session.seances import CATALOGUE_EXERCICES

RACINE = Path(__file__).resolve().parent.parent
DEMO = RACINE / "web" / "static" / "demo"
SONS_SOURCE = RACINE / "audio" / "Fichiers"

SONS_DEMO = ["bip"] + [str(n) for n in range(1, 21)]
"""Le socle strictement necessaire : le bip et les nombres annonces. La
bibliotheque s'arrete a 20, et la demo se tait au-dela plutot que d'inventer.
Les annonces combinatoires (`prochain_*`) ne servent qu'en seance complete."""


def exporter_catalogue():
    """Les exercices que la demo sait faire : ceux qui analysent la pose.

    Le nom de la fonction de detection est exporte pour que le JS retrouve sa
    jumelle dans detections.js — les deux portent le meme nom, c'est ce qui
    dispense d'une table de correspondance.
    """
    exercices = []
    sans_detection = []

    for nom, exercice in CATALOGUE_EXERCICES.items():
        if exercice.detection is None:
            sans_detection.append(nom)
            continue
        fiche = exercice.fiche()
        fiche["detection"] = exercice.detection.__name__
        exercices.append(fiche)

    exercices.sort(key=lambda f: f["nom"])
    return exercices, sans_detection


def copier_sons():
    destination = DEMO / "sons"
    destination.mkdir(parents=True, exist_ok=True)

    copies, manquants = 0, []
    for nom in SONS_DEMO:
        source = SONS_SOURCE / f"{nom}.wav"
        if source.exists():
            shutil.copy2(source, destination / f"{nom}.wav")
            copies += 1
        else:
            manquants.append(nom)
    return copies, manquants


def main():
    DEMO.mkdir(parents=True, exist_ok=True)

    exercices, sans_detection = exporter_catalogue()
    cible = DEMO / "catalogue.json"
    cible.write_text(
        json.dumps(exercices, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    copies, manquants = copier_sons()

    print(f"{len(exercices)} exercices exportes vers {cible}")
    if sans_detection:
        print(f"  ecartes (pas de detection de pose) : {', '.join(sans_detection)}")
    print(f"{copies} sons copies vers {DEMO / 'sons'}")
    if manquants:
        print(f"  manquants : {', '.join(manquants)}")


if __name__ == "__main__":
    main()
