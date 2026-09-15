"""Renomme des seances partout ou leur nom fait office de cle.

Le nom d'une seance n'est pas une etiquette : c'est la **cle** du catalogue,
et elle est recopiee dans quatre autres endroits qui ne se parlent pas.
En rater un ne leve aucune erreur — ca rend simplement muet ce qui s'appuyait
dessus :

1. `session/seances_personnalisees.json` — le catalogue lui-meme ;
2. `progression/programmes_personnalises.json` — le dict `seances` relie un
   libelle de programme a une seance jouable ; sans la mise a jour,
   `liaison_seances` rend None et le programme ne pilote plus rien ;
3. `seances.nom_seance` en base — c'est par ce nom que l'accueil retrouve la
   « derniere fois » et que `prochaine_seance` sait ou en est le programme ;
4. `utilisateurs.seance_initiale` — la seance choisie a l'inscription.

`exercices` et `series_realisees` heritent par leur cle etrangere : rien a y
faire, et surtout rien a y dupliquer.

Le script est **idempotent** : un ancien nom deja absent est ignore, et il
refuse d'ecraser un nom d'arrivee deja pris par une autre seance. On peut donc
le relancer sans risque, et l'essayer a blanc avant.

Usage :
    python -m scripts.renommer_seances --essai   # dit ce qu'il ferait
    python -m scripts.renommer_seances           # le fait
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SEANCES = RACINE / "session" / "seances_personnalisees.json"
PROGRAMMES = RACINE / "progression" / "programmes_personnalises.json"
BASE = RACINE / "historique" / "personaltrainer.db"

#: Ancien nom -> nouveau nom. Les noms techniques remontaient jusqu'a l'ecran
#: d'accueil (« jambes_abdos » dans le bandeau du programme) ; le nom affiche
#: et le nom stocke sont desormais le meme, plutot qu'un second champ « titre »
#: qu'il aurait fallu tenir a jour a cote.
RENOMMAGES = {
    "upper_push": "Upper Push",
    "jambes_abdos": "Jambes et abdos",
    "bras": "Bras",
    "Séance Haut du corps": "Haut du corps",
    "Séance bas du corps": "Bas du corps",
}


def _lire(chemin):
    return json.loads(chemin.read_text(encoding="utf-8"))


def _ecrire(chemin, donnees):
    # `indent=2`, comme `enregistrer_seance_personnalisee` et
    # `_ecrire_programmes_personnalises` : un autre reglage reformaterait le
    # fichier entier et noierait le renommage dans le diff.
    chemin.write_text(
        json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def renommer_catalogue(journal):
    """Les cles de `seances_personnalisees.json`, dans l'ordre d'origine."""
    catalogue = _lire(SEANCES)
    for ancien, nouveau in RENOMMAGES.items():
        if ancien in catalogue and nouveau in catalogue:
            raise SystemExit(
                f"Refus : « {nouveau} » existe deja et n'est pas « {ancien} »."
            )

    renomme = {RENOMMAGES.get(nom, nom): blocs for nom, blocs in catalogue.items()}
    for nom in catalogue:
        if nom in RENOMMAGES:
            journal.append(f"  seance   {nom} -> {RENOMMAGES[nom]}")
    return renomme


def renommer_programmes(journal):
    """Les valeurs du dict `seances`, et les libelles quand ils sont le meme mot.

    Un libelle de programme (« Push ») et une seance (« Upper Push ») sont deux
    choses distinctes, et le projet tient a la distinction. Mais quand un
    programme a ete ecrit en reprenant le nom de la seance comme libelle — le
    cas de « Seance bas du corps » —, renommer l'un sans l'autre ferait
    reapparaitre a l'ecran le nom qu'on vient justement d'enterrer.
    """
    programmes = _lire(PROGRAMMES)
    for cle, programme in programmes.items():
        for exigence in programme.get("exigences", []):
            libelle = exigence.get("seance")
            if libelle in RENOMMAGES:
                exigence["seance"] = RENOMMAGES[libelle]
                journal.append(f"  exigence {cle} : {libelle} -> {exigence['seance']}")

        liens = programme.get("seances") or {}
        programme["seances"] = {
            RENOMMAGES.get(libelle, libelle): RENOMMAGES.get(seance, seance)
            for libelle, seance in liens.items()
        }
        for libelle, seance in liens.items():
            if seance in RENOMMAGES:
                journal.append(
                    f"  lien     {cle} : {libelle} -> {RENOMMAGES[seance]}"
                )
    return programmes


def renommer_base(connexion, journal):
    """`seances.nom_seance` et `utilisateurs.seance_initiale`."""
    for ancien, nouveau in RENOMMAGES.items():
        compte = connexion.execute(
            "SELECT COUNT(*) FROM seances WHERE nom_seance = ?", (ancien,)
        ).fetchone()[0]
        if compte:
            journal.append(f"  historique {ancien} -> {nouveau} ({compte} seances)")
            connexion.execute(
                "UPDATE seances SET nom_seance = ? WHERE nom_seance = ?",
                (nouveau, ancien),
            )

        compte = connexion.execute(
            "SELECT COUNT(*) FROM utilisateurs WHERE seance_initiale = ?", (ancien,)
        ).fetchone()[0]
        if compte:
            journal.append(f"  profils    {ancien} -> {nouveau} ({compte} profils)")
            connexion.execute(
                "UPDATE utilisateurs SET seance_initiale = ? WHERE seance_initiale = ?",
                (nouveau, ancien),
            )


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument(
        "--essai", action="store_true", help="affiche les changements sans les ecrire"
    )
    arguments = analyseur.parse_args()

    journal = []
    catalogue = renommer_catalogue(journal)
    programmes = renommer_programmes(journal)

    connexion = sqlite3.connect(BASE) if BASE.exists() else None
    if connexion is not None:
        renommer_base(connexion, journal)
    else:
        journal.append(f"  (aucune base a {BASE}, historique non touche)")

    if not journal:
        print("Rien a renommer : les noms sont deja a jour.")
        return 0

    print("\n".join(journal))

    if arguments.essai:
        if connexion is not None:
            connexion.rollback()
        print("\nEssai : rien n'a ete ecrit.")
        return 0

    _ecrire(SEANCES, catalogue)
    _ecrire(PROGRAMMES, programmes)
    if connexion is not None:
        connexion.commit()

    print("\nRenomme. Relance `python -m scripts.preparer_demo` pour que")
    print("l'application serve les nouveaux noms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
