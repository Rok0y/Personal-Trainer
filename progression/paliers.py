"""Table de paliers d'un exercice : la brique de base du moteur de progression.

Un palier est un triplet (poids, séries, cible) et un *niveau* en est l'index,
à partir de 1. La liste des paliers n'est jamais matérialisée : une spec peut
décrire un barème sans fin (`cible_max` à None), donc le barème est une
fonction du niveau, pas un tableau que l'on pourrait parcourir. Aucune spec
n'use de cette liberté aujourd'hui — le gainage a fini par recevoir un plafond
à deux minutes — mais le mécanisme la préserve.

**L'invariant du barème est le volume** (séries x cible x poids), qui ne
redescend jamais d'un palier au suivant. C'est ce qui décide où repart la cible
après une hausse de poids : passer de 3x15 à 8 kg (360 kg) à 3x8 à 10 kg
(240 kg) serait une régression d'un tiers déguisée en progression, alors que
3x12 à 10 kg (360 kg) tient le volume. La cible de départ d'un poids est donc la
plus petite qui égale au moins le volume déjà atteint — jamais `cible_min`,
sauf pour l'haltère le plus léger.

Le barème se lit donc comme une suite de tranches de **longueurs inégales** :
plus le poids monte, moins il reste de répétitions à gagner avant la bascule
suivante. C'est pourquoi ce module parcourt ses tranches au lieu de calculer un
index par arithmétique modulo.

L'ordre des bascules reste le même : la **cible** monte d'abord, puis le
**poids** (cible ramenée à son plancher de volume), puis les **séries**, une
fois l'haltère le plus lourd épuisé. Un exercice au poids du corps n'a qu'une
valeur de poids possible : sa deuxième roue ne tourne jamais et le barème se
réduit de lui-même à « cible puis séries », sans cas particulier dans le code.

**Le barème n'a pas de fin.** Une fois l'haltère le plus lourd et le plafond de
séries atteints, il ne reste qu'un axe : les répétitions, qui montent alors
sans plafond (la *tranche ouverte*, `longueur` à None dans `_iterer_tranches`).
Conséquence importante — aucun objectif n'est jamais « hors d'atteinte » : il
peut demander beaucoup de répétitions, mais son palier existe toujours. C'est
pourquoi il n'existe pas de « nombre total de paliers », seulement un
`dernier_palier_borne` qui repère où commence cette dernière tranche.

Le niveau d'un exercice n'est *pas* stocké : il se déduit de l'historique
(voir `progression/niveaux.py`). Ce module ne connaît que le barème.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Mapping

from progression.reglages import REGLAGES

UNITE_REPETITIONS = "repetitions"
UNITE_SECONDES = "secondes"

#: Les haltères réellement disponibles. Deux échelles, parce qu'une paire ne
#: monte pas aussi haut qu'un haltère seul.
ECHELLE_UN_HALTERE = (2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18)
ECHELLE_DEUX_HALTERES = (2, 3, 4, 5, 6, 8, 10)
#: Poids du corps : une seule valeur, donc la roue du poids ne tourne jamais.
SANS_CHARGE = (0,)

#: Plafond de séries commun à tous les exercices. Un barème qui monterait à
#: huit séries de pompes proposerait une séance que personne ne fait : passé ce
#: point, la progression relève d'une variante plus dure du mouvement, pas
#: d'une série de plus.
SERIES_MAX_PAR_DEFAUT = REGLAGES.get("series_max_par_defaut", 6)

#: Seules ces clés peuvent être surchargées sur un palier. Une surcharge
#: corrige un palier existant, elle n'en insère ni n'en supprime jamais :
#: sinon tous les niveaux au-dessus se décaleraient et l'historique déjà
#: interprété changerait de sens rétroactivement.
CLES_SURCHARGEABLES = ("poids", "series", "cible")


@dataclass(frozen=True)
class Palier:
    """Ce qu'il faut réaliser pour valider un niveau."""

    niveau: int
    poids: float
    series: int
    cible: int  # répétitions ou secondes, selon `unite`
    unite: str

    @property
    def volume(self):
        return volume(self.series, self.cible, self.poids)

    def resume(self):
        suffixe = " s" if self.unite == UNITE_SECONDES else ""
        charge = f" à {self.poids:g} kg" if self.poids else ""
        return f"{self.series}x{self.cible}{suffixe}{charge}"


@dataclass(frozen=True)
class SpecProgression:
    """Règle de progression d'un exercice, d'où découlent tous ses paliers.

    `cible_max` à None décrit un barème sans fin : ni le poids ni les séries
    n'entrent alors jamais en jeu, puisque la fourchette de cible n'est jamais
    épuisée, et la question du volume ne se pose pas — la cible ne redescend
    jamais.
    """

    series: int
    cible_min: int
    cible_max: int | None = None
    pas: int = 1
    unite: str = UNITE_REPETITIONS
    #: Au-delà de six séries dures, chaque série supplémentaire coûte du temps
    #: et de la fatigue pour un rendement qui s'effondre : le barème s'arrête
    #: là plutôt que de proposer des séances interminables.
    series_max: int | None = SERIES_MAX_PAR_DEFAUT
    #: Fourchette d'haltères réellement pertinente pour cet exercice. Sans
    #: elle, tout partirait de 2 kg — un curl à 2 kg n'est pas un niveau 1,
    #: c'est un échauffement, et le barème gaspillerait ses premiers paliers.
    poids_min: float | None = None
    poids_max: float | None = None
    surcharges: Mapping[int, Mapping[str, float]] = field(default_factory=dict)


#: Un barème par exercice, calé sur ce qui s'y pratique réellement. Les trois
#: réglages qui comptent sont la fourchette de poids (un curl ne commence pas à
#: 2 kg), la fourchette de répétitions (un triceps se travaille lourd et court,
#: une élévation latérale léger et long) et le nombre de séries. Des réglages
#: uniformes produiraient des niveaux incomparables et des premiers paliers
#: triviaux, gaspillés.
# **Le bas du barème appartient au débutant.** `cible_min` est le premier palier
# proposé à quelqu'un dont l'historique ne prouve rien : le fixer au niveau
# d'un pratiquant confirmé (4x8 pompes, 3x30 s de gainage) laisse un débutant
# « hors barème », c'est-à-dire sans objectif du tout. Sur les mouvements au
# poids du corps il est donc délibérément très bas.
#
# En baisser un est sans danger tant qu'on ne touche **ni `series` ni
# `poids_min`** : l'échelle de charge n'a qu'une valeur (SANS_CHARGE), la
# première tranche s'allonge donc par le bas et tous les paliers supérieurs se
# décalent d'une constante, sans changer de contenu. Toucher `series` ou
# `poids_min` fait au contraire recalculer le départ de chaque tranche par
# `_premiere_cible`, et rebat tout le barème.
# ===========================================================================
# CE QUE VEUT DIRE CHAQUE RÉGLAGE DE `reglages.json`
#
# Les valeurs ont déménagé dans `progression/reglages.json`, pour être
# réglables depuis `dev/baremes.html` — y compris sur la tablette, là où on
# les juge. Leur *raison*, elle, est restée ici : JSON ne prend pas de
# commentaires, et ces réglages en demandent. **Modifier un nombre là-bas sans
# avoir lu la note correspondante ici est la façon la plus simple de casser le
# barème en silence.**
#
# `cible_min` — **le bas du barème appartient au débutant.** C'est le premier
#   palier proposé à quelqu'un dont l'historique ne prouve rien : le fixer au
#   niveau d'un pratiquant confirmé laisse un débutant « hors barème »,
#   c'est-à-dire sans objectif du tout. Sur les mouvements au poids du corps il
#   est délibérément très bas.
#   En baisser un est sans danger tant qu'on ne touche **ni `series` ni
#   `poids_min`** : la première tranche s'allonge par le bas et tous les
#   paliers supérieurs se décalent d'une *constante*, sans changer de contenu.
#   Toucher `series` ou `poids_min` fait au contraire recalculer le départ de
#   chaque tranche par `_premiere_cible`, et rebat tout le barème.
#
# `cible_max` — fixe le volume de fin de tranche, donc l'entrée de la suivante.
#   C'est le réglage par lequel on ajuste un barème à un programme : le baisser
#   fait entrer les séries en jeu plus tôt. Piège du baisser : les séances déjà
#   enregistrées portent des cibles qui peuvent désormais le dépasser, et
#   `ressenti._cible_visee` ne sait alors plus les traduire — transitoire, la
#   première séance jouée sur le nouveau barème rétablit un repère valide.
#
# `poids_min` — un curl ne commence pas à 2 kg pour quelqu'un qui en a fait :
#   sans cette borne, le barème gaspille ses premiers paliers. Mais la
#   descendre est justement ce qui ouvre le barème aux débutants.
#   **Et `0` y veut dire autre chose que « très bas » : « la charge est
#   facultative ».** `echelle_poids` ajoute alors un cran sans charge *devant*
#   les haltères (`charge_facultative`), et `exercice_realisable` cesse
#   d'exiger de la fonte pour ce mouvement. C'est la seule déclaration de la
#   règle — ne pas en tenir une seconde à côté de `MATERIEL_EXERCICES`, qui
#   répond à une autre question : ce qu'il faut pour *charger* le mouvement,
#   pas s'il faut le charger. Réservé aux mouvements qui gardent un sens à
#   vide : un squat ou une fente, oui ; un curl ou un développé, non.
#   Le prix est celui de tout changement de `poids_min` — tous les paliers se
#   recalculent. Mesuré en ouvrant Squat et les deux fentes : les numéros de
#   niveau montent de 6 à 8 crans alors qu'aucune performance ne change de
#   valeur, exactement comme lors de la baisse de `cible_min`. Penser aussi à
#   la **première borne de ligue** de l'exercice, qui vaut souvent le volume
#   de l'ancien palier 1 et se retrouve deux crans trop haut.
#
# `poids_max` — le plafond de charge n'est pas celui du matériel. Sans lui, le
#   barème proposait des paliers jusqu'à l'haltère de 18 kg au curl unilatéral,
#   une charge qu'on ne curle pas d'un bras — et une exigence de programme s'y
#   calait, la rendant absurde.
#
# `series` / `series_max` — au-delà de six séries dures, chaque série
#   supplémentaire coûte du temps et de la fatigue pour un rendement qui
#   s'effondre ; la progression relève alors d'une variante plus dure.
#
# Réglages par famille de mouvement, qui expliquent les écarts entre exercices :
#   - **poids du corps** (pompes, squat sur chaise, crunches) : sans axe de
#     charge, la fourchette de répétitions est allongée, sinon le barème est
#     épuisé en une poignée de paliers ;
#   - **variantes assistées** (pompes inclinées, sur les genoux) : mêmes
#     fourchettes, départ encore plus bas — elles existent pour que quelqu'un
#     qui ne fait pas une pompe complète ait quand même une progression ;
#   - **isolation légère** (élévations latérales, oiseau) : beaucoup de
#     répétitions, jamais très lourd ;
#   - **lourd et court** (extension triceps) : fourchette basse des deux côtés,
#     pour qu'une série de 7 à 14 kg reste dans le barème plutôt que d'en
#     sortir alors qu'elle vaut plus que 15 à 6 kg ;
#   - **jambes** : elles encaissent plus de répétitions, et les haltères y sont
#     vite le facteur limitant ;
#   - **gainage** : plafonné à une minute par série — au-delà, tenir plus
#     longtemps ne teste plus grand-chose, et c'est le nombre de séries qui
#     prend le relais.
# ===========================================================================


def _spec_depuis_le_fichier(champs):
    """Un `SpecProgression` depuis une entrée de `reglages.json`.

    Les clés de `surcharges` redeviennent des entiers : JSON n'a que des clés
    de texte, alors que le barème indexe ses surcharges par numéro de niveau.
    C'est le seul endroit où la traduction se fait — le jumeau JavaScript, lui,
    interroge la table avec `String(niveau)`.
    """
    champs = dict(champs)
    surcharges = champs.pop("surcharges", None) or {}
    return SpecProgression(
        **champs,
        surcharges={int(niveau): valeurs for niveau, valeurs in surcharges.items()},
    )


#: Un barème par exercice, calé sur ce qui s'y pratique réellement — et lu
#: depuis `reglages.json`, qui est la seule source des deux côtés du portage.
#: Les trois réglages qui comptent restent les mêmes : la fourchette de poids
#: (un curl ne commence pas à 2 kg pour un pratiquant confirmé), la fourchette
#: de répétitions (un triceps se travaille lourd et court, une élévation
#: latérale léger et long) et le nombre de séries. Des réglages uniformes
#: produiraient des niveaux incomparables.
SPECS = {
    nom: _spec_depuis_le_fichier(champs)
    for nom, champs in REGLAGES["specs"].items()
}


def volume(series, cible, poids):
    """Charge totale déplacée sur l'ensemble des séries.

    Le poids du corps compte pour 1 kg : seules les répétitions font alors la
    différence, et le barème n'a pas besoin d'un cas particulier pour éviter
    de tout multiplier par zéro.
    """
    return series * cible * (poids or 1)


def est_suivi_par_le_moteur(nom_exercice):
    """Point d'entrée unique de la règle « cet exercice a-t-il des paliers ? ».

    Les échauffements n'en ont pas (ils ne comptent nulle part), et l'AMRAP est
    laissé de côté pour l'instant : son objectif est un plancher, pas une cible.
    """
    return nom_exercice in SPECS


def exercices_suivis():
    """Noms des exercices dotés d'un barème."""
    return tuple(SPECS)


def specification(nom_exercice):
    return SPECS.get(nom_exercice)


def unite(nom_exercice):
    spec = SPECS.get(nom_exercice)
    return spec.unite if spec else None


def charge_facultative(nom_exercice):
    """La charge est-elle facultative sur ce mouvement chargeable ?

    Point d'entrée unique de la règle, et elle se déclare **dans la spec** :
    `poids_min` à 0 veut dire « ce barème commence au poids du corps ». Une
    seconde liste tenue à côté de `MATERIEL_EXERCICES` finirait par en diverger
    sans que rien ne le signale — c'est ce que la duplication de `PROGRAMMES` a
    déjà coûté au projet.

    La question n'est pas « quel matériel ce mouvement demande » : ça, c'est
    `MATERIEL_EXERCICES`, et un squat réclame toujours deux haltères dès qu'on
    le charge. C'est « en dessous de quelle charge le mouvement cesse d'avoir
    un sens », ce que `poids_min` dit déjà pour toutes ses autres valeurs — un
    curl à vide n'est pas un curl, un squat à vide en est un.

    Le nom dit « facultative » et non « au poids du corps » parce que la
    fonction ne répond que des mouvements **chargeables**. Les pompes ou le
    gainage rendent False alors qu'ils se font évidemment sans charge : ils
    n'ont aucune échelle de poids (`nombre_halteres` vaut 0), donc ni
    `echelle_poids` ni `exercice_realisable` ne l'interrogent à leur sujet —
    les deux ont déjà répondu. Un prédicat qui ne couvre qu'une moitié des cas
    doit le dire dans son nom, sinon c'est le lecteur suivant qui paie.
    """
    spec = SPECS.get(nom_exercice)
    return spec is not None and spec.poids_min == 0


def echelle_poids(nom_exercice):
    """Échelle du matériel : ce que les haltères du profil connecté permettent.

    Les deux constantes ci-dessus ne sont plus que la gamme de référence : le
    stock réellement possédé est déclaré par profil (`core.materiel`) et les
    deux échelles s'en dérivent. Un profil qui n'a rien déclaré retrouve
    exactement ces constantes, donc son barème ne bouge pas.
    """
    # Import différé : `session.seances` consomme le moteur de progression, et
    # un import au chargement du module fermerait le cycle.
    from core.materiel import echelle_disponible
    from session.seances import nombre_halteres

    nb_halteres = nombre_halteres(nom_exercice)
    if nb_halteres <= 0:
        return SANS_CHARGE

    echelle = echelle_disponible(nb_halteres)
    # Le poids du corps est un **cran du barème**, pas une absence de matériel :
    # un squat à vide est un vrai palier — celui par lequel on commence — et il
    # se place avant le premier haltère au lieu de manquer. Sans ce cran, le
    # barème n'a aucun palier jouable par qui n'a pas de fonte, et le moteur
    # n'a donc rien à lui proposer.
    if charge_facultative(nom_exercice):
        return SANS_CHARGE + echelle
    return echelle


def _dans_la_fourchette(echelle, spec):
    return tuple(
        poids
        for poids in echelle
        if (spec.poids_min is None or poids >= spec.poids_min)
        and (spec.poids_max is None or poids <= spec.poids_max)
    )


def echelle_exercice(nom_exercice):
    """Échelle du matériel restreinte à la fourchette utile de l'exercice.

    C'est elle que le barème utilise : une extension triceps ne commence pas à
    2 kg et une élévation latérale ne finira jamais à 18 kg.

    **C'est ici que vit le garde « le barème reste calculable pour tout le
    monde »**, et il y vit parce que c'est le seul endroit qui sache si
    l'exercice a un cran au poids du corps. `echelle_disponible` rend
    honnêtement un tuple vide quand le profil n'a pas de quoi charger ; un
    squat retombe alors sur `(0,)`, qui est sa **vraie** échelle et non un
    repli, tandis qu'un curl retombe sur la gamme supposée, faute de mieux et
    parce qu'un barème vide casserait jusqu'à l'écran des records.

    Le repli portait auparavant sur l'inventaire (`possedes or POIDS_SUPPOSES`),
    ce qui rendait la gamme entière à qui ne possède rien — et faisait tester
    le squat à 8 kg à quelqu'un qui n'a pas d'haltères. *Un repli placé trop
    tôt répond à la place de celui qui savait.*
    """
    echelle = echelle_poids(nom_exercice)
    spec = SPECS.get(nom_exercice)
    if spec is None:
        return echelle or _gamme_supposee()

    retenue = _dans_la_fourchette(echelle, spec)
    if retenue:
        return retenue
    # Des bornes trop étroites sur une échelle non vide : on garde le cran le
    # plus bas plutôt que de laisser un barème sans aucun palier.
    if echelle:
        return echelle[:1]
    # Rien à charger, et pas de cran au poids du corps (un curl, un développé).
    # La gamme supposée garde le barème calculable et les niveaux comparables
    # d'un profil à l'autre ; `exercice_realisable` reste seul juge de savoir
    # si la personne peut réellement faire ce mouvement.
    supposee = _gamme_supposee()
    return _dans_la_fourchette(supposee, spec) or supposee[:1]


def _gamme_supposee():
    """La gamme d'haltères qu'on suppose à qui n'a rien déclaré."""
    from core.materiel import POIDS_SUPPOSES

    return POIDS_SUPPOSES


def _premiere_cible(spec, volume_a_egaler, series, poids, plafonnee=True):
    """Plus petite cible du barème qui tient le volume déjà atteint.

    Retourne None si même `cible_max` n'y suffit pas : ce cran de poids est
    alors inatteignable sans régresser, et le barème l'ignore. `plafonnee` à
    False lève cette limite, pour la tranche ouverte où les répétitions ne sont
    plus bornées.
    """
    cible = spec.cible_min
    while volume(series, cible, poids) < volume_a_egaler:
        cible += spec.pas
        if plafonnee and cible > spec.cible_max:
            return None
    return cible


def _iterer_tranches(spec, echelle):
    """Tranches successives du barème : (séries, poids, cible de départ, longueur).

    Une `longueur` à None marque la **tranche ouverte** : la dernière, celle où
    tout est épuisé sauf les répétitions, qui montent alors sans plafond.

    Générateur **infini** : il se termine toujours par cette tranche ouverte, à
    laquelle tout appelant doit s'arrêter par lui-même.
    """
    volume_atteint = 0

    # Le poids monte, les séries ne bougent pas.
    for poids in echelle:
        depart = _premiere_cible(spec, volume_atteint, spec.series, poids)
        if depart is None:
            continue
        longueur = (spec.cible_max - depart) // spec.pas + 1
        yield spec.series, poids, depart, longueur
        volume_atteint = volume(spec.series, spec.cible_max, poids)

    # Le poids est épuisé : on reste sur l'haltère le plus lourd et c'est le
    # nombre de séries qui augmente. Repartir du poids le plus léger serait un
    # recul, pas une progression.
    poids = echelle[-1]
    series = spec.series
    while spec.series_max is None or series < spec.series_max:
        series += 1
        depart = _premiere_cible(spec, volume_atteint, series, poids)
        if depart is None:
            break
        longueur = (spec.cible_max - depart) // spec.pas + 1
        yield series, poids, depart, longueur
        volume_atteint = volume(series, spec.cible_max, poids)

    # Tout est épuisé : le plafond de répétitions saute, et elles montent
    # indéfiniment. C'est ce qui garantit qu'aucun objectif n'est jamais hors
    # d'atteinte — il demandera beaucoup de répétitions, mais il existe.
    depart = _premiere_cible(spec, volume_atteint, series, poids, plafonnee=False)
    yield series, poids, depart, None


def tranches(nom_exercice, series_max=None):
    """Découpage lisible du barème, pour l'affichage et l'outillage.

    `series_max` borne le parcours : indispensable tant qu'une spec n'en
    déclare pas, puisque les tranches sont un générateur infini. Un barème sans
    fin (`cible_max` à None) n'a pas de tranche du tout : sa cible ne redescend
    jamais, donc rien ne le découpe.
    """
    spec = SPECS.get(nom_exercice)
    if spec is None or spec.cible_max is None:
        return []

    plafond = series_max if series_max is not None else spec.series
    resultat = []
    premier_niveau = 1
    for series, poids, depart, longueur in _iterer_tranches(
        spec, echelle_exercice(nom_exercice)
    ):
        if series > plafond:
            break
        if longueur is None:
            # Tranche ouverte : ni fin, ni volume maximum. On la décrit quand
            # même, c'est là que le barème se termine réellement.
            resultat.append(
                {
                    "series": series,
                    "poids": poids,
                    "cible_min": depart,
                    "cible_max": None,
                    "niveau_min": premier_niveau,
                    "niveau_max": None,
                    "volume_max": None,
                }
            )
            break
        resultat.append(
            {
                "series": series,
                "poids": poids,
                "cible_min": depart,
                "cible_max": spec.cible_max,
                "niveau_min": premier_niveau,
                "niveau_max": premier_niveau + longueur - 1,
                "volume_max": volume(series, spec.cible_max, poids),
            }
        )
        premier_niveau += longueur
    return resultat


def dernier_palier_borne(nom_exercice):
    """Dernier niveau avant la tranche ouverte, où les répétitions s'envolent.

    Le barème n'a pas de fin — passé le poids maximum et le plafond de séries,
    les répétitions montent indéfiniment —, donc « nombre total de paliers »
    n'a pas de sens. Ce repère sert seulement à l'affichage et à l'outillage.
    """
    spec = SPECS.get(nom_exercice)
    if spec is None or spec.cible_max is None:
        return None
    bornees = [
        tranche
        for tranche in tranches(nom_exercice, series_max=spec.series_max)
        if tranche["niveau_max"] is not None
    ]
    return bornees[-1]["niveau_max"] if bornees else None


def niveau_pour_volume(nom_exercice, volume_cible):
    """Premier niveau dont le palier atteint ce volume.

    Sert à traduire une prescription écrite avec un autre matériel que le sien
    (« 4x12 à 28 kg ») en un niveau atteignable avec le sien : c'est le volume
    qui fait foi, pas la charge, donc une répétition à 20 kg en vaut deux à
    10 kg. Grâce à la tranche ouverte, un volume est **toujours** atteignable —
    il demandera peut-être beaucoup de répétitions, mais le palier existe.
    """
    spec = SPECS.get(nom_exercice)
    if spec is None:
        return None

    if spec.cible_max is None:
        # Barème déjà linéaire et sans fin : pas de tranches à parcourir.
        # `_iterer_tranches` planterait sur son `cible_max` absent.
        echelle = echelle_exercice(nom_exercice)
        cible = spec.cible_min
        while volume(spec.series, cible, echelle[0]) < volume_cible:
            cible += spec.pas
        return (cible - spec.cible_min) // spec.pas + 1

    premier_niveau = 1
    for series, poids, depart, longueur in _iterer_tranches(
        spec, echelle_exercice(nom_exercice)
    ):
        dernier = (
            None if longueur is None else depart + (longueur - 1) * spec.pas
        )
        # Le volume croît le long du barème : la bonne tranche est la première
        # dont la cible haute suffit — et la tranche ouverte suffit toujours.
        if dernier is None or volume(series, dernier, poids) >= volume_cible:
            cible = depart
            while volume(series, cible, poids) < volume_cible:
                cible += spec.pas
            return premier_niveau + (cible - depart) // spec.pas
        premier_niveau += longueur
    return None


def _palier_genere(spec, echelle, niveau):
    if spec.cible_max is None:
        return Palier(
            niveau=niveau,
            poids=echelle[0],
            series=spec.series,
            cible=spec.cible_min + (niveau - 1) * spec.pas,
            unite=spec.unite,
        )

    restant = niveau
    for series, poids, depart, longueur in _iterer_tranches(spec, echelle):
        # `longueur` à None : tranche ouverte, elle contient tous les niveaux
        # restants quels qu'ils soient.
        if longueur is None or restant <= longueur:
            return Palier(
                niveau=niveau,
                poids=poids,
                series=series,
                cible=depart + (restant - 1) * spec.pas,
                unite=spec.unite,
            )
        restant -= longueur
    return None


def _appliquer_surcharge(spec, palier_genere):
    surcharge = spec.surcharges.get(palier_genere.niveau)
    if not surcharge:
        return palier_genere
    inconnues = set(surcharge) - set(CLES_SURCHARGEABLES)
    if inconnues:
        raise ValueError(f"Surcharge de palier invalide : {sorted(inconnues)}")
    return replace(palier_genere, **surcharge)


def palier(nom_exercice, niveau):
    """Le palier d'un niveau, ou None si le barème ne va pas jusque-là."""
    spec = SPECS.get(nom_exercice)
    if spec is None or niveau < 1:
        return None
    genere = _palier_genere(spec, echelle_exercice(nom_exercice), niveau)
    if genere is None:
        return None
    return _appliquer_surcharge(spec, genere)


def _valide(palier_teste, poids, series, cible):
    """Une performance valide un palier si elle est **au moins aussi lourde et
    au moins aussi volumineuse**.

    Le volume prime, mais pas seul : exiger en plus `poids >= palier.poids`
    empêche une longue série légère de valider un palier lourd. À poids égal,
    en revanche, la répartition séries/répétitions est libre — c'est ce qui
    permet à un travail lourd et court (3x7 à 14 kg, 294 kg) de valider un
    palier plus léger et plus long (3x12 à 8 kg, 288 kg), que la comparaison
    répétition à répétition rejetait à tort.
    """
    if palier_teste is None:
        return False
    return (
        poids >= palier_teste.poids
        and volume(series, cible, poids) >= palier_teste.volume
    )


def _niveaux_candidats(spec, echelle, poids, series, cible):
    """Niveaux qu'une performance pourrait valider, sans les vérifier.

    Inutile de balayer tout le barème (il peut être infini) : dans chaque
    tranche, un seul niveau est intéressant — celui de la meilleure cible
    tenue. Le parcours s'arrête dès que les tranches réclament plus de séries
    que la performance n'en compte.
    """
    if poids < echelle[0] or cible <= 0:
        return []

    if spec.cible_max is None:
        if cible < spec.cible_min:
            return []
        # `int()` explicite : une durée est un REAL en base, et sans cette
        # conversion le niveau lui-même sortirait en flottant.
        return [int((cible - spec.cible_min) // spec.pas) + 1]

    volume_realise = volume(series, cible, poids)
    candidats = []
    premier_niveau = 1
    for series_tranche, poids_tranche, depart, longueur in _iterer_tranches(
        spec, echelle
    ):
        # Le volume d'entrée d'une tranche ne redescend jamais (c'est
        # l'invariant du barème) : dès qu'il dépasse la performance, aucune
        # tranche suivante ne pourra être validée. C'est aussi ce qui fait
        # terminer la boucle sur un générateur infini.
        if volume(series_tranche, depart, poids_tranche) > volume_realise:
            break

        if poids_tranche <= poids:
            # Plus haute cible de la tranche que le volume réalisé couvre. La
            # tranche ouverte n'a pas de plafond de cible, mais la boucle reste
            # bornée par le volume réalisé.
            atteinte = depart
            while (
                longueur is None or atteinte + spec.pas <= spec.cible_max
            ) and volume(
                series_tranche, atteinte + spec.pas, poids_tranche
            ) <= volume_realise:
                atteinte += spec.pas
            candidats.append(premier_niveau + (atteinte - depart) // spec.pas)

        if longueur is None:
            break
        premier_niveau += longueur

    return candidats


def niveau_pour(nom_exercice, poids, series, cible):
    """Le plus haut niveau qu'une performance valide, ou None si aucun.

    None signifie « hors barème » — la performance n'atteint même pas le
    palier de base — ce qui est distinct du niveau 1.
    """
    spec = SPECS.get(nom_exercice)
    if spec is None:
        return None

    echelle = echelle_exercice(nom_exercice)
    candidats = _niveaux_candidats(spec, echelle, poids, series, cible)
    # Une surcharge peut placer un palier n'importe où : on les repasse tous,
    # ils sont peu nombreux.
    candidats += list(spec.surcharges)

    valides = [
        niveau
        for niveau in candidats
        if _valide(palier(nom_exercice, niveau), poids, series, cible)
    ]
    return max(valides) if valides else None


def signature(nom_exercice):
    """Empreinte du barème d'un exercice, pour invalider un cache de niveaux.

    Modifier une spec (ou ajouter un haltère) décale la numérotation des
    niveaux : un niveau mis en cache sous l'ancien barème deviendrait un
    mensonge. La signature couvre donc la spec *et* l'échelle de poids.
    """
    spec = SPECS.get(nom_exercice)
    if spec is None:
        return None
    empreinte = json.dumps(
        {
            "series": spec.series,
            "cible_min": spec.cible_min,
            "cible_max": spec.cible_max,
            "pas": spec.pas,
            "unite": spec.unite,
            "series_max": spec.series_max,
            "surcharges": {
                str(niveau): dict(sorted(valeurs.items()))
                for niveau, valeurs in sorted(spec.surcharges.items())
            },
            "echelle": list(echelle_exercice(nom_exercice)),
        },
        sort_keys=True,
    )
    return hashlib.sha256(empreinte.encode("utf-8")).hexdigest()[:12]
