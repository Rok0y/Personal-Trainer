from mouvements.outils import calculer_angle, calculer_distance
from session.circuit import Exercice


# ==================================
# Curl biceps droit
# ==================================
# Seuil de fin resserre de 30 a 20 degres : « la validation arrive trop tot »,
# le poignet devait encore monter vers l'epaule. Mesure au banc d'essai, une
# repetition franche monte a 3 degres (droit) et 9 (gauche) en mediane : 20
# laisse de la marge sans compter une demi-repetition.
CURL_FIN = 20


def curl_biceps_droit_detection(corps):
    angle = calculer_angle(corps.epaule_droite, corps.coude_droit, corps.poignet_droit)
    if angle < CURL_FIN:
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
    # Seuil resserre de 45 a 23 degres, valeur donnee par le testeur en lisant
    # la jauge : a 45, le coude etait deja franchement sorti du buste.
    if calculer_angle(hanche, epaule, coude) > 23:
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
    orientation="face",
    detection=curl_biceps_droit_detection,
    description="Curl biceps avec haltère du bras droit.",
    instructions=[
        "Garde le coude proche du corps.",
        "Contrôle la descente.",
        "Ne balance pas le mouvement.",
    ],
    mise_en_place=[
        "Debout, un haltère dans la main droite, bras le long du corps.",
        "Place-toi face à la caméra.",
        "Il faut que ta tête et tes hanches soient visibles à l'écran.",
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
    if angle < CURL_FIN:
        return "fin"
    elif angle > 160:
        return "debut"
    return "milieu"


curl_biceps_gauche = Exercice(
    nom="Curl biceps gauche",
    orientation="face",
    detection=curl_biceps_gauche_detection,
    description="Curl biceps avec haltère du bras gauche.",
    instructions=[
        "Garde le coude proche du corps.",
        "Contrôle la descente.",
        "Ne balance pas le mouvement.",
    ],
    mise_en_place=[
        "Debout, un haltère dans la main gauche, bras le long du corps.",
        "Place-toi face à la caméra.",
        "Il faut que ta tête et tes hanches soient visibles à l'écran.",
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


def _hauteur_sous_epaule(poignet, epaule, hanche):
    """De combien le poignet est sous l'épaule, rapporté au buste.

    Sans unité, donc indépendant de la taille et de la distance à la caméra :
    environ 1 bras le long du corps, 0 à hauteur d'épaule, négatif au-dessus.
    None quand le buste n'a pas de longueur lisible.
    """
    buste = calculer_distance(epaule, hanche)
    if buste <= 0:
        return None
    return (poignet.y - epaule.y) / buste


def _ecart_lateral(poignet, epaule, autre_epaule, hanche):
    """De combien le poignet est sorti *vers l'extérieur* de son épaule.

    L'extérieur est le côté opposé à l'autre épaule : de face, c'est ce qui
    distingue une élévation latérale d'une élévation frontale, où les poignets
    restent devant les épaules. Rapporté au buste, comme la hauteur.
    """
    buste = calculer_distance(epaule, hanche)
    if buste <= 0:
        return None
    if epaule.x >= autre_epaule.x:
        sortie = poignet.x - epaule.x
    else:
        sortie = epaule.x - poignet.x
    return sortie / buste


def elevation_laterale_detection(corps):
    """Bras montés sur les côtés, tendus, jusqu'à hauteur d'épaule.

    La détection ne regardait que la hauteur des poignets : « pas les deux
    mains sous les épaules » valait « fin ». Lever les bras devant soi ou au
    hasard comptait donc aussi, et faute de zone intermédiaire le moindre
    tremblement autour de l'épaule faisait un aller-retour. La fin exige
    désormais les trois choses qui font une élévation latérale — la hauteur,
    des bras tendus, et chaque poignet sorti de son côté —, et le départ des
    mains nettement basses, d'où une vraie zone intermédiaire.
    """
    hauteur_droite = _hauteur_sous_epaule(
        corps.poignet_droit, corps.epaule_droite, corps.hanche_droite
    )
    hauteur_gauche = _hauteur_sous_epaule(
        corps.poignet_gauche, corps.epaule_gauche, corps.hanche_gauche
    )
    if hauteur_droite is None or hauteur_gauche is None:
        return "milieu"
    if hauteur_droite > 0.6 and hauteur_gauche > 0.6:
        return "debut"

    angle_coude_droit = calculer_angle(
        corps.epaule_droite, corps.coude_droit, corps.poignet_droit
    )
    angle_coude_gauche = calculer_angle(
        corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    )
    ecart_droit = _ecart_lateral(
        corps.poignet_droit, corps.epaule_droite, corps.epaule_gauche, corps.hanche_droite
    )
    ecart_gauche = _ecart_lateral(
        corps.poignet_gauche, corps.epaule_gauche, corps.epaule_droite, corps.hanche_gauche
    )
    if (
        hauteur_droite < 0.15
        and hauteur_gauche < 0.15
        and angle_coude_droit > 140
        and angle_coude_gauche > 140
        and ecart_droit > 0.3
        and ecart_gauche > 0.3
    ):
        return "fin"
    return "milieu"


elevation_laterale = Exercice(
    nom="Elevations latérales",
    orientation="face",
    detection=elevation_laterale_detection,
    description="Élévations latérales à deux haltères : monter les bras sur les côtés jusqu'à hauteur des épaules.",
    instructions=[
        "Monte les bras sur les côtés, pas devant toi, jusqu'à hauteur des épaules.",
        "Garde les bras presque tendus.",
        "Contrôle la descente jusqu'en bas, mains le long des cuisses.",
    ],
    mise_en_place=[
        "Debout, un haltère dans chaque main, bras le long du corps.",
        "Place-toi face à la caméra, les deux bras entièrement visibles.",
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


# En deca de cet ecart de visibilite, les deux bras sont aussi bien vus l'un
# que l'autre (de face, typiquement) : c'est alors la profondeur qui tranche.
MARGE_VISIBILITE = 0.1


def _visibilite_bras(coude, poignet):
    return (coude.visibilite + poignet.visibilite) / 2


def _bras_proche(corps):
    """Épaule, coude et poignet du bras que la caméra voit vraiment.

    De profil, le bras éloigné est masqué par le corps et son coude est une
    estimation du modèle — qui, mesuré sur des pompes, restait tendu à 173°
    pendant que le bras visible pliait à 60°. Exiger les deux coudes revenait
    donc à exiger que l'estimation soit juste, et la moyenne ne valait pas
    mieux : (173 + 60) / 2 n'atteint jamais le seuil.

    Le choix se faisait sur la profondeur (`z`), la coordonnée la moins fiable
    du modèle : qu'elle désigne le bras caché, et la détection lisait un coude
    inventé, toujours tendu — aucune pompe comptée sur toute une séance. Il se
    fait désormais sur la **visibilité** du coude et du poignet. C'est
    l'inverse de la règle du cadrage, qui l'écarte parce qu'elle s'effondre sur
    le membre éloigné alors que le cadrage est bon : ici, cet effondrement est
    précisément l'information cherchée. Prendre le bras le plus plié aurait
    évité `z` aussi, mais un saut du bras caché y aurait armé des répétitions
    fantômes. De face, les deux bras sont aussi visibles et bougent ensemble :
    la profondeur départage, et l'un ou l'autre convient.
    """
    gauche = _visibilite_bras(corps.coude_gauche, corps.poignet_gauche)
    droite = _visibilite_bras(corps.coude_droit, corps.poignet_droit)
    if abs(gauche - droite) >= MARGE_VISIBILITE:
        bras_gauche = gauche > droite
    else:
        bras_gauche = corps.epaule_gauche.z <= corps.epaule_droite.z
    if bras_gauche:
        return corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    return corps.epaule_droite, corps.coude_droit, corps.poignet_droit


def _angle_coude_proche(corps):
    epaule, coude, poignet = _bras_proche(corps)
    return calculer_angle(epaule, coude, poignet)


# Deux seuils en bas, et ils ne disent pas la meme chose. Le premier decide si
# la pompe **compte** ; le second si elle etait **assez profonde**. Ils etaient
# confondus a 100 degres : une pompe qui s'arretait a 110 n'etait pas comptee,
# sans rien dire — une sur deux, a la seance du 5 octobre. Elle compte
# desormais, et l'ecart se dit en avertissement (`pompe_profondeur`), jamais en
# repetition retiree : meme regle que la faute du genou des fentes.
SEUIL_COMPTAGE_POMPE = 120
SEUIL_PROFONDEUR_POMPE = 100


def pompe_detection(corps):
    # Corps a l'horizontale, ou rien ne compte. Seul l'angle du coude etait
    # lu, si bien que plier le bras debout comptait une pompe — remonte du
    # banc d'essai, des repetitions en trop pendant l'installation. Meme
    # condition que le developpe couche, et meme defaut : un angle de membre
    # ne dit pas ou se trouve le corps. Moins de 45 degres d'inclinaison,
    # donc les pompes inclinees sur une chaise ou un plan de travail passent.
    if _buste_vertical(corps) >= 0:
        return "milieu"
    angle_coude = _angle_coude_proche(corps)
    if angle_coude < SEUIL_COMPTAGE_POMPE:
        return "debut"
    elif angle_coude > 160:
        return "fin"
    return "milieu"


def pompe_profondeur(corps):
    """`"profond"` quand le coude passe sous l'angle d'une pompe complète.

    Ce n'est pas une faute de forme : une image à 110° ne dit rien, toute
    pompe profonde y passe en descendant. Le moteur retient si ce jeton a été
    vu **pendant la descente** (`Exercice.amplitude`), et n'avertit qu'une
    fois la répétition comptée.
    """
    if _angle_coude_proche(corps) < SEUIL_PROFONDEUR_POMPE:
        return "profond"
    return None


# Ce qui est verifie pendant la descente, et ce qu'on dit si ca manque.
AMPLITUDE_POMPE = (pompe_profondeur, "forme_pompe_pas_assez_profonde")


pompe = Exercice(
    nom="Pompes",
    # De profil, et c'est un changement assume. La fiche disait « face a la
    # camera » pendant que ses deux variantes assistees — meme mouvement,
    # meme detection — disaient « de profil » : une contradiction qui restait
    # muette tant que personne ne la prononcait. De face, le comptage
    # « buggait parfois », ce qui est le symptome attendu — les coudes flechis
    # dans un plan oblique se projettent mal, et c'est la lecon deja payee sur
    # le squat, ou un angle sagittal lu de face bloquait la detection a « fin »
    # et ne comptait rien. A re-evaluer apres quelques seances : si le profil
    # ne compte pas mieux, c'est le seuil qu'il faut regarder, pas la vue.
    orientation="profil",
    detection=pompe_detection,
    amplitude=AMPLITUDE_POMPE,
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


def _buste_vertical(corps):
    """Écart vertical moins écart horizontal entre le milieu des épaules et
    celui des hanches.

    Négatif quand le buste est plus couché que debout, quel que soit le côté
    de la caméra. Même comparaison que `positions._torse_vertical`, rendue en
    nombre plutôt qu'en booléen pour que le banc d'essai puisse l'afficher.
    """
    epaules_x = (corps.epaule_gauche.x + corps.epaule_droite.x) / 2
    epaules_y = (corps.epaule_gauche.y + corps.epaule_droite.y) / 2
    hanches_x = (corps.hanche_gauche.x + corps.hanche_droite.x) / 2
    hanches_y = (corps.hanche_gauche.y + corps.hanche_droite.y) / 2
    return abs(epaules_y - hanches_y) - abs(epaules_x - hanches_x)


def developpe_couche_sol_detection(corps):
    # Le mouvement se fait allongé, et rien ne le vérifiait : debout, plier
    # et tendre les coudes comptait des répétitions. Hors de la position
    # allongée, rien n'est ni début ni fin, donc rien ne compte.
    if _buste_vertical(corps) >= 0:
        return "milieu"
    # Caméra sur le côté : même raison que pour les pompes.
    angle_coude = _angle_coude_proche(corps)
    if angle_coude < 100:
        return "debut"
    elif angle_coude > 160:
        return "fin"
    return "milieu"


developpe_couche_sol = Exercice(
    nom="Developpé couché altères",
    orientation="allonge_camera_de_cote",
    detection=developpe_couche_sol_detection,
    description="Développé couché au sol, un haltère dans chaque main, poussée verticale.",
    instructions=[
        "Garde la tête posée au sol, regard vers le plafond.",
        "Garde les bras dans l'axe de la poitrine.",
        "Descends les coudes jusqu'au niveau du buste, pas plus bas.",
    ],
    mise_en_place=[
        "Allongé sur le dos sur un tapis, jambes tendues ou genoux pliés, au choix.",
        "Un haltère dans chaque main, bras tendus au-dessus de la poitrine.",
        "Place la caméra sur le côté, à hauteur de ton corps, et non vers tes pieds.",
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


def _coudes_leves(corps):
    return (
        corps.coude_gauche.y < corps.epaule_gauche.y
        and corps.coude_droit.y < corps.epaule_droite.y
    )


def _ecart_rapporte_aux_epaules(point_gauche, point_droit, corps):
    """Distance entre deux points, rapportée à la largeur des épaules. De face
    seulement : de profil, les épaules se superposent. None si elle est nulle."""
    largeur = calculer_distance(corps.epaule_gauche, corps.epaule_droite)
    if largeur <= 0:
        return None
    return calculer_distance(point_gauche, point_droit) / largeur


def extension_triceps_au_dessus_de_la_tete_detection(corps):
    angle_coude_droit = calculer_angle(
        corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
    )
    angle_coude_gauche = calculer_angle(
        corps.epaule_droite, corps.coude_droit, corps.poignet_droit
    )
    # Seul l'angle des coudes etait lu : n'importe quelle flexion des bras,
    # le long du corps comprise, comptait. Le mouvement se fait coudes en
    # l'air et un seul haltere tenu a deux mains — donc poignets presque
    # joints. Hors de cette position, ni debut ni fin.
    ecart_poignets = _ecart_rapporte_aux_epaules(
        corps.poignet_gauche, corps.poignet_droit, corps
    )
    if not _coudes_leves(corps) or ecart_poignets is None or ecart_poignets >= 0.6:
        return "milieu"
    if angle_coude_droit < 90 and angle_coude_gauche < 90:
        return "debut"
    # 140 et non 150 : il fallait verrouiller les bras au-dela du naturel pour
    # que la repetition compte (retour de seance).
    elif angle_coude_droit > 140 and angle_coude_gauche > 140:
        return "fin"
    return "milieu"


def extension_triceps_erreur_coudes(corps):
    """Coudes écartés vers l'extérieur, au-delà de la largeur des épaules.

    Seulement coudes levés : bras le long du corps, pendant la mise en place,
    les coudes sont naturellement à la largeur des épaules et la faute serait
    signalée avant d'avoir commencé.
    """
    if not _coudes_leves(corps):
        return None
    ecart = _ecart_rapporte_aux_epaules(corps.coude_gauche, corps.coude_droit, corps)
    # 1,5 et non 1,1 : des coudes a la largeur des epaules sont deja
    # acceptables sur ce mouvement, et l'alerte reprochait une position
    # correcte. Passe par 1,35, encore juge severe a la seance du 5 octobre.
    if ecart is not None and ecart > 1.5:
        return "forme_coudes_trop_ecartes"
    return None


extension_triceps_au_dessus_de_la_tete = Exercice(
    nom="Extension Triceps",
    orientation="face",
    detection=extension_triceps_au_dessus_de_la_tete_detection,
    description="Extension triceps à un haltère tenu à deux mains, derrière la tête.",
    instructions=[
        "Garde les coudes en l'air, au-dessus des épaules, tout le mouvement.",
        "Garde les mains jointes sur l'haltère.",
        "Garde les coudes serrés près de la tête, ils ne s'écartent pas.",
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
    erreurs=[extension_triceps_erreur_coudes],
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
    # Un développé épaule se termine *au-dessus de la tête*, et l'angle du
    # coude seul ne le dit pas : bras baissés et tendus le long du corps, il
    # dépasse aussi 150 degrés. Un testeur comptait donc une répétition en
    # abandonnant sa série, « comme si retendre les bras sous les épaules
    # comptait pour un ». Ce qui fait la position haute, c'est que les
    # poignets sont passés au-dessus des épaules.
    mains_en_haut = (
        corps.poignet_gauche.y < corps.epaule_gauche.y
        and corps.poignet_droit.y < corps.epaule_droite.y
    )
    # Seuil bas ouvert de 40 a 60 degres : a 40 il fallait descendre les
    # halteres bien plus bas que les oreilles, ce que la fiche ne demande pas.
    if angle_coude_droit < 60 and angle_coude_gauche < 60:
        return "debut"
    elif angle_coude_droit > 150 and angle_coude_gauche > 150 and mains_en_haut:
        return "fin"
    return "milieu"


developpe_epaule = Exercice(
    nom="Développé épaule",
    orientation="face",
    detection=developpe_epaule_detection,
    description="Développé épaule debout : pousser les haltères au-dessus de la tête.",
    instructions=[
        "Garde la tête droite, sans avancer le menton.",
        "Pousse les haltères à la verticale jusqu'à tendre les bras.",
        "Redescends jusqu'à hauteur des oreilles.",
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
    # Seuils ouverts de 70/95 a 85/100 : a 70 degres il fallait decoller tout
    # le dos, c'est-a-dire faire un releve de buste et non un crunch. L'ecart
    # de 15 degres entre les deux bornes est conserve — c'est lui qui empeche
    # un tremblement de landmark de compter une repetition.
    if angle_hanche_droite < 85 and angle_hanche_gauche < 85:
        return "fin"
    elif angle_hanche_droite > 100 and angle_hanche_gauche > 100:
        return "debut"
    return "milieu"


crunches = Exercice(
    nom="Crunches",
    orientation="allonge_camera_de_cote",
    detection=crunches_detection,
    description="Crunch au sol : décoller les épaules en contractant les abdominaux.",
    instructions=[
        "Garde le menton décollé du buste, sans tirer sur la nuque.",
        "Redescends sans relâcher complètement les abdominaux.",
        "Pose les mains sur le sol derrière la tête, puis pose-les sur tes genoux.",
    ],
    mise_en_place=[
        "Allongé sur le dos, genoux pliés, pieds à plat sur le tapis.",
        "Place-toi de façon à avoir la caméra sur le côté.",
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
    """Bassin aligné et hanches soulevées du sol.

    Deux réglages ici viennent de tests, et vont dans des sens opposés.

    Le seuil est passé de 145 à 135 degrés : un bassin légèrement bas reste un
    gainage, et à 145 le maintien se coupait par à-coups alors que la position
    était tenue.

    Surtout, les deux côtés sont **moyennés et non exigés ensemble**. La fiche
    demande une vue de profil : la jambe éloignée est donc *toujours* masquée
    et son genou estimé par le modèle. Exiger que les deux angles dépassent le
    seuil revient à exiger que cette estimation soit exacte — un testeur voyait
    le chrono s'arrêter par intermittence et l'attribuait à ses genoux. Une
    moyenne encaisse l'estimation. Ce qu'elle abandonne, c'est la détection
    d'un bassin affaissé d'un seul côté — que la conjonction avait été
    introduite pour attraper, mais qu'une vue de profil ne montre de toute
    façon pas.
    """
    angle_hanche_droite = calculer_angle(
        corps.epaule_gauche, corps.hanche_gauche, corps.genou_gauche
    )
    angle_hanche_gauche = calculer_angle(
        corps.epaule_droite, corps.hanche_droite, corps.genou_droit
    )
    hanches_droites = (angle_hanche_droite + angle_hanche_gauche) / 2 > 135

    hanche_au_dessus_coude = corps.hanche_gauche.y < corps.coude_gauche.y

    # Tombé à plat ventre, le chrono continuait : un corps allongé est aligné,
    # et sa hanche passe au-dessus du coude dès que celui-ci est posé devant.
    # Comme pour la planche latérale, ce qui fait le gainage, c'est l'effort —
    # les épaules soulevées au-dessus des coudes, et les hanches décollées du
    # sol. Moyenne des deux côtés pour l'appui, pour la même raison que les
    # angles de hanche : de profil, le bras éloigné est estimé.
    appui = (
        _appui_sur_le_bras(corps.epaule_gauche, corps.coude_gauche, corps.hanche_gauche)
        + _appui_sur_le_bras(corps.epaule_droite, corps.coude_droit, corps.hanche_droite)
    ) / 2
    decollee = _hanche_decollee(
        (corps.epaule_gauche.y + corps.epaule_droite.y) / 2,
        (corps.hanche_gauche.y + corps.hanche_droite.y) / 2,
        (corps.cheville_gauche.y + corps.cheville_droite.y) / 2,
    )
    en_appui = appui > 0.25 and decollee is not None and decollee > 0.3

    if hanches_droites and hanche_au_dessus_coude and en_appui:
        return "maintien"

    return "repos"


planche = Exercice(
    nom="Gainage planche",
    orientation="profil",
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
        return "debut"
    elif distance_moyenne > 0.15:
        return "fin"
    return "milieu"


squat = Exercice(
    nom="Squat",
    orientation="face",
    detection=squat_detection,
    description="Squat descendu jusqu'à ce que les coudes touchent les genoux : c'est ce contact qui valide la répétition, chargé ou à vide.",
    # La consigne dit ce que la detection mesure, et c'est tout son objet.
    # `squat_detection` compte la repetition sur le **contact coude-genou** ;
    # la fiche decrivait jusqu'ici une position (« descends les hanches vers
    # l'arriere ») et ne mentionnait ce contact qu'en troisieme ligne, comme
    # un detail de style. La machine notait une chose, l'ecran en demandait
    # une autre — et un comptage qui ne prend pas parait alors capricieux.
    #
    # Le contact vient donc avant la remontee, puisque c'est le point bas qui
    # valide, et il est nomme comme un but a atteindre plutot que comme une
    # tolerance a respecter. La ligne des bras a vide n'est pas decorative :
    # sans halteres on ne sait pas quoi en faire, et c'est precisement eux qui
    # portent la mesure.
    instructions=[
        "Garde le dos droit, regard devant.",
        "Descends les hanches vers l'arrière, comme pour t'asseoir.",
        "En bas, va toucher tes genoux avec tes coudes : c'est ce contact qui compte la répétition.",
        "À vide, laisse tes bras descendre devant toi pour aller les chercher.",
        "Remonte en poussant sur les talons.",
    ],
    mise_en_place=[
        "Pieds écartés de la largeur des hanches, pointes légèrement vers l'extérieur.",
        "Un haltère dans chaque main si tu veux charger, bras le long du corps ; sinon à vide, bras libres.",
        "Place-toi face à la caméra, jambes entières visibles.",
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
        return "debut"
    elif angle_genou_droit > 150:
        return "fin"
    return "milieu"


def _genou_depasse_pied(genou, cheville, talon, pointe):
    """De combien le genou avant passe devant la pointe du pied, rapporté au tibia.

    Le sens du regard se lit sur le pied lui-même (du talon vers la pointe) :
    la fonction ne suppose donc pas de quel côté est la caméra. Positif quand
    le genou dépasse, négatif tant qu'il reste en arrière. None quand le pied
    est vu de bout ou le tibia illisible : sans sens ni échelle, il n'y a rien
    à mesurer.
    """
    longueur_pied = pointe.x - talon.x
    tibia = calculer_distance(genou, cheville)
    if abs(longueur_pied) < 0.01 or tibia <= 0:
        return None
    sens = 1 if longueur_pied > 0 else -1
    return (genou.x - pointe.x) * sens / tibia


def _faute_genou_avant(genou, cheville, talon, pointe):
    """Faute affichée seulement : elle ne retire rien au comptage de la fente."""
    depassement = _genou_depasse_pied(genou, cheville, talon, pointe)
    if depassement is not None and depassement > 0.05:
        return "forme_genou_avant_trop_avance"
    return None


def fente_droite_erreur_genou(corps):
    return _faute_genou_avant(
        corps.genou_droit, corps.cheville_droite, corps.talon_droit, corps.pointe_pied_droite
    )


def fente_gauche_erreur_genou(corps):
    return _faute_genou_avant(
        corps.genou_gauche, corps.cheville_gauche, corps.talon_gauche, corps.pointe_pied_gauche
    )


fente_droite = Exercice(
    nom="Fente droite",
    orientation="profil_camera_gauche",
    detection=fente_droite_detection,
    description="Fente avec la jambe droite vers l'avant, jusqu'à ce que le genou droit soit fléchi à environ 90 degrés.",
    instructions=[
        "Garde le buste droit.",
        "Descends le genou arrière vers le sol sans le toucher.",
        "Le genou avant ne doit pas dépasser la pointe du pied.",
        "Remonte en poussant sur le talon avant.",
    ],
    mise_en_place=[
        "Debout, jambe droite avancée d'un grand pas.",
        "Un haltère dans chaque main si tu veux charger ; sinon mains sur les hanches.",
        "Buste droit, regard devant.",
        "Place-toi de profil, la caméra à ta gauche, jambes entières visibles.",
    ],
    erreurs_frequentes=[
        "Le genou avant qui dépasse largement la pointe du pied.",
        "Le buste qui bascule en avant.",
        "Un pas trop court, qui écrase le genou arrière.",
    ],
    erreurs=[fente_droite_erreur_genou],
)
# ==================================
# Fente gauche
# ==================================


def fente_gauche_detection(corps):
    angle_genou_gauche = calculer_angle(
        corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche
    )

    if angle_genou_gauche < 100:
        return "debut"
    elif angle_genou_gauche > 150:
        return "fin"
    return "milieu"


fente_gauche = Exercice(
    nom="Fente gauche",
    orientation="profil_camera_droite",
    detection=fente_gauche_detection,
    description="Fente avec la jambe gauche vers l'avant, jusqu'à ce que le genou gauche soit fléchi à environ 90 degrés.",
    instructions=[
        "Garde le buste droit.",
        "Descends le genou arrière vers le sol sans le toucher.",
        "Le genou avant ne doit pas dépasser la pointe du pied.",
        "Remonte en poussant sur le talon avant.",
    ],
    mise_en_place=[
        "Debout, jambe gauche avancée d'un grand pas.",
        "Un haltère dans chaque main si tu veux charger ; sinon mains sur les hanches.",
        "Buste droit, regard devant.",
        "Place-toi de profil, la caméra à ta droite, jambes entières visibles.",
    ],
    erreurs_frequentes=[
        "Le genou avant qui dépasse largement la pointe du pied.",
        "Le buste qui bascule en avant.",
        "Un pas trop court, qui écrase le genou arrière.",
    ],
    erreurs=[fente_gauche_erreur_genou],
)

# ==================================
# Souleve de terre roumain
# ==================================


def souleve_de_terre_roumain_detection(corps):
    distance_gauche = calculer_distance(corps.poignet_gauche, corps.cheville_gauche)
    distance_droite = calculer_distance(corps.poignet_droit, corps.cheville_droite)
    distance_moyenne = (distance_gauche + distance_droite) / 2

    if distance_moyenne < 0.10:
        return "debut"
    elif distance_moyenne > 0.20:
        return "fin"
    return "milieu"


souleve_roumain = Exercice(
    nom="Souleve de terre roumain",
    orientation="face",
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
        "Place-toi face à la caméra, corps entier visible.",
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


def _appui_sur_le_bras(epaule, coude, hanche):
    """De combien le buste est soulevé par l'appui sur le bras.

    Rapporté à la longueur du buste, donc sans unité : indépendant de la taille
    de la personne et du cadrage. Vaut environ 0 quand on est simplement
    allongé sur le côté — l'épaule est alors à la hauteur du coude, tous deux
    au sol — et grimpe vers 0,5 dès qu'on se redresse sur l'avant-bras.
    """
    buste = calculer_distance(epaule, hanche)
    if buste <= 0:
        return 0.0
    return (coude.y - epaule.y) / buste


def _hanche_decollee(y_epaule, y_hanche, y_cheville):
    """Hauteur de la hanche au-dessus des pieds, rapportée à celle de l'épaule.

    En planche, la hanche est sur la ligne qui va des pieds à l'épaule : vers
    0,5. Hanches posées au sol, elle est à la hauteur des pieds : vers 0.
    C'est la mesure qui manquait pour distinguer l'effort de la position
    allongée — un corps au repos, appuyé sur un coude, garde le buste soulevé.
    None quand l'épaule n'est pas plus haut que les pieds.
    """
    hauteur = y_cheville - y_epaule
    if hauteur <= 0:
        return None
    return (y_cheville - y_hanche) / hauteur


def _gainage_lateral_decolle(epaule, hanche, cheville):
    decollee = _hanche_decollee(epaule.y, hanche.y, cheville.y)
    return decollee is not None and decollee > 0.3


def detection_gainage_laterale_gauche(corps):
    angle_hanche_gauche = calculer_angle(
        corps.epaule_gauche, corps.hanche_gauche, corps.cheville_gauche
    )
    # Meme resserrement que du cote droit, et pour la meme raison : le maintien
    # se declenchait avant que la position soit prise.
    corps_aligne = angle_hanche_gauche > 155

    cote_gauche_au_sol = corps.epaule_gauche.y > corps.epaule_droite.y

    hanche_au_dessus_coude = corps.hanche_gauche.y < corps.coude_gauche.y

    # Allongé sur le côté sans rien faire, les trois conditions précédentes
    # sont réunies : le corps est aligné, le bon côté est en bas, et la hanche
    # passe de justesse au-dessus du coude puisque tous deux touchent le sol.
    # Un testeur voyait donc le chrono tourner « alors que je ne suis pas en
    # position ». Ce qui distingue vraiment une planche latérale, c'est que le
    # buste est *soulevé* par l'appui sur l'avant-bras.
    souleve = _appui_sur_le_bras(corps.epaule_gauche, corps.coude_gauche, corps.hanche_gauche) > 0.25

    # Buste soulevé ne suffisait pas : mesuré au banc d'essai, il n'est jamais
    # descendu sous 0,43, parce qu'allongé sur le côté on reste appuyé sur
    # le coude. Ce qui manquait, c'est la hanche décollée du sol.
    decollee = _gainage_lateral_decolle(corps.epaule_gauche, corps.hanche_gauche, corps.cheville_gauche)

    if corps_aligne and cote_gauche_au_sol and hanche_au_dessus_coude and souleve and decollee:
        return "maintien"

    return "repos"


planche_laterale_gauche = Exercice(
    nom="Gainage planche laterale gauche",
    orientation="face",
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
    # Seuil resserre de 150 a 155 degres : a 150 le corps pouvait casser de 30
    # degres et passer pour aligne, si bien qu'un testeur a compte du temps les
    # fesses posees au sol. Resserre modestement et non a 165 : ce mode n'a pas
    # d'hysteresis, donc un seuil trop pres de la position parfaite ferait
    # clignoter le maintien.
    corps_aligne = angle_hanche_droite > 155

    cote_droit_au_sol = corps.epaule_droite.y > corps.epaule_gauche.y

    hanche_au_dessus_coude = corps.hanche_droite.y < corps.coude_droit.y

    # Allongé sur le côté sans rien faire, les trois conditions précédentes
    # sont réunies : le corps est aligné, le bon côté est en bas, et la hanche
    # passe de justesse au-dessus du coude puisque tous deux touchent le sol.
    # Un testeur voyait donc le chrono tourner « alors que je ne suis pas en
    # position ». Ce qui distingue vraiment une planche latérale, c'est que le
    # buste est *soulevé* par l'appui sur l'avant-bras.
    souleve = _appui_sur_le_bras(corps.epaule_droite, corps.coude_droit, corps.hanche_droite) > 0.25

    # Buste soulevé ne suffisait pas : mesuré au banc d'essai, il n'est jamais
    # descendu sous 0,43, parce qu'allongé sur le côté on reste appuyé sur
    # le coude. Ce qui manquait, c'est la hanche décollée du sol.
    decollee = _gainage_lateral_decolle(corps.epaule_droite, corps.hanche_droite, corps.cheville_droite)

    if corps_aligne and cote_droit_au_sol and hanche_au_dessus_coude and souleve and decollee:
        return "maintien"

    return "repos"


planche_laterale_droite = Exercice(
    nom="Gainage planche laterale droite",
    orientation="face",
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

    # Seuil du haut ouvert de 70 a 90 degres : a 70 le rowing demandait de
    # replier le bras au-dela de ce que le mouvement exige, et des tirages
    # complets s'arretaient a 74-81 degres sans compter.
    if angle_coude_gauche < 90 and poignet_au_dessus_hanche and buste_penche:
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
    orientation="profil_camera_gauche",
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
        "Main droite en appui sur une chaise, dos à plat.",
        "Haltère dans la main gauche, bras tendu vers le sol.",
        "Place-toi de profil, la caméra à ta gauche, buste et bras visibles.",
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

    # Seuil du haut ouvert de 70 a 90 degres : a 70 le rowing demandait de
    # replier le bras au-dela de ce que le mouvement exige, et des tirages
    # complets s'arretaient a 74-81 degres sans compter.
    if angle_coude_droit < 90 and poignet_au_dessus_hanche and buste_penche:
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
    orientation="profil_camera_droite",
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
        "Main gauche en appui sur une chaise, dos à plat.",
        "Haltère dans la main droite, bras tendu vers le sol.",
        "Place-toi de profil, la caméra à ta droite, buste et bras visibles.",
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
    orientation="profil_camera_gauche",
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
        "Place-toi de profil, la caméra à ta gauche, corps entier visible.",
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

    # 65 et non 80 : buste penche face a la camera, le torse se raccourcit a
    # l'image et 80 degres demandaient des bras plus haut que l'horizontale —
    # la seance n'en comptait presque aucune.
    if angle_bras_moyen > 65:
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
    orientation="face",
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


def _descente_hanche(hanche, genou, cheville):
    """Hauteur de la hanche au-dessus du genou, rapportée à celle du tibia.

    Rapportée, donc sans unité : le résultat ne dépend ni de la taille de la
    personne ni de sa distance à la caméra. Vaut environ 1 debout, tend vers 0
    quand la hanche arrive à hauteur de genou.
    """
    tibia = cheville.y - genou.y
    if tibia <= 0:
        return None
    return (genou.y - hanche.y) / tibia


def squat_sur_chaise_detection(corps):
    """Profondeur lue sur la descente de la hanche, et non sur un angle.

    Deux repères ont été essayés avant celui-ci, et chacun supposait un point de
    vue. La distance coude-genou de `squat_detection` suppose des haltères qui
    pendent le long du corps ; au poids du corps les bras partent devant pour
    l'équilibre. L'angle du genou, lui, ne se lit que de profil : la flexion se
    fait dans le plan sagittal, donc *vers* la caméra quand on lui fait face, et
    une projection en deux dimensions garde alors la jambe presque droite au
    plus bas du mouvement. Mesuré sur une pose de face plausible, l'angle ne
    descendait pas sous 124° au plus profond, là où le seuil exigeait 110 : la
    détection ne quittait jamais `"fin"`, ne s'armait donc jamais, et ne
    comptait aucune répétition — c'est le défaut remonté par un testeur.

    Ce qui se voit des deux points de vue, c'est que la hanche descend vers le
    genou. Les deux jambes sont moyennées et non exigées ensemble : de face
    elles sont également visibles, de profil la plus éloignée est estimée, et
    une moyenne encaisse cette estimation là où une conjonction s'y casse.
    """
    mesures = [
        mesure
        for mesure in (
            _descente_hanche(
                corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche
            ),
            _descente_hanche(
                corps.hanche_droite, corps.genou_droit, corps.cheville_droite
            ),
        )
        if mesure is not None
    ]
    if not mesures:
        return "milieu"

    descente = sum(mesures) / len(mesures)
    if descente < 0.45:
        return "debut"
    if descente > 0.75:
        return "fin"
    return "milieu"


pompes_inclinees = Exercice(
    nom="Pompes inclinées",
    orientation="profil",
    # Les angles de coude ne dépendent pas de l'inclinaison : la détection des
    # pompes s'applique telle quelle.
    detection=pompe_detection,
    amplitude=AMPLITUDE_POMPE,
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
    orientation="profil",
    detection=pompe_detection,
    amplitude=AMPLITUDE_POMPE,
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
    orientation="profil",
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
    orientation="face",
    detection=squat_sur_chaise_detection,
    description=(
        "Squat au poids du corps, en s'asseyant sur une chaise puis en se relevant."
    ),
    mise_en_place=[
        "Place une chaise derrière toi, debout, pieds écartés de la largeur des hanches.",
        "Tends les bras devant toi pour l'équilibre.",
        "Place-toi face à la caméra, jambes entières visibles.",
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
