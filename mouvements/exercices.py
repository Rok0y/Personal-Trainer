from mouvements.outils import calculer_angle, calculer_distance
from session.circuit import Exercice


# ==================================
# Curl biceps droit
# ==================================
def curl_biceps_droit_detection(corps):
    angle = calculer_angle(corps.epaule_droite, corps.coude_droit, corps.poignet_droit)
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
        "Ne balance pas le mouvement.",
    ],
    erreurs=[coude_trop_tendu_curl_droit, epaule_trop_avancee_curl_droit],
)

# ==================================
# Curl biceps gauche
# ==================================


def curl_biceps_gauche_detection(corps):
    angle = calculer_angle(
        corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    )
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
        "Ne balance pas le mouvement.",
    ],
    erreurs=[],
)

# ==================================
# Elevation latérale
# ==================================


def elevation_laterale_detection(corps):
    angle_coude_droit = calculer_angle(
        corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    )
    angle_coude_gauche = calculer_angle(
        corps.epaule_droite, corps.coude_droit, corps.poignet_droit
    )
    if (
        corps.poignet_droit.y > corps.epaule_droite.y
        and corps.poignet_gauche.y > corps.epaule_gauche.y
    ):
        return "debut"
    else:
        return "fin"


elevation_laterale = Exercice(
    nom="Elevations latérales",
    detection=elevation_laterale_detection,
    description="Curl biceps avec haltère du bras gauche.",
    instructions=["Contrôle la descente.", "Ne balance pas le mouvement."],
    erreurs=[],
)

# ==================================
# Pompes
# ==================================


def pompe_detection(corps):
    angle_coude_droit = calculer_angle(
        corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    )
    angle_coude_gauche = calculer_angle(
        corps.epaule_droite, corps.coude_droit, corps.poignet_droit
    )
    if angle_coude_droit < 100 and angle_coude_gauche < 100:
        return "fin"
    elif angle_coude_droit > 160 and angle_coude_gauche > 160:
        return "debut"
    return "milieu"


pompe = Exercice(
    nom="Pompes",
    detection=pompe_detection,
    description="En position gainage, faire une pompe",
    instructions=[
        "laisse ta tête en position neutre",
        "N'écarte pas trop les coudes" "Garde les jambes et le dos alignés",
    ],
    erreurs=[],
)

# ==================================
# Developpé couché altères
# ==================================


def developpe_couche_sol_detection(corps):
    angle_coude_droit = calculer_angle(
        corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    )
    angle_coude_gauche = calculer_angle(
        corps.epaule_droite, corps.coude_droit, corps.poignet_droit
    )
    if angle_coude_droit < 100 and angle_coude_gauche < 100:
        return "fin"
    elif angle_coude_droit > 160 and angle_coude_gauche > 160:
        return "debut"
    return "milieu"


developpe_couche_sol = Exercice(
    nom="Developpé couché altères",
    detection=developpe_couche_sol_detection,
    description="Allongé au sol, faire un développé couché avec des altères dans chaque main",
    instructions=[
        "laisse ta tête en position neutre",
        "Garde les bras dans l'axe des pecs",
    ],
    erreurs=[],
)

# ==================================
# Extension triceps
# ==================================


def extension_triceps_au_dessus_de_la_tete_detection(corps):
    angle_coude_droit = calculer_angle(
        corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    )
    angle_coude_gauche = calculer_angle(
        corps.epaule_droite, corps.coude_droit, corps.poignet_droit
    )
    if angle_coude_droit < 90 and angle_coude_gauche < 90:
        return "fin"
    elif angle_coude_droit > 150 and angle_coude_gauche > 150:
        return "debut"
    return "milieu"


extension_triceps_au_dessus_de_la_tete = Exercice(
    nom="Extension Triceps",
    detection=extension_triceps_au_dessus_de_la_tete_detection,
    description="tenir une altère en haut de sa tête et faire la faire descendre dans le dos en utilisant les triceps",
    instructions=["laisse ta tête en position neutre", "n'écarte pas trops les coudes"],
    erreurs=[],
)

# ==================================
# Développé épaule
# ==================================


def developpe_epaule_detection(corps):
    angle_coude_droit = calculer_angle(
        corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    )
    angle_coude_gauche = calculer_angle(
        corps.epaule_droite, corps.coude_droit, corps.poignet_droit
    )
    if angle_coude_droit < 40 and angle_coude_gauche < 40:
        return "fin"
    elif angle_coude_droit > 150 and angle_coude_gauche > 150:
        return "debut"
    return "milieu"


developpe_epaule = Exercice(
    nom="Développé épaule",
    detection=developpe_epaule_detection,
    description="Tenir des altères dans chaque mains et pousser vers le haut",
    instructions=["laisse ta tête en position neutre", "n'écarte pas trops les coudes"],
    erreurs=[],
)

# ==================================
# Crunches
# ==================================


def crunches_detection(corps):
    angle_hanche_droite = calculer_angle(
        corps.epaule_gauche, corps.hanche_gauche, corps.genou_gauche
    )
    angle_hanche_gauche = calculer_angle(
        corps.epaule_droite, corps.hanche_droite, corps.genou_droit
    )
    if angle_hanche_droite < 70 and angle_hanche_gauche < 70:
        return "fin"
    elif angle_hanche_droite > 95 and angle_hanche_gauche > 95:
        return "debut"
    return "milieu"


crunches = Exercice(
    nom="Crunches",
    detection=crunches_detection,
    description="Alongé sur le coté pour que la caméra voit le coté",
    instructions=["laisse ta tête en position neutre", "n'écarte pas trops les coudes"],
    erreurs=[],
)

# ==================================
# Planche
# ==================================


def detection_gainage(corps):
    angle_hanche_droite = calculer_angle(
        corps.epaule_gauche, corps.hanche_gauche, corps.genou_gauche
    )
    angle_hanche_gauche = calculer_angle(
        corps.epaule_droite, corps.hanche_droite, corps.genou_droit
    )
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
        "Ne laisse pas tomber les hanches",
    ],
    erreurs=[],
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
        "Remonte en poussant sur les talons.",
    ],
    erreurs=[],
)

# ==================================
# Fente droite
# ==================================


def fente_droite_detection(corps):
    angle_genou_droit = calculer_angle(
        corps.hanche_droite, corps.genou_droit, corps.cheville_droite
    )

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
        "Remonte en poussant sur le talon avant.",
    ],
    erreurs=[],
)
# ==================================
# Fente gauche
# ==================================


def fente_gauche_detection(corps):
    angle_genou_gauche = calculer_angle(
        corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche
    )

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
        "Remonte en poussant sur le talon avant.",
    ],
    erreurs=[],
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
        "Remonte en contractant les fessiers.",
    ],
    erreurs=[],
)

# ==================================
# Planche laterale gauche
# ==================================


def detection_gainage_laterale_gauche(corps):
    angle_hanche_gauche = calculer_angle(
        corps.epaule_gauche, corps.hanche_gauche, corps.cheville_gauche
    )
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
        "Ne laisse pas tomber les hanches",
    ],
    erreurs=[],
)


# ==================================
# Planche laterale droite
# ==================================


def detection_gainage_laterale_droite(corps):
    angle_hanche_droite = calculer_angle(
        corps.epaule_droite, corps.hanche_droite, corps.cheville_droite
    )
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
        "Ne laisse pas tomber les hanches",
    ],
    erreurs=[],
)

# ==================================
# Rowing unilateral gauche
# ==================================


def rowing_unilateral_gauche_detection(corps):
    angle_coude_gauche = calculer_angle(
        corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    )
    angle_buste_gauche = calculer_angle(
        corps.epaule_gauche, corps.hanche_gauche, corps.genou_gauche
    )

    poignet_au_dessus_hanche = corps.poignet_gauche.y < corps.hanche_gauche.y
    buste_penche = angle_buste_gauche < 160

    if angle_coude_gauche < 70 and poignet_au_dessus_hanche and buste_penche:
        return "fin"
    elif angle_coude_gauche > 150:
        return "debut"
    return "milieu"


def rowing_unilateral_gauche_erreur_buste(corps):
    angle_buste_gauche = calculer_angle(
        corps.epaule_gauche, corps.hanche_gauche, corps.genou_gauche
    )
    if angle_buste_gauche >= 160:
        return "Penche-toi davantage vers l'avant"
    return None


rowing_unilateral_gauche = Exercice(
    nom="Rowing unilateral gauche",
    detection=rowing_unilateral_gauche_detection,
    description="Rowing unilatéral bras gauche : tirer l'haltère vers la hanche en contractant le dos.",
    instructions=[
        "Garde le dos droit, buste penché en avant.",
        "Tire le coude vers l'arrière, proche du corps.",
        "Monte le poignet au-dessus de la hanche.",
        "Contracte l'omoplate en haut du mouvement.",
        "Contrôle la descente.",
    ],
    erreurs=[rowing_unilateral_gauche_erreur_buste],
)

# ==================================
# Rowing unilateral droit
# ==================================


def rowing_unilateral_droit_detection(corps):
    angle_coude_droit = calculer_angle(
        corps.epaule_droite, corps.coude_droit, corps.poignet_droit
    )
    angle_buste_droit = calculer_angle(
        corps.epaule_droite, corps.hanche_droite, corps.genou_droit
    )

    poignet_au_dessus_hanche = corps.poignet_droit.y < corps.hanche_droite.y
    buste_penche = angle_buste_droit < 160

    if angle_coude_droit < 70 and poignet_au_dessus_hanche and buste_penche:
        return "fin"
    elif angle_coude_droit > 150:
        return "debut"
    return "milieu"


def rowing_unilateral_droit_erreur_buste(corps):
    angle_buste_droit = calculer_angle(
        corps.epaule_droite, corps.hanche_droite, corps.genou_droit
    )
    if angle_buste_droit >= 160:
        return "Penche-toi davantage vers l'avant"
    return None


rowing_unilateral_droit = Exercice(
    nom="Rowing unilateral droit",
    detection=rowing_unilateral_droit_detection,
    description="Rowing unilatéral bras droit : tirer l'haltère vers la hanche en contractant le dos.",
    instructions=[
        "Garde le dos droit, buste penché en avant.",
        "Tire le coude vers l'arrière, proche du corps.",
        "Monte le poignet au-dessus de la hanche.",
        "Contracte l'omoplate en haut du mouvement.",
        "Contrôle la descente.",
    ],
    erreurs=[rowing_unilateral_droit_erreur_buste],
)

# ==================================
# Rowing penche
# ==================================


def rowing_penche_detection(corps):
    angle_coude_gauche = calculer_angle(
        corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    )
    angle_buste_gauche = calculer_angle(
        corps.epaule_gauche, corps.hanche_gauche, corps.genou_gauche
    )

    poignet_au_dessus_hanche = corps.poignet_gauche.y < corps.hanche_gauche.y
    buste_penche = angle_buste_gauche < 165

    if angle_coude_gauche < 70 and poignet_au_dessus_hanche and buste_penche:
        return "fin"
    elif angle_coude_gauche > 150:
        return "debut"
    return "milieu"


def rowing_penche_erreur_buste(corps):
    angle_buste_gauche = calculer_angle(
        corps.epaule_gauche, corps.hanche_gauche, corps.genou_gauche
    )
    if angle_buste_gauche >= 165:
        return "Penche-toi davantage vers l'avant"
    return None


def rowing_penche_erreur_genoux(corps):
    angle_genou_gauche = calculer_angle(
        corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche
    )
    if angle_genou_gauche < 155:
        return "Garde les jambes presque tendues, plie moins les genoux"
    return None


rowing_penche = Exercice(
    nom="Rowing penche",
    detection=rowing_penche_detection,
    description="Rowing penché à deux haltères en prise neutre : tirer les coudes le plus haut possible.",
    instructions=[
        "Penche le buste en avant, dos droit.",
        "Garde les jambes presque tendues, avec une légère flexion des genoux.",
        "Saisis les haltères en prise neutre.",
        "Tire les coudes le plus haut possible, le long du corps.",
        "Monte le poignet au-dessus de la hanche.",
        "Contracte les omoplates en haut du mouvement.",
        "Contrôle la descente.",
    ],
    erreurs=[rowing_penche_erreur_buste, rowing_penche_erreur_genoux],
)

# ==================================
# Oiseau
# ==================================


def oiseau_detection(corps):
    angle_bras_gauche = calculer_angle(
        corps.hanche_gauche, corps.epaule_gauche, corps.coude_gauche
    )
    angle_bras_droit = calculer_angle(
        corps.hanche_droite, corps.epaule_droite, corps.coude_droit
    )
    angle_bras_moyen = (angle_bras_gauche + angle_bras_droit) / 2

    if angle_bras_moyen > 80:
        return "fin"
    elif angle_bras_moyen < 30:
        return "debut"
    return "milieu"


def oiseau_erreur_coudes(corps):
    angle_coude_gauche = calculer_angle(
        corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    )
    angle_coude_droit = calculer_angle(
        corps.epaule_droite, corps.coude_droit, corps.poignet_droit
    )
    angle_coude_moyen = (angle_coude_gauche + angle_coude_droit) / 2

    if angle_coude_moyen > 170:
        return "Garde les coudes legerement flechis, ne tends pas completement les bras"
    if angle_coude_moyen < 120:
        return "Ne plie pas trop les coudes"
    return None


oiseau = Exercice(
    nom="Oiseau",
    detection=oiseau_detection,
    description="Oiseau debout à deux haltères : écarter les bras sur les côtés, coudes légèrement fléchis.",
    instructions=[
        "Penche légèrement le buste en avant.",
        "Garde les coudes légèrement fléchis.",
        "Écarte les bras sur les côtés jusqu'à hauteur des épaules.",
        "Contracte les omoplates en haut du mouvement.",
        "Contrôle la descente.",
    ],
    erreurs=[oiseau_erreur_coudes],
)
