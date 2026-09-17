"""Les briques dont le coach compose ses phrases.

**Une annonce se compose, elle ne s'enregistre pas en entier.** Le coach savait
nommer le prochain exercice, mais au prix d'un `.wav` par combinaison exercice x
poids x series x repetitions : seize fichiers sur le disque pour les seules
combinaisons deja jouees, et un script qui ne savait qu'imprimer la liste de ce
qui manquait. La seule issue etait d'enregistrer indefiniment, donc le coach
retombait sur un « changement d'exercice » generique des qu'un objectif
changeait — c'est-a-dire a chaque progression.

Une phrase est desormais une **suite de briques** : « prochain exercice, curl
biceps droit », « prepare un haltere de 8 kilos », « place-toi de profil ».
Chaque brique est enregistree une fois et reutilisee partout. `cadrage.js`
faisait deja ce calcul a l'ecrit — sept parties du corps et quatre actions au
lieu des vingt-huit phrases qu'une table unique aurait demandees — et ce module
ne fait que l'etendre a la voix.

**Deux criteres decident d'un decoupage, et il faut les deux.** Le premier est
la recombinaison : un morceau merite sa prise s'il se retrouve derriere ou
devant *plusieurs* autres. Les cinq orientations servent trente-neuf
mouvements, les sept parties du corps du cadrage se croisent avec quatre
actions, et le nom d'un exercice se dit derriere **trois** amorces — « prochain
exercice », « le premier exercice sera », « pour finir » — soit quarante-deux
prises la ou les phrases entieres en demanderaient cent dix-sept. Le second
critere est la **couture** : elle doit tomber sur une pause que la phrase a
deja. « Prochain exercice : curl biceps droit » s'annonce comme un titre, avec
un deux-points naturel ou le raccord ne s'entend pas.

C'est le second critere qui a fait reculer le decoupage des charges. « Prepare
un haltere de » + « 8 » + « kilos » coupe **a l'interieur d'un groupe
nominal**, la ou la voix ne s'arrete jamais : trois attaques et trois chutes
pour une seule clause, et ca s'entend comme un saccadement meme prononce a
plat — pour un gain de dix-sept prises. Une charge s'enregistre donc entiere.
*On factorise ce qui se recombine, et seulement la ou la phrase respire
deja.*

D'ou deux tables plutot qu'une. `BRIQUES` est le vocabulaire **enregistre tel
quel**, un fichier par entree — les amorces et les noms de mouvements en font
partie. `FRAGMENTS` ne porte que des morceaux de texte qui n'existent **jamais
seuls sur le disque** : ils composent le texte, donc le nom, des phrases qui
s'enregistrent entieres. Il n'y reste que les charges.

La regle qui en decoule gouverne tout ajout de texte au projet : **l'ecrit est
gratuit et peut etre exhaustif, la voix est chere et doit etre factorisee.**
Les vingt-trois exercices ont chacun leur `mise_en_place` de trois lignes, mais
l'orientation camera qu'elles decrivent ne prend que cinq valeurs distinctes :
l'ecran affiche les trois lignes, le coach dit la ligne partagee.

**Le nom du fichier est le texte prononce**, normalise. « Recule d'un pas »
s'enregistre dans `recule_d_un_pas.wav`. Ce n'est pas une commodite : c'est ce
qui rend la feuille d'enregistrement fiable, puisqu'elle est *derivee* de ces
tables et non tenue a la main a cote d'elles. Deux listes qui doivent coincider
finissent toujours par diverger ; une seule ne le peut pas.

Corollaire : il n'y a **pas de cle distincte du texte**. Ailleurs dans le projet
un message porte une cle pour qu'on puisse le reformuler en un seul endroit
(`core/messages.py`) ; ici reformuler veut dire reenregistrer, donc la cle n'a
rien a proteger. `BRIQUES` ne sert qu'a nommer le vocabulaire fixe pour que le
code se lise, et les noms d'exercices n'y figurent meme pas — le catalogue en
est deja la source.

**Ce module n'importe que la bibliotheque standard, et ce n'est pas negociable.**
`scripts/preparer_demo.py` doit pouvoir l'importer pour exporter ses tables vers
le navigateur, or le workflow de deploiement n'installe que numpy : un import de
`pygame` — ce que fait `audio.lecteur`, donc `audio.coach` — ferait echouer le
deploiement pour une raison sans aucun rapport avec le son. Meme contrainte, et
meme motif, que `progression/paliers.py`. Si l'arbre d'imports s'alourdit un
jour, l'etape doit echouer bruyamment plutot que d'etre blindee a l'avance.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Du texte au fichier
# ---------------------------------------------------------------------------


def normaliser_nom(texte):
    """Le nom de fichier d'un texte : sans accents, sans ponctuation, minuscules.

    Point d'entree unique de cette traduction, des deux cotes du portage — le
    jumeau est `normaliser_nom` dans `web/static/js/annonces.js`.
    `audio/coach.py` la reexporte pour ses appelants historiques.
    """
    sans_accents = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(
        caractere
        for caractere in sans_accents
        if unicodedata.category(caractere) != "Mn"
    )

    return re.sub(r"[^a-z0-9]+", "_", sans_accents.lower()).strip("_")


def fichier(texte):
    """Le `.wav` qui porte ce texte.

    Aucun cas particulier pour les nombres : `normaliser_nom("12")` rend `"12"`,
    donc `12.wav` — exactement le fichier deja enregistre pour le comptage des
    repetitions. Les vingt premieres prises sont ainsi reutilisees sans qu'une
    seule ligne ne les distingue.
    """
    return f"{normaliser_nom(texte)}.wav"


# ---------------------------------------------------------------------------
# Le vocabulaire fixe
# ---------------------------------------------------------------------------

#: Les briques dont le code parle par leur nom. Les valeurs sont le texte
#: **exactement** prononce : les changer impose de reenregistrer.
#:
#: Ce qui n'est volontairement pas ici : les noms d'exercices, dont le catalogue
#: est deja la source, les nombres, qui sont leur propre texte, et les
#: `FRAGMENTS`, qui ne s'enregistrent jamais seuls.
BRIQUES = {
    # --- Les amorces qui annoncent un mouvement ----------------------------
    # Elles se disent **devant un nom d'exercice**, jamais seules, et c'est
    # pour elles que le nom du mouvement reste une prise a part : trois
    # amorces x trente-neuf mouvements se recombinent, et la couture tombe
    # sur la pause d'un deux-points — « prochain exercice : curl biceps
    # droit ». Prononce-les donc **suspendues**, sans chute de fin de phrase.
    #
    # Vocabulaire ferme, declare dans `AMORCES_EXERCICE` : le coach choisit
    # selon la position du mouvement dans la seance, et non au hasard.
    "prochain_exercice": "Prochain exercice",
    "premier_exercice": "Le premier exercice sera",
    "dernier_exercice": "Pour finir",
    # --- Orientation par rapport a la camera -------------------------------
    # Cinq valeurs couvrent les trente-neuf mouvements du catalogue. C'est le
    # gain de factorisation le plus net du module : la ligne de cadrage de
    # chaque `mise_en_place` est propre a l'exercice a l'ecrit, mais ne dit
    # jamais que l'une de ces cinq choses a la voix.
    "orientation_face": "Place-toi face à la caméra",
    "orientation_profil": "Place-toi de profil",
    "orientation_profil_camera_gauche": "Place-toi de profil, la caméra à ta gauche",
    "orientation_profil_camera_droite": "Place-toi de profil, la caméra à ta droite",
    "orientation_allonge_camera_de_cote": "Allonge-toi, la caméra sur le côté",
    # --- Cadrage : ce qui manque ------------------------------------------
    # Jumeaux vocaux de `CE_QUI_MANQUE` dans `web/static/js/cadrage.js`. Sept
    # parties et quatre actions, assemblees deux a deux : onze prises couvrent
    # les vingt-huit consignes possibles.
    "cadrage_manque_tete": "Je ne vois pas ta tête",
    "cadrage_manque_epaules": "Je ne vois pas tes épaules",
    "cadrage_manque_coudes": "Je ne vois pas tes coudes",
    "cadrage_manque_mains": "Je ne vois pas tes mains",
    "cadrage_manque_hanches": "Je ne vois pas tes hanches",
    "cadrage_manque_genoux": "Je ne vois pas tes genoux",
    "cadrage_manque_pieds": "Je ne vois pas tes pieds",
    # --- Cadrage : quoi faire ---------------------------------------------
    # Volontairement sans gauche ni droite, pour la meme raison qu'a l'ecrit :
    # l'image peut etre affichee en miroir, donc un cote a l'ecran est l'autre
    # dans la piece. Le centre, lui, est le meme des deux cotes.
    "cadrage_action_recule": "Recule, tu ne tiens pas dans l'image",
    "cadrage_action_baisse_camera": "Baisse la caméra ou incline-la vers le bas",
    "cadrage_action_monte_camera": "Monte la caméra ou incline-la vers le haut",
    "cadrage_action_centre": "Place-toi au centre de l'image",
    # --- Installation, dite au debut d'une seance --------------------------
    # Decoupees court, et pas seulement pour la longueur du nom de fichier :
    # une brique de huit secondes se reenregistre en entier pour un mot a
    # corriger, ne se reutilise nulle part, et rend le coach bavard au moment
    # ou l'on veut agir. `verifier_annonces.py` refuse au-dela de
    # `LONGUEUR_MAXIMALE_NOM` — la longueur du nom **mesure** celle de la
    # phrase, donc le plafond est un garde-fou editorial et non technique.
    "installation_hauteur": "Pose ton appareil à hauteur de poitrine",
    "installation_pas_au_sol": "Posé au sol, il ne te verra pas en entier",
    "installation_distance": "Recule à deux ou trois mètres",
    "installation_tapis": "Place ton tapis perpendiculaire à la caméra",
    "installation_pas_de_cote": "Fais un pas à droite, puis un pas à gauche",
    "installation_pas_arriere": "Puis un pas en arrière et un pas en avant",
    "installation_toujours_visible": "On doit te voir en entier à chaque fois",
    "installation_bien_cadre": "Parfait, tu es bien cadré",
    "installation_appareil_droit": "Garde l'appareil bien droit, pas incliné",
    "installation_ne_le_bouge_plus": "Une fois posé, ne le bouge plus",
    "installation_respecte_l_angle": "Chaque exercice te dira comment te placer",
    "installation_verifions": "Vérifions que tu tiens dans l'image",
    # --- Les deux gestes ---------------------------------------------------
    "geste_bras_en_x": "Croise les bras devant toi pour démarrer",
    "geste_deux_bras_leves": "Lève les deux bras pour remettre à zéro",
    # Les quatre suivantes accompagnent l'exercice de l'accueil, ou les deux
    # gestes sont **joues** et non seulement decrits : « leve les bras » au
    # present s'adresse a quelqu'un qui doit le faire maintenant, la ou
    # `geste_deux_bras_leves` enonce une regle.
    "geste_valide_la_serie": "Croise les bras pour valider ta série",
    "geste_hauteur_libre": "En haut ou en bas, seul le croisement compte",
    "geste_compteur_monte": "Ton compteur monte à chaque répétition",
    "geste_leve_les_bras_maintenant": "Lève les deux bras et tiens la position",
    "geste_remis_a_zero": "C'est bien, te voilà reparti de zéro",
    "geste_croise_les_bras": "Croise les bras et tiens la position",
    "geste_bravo": "Bravo, tu sais tout piloter de loin",
    # --- Accueil d'un nouveau profil --------------------------------------
    "bienvenue": "Bienvenue, je suis ton coach",
    "bienvenue_pose_et_entraine": "Tu poses ton appareil, et tu t'entraînes",
    "bienvenue_camera_compte": "Ma caméra compte tes répétitions",
    "bienvenue_je_te_guide": "Et je te guide à la voix",
    "bienvenue_rien_ne_sort": "Aucune image ne sort de ton appareil",
    "bienvenue_pret": "On y va quand tu veux",
}

#: Les morceaux de texte qui ne s'enregistrent **jamais seuls**. Ils ne
#: servent qu'a composer le texte — donc le nom de fichier — d'une phrase
#: enregistree d'un souffle, et n'apparaissent pour cette raison ni sur la
#: feuille de prise de son ni parmi les fichiers attendus sur le disque.
#:
#: Ils etaient dans `BRIQUES`, et la voix cousait « prepare un haltere de » a
#: « 8 » puis a « kilos » au moment de lire. La couture s'entendait, parce
#: qu'elle tombait **a l'interieur d'un groupe nominal**, la ou la voix ne
#: s'arrete jamais (voir l'en-tete). Les garder en table plutot qu'en litteral
#: dans les fonctions preserve ce qui les rendait utiles : la formulation se
#: corrige en un seul endroit, et le nom de fichier suit.
#:
#: Le navigateur les recoit **dans la meme table que `BRIQUES`**
#: (`donnees/sons.json`, cle `briques`) : il n'en connait que les noms de
#: fichiers, dont il assemble les morceaux (`fichier_assemble` dans
#: `annonces.js`). C'est ici, du cote du texte, que la distinction a un sens.
FRAGMENTS = {
    # Deux entrees la ou « prepare » + « un » + « haltere » + « de » en aurait
    # demande quatre : le nombre d'halteres ne prend que deux valeurs.
    "prepare_un_haltere_de": "Prépare un haltère de",
    "prepare_deux_halteres_de": "Prépare deux haltères de",
    "kilos": "kilos",
    # Singulier du seul cas ou il sert : un haltere de 1 kg. `POIDS_REFERENCE`
    # ne le propose pas, donc la prise n'est pas demandee — un poids saisi a
    # la main a 1 kg laisse la clause muette, ce qui est le comportement
    # normal d'un fichier absent.
    "kilo": "kilo",
}

#: Plafond de longueur d'un nom de fichier, controle par
#: `scripts/verifier_annonces.py`. Il ne protege pas le systeme de fichiers :
#: il mesure la **phrase**, puisque le nom en est la traduction directe. Une
#: brique qui le depasse est une brique a decouper, pas un nom a tronquer —
#: tronquer cacherait le symptome et ouvrirait des collisions entre deux
#: phrases de meme debut.
#:
#: Il s'applique aussi aux **charges**, seules phrases assemblees qui restent
#: (« prepare deux halteres de 25 kilos » : 33 caracteres) : celles-la ne se
#: decoupent pas, puisque c'est precisement leur decoupage qui s'entendait.
LONGUEUR_MAXIMALE_NOM = 55


#: Les facons d'annoncer un mouvement, selon sa place dans la seance.
#: Vocabulaire **ferme**, sur le modele d'`ORIENTATIONS` : l'appelant choisit,
#: et `brique()` leve sur une cle inconnue plutot que de laisser une amorce
#: muette.
#:
#: C'est l'existence de ces trois valeurs qui justifie que le nom d'un
#: mouvement reste une **prise separee**. Avec une seule amorce, les phrases
#: entieres auraient ete le bon choix : rien ne se recombinait.
AMORCES_EXERCICE = (
    "prochain_exercice",
    "premier_exercice",
    "dernier_exercice",
)

#: Les orientations admises, dans l'ordre ou elles se lisent. Vocabulaire
#: **ferme** : `Exercice.orientation` ne prend que ces valeurs, et
#: `scripts/verifier_annonces.py` le controle.
#:
#: Elle est **declaree** sur chaque exercice et non deduite du texte de
#: `mise_en_place`. Deduire reviendrait a analyser une phrase francaise, qui
#: mentirait en silence le jour ou quelqu'un la reformule — et un coach qui dit
#: « place-toi face a la camera » pour un gainage est pire que muet.
ORIENTATIONS = (
    "face",
    "profil",
    "profil_camera_gauche",
    "profil_camera_droite",
    "allonge_camera_de_cote",
)

#: Il n'y a **volontairement pas de valeur par defaut**. `orientation` a None
#: veut dire « on n'a rien de sur a dire », et le coach se tait — c'est le cas
#: des echauffements, dont aucune fiche ne parle de la camera.
#:
#: Un defaut a « face » serait pire que le silence : il ferait affirmer une
#: consigne que personne n'a verifiee, sur des mouvements ou elle peut etre
#: fausse. C'est la lecon de `cadrage.js`, payee en conditions reelles — une
#: consigne qui se declenche a tort apprend a ne plus l'ecouter.


def brique(cle):
    """Le fichier d'une brique du vocabulaire fixe. Leve sur une cle inconnue.

    Elle **leve**, contrairement a `coach()` qui sort en silence : une cle
    inconnue ici est une faute de frappe dans du code, pas une donnee absente.
    Les appelants qui tournent dans la boucle camera passent par les fabriques
    de sequence ci-dessous, qui ne fabriquent que des cles valides.
    """
    return fichier(BRIQUES[cle])


# ---------------------------------------------------------------------------
# Les fabriques de sequences
# ---------------------------------------------------------------------------
#
# Chacune rend une **liste de fichiers**, jouee comme un seul evenement par
# `jouer_sequence` / `Lecteur.sequence`. Une liste vide veut dire « rien a
# dire » : c'est un silence, jamais une erreur.

#: Au-dela, la partie chiffree est muette. Ce n'est pas une limite technique
#: mais le point ou enregistrer un nombre de plus cesse de valoir le detour :
#: le bareme se terminant par une tranche ouverte, il n'existe aucun plafond a
#: atteindre, et une annonce sans son nombre reste utile.
NOMBRE_MAXIMAL_DIT = 60


def nombre_dit(valeur):
    """L'entier qu'on sait prononcer, ou None. Point d'entree unique du plafond.

    Extrait de `sequence_nombre` parce que deux appelants ont besoin du
    **nombre** et non de son fichier : la composition d'une charge, qui l'ecrit
    dans une phrase, et le choix du singulier.

    Le refus d'un flottant non entier n'est pas decoratif : un haltere de
    17,5 kg est declarable (`core.materiel.poids_declarable` arrondit au
    demi-kilo) et n'a aucune prise. `int(17.5)` rendait 17, donc le coach
    annoncait une charge fausse — la ou le jumeau JavaScript, qui teste
    `Number.isInteger`, se taisait deja. Divergence reelle entre les deux
    portages, invisible parce que le harnais ne tirait que des entiers.
    """
    try:
        entier = int(valeur)
    except (TypeError, ValueError):
        return None

    if isinstance(valeur, float) and valeur != entier:
        return None

    if not 1 <= entier <= NOMBRE_MAXIMAL_DIT:
        return None

    return entier


def sequence_nombre(valeur):
    """Le nombre seul, s'il est enregistre. Sinon rien.

    Plus aucun appelant de production : le compteur de repetitions passe par
    `coach("compteur", n)`, et les charges sont desormais des phrases
    entieres. Conservee parce qu'elle est la forme « sequence » du nombre, que
    le portage compare, et que toute annonce chiffree a venir repassera par
    elle plutot que de refaire le plafond.
    """
    entier = nombre_dit(valeur)

    return [fichier(str(entier))] if entier is not None else []


def sequence_cadrage(partie, action):
    """La consigne de cadrage, en deux briques.

    `partie` peut valoir None : c'est le cas « coupe en haut *et* en bas », ou
    nommer une partie tromperait puisqu'il en manque des deux cotes. C'est
    `message_de_cadrage` (`web/static/js/cadrage.js`) qui en decide.
    """
    sons = []

    if partie:
        sons.append(brique(f"cadrage_manque_{partie}"))

    if action:
        sons.append(brique(f"cadrage_action_{action}"))

    return sons


def sequence_orientation(orientation):
    """Comment se placer par rapport a la camera, pour ce mouvement-la."""
    if orientation not in ORIENTATIONS:
        return []

    return [brique(f"orientation_{orientation}")]


def texte_charge(nombre_halteres, poids):
    """« Prepare deux halteres de 8 kilos », ou None s'il n'y a rien a dire.

    None des que la phrase serait incomplete : poids du corps, materiel non
    declare, ou charge qu'on ne sait pas prononcer. **Entiere ou rien** — une
    amorce suivie d'un blanc s'entend comme une panne, la ou son absence
    s'entend comme une annonce breve.
    """
    entier = nombre_dit(poids)

    if entier is None or nombre_halteres not in (1, 2):
        return None

    amorce = FRAGMENTS[
        "prepare_un_haltere_de" if nombre_halteres == 1 else "prepare_deux_halteres_de"
    ]
    unite = FRAGMENTS["kilo" if entier == 1 else "kilos"]

    return f"{amorce} {entier} {unite}"


def fichiers_charges(poids_possibles):
    """Les `.wav` de charge de ces poids : un par (nombre d'halteres, poids).

    La gamme est **injectee**, pour la meme raison que `nombre_halteres` l'est
    plus bas : elle vit dans `core.materiel`, que ce module ne peut pas
    importer sans perdre sa legerete d'imports (voir l'en-tete).

    Aucun appelant de production n'en a besoin — on compose toujours a partir
    d'un poids reel, et un fichier absent est un silence. Elle ne sert qu'aux
    scripts qui doivent **enumerer** ce qui reste a enregistrer ou a copier.
    """
    return {
        fichier(texte)
        for halteres in (1, 2)
        for poids in poids_possibles
        if (texte := texte_charge(halteres, poids))
    }


def sequence_prochain_exercice(etape, nombre_halteres=0, amorce="prochain_exercice"):
    """L'annonce du prochain exercice : ce qu'il est, et ce qu'il faut sortir.

    C'est **la** phrase que ce module existe pour rendre possible : celle qui
    demandait jusqu'ici un `.wav` par combinaison exercice x poids x series x
    repetitions.

    « Prochain exercice. Curl biceps droit. Prepare un haltere de 8 kilos. »

    `amorce` est une cle d'`AMORCES_EXERCICE`, choisie par l'appelant selon la
    position du mouvement dans la seance : « le premier exercice sera » a
    l'entree, « pour finir » sur le dernier, « prochain exercice » partout
    ailleurs. C'est l'appelant qui sait — ce module ne voit qu'une etape.

    **Les series et les repetitions n'y sont volontairement pas.** Elles sont
    deja a l'ecran, et les dire allongeait l'annonce de plusieurs secondes au
    moment precis ou l'on veut agir plutot qu'ecouter. Le critere retenu : on
    prononce ce qui demande un **geste** pendant le repos, pas ce qui se lit.
    Les rajouter tiendrait en trois lignes ici et deux briques de plus.

    Le nom de l'exercice **est** son propre texte : `fichier(etape["exercice"])`
    suffit, il n'y a aucune table a tenir a jour a cote du catalogue.

    `nombre_halteres` est **injecte** et non lu ici : il vit dans
    `session.seances.nombre_halteres`, qui tire tout le catalogue, alors que ce
    module doit rester sans dependance (voir l'en-tete). Un et deux ne sont pas
    interchangeables a l'oreille — on ne sort pas la meme chose du placard — et
    c'est une information qu'aucun ecran regarde de trois metres ne donne.

    Rend une liste de fichiers, jouee comme un seul evenement indivisible.
    """
    if etape is None:
        return []

    # L'amorce, puis le nom du mouvement — deux prises, parce qu'elles se
    # recombinent : trois amorces x trente-neuf mouvements, et la couture
    # tombe sur la pause d'un deux-points (voir l'en-tete). La charge, elle,
    # est une phrase entiere : la sienne tomberait au milieu d'un groupe
    # nominal.
    sons = [brique(amorce), fichier(etape["exercice"])]

    # Poids du corps, ou materiel non declare : il n'y a rien a preparer, et le
    # silence le dit sans ambiguite. « Zero kilo » n'existe pas.
    charge = texte_charge(nombre_halteres, etape.get("poids") or 0)

    if charge:
        sons.append(fichier(charge))

    return sons

