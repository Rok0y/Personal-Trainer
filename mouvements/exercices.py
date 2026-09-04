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


def _coude_qui_part_en_avant(hanche, epaule, coude):
    """Le coude quitte le buste : le curl se transforme en élévation frontale.

    C'est la faute la plus fréquente du mouvement, et la seule qui se voie de
    façon fiable sur une pose : l'angle hanche-épaule-coude reste petit tant
    que le bras pend le long du corps.
    """
    if calculer_angle(hanche, epaule, coude) > 45:
        return "forme_coude_qui_part_en_avant"
    return None


def coude_avance_curl_droit(corps):
    return _coude_qui_part_en_avant(
        corps.hanche_droite, corps.epaule_droite, corps.coude_droit
    )


def coude_avance_curl_gauche(corps):
    return _coude_qui_part_en_avant(
        corps.hanche_gauche, corps.epaule_gauche, corps.coude_gauche
    )


curl_biceps_droit = Exercice(
    nom="Curl biceps droit",
    detection=curl_biceps_droit_detection,
    description="Curl biceps avec haltère du bras droit.",
    instructions=[
        "Garde le coude proche du corps.",
        "Contrôle la descente.",
        "Ne balance pas le mouvement.",
    ],
    mise_en_place=[
        "Debout, un haltère dans la main droite, bras le long du corps.",
        "Place-toi de profil ou légèrement de trois quarts face à la caméra.",
        "Recule jusqu'à ce que ta tête et tes hanches soient visibles à l'écran.",
    ],
    erreurs_frequentes=[
        "Balancer le buste pour lancer l'haltère : le dos doit rester immobile.",
        "Le coude qui part en avant : le mouvement devient une élévation.",
        "Laisser tomber l'haltère à la descente au lieu de la freiner.",
    ],
    erreurs=[coude_avance_curl_droit],
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
    mise_en_place=[
        "Debout, un haltère dans la main gauche, bras le long du corps.",
        "Place-toi de profil ou légèrement de trois quarts face à la caméra.",
        "Recule jusqu'à ce que ta tête et tes hanches soient visibles à l'écran.",
    ],
    erreurs_frequentes=[
        "Balancer le buste pour lancer l'haltère : le dos doit rester immobile.",
        "Le coude qui part en avant : le mouvement devient une élévation.",
        "Laisser tomber l'haltère à la descente au lieu de la freiner.",
    ],
    erreurs=[coude_avance_curl_gauche],
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
    description="Élévations latérales à deux haltères : monter les bras sur les côtés jusqu'à hauteur des épaules.",
    instructions=["Contrôle la descente.", "Ne balance pas le mouvement."],
    mise_en_place=[
        "Debout, un haltère dans chaque main, bras le long du corps.",
        "Place-toi face à la caméra, les deux bras entièrement visibles.",
        "Prends léger : c'est un mouvement d'isolation, pas de force.",
    ],
    erreurs_frequentes=[
        "Monter plus haut que les épaules : inutile, et ça sollicite le cou.",
        "Hausser les épaules vers les oreilles pendant la montée.",
        "Prendre trop lourd et s'aider d'une impulsion des jambes.",
    ],
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
    description="Pompes au sol, mains sous les épaules, corps aligné des talons à la tête.",
    instructions=[
        "Garde la tête dans le prolongement du dos, regard vers le sol.",
        "N'écarte pas trop les coudes.",
        "Garde les jambes et le dos alignés.",
    ],
    mise_en_place=[
        "Mains au sol un peu plus larges que les épaules, bras tendus.",
        "Corps aligné des talons aux épaules, regard vers le sol.",
        "Place-toi de profil face à la caméra, corps entier dans le champ.",
    ],
    erreurs_frequentes=[
        "Les hanches qui tombent ou qui remontent : garde une ligne droite.",
        "Les coudes complètement écartés à 90° : garde-les à environ 45°.",
        "Ne descendre qu'à moitié : la poitrine doit approcher du sol.",
    ],
    erreurs=[],
    variante_facile="Pompes sur les genoux",
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
    description="Développé couché au sol, un haltère dans chaque main, poussée verticale.",
    instructions=[
        "Garde la tête posée au sol, regard vers le plafond.",
        "Garde les bras dans l'axe de la poitrine.",
        "Descends les coudes jusqu'au niveau du buste, sans plus bas.",
    ],
    mise_en_place=[
        "Allongé sur le dos sur un tapis, genoux pliés, pieds au sol.",
        "Un haltère dans chaque main, bras tendus au-dessus de la poitrine.",
        "Place la caméra sur le côté, à hauteur du sol, corps entier visible.",
    ],
    erreurs_frequentes=[
        "Descendre les coudes trop bas : ça met l'épaule en tension inutile.",
        "Écarter complètement les coudes au lieu de les garder à 45°.",
        "Cambrer le bas du dos pour pousser plus lourd.",
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
    description="Extension triceps à un haltère tenu à deux mains, derrière la tête.",
    instructions=[
        "Garde la tête droite, dans le prolongement du dos.",
        "Garde les coudes serrés vers l'avant, ils ne s'écartent pas.",
        "Descends l'haltère derrière la nuque sans à-coup.",
    ],
    mise_en_place=[
        "Debout ou assis, un haltère tenu à deux mains au-dessus de la tête.",
        "Coudes serrés vers l'avant, proches des oreilles.",
        "Place-toi face à la caméra, tête et bras entièrement visibles.",
    ],
    erreurs_frequentes=[
        "Les coudes qui s'écartent vers l'extérieur pendant la descente.",
        "Cambrer le dos pour compenser une charge trop lourde.",
        "Descendre l'haltère derrière la nuque sans contrôle.",
    ],
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
    description="Développé épaule debout : pousser les haltères au-dessus de la tête.",
    instructions=[
        "Garde la tête droite, sans avancer le menton.",
        "Pousse les haltères à la verticale jusqu'à tendre les bras.",
        "Redescends jusqu'à hauteur des oreilles, pas plus bas.",
    ],
    mise_en_place=[
        "Debout, un haltère dans chaque main à hauteur des épaules, paumes vers l'avant.",
        "Gaine le ventre pour éviter de cambrer.",
        "Place-toi face à la caméra, bras entièrement visibles au-dessus de la tête.",
    ],
    erreurs_frequentes=[
        "Cambrer le bas du dos quand la charge devient lourde.",
        "Ne pas tendre complètement les bras en haut du mouvement.",
        "Descendre les coudes trop bas sous la ligne des épaules.",
    ],
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
    description="Crunch au sol : décoller les épaules en contractant les abdominaux.",
    instructions=[
        "Garde le menton décollé du buste, sans tirer sur la nuque.",
        "Décolle les épaules du sol en soufflant.",
        "Redescends sans relâcher complètement les abdominaux.",
    ],
    mise_en_place=[
        "Allongé sur le dos, genoux pliés, pieds à plat sur le tapis.",
        "Mains sur les tempes ou croisées sur la poitrine, jamais derrière la nuque.",
        "Place la caméra sur le côté, à hauteur du sol.",
    ],
    erreurs_frequentes=[
        "Tirer sur la nuque avec les mains : garde le menton décollé du buste.",
        "Décoller tout le dos : seules les épaules et le haut du dos se lèvent.",
        "Aller trop vite : c'est la contraction qui compte, pas la vitesse.",
    ],
    erreurs=[],
)

# ==================================
# Planche
# ==================================


def detection_gainage(corps):
    # Les deux hanches sont comparees au seuil : la version precedente calculait
    # bien les deux angles mais n'en testait qu'un, si bien qu'un bassin
    # affaisse d'un seul cote passait pour un gainage correct.
    angle_hanche_droite = calculer_angle(
        corps.epaule_gauche, corps.hanche_gauche, corps.genou_gauche
    )
    angle_hanche_gauche = calculer_angle(
        corps.epaule_droite, corps.hanche_droite, corps.genou_droit
    )
    hanches_droites = angle_hanche_droite > 145 and angle_hanche_gauche > 145

    hanche_au_dessus_coude = corps.hanche_gauche.y < corps.coude_gauche.y
    if hanches_droites and hanche_au_dessus_coude:
        return "maintien"

    return "repos"


planche = Exercice(
    nom="Gainage planche",
    detection=detection_gainage,
    description="Maintenir une position de planche avec le corps aligné.",
    instructions=[
        "Garde le dos droit.",
        "Contracte les abdominaux.",
        "Ne laisse pas tomber les hanches.",
    ],
    mise_en_place=[
        "Avant-bras au sol, coudes à l'aplomb des épaules, pieds sur la pointe.",
        "Corps aligné des talons aux épaules, regard vers le sol.",
        "Place-toi de profil face à la caméra, corps entier dans le champ.",
    ],
    erreurs_frequentes=[
        "Les hanches qui s'affaissent : le bas du dos encaisse tout.",
        "Les fesses trop hautes : la position devient facile et ne travaille plus.",
        "Bloquer sa respiration : respire calmement pendant tout le maintien.",
    ],
    erreurs=[],
    variante_facile="Gainage sur les genoux",
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
    mise_en_place=[
        "Debout, un haltère dans chaque main, bras le long du corps.",
        "Pieds écartés de la largeur des hanches, pointes légèrement vers l'extérieur.",
        "Place-toi de profil face à la caméra, jambes entières visibles.",
    ],
    erreurs_frequentes=[
        "Les genoux qui rentrent vers l'intérieur pendant la remontée.",
        "Le dos qui s'arrondit en bas du mouvement.",
        "Décoller les talons : garde le poids réparti sur tout le pied.",
    ],
    erreurs=[],
    variante_facile="Squat sur chaise",
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
    mise_en_place=[
        "Debout, un haltère dans chaque main, jambe droite avancée d'un grand pas.",
        "Buste droit, regard devant.",
        "Place-toi de profil face à la caméra, jambes entières visibles.",
    ],
    erreurs_frequentes=[
        "Le genou avant qui dépasse largement la pointe du pied.",
        "Le buste qui bascule en avant.",
        "Un pas trop court, qui écrase le genou arrière.",
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
    mise_en_place=[
        "Debout, un haltère dans chaque main, jambe gauche avancée d'un grand pas.",
        "Buste droit, regard devant.",
        "Place-toi de profil face à la caméra, jambes entières visibles.",
    ],
    erreurs_frequentes=[
        "Le genou avant qui dépasse largement la pointe du pied.",
        "Le buste qui bascule en avant.",
        "Un pas trop court, qui écrase le genou arrière.",
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
    mise_en_place=[
        "Debout, un haltère dans chaque main devant les cuisses.",
        "Genoux très légèrement fléchis, et ils le restent tout le mouvement.",
        "Place-toi de profil face à la caméra, corps entier visible.",
    ],
    erreurs_frequentes=[
        "Plier les genoux comme pour un squat : le mouvement vient des hanches.",
        "Arrondir le bas du dos en descendant : c'est le principal risque.",
        "Éloigner les haltères des jambes au lieu de les faire glisser le long.",
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
        "Garde le corps aligné de la tête aux pieds.",
        "Contracte les abdominaux et les obliques.",
        "Ne laisse pas tomber les hanches.",
    ],
    mise_en_place=[
        "Allongé sur le côté gauche, avant-bras gauche au sol, coude sous l'épaule.",
        "Jambes tendues, pieds superposés, hanches décollées du sol.",
        "Place-toi face à la caméra, corps entier dans le champ.",
    ],
    erreurs_frequentes=[
        "Les hanches qui redescendent vers le sol au fil des secondes.",
        "Le buste qui pivote vers l'avant ou vers l'arrière.",
        "Poser l'épaule sur le coude au lieu de pousser dans le sol.",
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
        "Garde le corps aligné de la tête aux pieds.",
        "Contracte les abdominaux et les obliques.",
        "Ne laisse pas tomber les hanches.",
    ],
    mise_en_place=[
        "Allongé sur le côté droit, avant-bras droit au sol, coude sous l'épaule.",
        "Jambes tendues, pieds superposés, hanches décollées du sol.",
        "Place-toi face à la caméra, corps entier dans le champ.",
    ],
    erreurs_frequentes=[
        "Les hanches qui redescendent vers le sol au fil des secondes.",
        "Le buste qui pivote vers l'avant ou vers l'arrière.",
        "Poser l'épaule sur le coude au lieu de pousser dans le sol.",
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
        return "forme_buste_pas_assez_penche"
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
    mise_en_place=[
        "Main droite et genou droit en appui sur une chaise, dos à plat.",
        "Haltère dans la main gauche, bras tendu vers le sol.",
        "Place-toi de profil face à la caméra, buste et bras visibles.",
    ],
    erreurs_frequentes=[
        "Ne pas assez pencher le buste : il doit être proche de l'horizontale.",
        "Tirer avec le bras seul au lieu d'amener l'omoplate vers la colonne.",
        "Tourner le buste pour monter plus haut.",
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
        return "forme_buste_pas_assez_penche"
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
    mise_en_place=[
        "Main gauche et genou gauche en appui sur une chaise, dos à plat.",
        "Haltère dans la main droite, bras tendu vers le sol.",
        "Place-toi de profil face à la caméra, buste et bras visibles.",
    ],
    erreurs_frequentes=[
        "Ne pas assez pencher le buste : il doit être proche de l'horizontale.",
        "Tirer avec le bras seul au lieu d'amener l'omoplate vers la colonne.",
        "Tourner le buste pour monter plus haut.",
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
        return "forme_buste_pas_assez_penche"
    return None


def rowing_penche_erreur_genoux(corps):
    angle_genou_gauche = calculer_angle(
        corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche
    )
    if angle_genou_gauche < 155:
        return "forme_genoux_trop_plies"
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
    mise_en_place=[
        "Debout, un haltère dans chaque main, buste penché vers l'avant.",
        "Genoux presque tendus, dos plat, regard vers le sol devant toi.",
        "Place-toi de profil face à la caméra, corps entier visible.",
    ],
    erreurs_frequentes=[
        "Se redresser au fil des répétitions : le buste doit rester penché.",
        "Arrondir le dos, surtout en fin de série.",
        "Plier les genoux pour compenser un manque de souplesse.",
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
        return "forme_coudes_trop_tendus"
    if angle_coude_moyen < 120:
        return "forme_coudes_trop_plies"
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
    mise_en_place=[
        "Debout, buste penché vers l'avant, un haltère dans chaque main.",
        "Coudes légèrement fléchis, bras pendants sous les épaules.",
        "Place-toi face à la caméra, les deux bras entièrement visibles.",
    ],
    erreurs_frequentes=[
        "Prendre trop lourd : le mouvement devient un tirage, pas un écarté.",
        "Tendre complètement les bras, ou au contraire plier les coudes à angle droit.",
        "Se redresser pour aider la montée.",
    ],
    erreurs=[oiseau_erreur_coudes],
)


# ==================================
# Variantes assistées
# ==================================
# Régressions des mouvements au poids du corps. Elles n'existent pas pour faire
# nombre : sans elles, une personne qui ne fait pas une seule pompe complète
# reste « hors barème » — c'est-à-dire sans aucun objectif — parce que le
# premier palier des Pompes suppose déjà de savoir en faire. Chacune réutilise
# la détection du mouvement complet quand celle-ci reste valable, plutôt que
# d'introduire une heuristique de plus à maintenir.


def squat_sur_chaise_detection(corps):
    """Profondeur lue sur l'angle du genou, pas sur la distance coude-genou.

    `squat_detection` mesure l'écart entre le coude et le genou : ça suppose des
    haltères qui pendent le long du corps. Au poids du corps, les bras partent
    devant pour l'équilibre et ce repère ne veut plus rien dire.
    """
    angle_gauche = calculer_angle(
        corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche
    )
    angle_droit = calculer_angle(
        corps.hanche_droite, corps.genou_droit, corps.cheville_droite
    )
    if angle_gauche < 110 and angle_droit < 110:
        return "fin"
    if angle_gauche > 160 and angle_droit > 160:
        return "debut"
    return "milieu"


pompes_inclinees = Exercice(
    nom="Pompes inclinées",
    # Les angles de coude ne dépendent pas de l'inclinaison : la détection des
    # pompes s'applique telle quelle.
    detection=pompe_detection,
    description=(
        "Pompes mains posées sur une chaise ou un plan de travail : "
        "plus le support est haut, plus le mouvement est facile."
    ),
    mise_en_place=[
        "Pose les mains à plat sur l'assise d'une chaise stable, écartées de la largeur des épaules.",
        "Recule les pieds jusqu'à former une ligne droite des talons aux épaules.",
        "Place-toi de profil face à la caméra, corps entier visible.",
    ],
    instructions=[
        "Descends la poitrine vers la chaise en pliant les coudes.",
        "Garde le corps aligné, sans creuser le bas du dos.",
        "Remonte en poussant sur les mains, sans bloquer les coudes.",
    ],
    erreurs_frequentes=[
        "Les hanches qui tombent : contracte les fessiers et les abdominaux.",
        "Les coudes qui partent à 90° du buste : garde-les à environ 45°.",
        "Descendre trop peu : la poitrine doit approcher du support.",
    ],
    erreurs=[],
    variante_difficile="Pompes sur les genoux",
)

pompes_sur_les_genoux = Exercice(
    nom="Pompes sur les genoux",
    detection=pompe_detection,
    description=(
        "Pompes au sol avec les genoux posés : la moitié du corps à soulever en moins."
    ),
    mise_en_place=[
        "Pose les genoux sur un tapis, mains au sol un peu plus larges que les épaules.",
        "Aligne les épaules, les hanches et les genoux ; les pieds restent en l'air.",
        "Place-toi de profil face à la caméra.",
    ],
    instructions=[
        "Descends la poitrine vers le sol en pliant les coudes.",
        "Garde la tête dans le prolongement du dos.",
        "Remonte sans creuser le bas du dos.",
    ],
    erreurs_frequentes=[
        "S'asseoir sur les talons : les hanches doivent rester dans l'axe.",
        "Descendre la tête avant la poitrine.",
    ],
    erreurs=[],
    variante_facile="Pompes inclinées",
    variante_difficile="Pompes",
)

gainage_sur_les_genoux = Exercice(
    nom="Gainage sur les genoux",
    # L'angle épaule-hanche-genou reste celui d'un corps aligné, genoux au sol
    # ou non : la détection du gainage complet convient sans retouche.
    detection=detection_gainage,
    description="Planche sur les avant-bras avec les genoux posés au sol.",
    mise_en_place=[
        "Pose les avant-bras au sol, coudes sous les épaules.",
        "Pose les genoux au sol, hanches alignées avec les épaules.",
        "Place-toi de profil face à la caméra.",
    ],
    instructions=[
        "Serre les abdominaux et les fessiers.",
        "Garde une ligne droite des épaules aux genoux.",
        "Respire normalement, ne bloque pas.",
    ],
    erreurs_frequentes=[
        "Les hanches trop hautes : le gainage ne travaille plus.",
        "Le bas du dos creusé : rentre légèrement le bassin.",
    ],
    erreurs=[],
    variante_difficile="Gainage planche",
)

squat_sur_chaise = Exercice(
    nom="Squat sur chaise",
    detection=squat_sur_chaise_detection,
    description=(
        "Squat au poids du corps, en s'asseyant sur une chaise puis en se relevant."
    ),
    mise_en_place=[
        "Place une chaise derrière toi, debout, pieds écartés de la largeur des hanches.",
        "Tends les bras devant toi pour l'équilibre.",
        "Place-toi de profil face à la caméra, jambes entières visibles.",
    ],
    instructions=[
        "Descends les hanches vers l'arrière comme pour t'asseoir.",
        "Effleure l'assise sans t'y poser vraiment, ou assieds-toi si c'est trop dur.",
        "Remonte en poussant sur les talons.",
    ],
    erreurs_frequentes=[
        "Les genoux qui rentrent vers l'intérieur : garde-les dans l'axe des pieds.",
        "Le dos qui s'arrondit : regarde devant toi, poitrine ouverte.",
        "Se laisser tomber sur la chaise : contrôle la descente.",
    ],
    erreurs=[],
    variante_difficile="Squat",
)
