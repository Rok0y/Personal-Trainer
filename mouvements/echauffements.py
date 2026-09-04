"""Mouvements d'échauffement, joués en mode `echauffement` avant les exercices.

Contrairement à `mouvements/exercices.py`, la fonction de détection est ici
facultative : le mode avance au chrono, et une détection ne sert qu'à alimenter
l'affichage. Les rotations articulaires (cou, poignets, coudes) sont déclarées
sans détection : ce sont des mouvements trop petits pour que l'estimation de
pose les suive de façon fiable, et une heuristique bancale afficherait
n'importe quoi à l'écran sans rien apporter.

Les mouvements qui reprennent un exercice du catalogue en version échauffement
réutilisent sa fonction de détection plutôt que d'en dupliquer une variante.
"""

from mouvements.exercices import elevation_laterale_detection, pompe_detection, squat_detection
from session.circuit import Exercice


# ==================================
# Jumping jacks
# ==================================
def jumping_jacks_detection(corps):
    """Renvoie "fin" bras et jambes écartés, "debut" au repos, "milieu" entre.

    Rappel du repère MediaPipe : `y` croît vers le BAS de l'image, et `x` vers
    la droite. Les coordonnées sont normalisées (0-1) sur la taille de l'image,
    donc comparer des écarts entre points reste valable quelle que soit ta
    distance à la caméra — mais pas des valeurs absolues.
    """
    # TODO : détection jamais écrite. Sans conséquence pour l'instant — un
    # échauffement avance au temps et n'utilise la détection que pour l'affichage.
    return "milieu"


# ==================================
# Déclaration des mouvements
# ==================================

rotation_cou = Exercice(
    nom="Rotation du cou",
    description="Rotations lentes de la tête, d'une épaule à l'autre.",
    instructions=[
        "Va lentement, sans à-coup.",
        "Ne force jamais en arrière.",
    ],
)

rotation_epaules = Exercice(
    nom="Rotation des épaules",
    description="Grands cercles d'épaules, bras relâchés le long du corps.",
    instructions=[
        "Cherche l'amplitude maximale.",
        "Cinq tours vers l'arrière, puis cinq vers l'avant.",
    ],
)

rotation_coudes = Exercice(
    nom="Rotation des coudes",
    description="Bras écartés, avant-bras qui décrivent des cercles.",
    instructions=[
        "Garde les bras à l'horizontale.",
        "Change de sens à mi-parcours.",
    ],
)

rotation_poignets = Exercice(
    nom="Rotation des poignets",
    description="Doigts entrelacés, rotations des poignets dans les deux sens.",
    instructions=[
        "Amplitude complète, sans forcer.",
        "Change de sens à mi-parcours.",
    ],
)

elevations_laterales_a_vide = Exercice(
    nom="Élévations latérales à vide",
    detection=elevation_laterale_detection,
    description="Élévations latérales sans charge, pour ouvrir les épaules.",
    instructions=[
        "Monte jusqu'à l'horizontale, pas plus haut.",
        "Descends lentement, sans relâcher d'un coup.",
    ],
)

pompes_lentes = Exercice(
    nom="Pompes lentes",
    detection=pompe_detection,
    description="Pompes très lentes, pour réveiller épaules et pectoraux.",
    instructions=[
        "Trois secondes à la descente.",
        "Garde le corps gainé, sans creuser le dos.",
    ],
)

jumping_jacks = Exercice(
    nom="Jumping jacks",
    detection=jumping_jacks_detection,
    description="Sauts avec écart des bras et des jambes.",
    instructions=[
        "Bras au-dessus de la tête en haut du mouvement.",
        "Amortis la réception, reste souple sur les genoux.",
        "Recule assez pour rester dans le champ de la caméra.",
    ],
)

squat_de_priere = Exercice(
    nom="Squat de prière",
    detection=squat_detection,
    description="Squat sans charge, mains jointes devant la poitrine.",
    instructions=[
        "Descends jusqu'à ce que les cuisses soient parallèles au sol.",
        "Garde le dos droit et les talons au sol.",
    ],
)

squat_lent = Exercice(
    nom="Squat lent",
    detection=squat_detection,
    description="Squat sans charge, à vitesse très ralentie.",
    instructions=[
        "Trois secondes à la descente, trois à la remontée.",
        "Garde le dos droit et les talons au sol.",
    ],
)

rotation_genoux = Exercice(
    nom="Rotation des genoux",
    description="Pieds joints, mains sur les genoux, rotations en cercle.",
    instructions=[
        "Amplitude modérée, sans forcer.",
        "Change de sens à mi-parcours.",
    ],
)

rotation_chevilles = Exercice(
    nom="Rotation des chevilles",
    description="En appui sur une jambe, rotations de la cheville libre.",
    instructions=[
        "Amplitude complète, sans forcer.",
        "Change de sens et de jambe à mi-parcours.",
    ],
)

hanches_avant_arriere = Exercice(
    nom="Hanches en avant en arrière",
    description="Bassin qui bascule d'avant en arrière, jambes légèrement fléchies.",
    instructions=[
        "Reste souple sur les genoux.",
        "Va lentement, sans à-coup.",
    ],
)

abducteurs = Exercice(
    nom="Abducteurs",
    description="Écartement latéral de la jambe, en appui sur l'autre.",
    instructions=[
        "Monte la jambe sur le côté, sans pencher le buste.",
        "Change de jambe à mi-parcours.",
    ],
)

hip_thrust = Exercice(
    nom="Hip thrust",
    description="Allongé sur le dos, genoux fléchis, bascule du bassin vers le haut.",
    instructions=[
        "Serre les fessiers en haut du mouvement.",
        "Descends sans reposer complètement le bassin au sol.",
    ],
)

extensions_mollets = Exercice(
    nom="Extensions de mollets",
    description="Montées sur la pointe des pieds, sans charge.",
    instructions=[
        "Monte au maximum sur la pointe des pieds.",
        "Descends lentement, sans relâcher d'un coup.",
    ],
)

montees_de_genou = Exercice(
    nom="Montées de genou",
    description="Genoux montés alternativement à hauteur de hanche, sur place.",
    instructions=[
        "Monte le genou à hauteur de hanche.",
        "Garde un rythme régulier, sans te pencher en arrière.",
    ],
)
