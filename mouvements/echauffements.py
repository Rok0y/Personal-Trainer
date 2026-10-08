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
from mouvements.fiches import textes
from session.circuit import Exercice


# ==================================
# Déclaration des mouvements
# ==================================

rotation_cou = Exercice(
    nom="Rotation du cou",
    **textes("Rotation du cou"),
)

rotation_epaules = Exercice(
    nom="Rotation des épaules",
    **textes("Rotation des épaules"),
    changements=[(0.5, "sens")],
)

rotation_coudes = Exercice(
    nom="Rotation des coudes",
    **textes("Rotation des coudes"),
    changements=[(0.5, "sens")],
)

rotation_poignets = Exercice(
    nom="Rotation des poignets",
    **textes("Rotation des poignets"),
    changements=[(0.5, "sens")],
)

elevations_laterales_a_vide = Exercice(
    nom="Élévations latérales à vide",
    **textes("Élévations latérales à vide"),
    detection=elevation_laterale_detection,
)

pompes_lentes = Exercice(
    nom="Pompes lentes",
    **textes("Pompes lentes"),
    detection=pompe_detection,
)

# `detection=None`, comme les rotations articulaires : la fonction qui vivait
# ici retournait `"milieu"` quoi qu'elle reçoive — un squelette immobile, une
# pose absurde, n'importe quoi. Elle ne mesurait donc rien, et affichait
# pourtant « En mouvement » dans la carte « Étape », ce qui est pire que muet :
# un échauffement avance au temps, donc la seule chose que cette détection
# produisait était une position inventée. Même règle que l'orientation caméra,
# qui n'a volontairement pas de valeur par défaut.
#
# Le portage JavaScript ne l'avait jamais eue, et c'est ce côté-là qui était
# juste : l'application affichait « Échauffement en cours », c'est-à-dire la
# vérité. Écrire un jour une vraie détection de jumping jacks se fera des deux
# côtés à la fois, comme toute détection.
jumping_jacks = Exercice(
    nom="Jumping jacks",
    **textes("Jumping jacks"),
)

squat_de_priere = Exercice(
    nom="Squat de prière",
    **textes("Squat de prière"),
    detection=squat_detection,
)

squat_lent = Exercice(
    nom="Squat lent",
    **textes("Squat lent"),
    detection=squat_detection,
)

rotation_genoux = Exercice(
    nom="Rotation des genoux",
    **textes("Rotation des genoux"),
    changements=[(0.5, "sens")],
)

rotation_chevilles = Exercice(
    nom="Rotation des chevilles",
    **textes("Rotation des chevilles"),
    # Sens, jambe, sens : chaque cheville tourne dans les deux sens.
    changements=[(0.25, "sens"), (0.5, "jambe"), (0.75, "sens")],
)

hanches_avant_arriere = Exercice(
    nom="Hanches en avant en arrière",
    **textes("Hanches en avant en arrière"),
)

abducteurs = Exercice(
    nom="Abducteurs",
    **textes("Abducteurs"),
    changements=[(0.5, "jambe")],
)

hip_thrust = Exercice(
    nom="Hip thrust",
    **textes("Hip thrust"),
)

extensions_mollets = Exercice(
    nom="Extensions de mollets",
    **textes("Extensions de mollets"),
)

montees_de_genou = Exercice(
    nom="Montées de genou",
    **textes("Montées de genou"),
)
