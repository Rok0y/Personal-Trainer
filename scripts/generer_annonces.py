"""Oracle Python du portage d'`audio/annonces.py`.

Le module compose des phrases a partir de briques, et tout son travail tient
dans une traduction — du texte vers un nom de fichier — plus quatre fabriques
de sequences. Un ecart y est **muet par construction** : le navigateur
demanderait un `.wav` qui n'existe pas, `_tampon` rendrait `null`, et
l'annonce serait simplement plus courte. Personne ne le remarquerait avant de
s'apercevoir, des semaines plus tard, que le coach ne nomme plus rien.

Trois choses qu'un tirage ordinaire ne visiterait pas sont fabriquees expres :

- **les textes tordus** pour `normaliser_nom` : accents composes, ligatures,
  apostrophes droites et courbes, ponctuation collee, chiffres melanges aux
  lettres, espaces multiples, tirets en tete et en queue. C'est la seule
  fonction du module qui doive rendre exactement la meme chose des deux cotes
  sur **n'importe quelle** entree, puisqu'elle recoit des noms d'exercices que
  personne ne controle ;
- **les bornes de `NOMBRE_MAXIMAL_DIT`** : un seuil est precisement l'endroit
  ou `<=` se distingue de `<`, et des valeurs tirees au hasard dans une large
  plage n'y tombent quasiment jamais. 0, 1, 60, 61 sont visites nommement ;
- **le poids a 1**, seul cas ou l'unite passe au singulier, et le poids a 0,
  qui n'est pas « zero kilo » mais un mouvement au poids du corps. Les charges
  reelles commencant a 2, aucun tirage sur l'echelle ne les atteindrait.

Les noms de mouvements viennent du **catalogue reel** et non d'un tirage : ce
sont eux que la regle « le nom est le texte » doit traduire, et un exercice
ajoute au catalogue entre ainsi dans le harnais le jour ou il est ecrit.

Usage : `python -m scripts.generer_annonces`
Sortie : scripts/fixtures_annonces.jsonl
"""

import json
import random
from pathlib import Path

from audio import annonces
from session.seances import catalogue_mouvements, nombre_halteres

RACINE = Path(__file__).resolve().parent.parent
DESTINATION = Path(__file__).resolve().parent / "fixtures_annonces.jsonl"

GRAINE = 20260916

#: Des textes qui mettent `normaliser_nom` a l'epreuve. Ils ne decrivent rien :
#: ils cherchent les endroits ou Python et JavaScript pourraient ne pas
#: decomposer, minuscler ou filtrer de la meme facon.
TEXTES_TORDUS = [
    "Curl biceps droit",
    "Developpé couché altères",
    "Élévations latérales à vide",
    "Squat de prière",
    "Hanches en avant en arrière",
    "L'haltère, c'est-à-dire 8 kg",
    "Déjà-vu : où ça ?",
    "MAJUSCULES ET Accents ÉÀÙÇ",
    "ligature œuf et Æsop",
    "  espaces   multiples  ",
    "---tirets-en-tete-et-en-queue---",
    "ponctuation!?;:,.collee",
    "chiffres 12 et 345 melanges",
    "é compose contre é precompose",
    "tréma ïouï et cedille ça",
    "42",
    "0",
    "un_underscore_deja_la",
    "parenthèses (et crochets) [ici]",
    "",
]

#: Toutes les parties et toutes les actions de `cadrage.js`, plus le `None` du
#: cas « coupe en haut *et* en bas », ou nommer une partie tromperait.
PARTIES = [None, "tete", "epaules", "coudes", "mains", "hanches", "genoux",
           "pieds", "inconnue"]
ACTIONS = [None, "recule", "baisse_camera", "monte_camera", "centre",
           "inconnue"]

#: Les bornes, puis un echantillon au hasard. Le seuil compte plus que le
#: volume : c'est la qu'un `<=` devenu `<` se verrait.
NOMBRES = [
    -1, 0, 1, 2,
    annonces.NOMBRE_MAXIMAL_DIT - 1,
    annonces.NOMBRE_MAXIMAL_DIT,
    annonces.NOMBRE_MAXIMAL_DIT + 1,
    999,
]

#: 0 et 1 ne sont pas des charges reelles — l'echelle commence a 2 — mais ils
#: portent les deux cas particuliers : rien a preparer, et l'unite au
#: singulier.
POIDS = [0, 1, 2, 3, 5, 8, 10, 12, 18, 61, 100]


def main():
    hasard = random.Random(GRAINE)
    mouvements = sorted(catalogue_mouvements())

    NOMBRES.extend(hasard.sample(range(1, 120), 30))

    lignes = 0
    with DESTINATION.open("w", encoding="utf-8") as sortie:

        def ecrire(charge):
            nonlocal lignes
            sortie.write(json.dumps(charge, ensure_ascii=False) + "\n")
            lignes += 1

        # La table des briques telle quelle : c'est elle que `preparer_demo`
        # exporte, et le JS ne travaille que sur sa version resolue. Si les
        # deux cotes ne partent pas des memes fichiers, tout le reste compare
        # deux choses differentes en croyant les trouver identiques.
        ecrire({
            "genre": "briques",
            "table": {
                cle: annonces.fichier(texte)
                for cle, texte in annonces.BRIQUES.items()
            },
        })

        for texte in TEXTES_TORDUS + mouvements:
            ecrire({
                "genre": "normaliser",
                "texte": texte,
                "nom": annonces.normaliser_nom(texte),
                "fichier": annonces.fichier(texte),
            })

        for valeur in NOMBRES:
            ecrire({
                "genre": "nombre",
                "valeur": valeur,
                "sons": annonces.sequence_nombre(valeur),
            })

        for partie in PARTIES:
            for action in ACTIONS:
                # Une cle inconnue leve cote Python et rend null cote JS : c'est
                # une divergence d'API assumee (voir `brique` dans annonces.js),
                # donc le harnais releve le **refus** comme un comportement.
                try:
                    sons = annonces.sequence_cadrage(partie, action)
                except KeyError:
                    sons = None
                ecrire({
                    "genre": "cadrage",
                    "partie": partie,
                    "action": action,
                    "sons": sons,
                })

        for orientation in list(annonces.ORIENTATIONS) + [None, "", "inconnue"]:
            ecrire({
                "genre": "orientation",
                "orientation": orientation,
                "sons": annonces.sequence_orientation(orientation),
            })

        for nom in mouvements:
            reel = nombre_halteres(nom)
            for poids in POIDS:
                # On joue le nombre d'halteres **du catalogue** et les deux
                # autres valeurs : l'injection doit produire la meme phrase
                # quelle que soit sa provenance, et un exercice a deux halteres
                # joue a un doit dire « un haltere ».
                for halteres in {reel, 0, 1, 2}:
                    etape = {"exercice": nom, "poids": poids}
                    ecrire({
                        "genre": "prochain_exercice",
                        "etape": etape,
                        "halteres": halteres,
                        "sons": annonces.sequence_prochain_exercice(
                            etape, halteres
                        ),
                    })

        ecrire({
            "genre": "prochain_exercice",
            "etape": None,
            "halteres": 1,
            "sons": annonces.sequence_prochain_exercice(None, 1),
        })

    print(f"{len(mouvements)} mouvements, {len(TEXTES_TORDUS)} textes tordus")
    print(f"{lignes} questions")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


if __name__ == "__main__":
    main()
