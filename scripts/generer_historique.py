"""Oracle Python du portage de `historique/database.py`.

Même principe que `generer_scenarios.py`, appliqué à la persistance : on joue
une suite d'écritures sur une base neuve, on relit tout après chaque pas, et le
JavaScript devra rendre exactement la même chose.

Ce n'est pas un portage du SQL mais de **ce que le SQL produit**. La question
vérifiée est donc : « à écritures identiques, `recuperer_historique` rend-il la
même structure des deux côtés ? » — ce qui couvre les jointures, les valeurs de
repli (`or 0`, `or "repetitions"`), l'ordre des séances et le détail des séries.

Deux précautions rendent la comparaison possible. La base est une **copie
jetable** dans le dossier temporaire : ce script n'ouvre jamais
`historique/personaltrainer.db`, qui contient de vraies séances. Et l'horloge
est **figée** : `enregistrer_seance` horodate avec `datetime.now()`, donc deux
exécutions écriraient des dates différentes et le diff signalerait un écart qui
n'en est pas un.

Usage : `python -m scripts.generer_historique`
Sortie : scripts/fixtures_historique.jsonl, une écriture par ligne.
"""

import json
import random
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import historique.database as base_de_donnees

RACINE = Path(__file__).resolve().parent.parent
DESTINATION = Path(__file__).parent / "fixtures_historique.jsonl"

GRAINE = 20260911
NOMBRE_DE_SEANCES = 60

#: Point de départ de l'horloge figée, et pas de temps entre deux écritures.
#: Une minute suffit : le format stocké s'arrête à la minute, donc deux séances
#: plus rapprochées porteraient la même date — ce qui est justement le cas que
#: `progression/` ne doit pas départager par la date mais par l'identifiant.
DEBUT = datetime(2026, 3, 1, 8, 0)
PAS_HORAIRE = timedelta(minutes=1)

EXERCICES = [
    ("Curl biceps droit", "repetitions"),
    ("Curl biceps gauche", "repetitions"),
    ("Rowing unilateral droit", "repetitions"),
    ("Pompes", "repetitions"),
    ("Gainage planche", "maintien"),
    ("Squat", "repetitions"),
    ("Jumping jacks", "echauffement"),
]

RESSENTIS = ["trop_dur", "dur", "ok", "facile", "trop_facile"]


class _HorlogeFigee:
    """Remplace `datetime` dans le module de base, le temps du harnais.

    Seul `.now()` est utilisé par `historique.database` ; le reste de la classe
    n'a pas à exister. Avancer d'un pas à chaque appel plutôt que rendre une
    constante permet de vérifier que les dates *se suivent*, donc que rien ne
    réordonne les séances au passage.
    """

    def __init__(self):
        self.instant = DEBUT

    def now(self):
        valeur = self.instant
        self.instant += PAS_HORAIRE
        return valeur


def _exercice_au_hasard(tirage):
    nom, mode = tirage.choice(EXERCICES)
    series = tirage.randint(1, 4)
    maintien = mode == "maintien"
    cible = tirage.randint(20, 60) if maintien else tirage.randint(6, 15)

    detaillees = []
    for numero in range(1, series + 1):
        realise = tirage.randint(max(0, cible - 4), cible + 2)
        detaillees.append({
            "serie": numero,
            "repetitions": 0 if maintien else realise,
            "poids": tirage.choice([0, 4, 6, 8, 10]),
            "duree": realise if maintien else 0,
            "completee": realise >= cible,
        })

    return {
        "nom": nom,
        "series": series,
        "repetitions": sum(s["repetitions"] for s in detaillees),
        "poids": detaillees[0]["poids"],
        "mode": mode,
        "duree": sum(s["duree"] for s in detaillees),
        "commentaire": tirage.choice(["", "barre fixe", "avec élastique"]),
        "series_cibles": series,
        "repetitions_cibles": 0 if maintien else cible,
        "duree_cible": cible if maintien else 0,
        "entrelace_avec": tirage.choice([None, None, None, "Curl biceps gauche"]),
        "repos_entre_series": tirage.choice([30, 45, 60]),
        "repos_apres": tirage.choice([0, 45, 90]),
        "series_detaillees": detaillees,
    }


def main():
    tirage = random.Random(GRAINE)
    horloge = _HorlogeFigee()

    with tempfile.TemporaryDirectory() as dossier:
        # La vraie base n'est jamais ouverte : ce script écrit des dizaines de
        # séances fictives, et il n'a rien à faire dans un historique réel.
        base_de_donnees.CHEMIN_DB = str(Path(dossier) / "harnais.db")
        base_de_donnees.datetime = horloge
        base_de_donnees.initialiser()

        ecritures = []

        alice = base_de_donnees.creer_utilisateur("Alice")
        bob = base_de_donnees.creer_utilisateur("Bob")
        profils = [alice["id"], bob["id"]]
        ecritures.append(("creer_utilisateur", {"nom": "Alice"}))
        ecritures.append(("creer_utilisateur", {"nom": "Bob"}))

        with DESTINATION.open("w", encoding="utf-8") as fichier:

            def relever(pas, commande, arguments, resultat):
                fichier.write(json.dumps({
                    "pas": pas,
                    "commande": commande,
                    "arguments": arguments,
                    "resultat": resultat,
                    # Les deux profils sont relus à chaque pas : c'est ce qui
                    # vérifie le cloisonnement, et pas seulement le contenu.
                    "historique": {
                        str(profil): base_de_donnees.recuperer_historique(profil)
                        for profil in profils
                    },
                    "ancrages": {
                        str(profil): base_de_donnees.recuperer_ancrages(profil)
                        for profil in profils
                    },
                }, ensure_ascii=False) + "\n")

            for pas, (commande, arguments) in enumerate(ecritures):
                relever(pas, commande, arguments, None)

            pas = len(ecritures)
            seances_ecrites = []

            for _ in range(NOMBRE_DE_SEANCES):
                profil = tirage.choice(profils)
                arguments = {
                    "duree": tirage.randint(300, 3600),
                    "exercices": [
                        _exercice_au_hasard(tirage) for _ in range(tirage.randint(1, 4))
                    ],
                    "statut": tirage.choice(["finished", "finished", "abandoned"]),
                    "nom_seance": tirage.choice(["bras", "jambes_abdos", "Upper Pull", None]),
                    "utilisateur_id": profil,
                }
                identifiant = base_de_donnees.enregistrer_seance(**arguments)
                seances_ecrites.append((identifiant, profil, arguments["exercices"]))
                relever(pas, "enregistrer_seance", arguments, identifiant)
                pas += 1

                # Un ressenti une fois sur trois, sur un exercice de la séance
                # qu'on vient d'écrire : c'est exactement le chemin de l'écran
                # de fin, qui annote après coup.
                if tirage.random() < 0.34:
                    nom = tirage.choice(arguments["exercices"])["nom"]
                    ressentis = {nom: tirage.choice(RESSENTIS)}
                    modifies = base_de_donnees.enregistrer_ressentis(
                        identifiant, ressentis, utilisateur_id=profil
                    )
                    relever(pas, "enregistrer_ressentis",
                            {"seance_id": identifiant, "ressentis": ressentis,
                             "utilisateur_id": profil}, modifies)
                    pas += 1

                # Un ancrage de temps en temps, posé après la séance courante.
                if tirage.random() < 0.2:
                    nom = tirage.choice(EXERCICES)[0]
                    args = {
                        "nom_exercice": nom,
                        "niveau": tirage.randint(1, 30),
                        "raison": "harnais",
                        "utilisateur_id": profil,
                    }
                    base_de_donnees.enregistrer_ancrage(**args)
                    relever(pas, "enregistrer_ancrage", args, None)
                    pas += 1

            # Des suppressions en fin de parcours : elles ne doivent laisser ni
            # exercice ni série orpheline, ce que la relecture complète vérifie.
            for identifiant, profil, _ in tirage.sample(seances_ecrites, 6):
                supprimee = base_de_donnees.supprimer_seance(
                    identifiant, utilisateur_id=profil
                )
                relever(pas, "supprimer_seance",
                        {"seance_id": identifiant, "utilisateur_id": profil}, supprimee)
                pas += 1

    lignes = sum(1 for _ in DESTINATION.open(encoding="utf-8"))
    print(f"{lignes} ecritures relues, 2 profils")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


if __name__ == "__main__":
    main()
