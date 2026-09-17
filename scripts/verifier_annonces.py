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

Sept questions, donc, posees a froid plutot qu'en seance :

1. toute cle de `priorites` existe-t-elle dans `messages` ?
2. tout fichier declare est-il sur le disque ?
3. toute brique produit-elle un nom de fichier **unique** ?
4. les noms restent-ils lisibles, c'est-a-dire les phrases courtes ?
5. les orientations declarees sur les mouvements sont-elles au vocabulaire ?
6. les amorces que `Circuit` rend le sont-elles aussi ?
7. le jumeau JavaScript porte-t-il les memes fonctions ?

Usage : `python -m scripts.verifier_annonces`
"""

import ast
import re
import sys
from pathlib import Path

from audio import annonces
from core.materiel import POIDS_REFERENCE
from session.circuit import AMORCES_PAR_POSITION
from session.seances import catalogue_mouvements

#: Les fonctions Python qui n'ont **volontairement** pas de jumelle
#: JavaScript, et pourquoi. Elles se declarent au lieu d'etre tolerees, et la
#: declaration est verifiee **dans les deux sens** : une ligne qui n'excuse
#: plus rien est signalee, faute de quoi la liste pourrit et finit par couvrir
#: un vrai oubli.
FONCTIONS_SANS_JUMEAU = {
    # Le navigateur ne manipule aucun texte prononce : il assemble des noms de
    # fichiers (`fichier_assemble`, qui n'existe que de ce cote-la). Les deux
    # chemins doivent rendre le meme fichier, et c'est `comparer_annonces.mjs`
    # qui le prouve sur toutes les charges.
    "texte_charge",
    # Enumerer les charges a enregistrer ou a copier est un travail de script.
    # Rien ne l'enumere en seance : on compose depuis un poids reel.
    "fichiers_charges",
}

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


def _phrases_enregistrees():
    """Origine -> texte, pour tout ce qui s'enregistre en une prise.

    Les `BRIQUES`, les **noms de mouvements** — le nom est son propre texte,
    et il se dit derriere chacune des trois amorces — puis les **charges**,
    seules phrases assemblees. `FRAGMENTS` n'y est pas : ces morceaux ne sont
    jamais un fichier, ils composent le texte des charges.

    Source unique des trois controles qui suivent (fichiers attendus,
    collisions, longueur des noms) : les separer laisserait un des trois
    ignorer une famille sans que rien ne le dise.
    """
    phrases = dict(annonces.BRIQUES)

    for nom in catalogue_mouvements():
        phrases[f"mouvement:{nom}"] = nom

    for halteres in (1, 2):
        for poids in POIDS_REFERENCE:
            texte = annonces.texte_charge(halteres, poids)
            phrases[f"charge:{halteres}x{poids}"] = texte

    return phrases


def _fichiers_attendus():
    """Tout ce que le coach peut reclamer, phrase ou evenement."""
    tables = _tables_de_coach()

    attendus = set()
    for variantes in tables.get("messages", {}).values():
        attendus.update(variantes)
    attendus.update(
        annonces.fichier(texte) for texte in _phrases_enregistrees().values()
    )
    # Les nombres servent le compteur de repetitions (`coach("compteur", n)`),
    # plus les charges depuis qu'elles sont des phrases entieres.
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

    for origine, texte in _phrases_enregistrees().items():
        par_fichier.setdefault(annonces.fichier(texte), []).append(origine)

    return {f: o for f, o in par_fichier.items() if len(o) > 1}


def _noms_trop_longs():
    """Des phrases trop longues pour faire de bonnes briques.

    Le nom mesure la phrase. Au-dela du plafond, on ne tronque pas : on
    **decoupe** la brique, qui redevient reutilisable et reenregistrable.
    """
    trop = {}
    for cle, texte in _phrases_enregistrees().items():
        nom = annonces.fichier(texte)
        if len(nom) > annonces.LONGUEUR_MAXIMALE_NOM:
            trop[cle] = (len(nom), texte)
    return trop


def _amorces_invalides():
    """Une amorce que `Circuit` peut rendre et que le vocabulaire ignore.

    `session/circuit.py` ne peut pas importer `audio.annonces` sans se lier au
    vocabulaire du coach, et il dit deja ses phases par des chaines. Le prix
    de ce decouplage est qu'une faute de frappe y serait **muette** : `brique`
    leverait en pleine seance, dans un thread ou rien n'attrape. On paie donc
    l'inclusion ici, a froid.
    """
    return sorted(
        set(AMORCES_PAR_POSITION.values()) - set(annonces.AMORCES_EXERCICE)
    )


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

    manquantes = [
        f"fonction « {nom} » : presente en Python, absente d'annonces.js — "
        "le portage ne la couvre pas"
        for nom in sorted(attendues - exportees - FONCTIONS_SANS_JUMEAU)
    ]

    # Le sens inverse : une dispense qui n'excuse plus rien. Sans ce controle
    # la liste pourrit, et une ligne perimee couvrira un vrai oubli le jour ou
    # la fonction reviendra sous le meme nom.
    manquantes += [
        f"dispense « {nom} » : la fonction est pourtant exportee par "
        "annonces.js — retire-la de FONCTIONS_SANS_JUMEAU"
        for nom in sorted(FONCTIONS_SANS_JUMEAU & exportees)
    ]
    manquantes += [
        f"dispense « {nom} » : aucune fonction de ce nom en Python — "
        "retire-la de FONCTIONS_SANS_JUMEAU"
        for nom in sorted(FONCTIONS_SANS_JUMEAU - attendues)
    ]

    return manquantes


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

    for amorce in _amorces_invalides():
        problemes.append(
            f"amorce « {amorce} » : rendue par Circuit.amorce_annonce mais "
            f"hors du vocabulaire ({', '.join(annonces.AMORCES_EXERCICE)}) — "
            "`brique()` leverait en pleine seance"
        )

    for nom, orientation in sorted(_orientations_invalides().items()):
        problemes.append(
            f"« {nom} » : orientation « {orientation} » hors vocabulaire "
            f"({', '.join(annonces.ORIENTATIONS)})"
        )

    problemes.extend(_fonctions_manquantes_en_js())

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
