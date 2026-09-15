"""Oracle Python du portage de la lecture de `progression/programmes.py`.

Un programme est une liste d'exigences ; tout le reste — niveau requis,
avancement, prochaine séance — se **recalcule** à chaque lecture depuis
l'historique et le matériel. C'est donc un pur calcul, et il se vérifie comme
les autres : on fabrique des historiques, on pose des questions, on diffe.

Quatre choses sont fabriquées exprès parce qu'un programme réel ne les visite
pas :

- **des exigences hors du matériel déclaré** (« 4x12 à 28 kg » quand les
  haltères s'arrêtent à 10), seul moyen d'éprouver la traduction par le
  volume, qui est la règle centrale du module ;
- **des avancements qui tombent sur un demi exact** — `round()` arrondit au
  pair le plus proche en Python et vers le haut en JavaScript, et l'avancement
  y passe deux fois (par exigence, puis en moyenne) ;
- **des poids et cibles décimaux**, parce que `prescription` les écrit avec
  `:g` : `5.0` doit s'écrire « 5 » des deux côtés, jamais « 5.0 » ;
- **des liaisons de séance cassées** (un libellé qui pointe vers une séance
  absente du catalogue), qui doivent rendre `None` et non le nom mort.

Usage : `python -m scripts.generer_programmes`
Sortie : scripts/fixtures_programmes.jsonl
"""

import json
import random
from pathlib import Path

from progression import niveaux, paliers, programmes
from scripts.historiques_au_hasard import (
    INVENTAIRES,
    historique as tirer_historique,
    injecter_inventaire,
    palier_serialisable,
)

RACINE = Path(__file__).resolve().parent.parent
DESTINATION = Path(__file__).parent / "fixtures_programmes.jsonl"

GRAINE = 20260914
TIRAGES = 60

#: Des séances « jouables » fictives : `liaison_seances` ne garde un lien que
#: si la séance existe dans le catalogue, et c'est ce filtre qu'on éprouve.
CATALOGUE = {"bras": {}, "upper_push": {}, "jambes_abdos": {}}

#: Libellés de séance d'un programme. Le quatrième ne correspond à rien : un
#: programme dont une séance n'est pas liée doit rester lisible.
LIBELLES = ["Push", "Pull", "Jambes", "Mobilité"]


def _exigences(tirage, noms):
    """Des exigences volontairement disparates."""
    lignes = []
    for _ in range(tirage.randint(1, 8)):
        nom = tirage.choice(noms)
        # Une fois sur trois, une charge que le matériel ne permet pas : c'est
        # le cas que la traduction par le volume existe pour traiter.
        poids = (
            tirage.choice([0, 2, 5, 8])
            if tirage.random() < 0.66
            else tirage.choice([20, 24, 28, 32])
        )
        lignes.append({
            "seance": tirage.choice(LIBELLES),
            "exercice": nom,
            "series": tirage.randint(1, 6),
            # Des cibles entières et décimales : `:g` doit rendre « 12 » et
            # « 12.5 », jamais « 12.0 ».
            "cible": tirage.choice([8, 10, 12, 15, 20, 12.0, 22.5, 45.0]),
            "poids": poids,
        })
    return lignes


def _programme(tirage, noms, numero):
    exigences = _exigences(tirage, noms)
    libelles = []
    for exigence in exigences:
        if exigence["seance"] not in libelles:
            libelles.append(exigence["seance"])

    # Les liens sont posés au hasard, y compris vers des séances qui
    # n'existent pas : `liaison_seances` doit alors rendre None.
    liens = {}
    for libelle in libelles:
        choix = tirage.choice([*CATALOGUE, "seance_disparue", None])
        if choix:
            liens[libelle] = choix

    return {
        "nom": f"Programme {numero}",
        "description": "fabrique par le harnais",
        "exigences": exigences,
        "seances": liens,
    }


def _ancrer_dans_le_catalogue(tirage, seances):
    """Rattache l'historique aux séances du catalogue, et en abandonne.

    Sans ça, `prochaine_seance` ne trouve presque jamais de séance appartenant
    au programme : le générateur partagé tire ses noms parmi `bras`,
    `Upper Pull` et `None`, dont un seul est lié. Mesuré, le sabotage qui fait
    compter une séance abandonnée comme faite ne sortait que **4 divergences
    sur 180 programmes** — une détection, mais si mince qu'un défaut voisin
    passerait. C'est la même leçon que le superset de `refaire_derniere_serie` :
    les cas qui dépendent d'une coïncidence entre deux jeux de données sont
    hors de portée d'un tirage, il faut les viser.

    Un quart des séances est abandonné, parce que c'est précisément la règle en
    jeu : une séance abandonnée ne compte pas comme faite, on la repropose.
    """
    noms_lies = [*CATALOGUE, "seance_inconnue"]
    for seance in seances:
        seance["nom"] = tirage.choice(noms_lies)
        seance["statut"] = "abandoned" if tirage.random() < 0.25 else "finished"
    return seances


def _sans_personnalise(etat):
    """`personnalise` dit d'où vient le programme, pas où en est l'athlète.

    Le JavaScript ne le rend pas : dans l'application, *tous* les programmes
    viennent du fichier exporté, la question n'a donc pas de sens et aucun
    écran ne la pose. On l'écarte de la comparaison plutôt que d'inventer une
    valeur côté JS pour faire coïncider deux choses qui ne se comparent pas.
    """
    if etat is None:
        return None
    return {cle: valeur for cle, valeur in etat.items() if cle != "personnalise"}


def _serialiser(objet):
    if isinstance(objet, paliers.Palier):
        return palier_serialisable(objet)
    if isinstance(objet, set):
        return sorted(objet)
    raise TypeError(f"Non serialisable : {type(objet)}")


def main():
    tirage = random.Random(GRAINE)
    noms = list(paliers.exercices_suivis())
    lignes = 0

    with DESTINATION.open("w", encoding="utf-8") as fichier:
        for nom_inventaire, inventaire in INVENTAIRES.items():
            injecter_inventaire(inventaire)

            for numero in range(TIRAGES):
                connus = tirage.sample(noms, k=tirage.randint(2, max(2, len(noms) // 2)))
                seances = _ancrer_dans_le_catalogue(tirage, tirer_historique(tirage, connus))
                # Les ancrages sont lus en base par `etats_niveaux` : on les
                # neutralise, le harnais des niveaux les couvre déjà.
                niveaux.recuperer_ancrages = lambda *_, **__: {}

                programme = _programme(tirage, noms, numero)
                cle = f"programme_{numero}"
                # `tous_les_programmes` lit le disque : on l'y substitue, comme
                # les autres harnais détournent la lecture des ancrages.
                programmes.tous_les_programmes = lambda _p={cle: programme}: _p

                etats = niveaux.etats_niveaux(seances)

                fichier.write(json.dumps({
                    "inventaire": nom_inventaire,
                    "numero": numero,
                    "cle": cle,
                    "programme": programme,
                    "seances": seances,
                    "volumes": [
                        programmes.volume_exige(e) for e in programme["exigences"]
                    ],
                    "prescriptions": [
                        programmes.prescription(e) for e in programme["exigences"]
                    ],
                    "etats_exigences": [
                        programmes.etat_exigence(e, etats)
                        for e in programme["exigences"]
                    ],
                    "libelles": programmes.libelles_seances(programme),
                    "liaison": programmes.liaison_seances(cle, CATALOGUE),
                    "prochaine": programmes.prochaine_seance(cle, seances, CATALOGUE),
                    "etat_programme": _sans_personnalise(
                        programmes.etat_programme(cle, niveaux=etats)
                    ),
                }, ensure_ascii=False, default=_serialiser) + "\n")
                lignes += 1

    print(f"{len(INVENTAIRES)} inventaires x {TIRAGES} programmes")
    print(f"{lignes} lignes")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


if __name__ == "__main__":
    main()
