"""Mouvements d'échauffement, joués en mode `echauffement` avant les exercices.

Contrairement à `mouvements/exercices.py`, la fonction de détection est ici
facultative : le mode avance au chrono, et une détection ne sert qu'à alimenter
l'affichage. Un mouvement trop diffus pour être analysé de façon fiable (des
rotations d'épaules, un buste qui pivote) est déclaré sans détection plutôt
qu'avec une heuristique bancale qui afficherait n'importe quoi à l'écran.
"""

from mouvements.exercices import squat_detection
from session.circuit import Exercice


# ==================================
# Montées de genoux
# ==================================
def montees_genoux_detection(corps):
    """Course sur place : renvoie "fin" quand un genou est monté, "debut" sinon.

    Rappel du repère MediaPipe : `y` croît vers le BAS de l'image, donc un
    genou plus haut que sa hanche vérifie `genou.y < hanche.y`.

    Contrairement aux exercices bilatéraux (pompes, développé), on veut ici un
    OU et non un ET : les genoux montent en alternance, jamais ensemble.
    """
    # TODO(human)
    return "debut"


# ==================================
# Déclaration des mouvements
# ==================================

rotation_epaules = Exercice(
    nom="Rotation des épaules",
    description="Grands cercles d'épaules, bras relâchés le long du corps.",
    instructions=[
        "Cherche l'amplitude maximale.",
        "Cinq tours vers l'arrière, puis cinq vers l'avant.",
    ],
)

rotations_buste = Exercice(
    nom="Rotations du buste",
    description="Bassin fixe, rotations lentes du buste de gauche à droite.",
    instructions=[
        "Garde les hanches face à la caméra.",
        "Laisse les bras suivre le mouvement sans forcer.",
    ],
)

cercles_bras = Exercice(
    nom="Cercles de bras",
    description="Bras tendus à l'horizontale, cercles vers l'avant puis l'arrière.",
    instructions=[
        "Garde les coudes tendus.",
        "Commence petit, agrandis les cercles progressivement.",
    ],
)

talons_fesses = Exercice(
    nom="Talons-fesses",
    description="Course sur place, talons ramenés vers les fesses.",
    instructions=[
        "Reste sur l'avant des pieds.",
        "Garde le buste droit, ne te penche pas en avant.",
    ],
)

montees_genoux = Exercice(
    nom="Montées de genoux",
    detection=montees_genoux_detection,
    description="Course sur place, genoux montés à hauteur de hanches.",
    instructions=[
        "Monte les genoux au niveau des hanches.",
        "Reste dans le champ de la caméra.",
    ],
)

squat_a_vide = Exercice(
    nom="Squat à vide",
    detection=squat_detection,
    description="Squats lents et sans charge, pour ouvrir les hanches.",
    instructions=[
        "Descends lentement, plus bas à chaque répétition.",
        "Garde le dos droit et les talons au sol.",
    ],
)
