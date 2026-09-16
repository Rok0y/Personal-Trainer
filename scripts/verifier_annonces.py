"""Les tables du coach se tiennent-elles ?

**Une table de cles qui ne leve pas se verifie de l'exterieur.** `coach()` sort
en silence sur une cle inconnue — par la meme prudence qui interdit de lever
dans la boucle camera, ou une exception gelerait le flux video. La contrepartie
est qu'une cle mal orthographiee, une table oubliee ou un fichier jamais
enregistre ne se signalent **nulle part** : l'application se contente de ne
rien dire, ce que personne ne remarque.

Le projet en a la preuve. `repos_20.wav` etait sur le disque depuis toujours,
`annoncer_temps_repos` demandait la cle `"repos_20"`, et le dictionnaire
`messages` ne la declarait pas : le seuil des vingt secondes de repos etait
muet **des deux cotes**, sans que rien ne l'ait jamais dit. La meme inspection
sort encore `temps_30`, declare dans `priorites` et introuvable ailleurs.

Six questions, donc, posees a froid plutot qu'en seance :

1. toute cle de `priorites` existe-t-elle dans `messages` ?
2. tout fichier declare est-il sur le disque ?
3. toute brique produit-elle un nom de fichier **unique** ?
4. les noms restent-ils lisibles, c'est-a-dire les phrases courtes ?
5. les orientations declarees sur les mouvements sont-elles au vocabulaire ?
6. le jumeau JavaScript porte-t-il les memes fonctions ?

Usage : `python -m scripts.verifier_annonces`
"""

import ast
import re
import sys
from pathlib import Path

from audio import annonces
from session.seances import catalogue_mouvements

RACINE = Path(__file__).resolve().parent.parent
SONS = RACINE / "audio" / "Fichiers"
COACH = RACINE / "audio" / "coach.py"
ANNONCES_JS = RACINE / "web" / "static" / "js" / "annonces.js"


def _tables_de_coach():
    """`messages` et `priorites`, lues sans importer le module.

    Meme raison que dans `preparer_demo` : `audio.coach` tire pygame, donc une
    machine sans carte son ne peut pas l'importer — et un serveur n'en a pas.
    """
    arbre = ast.parse(COACH.read_text(encoding="utf-8"))
    tables = {}
    for noeud in arbre.body:
        cibles = getattr(noeud, "targets", [])
        nom = getattr(cibles[0], "id", None) if cibles else None
        if nom in {"messages", "priorites"}:
            tables[nom] = ast.literal_eval(noeud.value)
    return tables


def _cles_declarees_mais_muettes(tables):
    """Une priorite sans fichier : le son est demande, rien ne sort."""
    return sorted(set(tables.get("priorites", {})) - set(tables.get("messages", {})))


def _fichiers_attendus():
    """Tout ce que le coach peut reclamer, brique ou evenement."""
    tables = _tables_de_coach()

    attendus = set()
    for variantes in tables.get("messages", {}).values():
        attendus.update(variantes)
    attendus.update(annonces.fichier(texte) for texte in annonces.BRIQUES.values())
    attendus.update(annonces.fichier(nom) for nom in catalogue_mouvements())
    attendus.update(
        annonces.fichier(str(n)) for n in range(1, annonces.NOMBRE_MAXIMAL_DIT + 1)
    )
    return attendus


def _collisions():
    """Deux briques differentes qui produiraient le meme fichier.

    C'est la seule facon dont la regle « le nom du fichier est le texte » peut
    se retourner contre elle : deux textes qui ne different que par leur
    ponctuation s'ecrasent, et l'un des deux est prononce a la place de
    l'autre — sans aucun message.
    """
    par_fichier = {}
    sources = {cle: texte for cle, texte in annonces.BRIQUES.items()}
    sources.update({f"mouvement:{nom}": nom for nom in catalogue_mouvements()})

    for origine, texte in sources.items():
        par_fichier.setdefault(annonces.fichier(texte), []).append(origine)

    return {f: o for f, o in par_fichier.items() if len(o) > 1}


def _noms_trop_longs():
    """Des phrases trop longues pour faire de bonnes briques.

    Le nom mesure la phrase. Au-dela du plafond, on ne tronque pas : on
    **decoupe** la brique, qui redevient reutilisable et reenregistrable.
    """
    trop = {}
    for cle, texte in annonces.BRIQUES.items():
        nom = annonces.fichier(texte)
        if len(nom) > annonces.LONGUEUR_MAXIMALE_NOM:
            trop[cle] = (len(nom), texte)
    return trop


def _orientations_invalides():
    """Un mouvement dont l'orientation sort du vocabulaire ferme."""
    invalides = {}
    for nom, mouvement in catalogue_mouvements().items():
        orientation = getattr(mouvement, "orientation", None)
        if orientation is not None and orientation not in annonces.ORIENTATIONS:
            invalides[nom] = orientation
    return invalides


def _fonctions_manquantes_en_js():
    """Le jumeau porte-t-il les memes fonctions, sous les memes noms ?

    L'appariement se fait par le **nom**, comme partout dans le portage : c'est
    ce qui dispense d'une table de correspondance, laquelle deriverait.
    """
    if not ANNONCES_JS.exists():
        return ["(annonces.js absent)"]

    source = ANNONCES_JS.read_text(encoding="utf-8")
    exportees = set(re.findall(r"export function (\w+)", source))

    attendues = {
        nom
        for nom, valeur in vars(annonces).items()
        if callable(valeur) and not nom.startswith("_")
    }
    return sorted(attendues - exportees)


def main():
    problemes = []

    tables = _tables_de_coach()

    for cle in _cles_declarees_mais_muettes(tables):
        problemes.append(
            f"cle « {cle} » : une priorite lui est donnee, mais aucun fichier — "
            "elle est demandee et ne produit rien"
        )

    manquants = sorted(f for f in _fichiers_attendus() if not (SONS / f).exists())

    for fichier, origines in sorted(_collisions().items()):
        problemes.append(
            f"collision sur « {fichier} » : {', '.join(sorted(origines))} "
            "produisent le meme nom, l'un sera prononce a la place de l'autre"
        )

    for cle, (longueur, texte) in sorted(_noms_trop_longs().items()):
        problemes.append(
            f"brique « {cle} » : {longueur} caracteres de nom de fichier "
            f"(plafond {annonces.LONGUEUR_MAXIMALE_NOM}). La phrase est trop "
            f"longue pour une brique, decoupe-la — « {texte} »"
        )

    for nom, orientation in sorted(_orientations_invalides().items()):
        problemes.append(
            f"« {nom} » : orientation « {orientation} » hors vocabulaire "
            f"({', '.join(annonces.ORIENTATIONS)})"
        )

    for fonction in _fonctions_manquantes_en_js():
        problemes.append(
            f"fonction « {fonction} » : presente en Python, absente "
            "d'annonces.js — le portage ne la couvre pas"
        )

    if problemes:
        print(f"{len(problemes)} problemes :\n")
        for probleme in problemes:
            print(f"  - {probleme}")

    # Les sons manquants ne sont **pas** un probleme : ils sont l'etat normal
    # d'un enregistrement en cours, et un fichier absent est un silence, jamais
    # une panne. Ils se comptent, ils ne font pas echouer.
    attendus = _fichiers_attendus()
    print(
        f"\n{len(attendus) - len(manquants)} / {len(attendus)} sons enregistres."
        f" {len(manquants)} restent a faire — voir audio/A_ENREGISTRER.md"
    )

    if problemes:
        return 1

    print("Les tables du coach se tiennent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
