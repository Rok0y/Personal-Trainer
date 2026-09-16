"""Les briques dont le coach compose ses phrases.

**Une annonce se compose, elle ne s'enregistre pas en entier.** Le coach savait
nommer le prochain exercice, mais au prix d'un `.wav` par combinaison exercice x
poids x series x repetitions : seize fichiers sur le disque pour les seules
combinaisons deja jouees, et un script qui ne savait qu'imprimer la liste de ce
qui manquait. La seule issue etait d'enregistrer indefiniment, donc le coach
retombait sur un « changement d'exercice » generique des qu'un objectif
changeait — c'est-a-dire a chaque progression.

Une phrase est desormais une **suite de briques** : « prochain exercice »,
« curl biceps droit », « prepare », « 8 », « kilos ». Chaque brique est un bout
de texte court, enregistre une fois, reutilise partout. `cadrage.js` faisait
deja ce calcul a l'ecrit — sept parties du corps et quatre actions au lieu des
vingt-huit phrases qu'une table unique aurait demandees — et ce module ne fait
que l'etendre a la voix.

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
#: est deja la source, et les nombres, qui sont leur propre texte.
BRIQUES = {
    # --- Liaisons ---------------------------------------------------------
    # Assemblees au milieu d'une phrase, donc prononcees **a plat** : une
    # intonation de fin de phrase rendrait la couture audible.
    "prochain_exercice": "Prochain exercice",
    # Deux briques la ou « prepare » + « un » + « haltere » + « de » en aurait
    # demande quatre : le nombre d'halteres ne prend que deux valeurs, alors
    # que le **poids** en prend onze. On ne factorise que ce qui varie, et
    # decouper une amorce figee en mots ne ferait qu'ajouter des coutures
    # audibles au milieu d'un groupe qui se prononce d'un souffle.
    "prepare_un_haltere_de": "Prépare un haltère de",
    "prepare_deux_halteres_de": "Prépare deux haltères de",
    "kilos": "kilos",
    "kilo": "kilo",
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
    # --- Les deux gestes ---------------------------------------------------
    "geste_bras_en_x": "Croise les bras devant toi pour démarrer",
    "geste_deux_bras_leves": "Lève les deux bras pour remettre à zéro",
    # --- Accueil d'un nouveau profil --------------------------------------
    "bienvenue": "Bienvenue, je suis ton coach",
    "bienvenue_camera_compte": "Ma caméra compte tes répétitions",
    "bienvenue_je_te_guide": "Et je te guide à la voix",
    "bienvenue_rien_ne_sort": "Aucune image ne sort de ton appareil",
    "bienvenue_pret": "On y va quand tu veux",
}

#: Plafond de longueur d'un nom de fichier, controle par
#: `scripts/verifier_annonces.py`. Il ne protege pas le systeme de fichiers :
#: il mesure la **phrase**, puisque le nom en est la traduction directe. Une
#: brique qui le depasse est une brique a decouper, pas un nom a tronquer —
#: tronquer cacherait le symptome et ouvrirait des collisions entre deux
#: phrases de meme debut.
LONGUEUR_MAXIMALE_NOM = 55


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


def sequence_nombre(valeur):
    """Le nombre, s'il est enregistre. Sinon rien, et la phrase se poursuit."""
    try:
        entier = int(valeur)
    except (TypeError, ValueError):
        return []

    if not 1 <= entier <= NOMBRE_MAXIMAL_DIT:
        return []

    return [fichier(str(entier))]


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


def sequence_prochain_exercice(etape, nombre_halteres=0):
    """L'annonce du prochain exercice : ce qu'il est, et ce qu'il faut sortir.

    C'est **la** phrase que ce module existe pour rendre possible : celle qui
    demandait jusqu'ici un `.wav` par combinaison exercice x poids x series x
    repetitions.

    « Prochain exercice. Curl biceps droit. Prepare un haltere de 8 kilos. »

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

    sons = [brique("prochain_exercice"), fichier(etape["exercice"])]

    poids = etape.get("poids") or 0

    if poids <= 0 or nombre_halteres not in (1, 2):
        # Poids du corps, ou materiel non declare : il n'y a rien a preparer, et
        # le silence le dit sans ambiguite. « Zero kilo » n'existe pas.
        return sons

    amorce = (
        "prepare_un_haltere_de" if nombre_halteres == 1 else "prepare_deux_halteres_de"
    )
    chiffre = sequence_nombre(poids)

    # La clause entiere ou rien : une amorce suivie d'un blanc — « prepare un
    # haltere de… » — s'entend comme une panne, la ou son absence s'entend
    # comme une annonce breve.
    if chiffre:
        sons.append(brique(amorce))
        sons.extend(chiffre)
        sons.append(brique("kilo" if poids == 1 else "kilos"))

    return sons

