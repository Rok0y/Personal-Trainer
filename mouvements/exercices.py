from mouvements.outils import calculer_angle,calculer_distance
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
    angle_hanche_droite = calculer_angle(corps.epaule_gauche,corps.hanche_gauche,corps.genou_gauche)
    angle_hanche_gauche = calculer_angle(corps.epaule_droite,corps.hanche_droite,corps.genou_droit)
    hanches_droites = angle_hanche_gauche > 145

    hanche_au_dessus_coude = corps.hanche_gauche.y < corps.coude_gauche.y
    if hanches_droites and hanche_au_dessus_coude:
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

# ==================================
# Squat
# ==================================

def squat_detection(corps):
    distance_gauche = calculer_distance(corps.coude_gauche, corps.genou_gauche)
    distance_droite = calculer_distance(corps.coude_droit, corps.genou_droit)
    distance_moyenne = (distance_gauche + distance_droite) / 2

    if distance_moyenne < 0.05:
        return "fin"
    elif distance_moyenne > 0.15:
        return "debut"
    return "milieu"

squat = Exercice(
    nom="Squat",

    detection=squat_detection,

    description="Squat avec descente jusqu'à ce que les coudes se rapprochent des genoux.",

    instructions=[
        "Garde le dos droit.",
        "Descends les hanches vers l'arrière comme pour t'asseoir.",
        "Rapproche tes coudes de tes genoux en bas du mouvement.",
        "Remonte en poussant sur les talons."
    ],

    erreurs=[
        
    ]
)

# ==================================
# Fente droite
# ==================================

def fente_droite_detection(corps):
    angle_genou_droit = calculer_angle(corps.hanche_droite, corps.genou_droit, corps.cheville_droite)

    if angle_genou_droit < 100:
        return "fin"
    elif angle_genou_droit > 150:
        return "debut"
    return "milieu"

fente_droite = Exercice(
    nom="Fente droite",

    detection=fente_droite_detection,

    description="Fente avec la jambe droite vers l'avant, jusqu'à ce que le genou droit soit fléchi à environ 90 degrés.",

    instructions=[
        "Garde le buste droit.",
        "Descends le genou arrière vers le sol sans le toucher.",
        "Le genou avant ne doit pas dépasser la pointe du pied.",
        "Remonte en poussant sur le talon avant."
    ],

    erreurs=[
        
    ]
)
# ==================================
# Fente gauche
# ==================================

def fente_gauche_detection(corps):
    angle_genou_gauche = calculer_angle(corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche)

    if angle_genou_gauche < 100:
        return "fin"
    elif angle_genou_gauche > 150:
        return "debut"
    return "milieu"

fente_gauche = Exercice(
    nom="Fente gauche",

    detection=fente_gauche_detection,

    description="Fente avec la jambe gauche vers l'avant, jusqu'à ce que le genou gauche soit fléchi à environ 90 degrés.",

    instructions=[
        "Garde le buste droit.",
        "Descends le genou arrière vers le sol sans le toucher.",
        "Le genou avant ne doit pas dépasser la pointe du pied.",
        "Remonte en poussant sur le talon avant."
    ],

    erreurs=[
        
    ]
)

# ==================================
# Souleve de terre roumain
# ==================================

def souleve_de_terre_roumain_detection(corps):
    distance_gauche = calculer_distance(corps.poignet_gauche, corps.cheville_gauche)
    distance_droite = calculer_distance(corps.poignet_droit, corps.cheville_droite)
    distance_moyenne = (distance_gauche + distance_droite) / 2

    if distance_moyenne < 0.10:
        return "fin"
    elif distance_moyenne > 0.20:
        return "debut"
    return "milieu"

souleve_roumain = Exercice(
    nom="Souleve de terre roumain",

    detection=souleve_de_terre_roumain_detection,

    description="Souleve de terre roumain : descente des mains vers les pieds, jambes semi-tendues.",

    instructions=[
        "Garde le dos droit tout au long du mouvement.",
        "Pousse les hanches vers l'arrière.",
        "Garde une légère flexion des genoux, sans les plier davantage pendant la descente.",
        "Rapproche les mains des pieds sans arrondir le dos.",
        "Remonte en contractant les fessiers."
    ],

    erreurs=[
        
    ]
)

# ==================================
# Planche laterale gauche
# ==================================

def detection_gainage_laterale_gauche(corps):
    angle_hanche_gauche = calculer_angle(corps.epaule_gauche, corps.hanche_gauche, corps.cheville_gauche)
    corps_aligne = angle_hanche_gauche > 150

    cote_gauche_au_sol = corps.epaule_gauche.y > corps.epaule_droite.y

    hanche_au_dessus_coude = corps.hanche_gauche.y < corps.coude_gauche.y

    if corps_aligne and cote_gauche_au_sol and hanche_au_dessus_coude:
        return "maintien"

    return "repos"

planche_laterale_gauche = Exercice(
    nom="Gainage planche laterale gauche",
    detection=detection_gainage_laterale_gauche,
    description="Maintenir une position de planche latérale sur le côté gauche, corps aligné.",
    instructions=[
        "Garde le corps aligné de la tête aux pieds",
        "Contracte les abdominaux et les obliques",
        "Ne laisse pas tomber les hanches"
    ],
    erreurs=[]
)


# ==================================
# Planche laterale droite
# ==================================

def detection_gainage_laterale_droite(corps):
    angle_hanche_droite = calculer_angle(corps.epaule_droite, corps.hanche_droite, corps.cheville_droite)
    corps_aligne = angle_hanche_droite > 150

    cote_droit_au_sol = corps.epaule_droite.y > corps.epaule_gauche.y

    hanche_au_dessus_coude = corps.hanche_droite.y < corps.coude_droit.y

    if corps_aligne and cote_droit_au_sol and hanche_au_dessus_coude:
        return "maintien"

    return "repos"

planche_laterale_droite = Exercice(
    nom="Gainage planche laterale droite",
    detection=detection_gainage_laterale_droite,
    description="Maintenir une position de planche latérale sur le côté droit, corps aligné.",
    instructions=[
        "Garde le corps aligné de la tête aux pieds",
        "Contracte les abdominaux et les obliques",
        "Ne laisse pas tomber les hanches"
    ],
    erreurs=[]
)