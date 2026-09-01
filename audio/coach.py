import random
import re
import time
import unicodedata
from pathlib import Path

from audio.lecteur import jouer

messages = {
    "rep": ["rep.wav"],
    "debut": ["debut.wav"],
    "avant_derniere": ["avant_derniere.wav"],
    "derniere_rep": ["derniere_rep.wav"],
    "fin_serie": ["fin_serie.wav"],
    "repos": ["repos.wav"],
    "changement_exercice": ["changement_exercice.wav"],
    "fin_seance": ["fin_seance.wav"],
    "debut_serie": ["debut_serie.wav"],
    "preparation": ["preparation.wav"],
    "mi_parcours": [
        "mi_parcours_1.wav",
    ],
    "encore_5": [
        "encore_5_1.wav",
    ],
    "encore_3": [
        "encore_3_1.wav",
    ],
    "correction_gainage": [
        "correction_gainage_1.wav",
    ],
    "temps_20": [
        "temps_20_1.wav",
    ],
    "temps_10": [
        "temps_10_1.wav",
    ],
    "temps_5": [
        "temps_5_1.wav",
    ],
    "repos_10": [
        "repos_10.wav",
    ],
    "repos_5": [
        "repos_5.wav",
    ],
    "repos_5": [
        "repos_5.wav",
    ],
    "bip": ["bip.wav"],
}


priorites = {
    "rep": 1,
    "debut_serie": 5,
    "avant_derniere": 5,
    "derniere_rep": 10,
    "fin_serie": 10,
    "repos": 8,
    "changement_exercice": 5,
    "fin_seance": 10,
    "mi_parcours": 3,
    "encore_5": 4,
    "encore_3": 5,
    "correction_gainage": 7,
    "temps_30": 4,
    "temps_20": 6,
    "temps_10": 7,
    "temps_5": 8,
    "repos_10": 6,
    "repos_5": 8,
    "bip": 2,
}

DELAIS_ENTRE_ANNONCES = {
    "correction_gainage": 8,
}

dernieres_annonces = {}
DOSSIER_SONS = Path(__file__).with_name("Fichiers")


def coach(event, valeur=None):

    if event == "compteur":
        jouer(f"{valeur}.wav", 1)
        return

    if event not in messages:
        return

    maintenant = time.monotonic()
    delai = DELAIS_ENTRE_ANNONCES.get(event, 0)
    derniere_annonce = dernieres_annonces.get(event)

    if derniere_annonce is not None and maintenant - derniere_annonce < delai:
        return

    son = random.choice(messages[event])

    dernieres_annonces[event] = maintenant

    jouer(son, priorites.get(event, 5))


DOSSIER_ANNONCES_ETAPES = Path(__file__).with_name("Fichiers") / "annonces_etapes"


def normaliser_nom(texte):
    texte_sans_accents = unicodedata.normalize("NFD", texte)
    texte_sans_accents = "".join(
        caractere
        for caractere in texte_sans_accents
        if unicodedata.category(caractere) != "Mn"
    )

    return re.sub(r"[^a-z0-9]+", "_", texte_sans_accents.lower()).strip("_")


def nom_annonce_etape(etape):

    exercice = normaliser_nom(etape["exercice"])
    series = etape["series"]
    mot_series = "serie" if series == 1 else "series"
    poids = etape.get("poids", 0)

    if poids > 0:
        debut = f"prochain_{exercice}_{poids}_kilos_{series}_{mot_series}"
    else:
        debut = f"prochain_{exercice}_{series}_{mot_series}"

    if etape["mode"] == "repetitions":
        return f"{debut}_{etape['repetitions']}_repetitions"

    if etape["mode"] == "maintien":
        return f"{debut}_{etape['duree']}_secondes"

    if etape["mode"] == "chrono":
        return f"{debut}_chrono_{etape['duree']}_secondes"

    if etape["mode"] == "amrap":
        return f"{debut}_amrap_{etape['duree']}_secondes"

    return None


def annoncer_prochaine_etape(etape, annonce_secours):

    print("ANNONCE PROCHAINE ETAPE APPELEE")
    print(etape)

    if etape is None:
        return

    nom = nom_annonce_etape(etape)

    if nom is None:
        coach(annonce_secours)
        return

    candidats = list(DOSSIER_ANNONCES_ETAPES.glob(f"{nom}_*.wav"))

    if not candidats:
        print("AUCUN WAV ETAPE TROUVE")
        print("Recherche :", nom)
        coach(annonce_secours)
        return

    fichier = random.choice(candidats)

    jouer(fichier.name)


def annoncer_progression(repetitions, cible):
    restantes = cible - repetitions

    if restantes == 0:
        coach("fin_serie")
        return

    if restantes == 1:
        coach("avant_derniere")
        return

    if restantes == 3:
        coach("encore_3")
        return

    if restantes == 5:
        coach("encore_5")
        return

    if cible >= 8 and repetitions == cible // 2:
        coach("mi_parcours")


def annoncer_temps_restant(bloc, secondes_restantes):

    if bloc.temps_restant_precedent is None:
        bloc.temps_restant_precedent = secondes_restantes
        return

    seuils = [
        (20, "temps_20"),
        (10, "temps_10"),
        (5, "temps_5"),
    ]

    for seuil, message in seuils:

        if bloc.temps_restant_precedent > seuil and secondes_restantes <= seuil:
            coach(message)
            break

    bloc.temps_restant_precedent = secondes_restantes


def annoncer_temps_repos(seance, state, annoncer_exercice=False):

    secondes_restantes = int(seance.temps_restant)

    if (
        not hasattr(seance, "repos_restant_precedent")
        or seance.repos_restant_precedent is None
    ):
        seance.repos_restant_precedent = secondes_restantes
        return

    seuils = [
        (20, "repos_20"),
        (10, "repos_10"),
        (5, "repos_5"),
    ]

    for seuil, message in seuils:

        if seance.repos_restant_precedent > seuil and secondes_restantes <= seuil:
            coach(message)
            break

    seance.repos_restant_precedent = secondes_restantes
