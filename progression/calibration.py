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
conversion n'est exacte : l'estimation est volontairement prudente, et le
moteur d'objectifs la corrige dès la séance suivante.

**Le test se joue en séance, pas dans un tunnel d'accueil.** Il n'y a plus
d'écran préalable où passer chaque exercice l'un après l'autre : une séance
ordinaire rencontre un exercice dont elle ne sait rien
(`progression.objectifs.a_calibrer`), demande un maximum à la place de sa
cible, et pose l'ancrage à la fin de la série. L'avancement ne se stocke
toujours nulle part — un exercice est calibré s'il porte un ancrage.
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


#: Cible d'une série de test : un plafond qu'on n'atteint pas. Le test se
#: termine à la main (geste bras en X ou bouton « Série terminée »), jamais en
#: atteignant sa consigne — c'est ce qui en fait un maximum et non une série de
#: plus. Une valeur, plutôt qu'un mode dédié : tous les compteurs, l'audio et
#: l'affichage continuent de fonctionner sans connaître le test.
CIBLE_TEST = 999


def charge_de_test(nom_exercice):
    """La charge « relativement moyenne » sur laquelle tester un exercice.

    Le milieu de l'échelle réellement disponible, donc du matériel déclaré par
    le profil : tester à 2 kg ne dit rien de quelqu'un qui en soulève 10, et
    tester au maximum de la gamme décourage un débutant. Zéro pour un mouvement
    au poids du corps, dont l'échelle n'a qu'une valeur.
    """
    from progression.paliers import echelle_exercice

    echelle = echelle_exercice(nom_exercice)
    if not echelle:
        return 0
    return echelle[len(echelle) // 2]


def cloturer_test(nom_exercice, poids, maximum):
    """Traduit le maximum réalisé en ancrage de niveau, et le pose.

    Retourne le niveau ancré. Un maximum qui n'atteint pas le premier palier
    ancre quand même au palier 1 plutôt que de ne rien poser : sans ancrage
    l'exercice resterait « sans données » et redemanderait un test à chaque
    séance, ce qui est précisément la boucle qu'on veut éviter. Le moteur
    d'objectifs redescendra de lui-même si les séries échouent.
    """
    from historique.database import enregistrer_ancrage

    niveau = niveau_estime(nom_exercice, poids, maximum) or 1
    enregistrer_ancrage(nom_exercice, niveau, raison="Test en séance")
    return niveau


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
