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
    Détecte les avant-bras croisés devant le buste : poignet gauche passé
    du côté droit et poignet droit du côté gauche, sans dépasser la largeur
    des épaules. La hauteur n'est volontairement pas contrainte — la croix
    peut se former aussi bien devant la poitrine que devant le ventre.
    """
    x_min_epaules = min(corps.epaule_gauche.x, corps.epaule_droite.x)
    x_max_epaules = max(corps.epaule_gauche.x, corps.epaule_droite.x)

    return (
        corps.poignet_gauche.x < corps.poignet_droit.x
        and x_min_epaules <= corps.poignet_gauche.x <= x_max_epaules
        and x_min_epaules <= corps.poignet_droit.x <= x_max_epaules
    )


def deux_bras_leves(corps):
    """Détecte les deux bras levés au-dessus des épaules."""
    return bras_droit_leve(corps) and bras_gauche_leve(corps)


print("positions chargé")
