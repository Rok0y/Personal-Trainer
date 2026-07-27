from mouvements.outils import calculer_angle
from session.circuit import Exercice


# ==================================
# Curl biceps droit
# ==================================
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

# ==================================
# Curl biceps gauche
# ==================================

def curl_biceps_gauche_detection(corps):
    angle = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    if angle < 35:
        return "fin"
    elif angle > 160:
        return "debut"
    return "milieu"

curl_biceps_gauche = Exercice(
    nom="Curl biceps gauche",

    detection=curl_biceps_gauche_detection,

    description="Curl biceps avec haltère du bras gauche.",

    instructions=[
        "Garde le coude proche du corps.",
        "Contrôle la descente.",
        "Ne balance pas le mouvement."
    ],

    erreurs=[
        
    ]
)

# ==================================
# Elevation latérale
# ==================================

def elevation_laterale_detection(corps):
    angle_coude_droit = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    angle_coude_gauche = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if corps.poignet_droit.y > corps.epaule_droite.y and corps.poignet_gauche.y > corps.epaule_gauche.y:
        return "debut"
    else:
        return "fin" 

elevation_laterale = Exercice(
    nom="Elevations latérales",

    detection=elevation_laterale_detection,

    description="Curl biceps avec haltère du bras gauche.",

    instructions=[
        "Contrôle la descente.",
        "Ne balance pas le mouvement."
    ],

    erreurs=[
        
    ]
)

# ==================================
# Pompes
# ==================================

def pompe_detection(corps):
    angle_coude_droit = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    angle_coude_gauche = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if angle_coude_droit and angle_coude_gauche < 100:
        return "fin"
    elif angle_coude_droit and angle_coude_gauche > 160:
        return "debut"
    return "milieu"

pompe = Exercice(
    nom="Pompes",

    detection=pompe_detection,

    description="En position gainage, faire une pompe",

    instructions=[
        "laisse ta tête en position neutre",
        "N'écarte pas trop les coudes"
        "Garde les jambes et le dos alignés"
    ],

    erreurs=[
        
    ]
)

# ==================================
# Developpé couché altères
# ==================================

def developpe_couche_sol_detection(corps):
    angle_coude_droit = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    angle_coude_gauche = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if angle_coude_droit and angle_coude_gauche < 100:
        return "fin"
    elif angle_coude_droit and angle_coude_gauche > 160:
        return "debut"
    return "milieu"

developpe_couche_sol = Exercice(
    nom="Developpé couché altères",

    detection=developpe_couche_sol_detection,

    description="Allongé au sol, faire un développé couché avec des altères dans chaque main",

    instructions=[
        "laisse ta tête en position neutre",
        "Garde les bras dans l'axe des pecs"
    ],

    erreurs=[
        
    ]
)

# ==================================
# Extension triceps
# ==================================

def extension_triceps_au_dessus_de_la_tete_detection(corps):
    angle_coude_droit = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    angle_coude_gauche = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if angle_coude_droit and angle_coude_gauche < 90:
        return "fin"
    elif angle_coude_droit and angle_coude_gauche > 150:
        return "debut"
    return "milieu"

extension_triceps_au_dessus_de_la_tete = Exercice(
    nom="Extension Triceps",

    detection=extension_triceps_au_dessus_de_la_tete_detection,

    description="tenir une altère en haut de sa tête et faire la faire descendre dans le dos en utilisant les triceps",

    instructions=[
        "laisse ta tête en position neutre",
        "n'écarte pas trops les coudes"
    ],

    erreurs=[
        
    ]
)

# ==================================
# Développé épaule
# ==================================

def developpe_epaule_detection(corps):
    angle_coude_droit = calculer_angle(corps.epaule_gauche,corps.coude_gauche,corps.poignet_gauche)
    angle_coude_gauche = calculer_angle(corps.epaule_droite,corps.coude_droit,corps.poignet_droit)
    if angle_coude_droit and angle_coude_gauche < 40:
        return "fin"
    elif angle_coude_droit and angle_coude_gauche > 150:
        return "debut"
    return "milieu"

developpe_epaule = Exercice(
    nom="Développé épaule",

    detection=developpe_epaule_detection,

    description="Tenir des altères dans chaque mains et pousser vers le haut",

    instructions=[
        "laisse ta tête en position neutre",
        "n'écarte pas trops les coudes"
    ],

    erreurs=[
        
    ]
)

# ==================================
# Crunches
# ==================================

def crunches_detection(corps):
    angle_hanche_droite = calculer_angle(corps.epaule_gauche,corps.hanche_gauche,corps.genou_gauche)
    angle_hanche_gauche = calculer_angle(corps.epaule_droite,corps.hanche_droite,corps.genou_droit)
    if angle_hanche_droite and angle_hanche_gauche < 70:
        return "fin"
    elif angle_hanche_droite and angle_hanche_gauche > 95:
        return "debut"
    return "milieu"

crunches = Exercice(
    nom="Crunches",

    detection=crunches_detection,

    description="Alongé sur le coté pour que la caméra voit le coté",

    instructions=[
        "laisse ta tête en position neutre",
        "n'écarte pas trops les coudes"
    ],

    erreurs=[
        
    ]
)

# ==================================
# Planche
# ==================================

def detection_gainage(corps):
    """angle_hanche_droite = calculer_angle(corps.epaule_gauche,corps.hanche_gauche,corps.genou_gauche)
    angle_hanche_gauche = calculer_angle(corps.epaule_droite,corps.hanche_droite,corps.genou_droit)
    hanches_droites = angle_hanche_droite > 160 and angle_hanche_gauche > 160

    hanche_au_dessus_coude = corps.hanche_gauche.y < corps.coude_gauche.y
    if hanches_droites and hanche_au_dessus_coude:"""
    angle_coude_droit = calculer_angle(corps.poignet_droit, corps.coude_droit, corps.epaule_droite)
    if corps.poignet_droit.y < corps.epaule_droite.y and angle_coude_droit > 160:
        return "maintien"

    return "repos"
planche = Exercice(
    nom="Gainage planche",
    detection=detection_gainage,
    description="Maintenir une position de planche avec le corps aligné.",
    instructions=[
        "Garde le dos droit",
        "Contracte les abdominaux",
        "Ne laisse pas tomber les hanches"
    ],
    erreurs=[]
)