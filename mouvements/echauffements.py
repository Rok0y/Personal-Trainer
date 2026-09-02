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

from mouvements.exercices import elevation_laterale_detection, pompe_detection
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
    # TODO(human)
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
