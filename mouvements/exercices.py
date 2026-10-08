from mouvements.outils import calculer_angle, calculer_distance
from mouvements.fiches import textes
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
    **textes("Curl biceps droit"),
    orientation="face",
    detection=curl_biceps_droit_detection,
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
    **textes("Curl biceps gauche"),
    orientation="face",
    detection=curl_biceps_gauche_detection,
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
    **textes("Elevations latérales"),
    orientation="face",
    detection=elevation_laterale_detection,
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


# Les bornes de la position « mains au mur », rapportées au buste. Le poignet
# ne descend pas plus d'une demi-longueur de buste sous l'épaule (les mains se
# posent à hauteur de poitrine), ne monte pas plus d'un tiers au-dessus — au-
# delà, tenues trois secondes, deux mains en l'air ressembleraient au geste qui
# remet le compteur à zéro —, et s'avance d'au moins un cinquième de buste
# devant l'épaule : c'est ce qui écarte un bras qu'on plie debout le long du
# corps. L'avancée reste basse parce qu'en bas du mouvement, poitrine près du
# mur, l'épaule rejoint presque les mains.
HAUTEUR_MUR_MAX = 0.5
HAUTEUR_MUR_MIN = -0.35
AVANCEE_MUR_MIN = 0.2


def _poignet_devant_epaule(corps):
    """Hauteur et avancée du poignet du bras visible, rapportées au buste.

    La hauteur est celle de `_hauteur_sous_epaule` (0 à hauteur d'épaule,
    positive en dessous). L'avancée est l'écart horizontal entre épaule et
    poignet, sans signe : de profil, la caméra peut être d'un côté ou de
    l'autre. (None, None) quand le buste n'a pas de longueur lisible.
    """
    epaule, _, poignet = _bras_proche(corps)
    hanche = corps.hanche_gauche if epaule is corps.epaule_gauche else corps.hanche_droite
    hauteur = _hauteur_sous_epaule(poignet, epaule, hanche)
    if hauteur is None:
        return None, None
    return hauteur, abs(poignet.x - epaule.x) / calculer_distance(epaule, hanche)


def pompe_mur_detection(corps):
    """Pompe debout, mains contre un mur, vue de profil.

    `pompe_detection` ne peut pas servir : elle exige un buste couché, et c'est
    précisément ce qui l'empêche de compter un bras plié debout. Ici on est
    debout, donc la position doit être dite autrement — buste debout, mains
    devant soi à hauteur de poitrine. Une condition partagée par `"debut"` et
    `"fin"` fait tomber tout le reste en `"milieu"`, donc rien ne compte hors
    de la position. L'angle est celui des pompes, sur le bras que la caméra
    voit vraiment.
    """
    if _buste_vertical(corps) <= 0:
        return "milieu"
    hauteur, avancee = _poignet_devant_epaule(corps)
    if hauteur is None:
        return "milieu"
    if not HAUTEUR_MUR_MIN < hauteur < HAUTEUR_MUR_MAX or avancee <= AVANCEE_MUR_MIN:
        return "milieu"
    angle_coude = _angle_coude_proche(corps)
    if angle_coude < SEUIL_COMPTAGE_POMPE:
        return "debut"
    elif angle_coude > 160:
        return "fin"
    return "milieu"


pompe = Exercice(
    nom="Pompes",
    **textes("Pompes"),
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
    **textes("Developpé couché altères"),
    orientation="allonge_camera_de_cote",
    detection=developpe_couche_sol_detection,
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
    **textes("Extension Triceps"),
    orientation="face",
    detection=extension_triceps_au_dessus_de_la_tete_detection,
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
    **textes("Développé épaule"),
    orientation="face",
    detection=developpe_epaule_detection,
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
    **textes("Crunches"),
    orientation="allonge_camera_de_cote",
    detection=crunches_detection,
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
    **textes("Gainage planche"),
    orientation="profil",
    detection=detection_gainage,
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
    # La consigne (dans `fiches.json`) dit ce que la detection mesure, et
    # c'est tout son objet : `squat_detection` compte la repetition sur le
    # **contact coude-genou**. La fiche decrivait autrefois une position
    # (« descends les hanches vers l'arriere ») et ne mentionnait ce contact
    # qu'en troisieme ligne, comme un detail de style — la machine notait une
    # chose, l'ecran en demandait une autre, et un comptage qui ne prend pas
    # parait alors capricieux. Le contact y vient donc avant la remontee, nomme
    # comme un but a atteindre. A garder en relisant la fiche.
    **textes("Squat"),
    orientation="face",
    detection=squat_detection,
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
    **textes("Fente droite"),
    orientation="profil_camera_gauche",
    detection=fente_droite_detection,
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
    **textes("Fente gauche"),
    orientation="profil_camera_droite",
    detection=fente_gauche_detection,
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
    **textes("Souleve de terre roumain"),
    orientation="face",
    detection=souleve_de_terre_roumain_detection,
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
    **textes("Gainage planche laterale gauche"),
    orientation="face",
    detection=detection_gainage_laterale_gauche,
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
    **textes("Gainage planche laterale droite"),
    orientation="face",
    detection=detection_gainage_laterale_droite,
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
    **textes("Rowing unilateral gauche"),
    orientation="profil_camera_gauche",
    detection=rowing_unilateral_gauche_detection,
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
    **textes("Rowing unilateral droit"),
    orientation="profil_camera_droite",
    detection=rowing_unilateral_droit_detection,
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
    **textes("Rowing penche"),
    orientation="profil_camera_gauche",
    detection=rowing_penche_detection,
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
    **textes("Oiseau"),
    orientation="face",
    detection=oiseau_detection,
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
    **textes("Pompes inclinées"),
    orientation="profil",
    # Les angles de coude ne dépendent pas de l'inclinaison : la détection des
    # pompes s'applique telle quelle.
    detection=pompe_detection,
    amplitude=AMPLITUDE_POMPE,
    erreurs=[],
    variante_facile="Pompes contre le mur",
    variante_difficile="Pompes sur les genoux",
)

pompes_contre_le_mur = Exercice(
    nom="Pompes contre le mur",
    **textes("Pompes contre le mur"),
    orientation="profil",
    detection=pompe_mur_detection,
    amplitude=AMPLITUDE_POMPE,
    erreurs=[],
    variante_difficile="Pompes inclinées",
)

pompes_sur_les_genoux = Exercice(
    nom="Pompes sur les genoux",
    **textes("Pompes sur les genoux"),
    orientation="profil",
    detection=pompe_detection,
    amplitude=AMPLITUDE_POMPE,
    erreurs=[],
    variante_facile="Pompes inclinées",
    variante_difficile="Pompes",
)

gainage_sur_les_genoux = Exercice(
    nom="Gainage sur les genoux",
    **textes("Gainage sur les genoux"),
    orientation="profil",
    # L'angle épaule-hanche-genou reste celui d'un corps aligné, genoux au sol
    # ou non : la détection du gainage complet convient sans retouche.
    detection=detection_gainage,
    erreurs=[],
    variante_difficile="Gainage planche",
)

squat_sur_chaise = Exercice(
    nom="Squat sur chaise",
    **textes("Squat sur chaise"),
    orientation="face",
    detection=squat_sur_chaise_detection,
    erreurs=[],
    variante_difficile="Squat",
)
