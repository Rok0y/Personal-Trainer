from mouvements.outils import calculer_angle


def curl_biceps_droit(corps):
    angle = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if angle < 30:
        return "fin"
    elif angle > 160:
        return "debut"
    return "milieu"

def curl_biceps_gauche(corps):
    angle = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    if angle < 35:
        return "fin"
    elif angle > 160:
        return "debut"
    return "milieu"

def elevation_laterale(corps):
    angle_coude_droit = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    angle_coude_gauche = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if corps.poignet_droit.y > corps.epaule_droite.y and corps.poignet_gauche.y > corps.epaule_gauche.y:
        return "debut"
    else:
        return "fin" 

def pompe(corps):
    angle_coude_droit = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    angle_coude_gauche = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if angle_coude_droit and angle_coude_gauche < 100:
        return "fin"
    elif angle_coude_droit and angle_coude_gauche > 160:
        return "debut"
    return "milieu"

def developpe_couche_sol(corps):
    angle_coude_droit = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    angle_coude_gauche = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if angle_coude_droit and angle_coude_gauche < 100:
        return "fin"
    elif angle_coude_droit and angle_coude_gauche > 160:
        return "debut"
    return "milieu"

def extension_triceps_au_dessus_de_la_tete(corps):
    angle_coude_droit = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    angle_coude_gauche = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if angle_coude_droit and angle_coude_gauche < 90:
        return "fin"
    elif angle_coude_droit and angle_coude_gauche > 150:
        return "debut"
    return "milieu"

def developpe_epaule(corps):
    angle_coude_droit = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    angle_coude_gauche = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if angle_coude_droit and angle_coude_gauche < 40:
        return "fin"
    elif angle_coude_droit and angle_coude_gauche > 150:
        return "debut"
    return "milieu"