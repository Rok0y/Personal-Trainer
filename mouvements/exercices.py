from mouvements.outils import calculer_angle
from session.circuit import Exercice



def curl_biceps_droit_detection(corps):
    angle = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if angle < 30:
        return "fin"
    elif angle > 160:
        return "debut"
    return "milieu"

def coude_trop_tendu_curl_droit(corps):

    # Calcul de ton angle du coude
    angle_coude = 0  # remplacer par ton calcul actuel

    if angle_coude > 170:
        return True

    return False


def epaule_trop_avancee_curl_droit(corps):

    # Calcul de ta position d'épaule
    # à remplacer par ta logique

    return False


curl_biceps_droit = Exercice(
    nom="Curl biceps droit",

    detection=curl_biceps_droit_detection,

    description="Curl biceps avec haltère du bras droit.",

    instructions=[
        "Garde le coude proche du corps.",
        "Contrôle la descente.",
        "Ne balance pas le mouvement."
    ],

    erreurs=[
        coude_trop_tendu_curl_droit,
        epaule_trop_avancee_curl_droit
    ]
)

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

def crunches(corps):
    angle_hanche_droite = calculer_angle(corps.epaule_gauche,corps.hanche_gauche,corps.genou_gauche)
    angle_hanche_gauche = calculer_angle(corps.epaule_droite,corps.hanche_droite,corps.genou_droit)
    if angle_hanche_droite and angle_hanche_gauche < 70:
        return "fin"
    elif angle_hanche_droite and angle_hanche_gauche > 95:
        return "debut"
    return "milieu"