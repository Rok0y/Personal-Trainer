from pathlib import Path

from audio.coach import nom_annonce_etape
from session.seances import seance_jambes_abdos, seance_test

DOSSIER = Path("audio/Fichiers")

deja_vus = set()
seance = seance_jambes_abdos
for bloc in seance_jambes_abdos.exercices:

    etape = {
        "exercice": bloc.exercice.nom,
        "poids": bloc.poids,
        "series": bloc.nombre_series,
        "repetitions": bloc.repetitions_par_serie,
        "mode": bloc.mode,
        "duree": bloc.duree,
    }

    nom = nom_annonce_etape(etape)

    if nom is None:
        continue

    attendu = f"{nom}_1.wav"

    if attendu in deja_vus:
        continue

    deja_vus.add(attendu)

    if not (DOSSIER / attendu).exists():
        print(attendu)
