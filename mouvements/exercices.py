from mouvements.outils import calculer_angle


def curl_biceps_droit(corps):

    angle = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)

    if angle < 30:
        return "fin"

    elif angle > 160:
        return "debut"

    return "milieu"