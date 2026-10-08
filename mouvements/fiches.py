"""Les textes des fiches d'exercice, lus dans `mouvements/fiches.json`.

**Le texte d'un mouvement vit dans un fichier, pas dans le code**, pour la
même raison que les barèmes vivent dans `progression/reglages.json` : une
consigne ne se juge pas en la lisant dans un appel Python, elle se juge en la
lisant **comme la lira la personne qui s'entraîne**. `dev/fiches.html` montre
chaque fiche telle qu'elle s'affiche, à côté de ce que la détection vérifie et
de ce que le coach dira, la rend éditable, et rend le fichier prêt à coller.
`preparer_demo` le copie tel quel dans `donnees/fiches.json` : l'aller-retour
est exact.

Ce qui reste dans le code est ce qui est **couplé au code** : la détection,
l'amplitude, l'orientation et les changements (prononcés par le coach, donc
liés aux prises de son), les variantes (liées aux barèmes). Le texte, lui,
n'est lu par rien d'autre que les écrans.

Cinq champs par mouvement, et ils ne se recouvrent pas — voir
`session.circuit.Exercice` : `description`, `mise_en_place`, `instructions`,
`erreurs_frequentes`, `sensations` (ce qu'on doit sentir, et ce qui ne doit pas
arriver).

Bibliothèque standard seulement : `preparer_demo` importe le catalogue, et le
workflow de déploiement n'installe que numpy.
"""

import json
from pathlib import Path

FICHIER = Path(__file__).with_name("fiches.json")

#: Les champs d'une fiche, et leur forme : une phrase, ou une liste de lignes.
CHAMPS = {
    "description": str,
    "mise_en_place": list,
    "instructions": list,
    "erreurs_frequentes": list,
    "sensations": list,
}

_FICHES = json.loads(FICHIER.read_text(encoding="utf-8"))


def textes(nom):
    """Les textes de la fiche `nom`, prêts à passer à `Exercice(**textes(nom))`.

    **Lève à l'import** si le mouvement n'a pas d'entrée, ou si un champ manque
    ou n'a pas la bonne forme : un catalogue qui démarre est un catalogue dont
    chaque fiche est complète. C'est bruyant au lancement, et jamais dans la
    boucle caméra — l'inverse d'une fiche vide découverte en pleine séance.
    """
    if nom not in _FICHES:
        raise KeyError(f"« {nom} » n'a pas de fiche dans {FICHIER.name}")
    fiche = _FICHES[nom]
    sortie = {}
    for champ, forme in CHAMPS.items():
        valeur = fiche.get(champ)
        if not isinstance(valeur, forme):
            raise ValueError(f"« {nom} » : le champ {champ} doit être une {forme.__name__}")
        sortie[champ] = list(valeur) if forme is list else valeur
    return sortie


def noms():
    """Les mouvements qui ont une fiche, dans l'ordre du fichier."""
    return list(_FICHES)
