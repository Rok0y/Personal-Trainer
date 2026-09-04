"""Du test d'un débutant à son niveau de départ.

Un nouveau profil n'a pas d'historique, donc pas de niveau : `niveau_pour`
renvoie None sur tous les exercices et le moteur n'a rien à lui proposer. Le
test de calibration comble ce trou en fabriquant la seule chose que le barème
sait lire — une **performance** —, exactement comme le formulaire « Recaler mon
niveau » de la page Records. C'est pour ça que ce module ne pose aucun numéro
de niveau : il produit une performance, et le barème en déduit le reste.

Ce qui est mesuré est une **série unique au maximum** : « fais autant de
répétitions propres que tu peux, arrête-toi quand la forme se dégrade ». Un
seul effort par exercice, parce qu'un tunnel d'accueil qui demanderait trois
séries de chaque mouvement ne serait jamais terminé.

D'où la difficulté que ce module doit résoudre : un maximum en série unique et
une cible de barème ne mesurent pas la même chose. Vingt pompes d'affilée une
fois ne veulent pas dire quatre séries de vingt. Il faut convertir, et aucune
conversion n'est exacte — c'est pourquoi l'écran de confirmation existe, et
qu'il propose toujours le cran du dessous et celui du dessus.
"""

from progression.paliers import (
    est_suivi_par_le_moteur,
    niveau_pour,
    palier,
    specification,
    unite,
)

#: Part d'un maximum en série unique qu'on peut tenir série après série.
#: Repère d'entraîneur, pas une mesure : quelqu'un qui fait 20 pompes d'affilée
#: en tient environ 13 sur chacune de ses séries de travail. Volontairement
#: prudent — un objectif de départ trop bas se corrige en une séance, un
#: objectif trop haut décourage et fait échouer toutes les séries.
COEFFICIENT_SERIE_UNIQUE = 0.65


def series_de_reference(nom_exercice):
    """Nombre de séries sur lequel le barème de cet exercice raisonne."""
    spec = specification(nom_exercice)
    return spec.series if spec else None


def niveau_estime(nom_exercice, poids, maximum):
    """Niveau déduit d'un maximum réalisé en une seule série.

    `maximum` est en répétitions ou en secondes selon l'unité de l'exercice.
    Retourne le numéro de niveau, ou None si la performance n'atteint pas le
    premier palier (l'appelant proposera alors la variante assistée).
    """
    if not est_suivi_par_le_moteur(nom_exercice) or not maximum or maximum <= 0:
        return None

    series = series_de_reference(nom_exercice)
    if not series:
        return None

    # Le même coefficient sert aux répétitions et aux secondes. Les deux ne
    # fatiguent pourtant pas pareil — un gainage tenu au maximum s'effondre plus
    # vite d'une série à l'autre qu'une série de pompes —, mais une règle unique
    # vaut mieux ici que deux réglages dont personne ne saura lequel corriger le
    # jour où une estimation tombe à côté. C'est l'écran de confirmation, pas
    # une deuxième constante, qui rattrape l'écart.
    cible = max(1, round(maximum * COEFFICIENT_SERIE_UNIQUE))

    # `niveau_pour` rend None quand la performance n'atteint pas le premier
    # palier : on propage tel quel, c'est le signal « propose une variante plus
    # facile » et non « niveau zéro ».
    return niveau_pour(nom_exercice, poids, series, cible)


def proposition(nom_exercice, poids, maximum):
    """Ce que l'écran de confirmation a besoin d'afficher.

    Toujours trois crans quand ils existent — celui d'en dessous, celui qu'on
    propose, celui d'au-dessus. La conversion est une estimation : l'utilisateur
    doit pouvoir la corriger sans repasser par le test.
    """
    if not est_suivi_par_le_moteur(nom_exercice):
        return None

    niveau = niveau_estime(nom_exercice, poids, maximum)
    propose = palier(nom_exercice, niveau) if niveau else None

    return {
        "exercice": nom_exercice,
        "unite": unite(nom_exercice),
        "maximum": maximum,
        "poids": poids,
        "niveau": niveau,
        "palier": propose.resume() if propose else None,
        # `hors_barème` n'est pas « niveau 0 » : c'est « même le premier palier
        # n'est pas atteint », et la bonne réponse est alors une variante plus
        # facile, pas un niveau plus bas.
        "hors_bareme": niveau is None,
        "premier": palier(nom_exercice, 1).resume(),
        "voisins": paliers_voisins(nom_exercice, niveau),
    }


def paliers_voisins(nom_exercice, niveau):
    """Les crans immédiatement en dessous et au-dessus, pour l'ajustement.

    Une liste de dicts `{niveau, resume}` plutôt que deux champs : l'écran les
    affiche en boutons, et un cran manquant (niveau 1 n'a pas de précédent)
    disparaît de lui-même au lieu de demander une condition de plus au template.
    """
    if not niveau:
        return []
    voisins = []
    for candidat in (niveau - 1, niveau + 1):
        cran = palier(nom_exercice, candidat) if candidat >= 1 else None
        if cran is not None:
            voisins.append({"niveau": candidat, "resume": cran.resume()})
    return voisins


# ---------------------------------------------------------------------------
# Le tunnel d'accueil
# ---------------------------------------------------------------------------
#
# **Aucune table de suivi.** L'avancement du tunnel se déduit de ce qui existe
# déjà : un exercice est calibré s'il porte un ancrage. Quitter l'application
# en cours de route et revenir reprend donc au bon endroit sans qu'un état ait
# eu besoin d'être maintenu — c'est la même règle que le reste de
# `progression/`, où le niveau se dérive de l'historique plutôt que de se
# stocker.


def mode_de_test(nom_exercice):
    """Mode sous lequel tester un exercice, déduit de l'unité de son barème.

    Un barème en secondes ne peut pas se valider par un comptage de
    répétitions : c'est la même contrainte que celle qui fait qu'un bloc en
    `chrono` échappe au moteur d'objectifs.
    """
    from session.circuit import MODE_MAINTIEN, MODE_REPETITIONS
    from progression.paliers import UNITE_SECONDES

    if unite(nom_exercice) == UNITE_SECONDES:
        return MODE_MAINTIEN
    return MODE_REPETITIONS


def exercices_a_calibrer(nom_seance):
    """Exercices de cette séance que le test d'accueil doit couvrir.

    Les échauffements en sont exclus (ils ne comptent nulle part) comme les
    mouvements sans barème (rien à calibrer). L'ordre est celui de la séance :
    c'est celui dans lequel la personne les rencontrera.
    """
    from session.seances import catalogue

    seance = catalogue().get(nom_seance)
    if seance is None:
        return []

    noms = []
    for bloc in seance["exercices"]:
        nom = bloc.get("nom") or bloc.get("exercice")
        if not est_suivi_par_le_moteur(nom) or nom in noms:
            continue
        # Un exercice dont le mode ne parle pas l'unité du barème ne peut pas
        # être calibré par ce test : on le laisse au moteur d'objectifs.
        if bloc.get("mode") != mode_de_test(nom):
            continue
        noms.append(nom)
    return noms


def etat_tunnel(nom_seance, ancrages):
    """Où en est le tunnel : ce qui est fait, ce qui reste, l'étape courante.

    `ancrages` est le dictionnaire de `recuperer_ancrages()` — passé en
    argument plutôt que relu ici, pour que la même lecture serve à toutes les
    étapes d'une page.
    """
    exercices = exercices_a_calibrer(nom_seance)
    faits = [nom for nom in exercices if nom in ancrages]
    restants = [nom for nom in exercices if nom not in ancrages]
    return {
        "seance": nom_seance,
        "exercices": exercices,
        "faits": faits,
        "restants": restants,
        "courant": restants[0] if restants else None,
        "termine": not restants,
        "position": len(faits) + 1,
        "total": len(exercices),
    }
