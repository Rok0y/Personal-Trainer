"""
Catalogue des positions du corps.
Chaque fonction retourne True ou False.
"""

from mouvements.outils import calculer_angle


def bras_droit_leve(corps):
    """
    Détecte si le bras droit est levé.
    """
    angle_coude_droit = calculer_angle(
        corps.poignet_droit, corps.coude_droit, corps.epaule_droite
    )

    return corps.poignet_droit.y < corps.epaule_droite.y and angle_coude_droit > 160


def bras_gauche_leve(corps):
    """
    Détecte si le bras gauche est levé.
    """
    angle_coude_gauche = calculer_angle(
        corps.poignet_gauche, corps.coude_gauche, corps.epaule_gauche
    )

    return corps.poignet_gauche.y < corps.epaule_gauche.y and angle_coude_gauche > 160


def bras_en_x(corps):
    """
    Détecte la position bras en croix : bras tendus, à hauteur d'épaules.

    Les trois premières conditions ne vérifient que l'écartement horizontal.
    Prises seules, elles étaient vraies pour à peu près n'importe quelle
    posture — bras le long du corps, bras au-dessus de la tête, jumping jack
    en cours — et le geste « valider la série », qui déclenche au bout de
    3 secondes de maintien, se déclenchait donc tout seul.

    La contrainte de hauteur est proportionnelle à la largeur d'épaules
    plutôt qu'exprimée en valeur absolue : les coordonnées MediaPipe sont
    normalisées sur la taille de l'image, donc un seuil fixe deviendrait
    plus sévère à mesure qu'on s'éloigne de la caméra.
    """
    largeur_epaules = abs(corps.epaule_droite.x - corps.epaule_gauche.x)
    hauteur_epaules = (corps.epaule_gauche.y + corps.epaule_droite.y) / 2
    tolerance = largeur_epaules * 0.5

    return (
        corps.poignet_gauche.x < corps.epaule_gauche.x
        and corps.poignet_droit.x > corps.epaule_droite.x
        and corps.poignet_droit.x > corps.poignet_gauche.x
        and abs(corps.poignet_gauche.y - hauteur_epaules) < tolerance
        and abs(corps.poignet_droit.y - hauteur_epaules) < tolerance
    )


def deux_bras_leves(corps):
    """Détecte les deux bras levés au-dessus des épaules."""
    return bras_droit_leve(corps) and bras_gauche_leve(corps)


print("positions chargé")
