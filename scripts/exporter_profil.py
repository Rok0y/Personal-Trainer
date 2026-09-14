"""Exporte l'historique d'un profil SQLite vers une sauvegarde lisible par l'app.

L'application du navigateur tient sa base dans un **objet JavaScript ordinaire**
dont les cinq collections reprennent les cinq tables SQLite, colonne par
colonne. La migration est donc un transfert presque direct : il n'y a ni
conversion de schéma, ni jointure à refaire.

Deux choses seulement demandent de l'attention, et elles ont la même cause —
le profil.

1. **Le cloisonnement.** `utilisateur_id` ne figure que sur les deux tables
   racines (`seances`, `corrections_niveaux`) ; `exercices` et
   `series_realisees` en héritent par leur clé étrangère. On filtre donc les
   racines, puis on descend — filtrer les quatre tables indépendamment
   laisserait passer les exercices d'un autre profil.
2. **Le profil devient le numéro 1.** L'application ne connaît qu'un profil
   par appareil (`PROFIL = 1`) : les identifiants sont donc renumérotés, sans
   quoi l'historique importé serait invisible. C'est aussi ce qui permet
   d'exporter n'importe quel profil vers n'importe quel appareil.

**Le fichier produit n'est jamais versionné.** Il contient un historique
d'entraînement réel, et le dépôt est public — c'est exactement ce qui avait
motivé le retrait de `personaltrainer.db` du suivi Git. Il est écrit hors du
dépôt par défaut, et le script refuse d'écrire dedans.

Usage :
    python -m scripts.exporter_profil                 # liste les profils
    python -m scripts.exporter_profil Arthur          # écrit sur le Bureau
    python -m scripts.exporter_profil Arthur -s C:/…  # ailleurs
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
BASE = RACINE / "historique" / "personaltrainer.db"

#: La version que `historique.js` sait relire. Un import d'une autre version
#: est refusé bruyamment plutôt qu'appliqué à moitié.
VERSION_BASE = 1

#: Colonnes de `utilisateurs` que l'application relit. `mot_de_passe` n'existe
#: pas, mais lister explicitement évite qu'une colonne ajoutée plus tard parte
#: dans un export sans qu'on l'ait décidé.
COLONNES_UTILISATEUR = (
    "id", "nom", "cree_le", "onboarding_termine",
    "seance_initiale", "programme_choisi", "materiel",
)


def _lignes(connexion, requete, parametres=()):
    connexion.row_factory = sqlite3.Row
    return [dict(ligne) for ligne in connexion.execute(requete, parametres)]


def profils(connexion):
    return _lignes(connexion, "SELECT id, nom, cree_le FROM utilisateurs ORDER BY id")


def exporter(connexion, utilisateur_id):
    """La base de l'application, pour ce profil et lui seul."""
    seances = _lignes(
        connexion,
        "SELECT * FROM seances WHERE utilisateur_id = ? ORDER BY id",
        (utilisateur_id,),
    )
    ids_seances = {s["id"] for s in seances}

    exercices = [
        e for e in _lignes(connexion, "SELECT * FROM exercices ORDER BY id")
        if e["seance_id"] in ids_seances
    ]
    ids_exercices = {e["id"] for e in exercices}

    series = [
        s for s in _lignes(connexion, "SELECT * FROM series_realisees ORDER BY id")
        if s["exercice_id"] in ids_exercices
    ]

    ancrages = _lignes(
        connexion,
        "SELECT * FROM corrections_niveaux WHERE utilisateur_id = ? ORDER BY id",
        (utilisateur_id,),
    )

    profil = next(p for p in _lignes(connexion, "SELECT * FROM utilisateurs")
                  if p["id"] == utilisateur_id)
    utilisateur = {colonne: profil.get(colonne) for colonne in COLONNES_UTILISATEUR}

    # Le profil devient le numéro 1 : c'est le seul que l'application connaît.
    utilisateur["id"] = 1
    for ligne in seances:
        ligne["utilisateur_id"] = 1
    for ligne in ancrages:
        ligne["utilisateur_id"] = 1

    def prochain(lignes):
        return max((l["id"] for l in lignes), default=0) + 1

    return {
        "version": VERSION_BASE,
        # Les compteurs repartent **au-dessus du plus grand identifiant
        # existant** : les réutiliser écraserait silencieusement une séance à
        # la première enregistrée sur l'appareil.
        "prochains_id": {
            "utilisateurs": 2,
            "seances": prochain(seances),
            "exercices": prochain(exercices),
            "series_realisees": prochain(series),
            "corrections_niveaux": prochain(ancrages),
        },
        "utilisateurs": [utilisateur],
        "seances": seances,
        "exercices": exercices,
        "series_realisees": series,
        "corrections_niveaux": ancrages,
        "exporte_le": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("profil", nargs="?", help="nom du profil à exporter")
    analyseur.add_argument(
        "-s", "--sortie", type=Path,
        help="où écrire (par défaut : le Bureau). Jamais dans le dépôt.",
    )
    arguments = analyseur.parse_args()

    if not BASE.exists():
        print(f"Aucune base à {BASE}", file=sys.stderr)
        return 1

    connexion = sqlite3.connect(BASE)
    disponibles = profils(connexion)

    if not arguments.profil:
        print("Profils disponibles :\n")
        for profil in disponibles:
            seances = connexion.execute(
                "SELECT COUNT(*) FROM seances WHERE utilisateur_id = ?", (profil["id"],)
            ).fetchone()[0]
            print(f"  {profil['nom']:20} {seances:3} séances   (depuis {profil['cree_le']})")
        print("\nRelance avec le nom du profil à exporter.")
        return 0

    correspond = [p for p in disponibles if p["nom"].lower() == arguments.profil.lower()]
    if not correspond:
        noms = ", ".join(p["nom"] for p in disponibles)
        print(f"Profil « {arguments.profil} » introuvable. Connus : {noms}", file=sys.stderr)
        return 1

    profil = correspond[0]
    donnees = exporter(connexion, profil["id"])

    defaut = Path.home() / "Desktop" / f"coach-{profil['nom'].lower()}.json"
    destination = arguments.sortie or defaut
    if destination.is_dir():
        destination = destination / defaut.name

    # Le dépôt est public : un historique d'entraînement réel n'y entre pas,
    # même par accident. C'est la même règle qui a fait retirer la base du
    # suivi Git.
    try:
        destination.resolve().relative_to(RACINE)
    except ValueError:
        pass
    else:
        print(
            "Refus : cette sauvegarde contient un historique reel et le depot "
            "est public. Choisis une destination hors du projet.",
            file=sys.stderr,
        )
        return 1

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"Profil {profil['nom']} exporte :")
    print(f"  {len(donnees['seances']):4} seances")
    print(f"  {len(donnees['exercices']):4} exercices")
    print(f"  {len(donnees['series_realisees']):4} series realisees")
    print(f"  {len(donnees['corrections_niveaux']):4} ancrages de niveau")
    print(f"  materiel declare : {'oui' if donnees['utilisateurs'][0]['materiel'] else 'non'}")
    print(f"\nEcrit dans {destination}")
    print("\nDans l'application : Seances > Importer, et choisis ce fichier.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
