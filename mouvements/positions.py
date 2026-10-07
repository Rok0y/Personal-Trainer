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


def _torse_vertical(corps):
    """Le buste est-il debout ? Les épaules nettement au-dessus des hanches.

    On compare l'écart vertical entre le milieu des épaules et le milieu des
    hanches à leur écart horizontal : debout, le premier domine ; allongé, le
    second. Aucun seuil à régler, et l'orientation de la caméra n'y change
    rien — de face comme de profil, un buste debout est vertical dans l'image.
    """
    epaules_x = (corps.epaule_gauche.x + corps.epaule_droite.x) / 2
    epaules_y = (corps.epaule_gauche.y + corps.epaule_droite.y) / 2
    hanches_x = (corps.hanche_gauche.x + corps.hanche_droite.x) / 2
    hanches_y = (corps.hanche_gauche.y + corps.hanche_droite.y) / 2

    return hanches_y - epaules_y > abs(hanches_x - epaules_x)


def deux_bras_leves(corps):
    """Détecte les deux bras levés au-dessus des épaules, **debout**.

    Le buste debout n'est pas un raffinement : allongé sur le dos et filmé de
    côté, « poignets au-dessus des épaules, coudes tendus » est exactement la
    position haute du développé couché. Trois secondes bras tendus, et le geste
    de remise à zéro effaçait la série en cours. Un geste de contrôle ne doit
    pas pouvoir se confondre avec un mouvement d'exercice ; debout, on ne
    soulève rien bras tendus en marquant trois secondes d'arrêt — sauf au
    verrouillage d'un développé épaule, limite connue.
    """
    return (
        bras_droit_leve(corps) and bras_gauche_leve(corps) and _torse_vertical(corps)
    )


print("positions chargé")
