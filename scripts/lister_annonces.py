"""Ecrit `audio/A_ENREGISTRER.md` : ce qu'il reste a dire au micro.

**Le document est derive, jamais tenu a la main.** C'est toute sa valeur : le
nom du fichier y est celui que le code reclamera, et le texte celui que le nom
traduit, parce que les deux sortent de la meme table. Deux listes qu'on doit
garder d'accord finissent toujours par diverger — celle-ci ne le peut pas.

Il vaut aussi **etat d'avancement** : chaque ligne dit si la prise existe deja
sur le disque. On le relance apres chaque lot plutot que de cocher a la main.

L'ordre des familles n'est pas decoratif, il est economique : les premieres
debloquent le plus de phrases par prise. Les douze briques de liaison et
d'orientation font parler tout le catalogue ; les quarante nombres ne servent
qu'aux charges les plus lourdes.

    python -m scripts.lister_annonces
"""

import sys
from pathlib import Path

from audio import annonces
from session.seances import CATALOGUE_ECHAUFFEMENTS, CATALOGUE_EXERCICES

RACINE = Path(__file__).resolve().parent.parent
SONS = RACINE / "audio" / "Fichiers"
SORTIE = RACINE / "audio" / "A_ENREGISTRER.md"

#: Les familles, dans l'ordre ou on gagne a les enregistrer. La cle est le
#: prefixe des cles de `BRIQUES` ; les trois dernieres familles ne viennent pas
#: de cette table mais du catalogue et des nombres.
FAMILLES = [
    (
        ("prochain_exercice", "prepare_", "kilo"),
        "Liaisons",
        "Les mots qui cousent une annonce. Prononces **a plat**, au milieu "
        "d'une phrase : une intonation de fin de phrase rendrait la couture "
        "audible.",
    ),
    (
        ("orientation_",),
        "Orientation par rapport a la camera",
        "Cinq prises couvrent les trente-neuf mouvements du catalogue. C'est "
        "le meilleur rapport du lot.",
    ),
    (
        ("cadrage_",),
        "Cadrage",
        "Sept parties du corps et quatre actions, assemblees deux a deux : "
        "onze prises couvrent les vingt-huit consignes possibles.",
    ),
    (
        ("installation_", "geste_"),
        "Installation et gestes",
        "Le guidage du debut de seance, dit camera ouverte pendant qu'on se "
        "place.",
    ),
    (
        ("bienvenue",),
        "Accueil d'un nouveau profil",
        "Joue une seule fois dans la vie d'un profil. A enregistrer en "
        "dernier parmi les briques.",
    ),
]


def nombre_en_lettres(n):
    """« vingt-et-un » pour 21. Sert au document, jamais au code.

    Le fichier s'appelle `21.wav` — un nombre est son propre texte, donc son
    nom n'a pas besoin d'etre traduit. Mais on n'enregistre pas un chiffre, on
    enregistre un mot : la colonne « a prononcer » doit le donner.
    """
    unites = [
        "", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit",
        "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze",
        "seize", "dix-sept", "dix-huit", "dix-neuf",
    ]
    dizaines = {20: "vingt", 30: "trente", 40: "quarante", 50: "cinquante",
                60: "soixante"}

    if n < 20:
        return unites[n]

    dizaine, unite = (n // 10) * 10, n % 10

    if unite == 0:
        return dizaines[dizaine]
    if unite == 1:
        return f"{dizaines[dizaine]}-et-un"
    return f"{dizaines[dizaine]}-{unites[unite]}"


def _etat(fichier):
    return "deja fait" if (SONS / fichier).exists() else "**a enregistrer**"


def _tableau(lignes):
    """Un tableau Markdown, ou rien si la famille est complete."""
    entete = [
        "| Fichier | A prononcer | Etat |",
        "| --- | --- | --- |",
    ]
    return "\n".join(entete + lignes)


def _lignes_briques(prefixes):
    lignes, restants = [], 0
    for cle, texte in annonces.BRIQUES.items():
        if not cle.startswith(tuple(prefixes)):
            continue
        fichier = annonces.fichier(texte)
        etat = _etat(fichier)
        restants += etat.startswith("**")
        lignes.append(f"| `{fichier}` | « {texte} » | {etat} |")
    return lignes, restants


def _lignes_mouvements(catalogue):
    lignes, restants = [], 0
    for nom in sorted(catalogue):
        fichier = annonces.fichier(nom)
        etat = _etat(fichier)
        restants += etat.startswith("**")
        lignes.append(f"| `{fichier}` | « {nom} » | {etat} |")
    return lignes, restants


def _lignes_nombres():
    lignes, restants = [], 0
    for n in range(21, annonces.NOMBRE_MAXIMAL_DIT + 1):
        fichier = annonces.fichier(str(n))
        etat = _etat(fichier)
        restants += etat.startswith("**")
        lignes.append(f"| `{fichier}` | « {nombre_en_lettres(n)} » | {etat} |")
    return lignes, restants


EN_TETE = """# Ce qu'il reste a enregistrer

> Ce fichier est **genere**. Ne le modifie pas a la main : relance
> `python -m scripts.lister_annonces` apres chaque lot, il se met a jour tout
> seul et recompte ce qui reste.

## Comment enregistrer

1. Enregistre chaque phrase dans un `.wav` portant **exactement** le nom donne
   ci-dessous, et depose-le dans `audio/a_traiter/`.
2. Lance `python audio/nettoyer_sons.py` : il rogne les silences, pose un fondu
   et ecrit le resultat dans `audio/Fichiers/`.
3. Lance `python -m scripts.preparer_demo` pour que l'application les recoive.

## Trois choses a savoir avant de commencer

**Tu peux y aller par lots.** Un fichier absent est un **silence**, jamais une
panne : le coach abrege sa phrase et la seance continue. Rien n'attend que la
liste soit complete, et chaque prise ajoutee fait parler quelque chose de plus.

**Prononce a plat.** Ces phrases sont assemblees bout a bout — « prochain
exercice », « curl biceps droit », « prepare un haltere de », « huit »,
« kilos ». Une intonation descendante de fin de phrase ferait entendre la
couture au milieu de l'annonce. Garde le meme debit et le meme niveau d'une
prise a l'autre, c'est ce qui rend l'assemblage invisible.

**Le nom du fichier est le texte.** Si une formulation ne te plait pas, change
le texte dans `audio/annonces.py` et relance ce script : le nom de fichier
suivra. L'inverse — renommer un fichier — ne changerait rien, le code cherche
le nom que la table produit.
"""


def main():
    sections, total_restant = [], 0

    for prefixes, titre, note in FAMILLES:
        lignes, restants = _lignes_briques(prefixes)
        total_restant += restants
        if lignes:
            sections.append(f"## {titre}\n\n{note}\n\n{_tableau(lignes)}")

    for catalogue, titre, note in [
        (
            CATALOGUE_EXERCICES,
            "Noms des exercices",
            "Le nom **est** le texte : il n'y a aucune table a tenir a jour a "
            "cote du catalogue, et un exercice ajoute apparait ici tout seul.",
        ),
        (
            CATALOGUE_ECHAUFFEMENTS,
            "Noms des echauffements",
            "Meme regle. Ils sont annonces comme les exercices, meme s'ils ne "
            "comptent nulle part dans les statistiques.",
        ),
    ]:
        lignes, restants = _lignes_mouvements(catalogue)
        total_restant += restants
        if lignes:
            sections.append(f"## {titre}\n\n{note}\n\n{_tableau(lignes)}")

    lignes, restants = _lignes_nombres()
    total_restant += restants
    sections.append(
        "## Nombres de 21 a 60\n\n"
        "Les vingt premiers sont deja enregistres — ce sont ceux du comptage "
        "des repetitions, reutilises tels quels. Au-dela de soixante, le coach "
        "se tait sur le nombre et poursuit sa phrase : c'est un lot a faire en "
        "dernier, il ne sert qu'aux charges et aux cibles les plus elevees.\n\n"
        f"{_tableau(lignes)}"
    )

    document = (
        f"{EN_TETE}\n"
        f"**{total_restant} prises restantes.**\n\n"
        + "\n\n".join(sections)
        + "\n"
    )
    SORTIE.write_text(document, encoding="utf-8")

    print(f"{SORTIE.relative_to(RACINE)} ecrit — {total_restant} prises restantes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
