"""Ecrit `audio/A_ENREGISTRER.md` : ce qu'il reste a dire au micro.

**Le document est derive, jamais tenu a la main.** C'est toute sa valeur : le
nom du fichier y est celui que le code reclamera, et le texte celui que le nom
traduit, parce que les deux sortent de la meme table. Deux listes qu'on doit
garder d'accord finissent toujours par diverger — celle-ci ne le peut pas.

Il vaut aussi **etat d'avancement** : chaque ligne dit si la prise existe deja
sur le disque. On le relance apres chaque lot plutot que de cocher a la main.

L'ordre des familles n'est pas decoratif, il est economique : les premieres
debloquent le plus de phrases par prise. Trois amorces multipliees par
trente-neuf noms de mouvements font cent dix-sept annonces, cinq prises
d'orientation servent tout le catalogue, onze de cadrage couvrent vingt-huit
consignes ; en bout de liste viennent les lots **un pour un** — une prise par
charge, un nombre par nombre — qu'on peut arreter en route sans rien casser.

    python -m scripts.lister_annonces
"""

import sys
from pathlib import Path

from audio import annonces
from core.materiel import POIDS_REFERENCE
from progression.paliers import ECHELLE_DEUX_HALTERES, ECHELLE_UN_HALTERE
from session.seances import CATALOGUE_ECHAUFFEMENTS, CATALOGUE_EXERCICES

RACINE = Path(__file__).resolve().parent.parent
SONS = RACINE / "audio" / "Fichiers"
SORTIE = RACINE / "audio" / "A_ENREGISTRER.md"

#: Les familles, dans l'ordre ou on gagne a les enregistrer. La cle est le
#: prefixe des cles de `BRIQUES` ; les familles suivantes ne viennent pas de
#: cette table mais du catalogue, des gammes d'halteres et des nombres.
#:
#: `FRAGMENTS` n'y figure pas, et c'est tout l'objet du decoupage : ces
#: morceaux ne s'enregistrent jamais seuls, ils sont deja dans les phrases
#: assemblees plus bas.
FAMILLES = [
    (
        ("prochain_exercice", "premier_exercice", "dernier_exercice"),
        "Amorces d'annonce",
        "Trois facons d'annoncer un mouvement, selon sa place dans la seance. "
        "Elles se disent **devant** un nom d'exercice, jamais seules : "
        "prononce-les suspendues, sans chute de fin de phrase — « prochain "
        "exercice : curl biceps droit ». Trois prises x trente-neuf noms = "
        "cent dix-sept annonces, et c'est ce qui justifie que le nom du "
        "mouvement reste une prise a part.",
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
    """Une prise par mouvement, **le nom seul**.

    Il se dit derriere chacune des trois amorces, donc il se recombine : trois
    prises et trente-neuf noms valent cent dix-sept annonces. L'avoir cousu
    dans la prise de l'amorce aurait demande les cent dix-sept.
    """
    lignes, restants = [], 0
    for nom in sorted(catalogue):
        fichier = annonces.fichier(nom)
        etat = _etat(fichier)
        restants += etat.startswith("**")
        lignes.append(f"| `{fichier}` | « {nom} » | {etat} |")
    return lignes, restants


def _lignes_charges(couples):
    """Une prise par (nombre d'halteres, poids), dans l'ordre de la gamme."""
    lignes, restants = [], 0
    for halteres, poids in couples:
        texte = annonces.texte_charge(halteres, poids)
        fichier = annonces.fichier(texte)
        etat = _etat(fichier)
        restants += etat.startswith("**")
        lignes.append(f"| `{fichier}` | « {texte} » | {etat} |")
    return lignes, restants


def _gamme_courante():
    """Les charges que le bareme propose avec le materiel suppose.

    Deux echelles et non une : au-dela de 10 kg le materiel par defaut n'a
    qu'un exemplaire de chaque haltere, donc un mouvement bilateral s'arrete
    la. Ce sont exactement les bornes de `progression/paliers.py`, d'ou elles
    sont lues plutot que recopiees.
    """
    return [(1, poids) for poids in ECHELLE_UN_HALTERE] + [
        (2, poids) for poids in ECHELLE_DEUX_HALTERES
    ]


def _gamme_lourde():
    """Le reste de ce que le questionnaire propose de posseder.

    `POIDS_REFERENCE` va jusqu'a 40 kg : quelqu'un qui declare ce materiel
    verra ces charges dans ses objectifs. Ce lot est donc utile mais **passe
    en dernier**, et se coupe a la hauteur de son propre placard — une charge
    sans prise laisse l'annonce breve, jamais muette.
    """
    return [(1, p) for p in POIDS_REFERENCE if p > max(ECHELLE_UN_HALTERE)] + [
        (2, p) for p in POIDS_REFERENCE if p > max(ECHELLE_DEUX_HALTERES)
    ]


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

## Quatre choses a savoir avant de commencer

**Tu peux y aller par lots.** Un fichier absent est un **silence**, jamais une
panne : le coach abrege sa phrase et la seance continue. Rien n'attend que la
liste soit complete, et chaque prise ajoutee fait parler quelque chose de plus.

**Les prises s'enchainent, et chaque famille se prononce en consequence.**
Une annonce de changement d'exercice en joue quatre a la suite : « Prochain
exercice » · « Curl biceps droit » · « Prepare un haltere de 8 kilos » ·
« Place-toi de profil ». Les **amorces** et les **noms de mouvements** se
disent donc suspendus, sans chute de fin de phrase — un nom d'exercice est
annonce comme un titre. Les autres familles sont des phrases completes, dites
d'un ton normal.

**Le meme debit et le meme niveau d'une prise a l'autre**, dans tous les cas :
c'est ce qui rend l'enchainement naturel, bien plus que l'intonation de
chacune.

**Une charge ne se decoupe pas**, en revanche : « prepare un haltere de 8
kilos » est une seule prise, parce que couper avant le nombre tombe au milieu
d'un groupe nominal — la ou la voix ne s'arrete jamais — et s'entend comme un
saccadement.

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
            "Le nom **est** le texte : aucune table a tenir a jour a cote du "
            "catalogue, et un exercice ajoute apparait ici tout seul. "
            "Prononce-les **isoles et neutres** : chacun se dit derriere l'une "
            "des trois amorces ci-dessus, et se trouve suivi d'une charge ou "
            "d'une consigne de placement.",
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

    for couples, titre, note in [
        (
            _gamme_courante(),
            "Charges — la gamme courante",
            "Ce que le bareme propose avec le materiel suppose : jusqu'a "
            f"{max(ECHELLE_UN_HALTERE)} kg a un haltere, "
            f"{max(ECHELLE_DEUX_HALTERES)} kg a la paire. Une phrase entiere "
            "par charge : couper avant le nombre tombe au milieu d'un "
            "groupe nominal, et ca s'entend — contrairement a la couture "
            "entre une amorce et un nom d'exercice, qui tombe sur une pause "
            "que la phrase a deja.",
        ),
        (
            _gamme_lourde(),
            "Charges lourdes — a faire en dernier",
            "Le questionnaire de materiel va jusqu'a 40 kg, donc ces charges "
            "existent pour qui les declare. **Coupe ce lot a la hauteur de "
            "ton propre placard** : une charge sans prise rend l'annonce "
            "breve (« prochain exercice, squat »), jamais muette.",
        ),
    ]:
        lignes, restants = _lignes_charges(couples)
        total_restant += restants
        if lignes:
            sections.append(f"## {titre}\n\n{note}\n\n{_tableau(lignes)}")

    lignes, restants = _lignes_nombres()
    total_restant += restants
    sections.append(
        "## Nombres de 21 a 60\n\n"
        "Les vingt premiers sont deja enregistres — ce sont ceux du comptage "
        "des repetitions, reutilises tels quels. Ceux-ci servent la meme chose "
        "au-dela de vingt repetitions, ce que le bareme atteint sur les "
        "mouvements au poids du corps. Les charges, elles, ne passent plus par "
        "eux : elles sont devenues des phrases entieres.\n\n"
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
