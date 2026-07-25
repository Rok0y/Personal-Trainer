"""
Catalogue des positions du corps.
Chaque fonction retourne True ou False.
"""
from mouvements.outils import calculer_angle


def bras_droit_leve(corps):
    """
    Détecte si le bras droit est levé.
    """
    angle_coude_droit = calculer_angle(corps.poignet_droit, corps.coude_droit, corps.epaule_droite)

    return (
        corps.poignet_droit.y < corps.epaule_droite.y
        and
        angle_coude_droit > 160
    )




def bras_gauche_leve(corps):
    """
    Détecte si le bras gauche est levé.
    """
    angle_coude_gauche = calculer_angle(corps.poignet_gauche, corps.coude_gauche, corps.epaule_gauche)

    return (
        corps.poignet_gauche.y < corps.epaule_gauche.y
        and
        angle_coude_gauche > 160
    )



def bras_en_x(corps):
    """
    Détecte la position bras en croix.
    """

    return (
        corps.poignet_gauche.x < corps.epaule_gauche.x
        and
        corps.poignet_droit.x > corps.epaule_droite.x
    )
print("positions chargé")