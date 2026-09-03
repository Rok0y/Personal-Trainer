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

Le niveau d'un exercice n'est *pas* stocké : il se déduit de l'historique
(voir `progression/niveaux.py`). Ce module ne connaît que le barème.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Mapping

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
SERIES_MAX_PAR_DEFAUT = 6

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
SPECS = {
    # --- Haut du corps, poussée ---
    "Developpé couché altères": SpecProgression(
        series=4, cible_min=8, cible_max=15, poids_min=4
    ),
    # Poids du corps : sans axe de charge, la fourchette de répétitions est
    # allongée pour que le barème ne soit pas épuisé en une poignée de paliers.
    "Pompes": SpecProgression(series=4, cible_min=8, cible_max=25),
    "Développé épaule": SpecProgression(
        series=3, cible_min=8, cible_max=15, poids_min=4
    ),
    # Isolation légère : beaucoup de répétitions, et jamais très lourd.
    "Elevations latérales": SpecProgression(
        series=3, cible_min=10, cible_max=18, poids_min=2, poids_max=8
    ),
    # Lourd et court : la fourchette basse évite qu'une série de 7 à 14 kg
    # tombe hors barème alors qu'elle vaut plus que 15 répétitions à 6 kg.
    "Extension Triceps": SpecProgression(
        series=3, cible_min=6, cible_max=12, poids_min=8
    ),
    # --- Haut du corps, tirage ---
    "Rowing unilateral droit": SpecProgression(
        series=4, cible_min=6, cible_max=12, poids_min=8
    ),
    "Rowing unilateral gauche": SpecProgression(
        series=4, cible_min=6, cible_max=12, poids_min=8
    ),
    "Rowing penche": SpecProgression(series=3, cible_min=8, cible_max=15, poids_min=4),
    "Oiseau": SpecProgression(
        series=3, cible_min=10, cible_max=18, poids_min=2, poids_max=8
    ),
    "Curl biceps droit": SpecProgression(
        series=4, cible_min=8, cible_max=15, poids_min=4
    ),
    "Curl biceps gauche": SpecProgression(
        series=4, cible_min=8, cible_max=15, poids_min=4
    ),
    # --- Bas du corps ---
    # Les jambes encaissent plus de répétitions que le haut du corps, et les
    # haltères y sont vite le facteur limitant.
    "Squat": SpecProgression(series=4, cible_min=10, cible_max=20, poids_min=4),
    "Fente droite": SpecProgression(series=4, cible_min=8, cible_max=15, poids_min=4),
    "Fente gauche": SpecProgression(series=4, cible_min=8, cible_max=15, poids_min=4),
    "Souleve de terre roumain": SpecProgression(
        series=4, cible_min=8, cible_max=15, poids_min=4
    ),
    # --- Abdos et gainage ---
    "Crunches": SpecProgression(series=3, cible_min=12, cible_max=25),
    # Le gainage plafonne à deux minutes par série : au-delà, tenir plus
    # longtemps ne teste plus grand-chose, et c'est le nombre de séries qui
    # prend le relais.
    "Gainage planche": SpecProgression(
        series=3, cible_min=30, cible_max=120, pas=2, unite=UNITE_SECONDES
    ),
    "Gainage planche laterale droite": SpecProgression(
        series=1, cible_min=20, cible_max=120, pas=2, unite=UNITE_SECONDES
    ),
    "Gainage planche laterale gauche": SpecProgression(
        series=1, cible_min=20, cible_max=120, pas=2, unite=UNITE_SECONDES
    ),
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


def echelle_poids(nom_exercice):
    """Échelle du matériel : ce que les haltères disponibles permettent."""
    # Import différé : `session.seances` consommera le moteur de progression au
    # ticket T5, et un import au chargement du module créerait alors un cycle.
    from session.seances import nombre_halteres

    nb_halteres = nombre_halteres(nom_exercice)
    if nb_halteres >= 2:
        return ECHELLE_DEUX_HALTERES
    if nb_halteres == 1:
        return ECHELLE_UN_HALTERE
    return SANS_CHARGE


def echelle_exercice(nom_exercice):
    """Échelle du matériel restreinte à la fourchette utile de l'exercice.

    C'est elle que le barème utilise : une extension triceps ne commence pas à
    2 kg et une élévation latérale ne finira jamais à 18 kg.
    """
    echelle = echelle_poids(nom_exercice)
    spec = SPECS.get(nom_exercice)
    if spec is None:
        return echelle
    retenue = tuple(
        poids
        for poids in echelle
        if (spec.poids_min is None or poids >= spec.poids_min)
        and (spec.poids_max is None or poids <= spec.poids_max)
    )
    # Une fourchette qui ne retient rien (matériel absent, bornes trop
    # étroites) laisserait un barème vide : on garde alors le cran le plus bas.
    return retenue or echelle[:1]


def _premiere_cible(spec, volume_a_egaler, series, poids):
    """Plus petite cible du barème qui tient le volume déjà atteint.

    Retourne None si même `cible_max` n'y suffit pas : ce cran de poids est
    alors inatteignable sans régresser, et le barème l'ignore.
    """
    cible = spec.cible_min
    while volume(series, cible, poids) < volume_a_egaler:
        cible += spec.pas
        if cible > spec.cible_max:
            return None
    return cible


def _iterer_tranches(spec, echelle):
    """Tranches successives du barème : (séries, poids, cible de départ, longueur).

    Générateur **potentiellement infini** : sans `series_max`, on peut toujours
    ajouter une série. Tout appelant doit donc s'arrêter par lui-même.
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
            return
        longueur = (spec.cible_max - depart) // spec.pas + 1
        yield series, poids, depart, longueur
        volume_atteint = volume(series, spec.cible_max, poids)


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


def nombre_paliers(nom_exercice):
    """Nombre total de paliers d'un exercice, ou None si le barème est sans fin."""
    spec = SPECS.get(nom_exercice)
    if spec is None or spec.cible_max is None or spec.series_max is None:
        return None
    decoupage = tranches(nom_exercice, series_max=spec.series_max)
    return decoupage[-1]["niveau_max"] if decoupage else None


def niveau_pour_volume(nom_exercice, volume_cible):
    """Premier niveau dont le palier atteint ce volume, ou None s'il est hors
    d'atteinte du barème.

    Sert à traduire une prescription écrite avec un autre matériel que le sien
    (« 4x12 à 28 kg ») en un niveau atteignable avec le sien : c'est le volume
    qui fait foi, pas la charge, donc une répétition à 20 kg en vaut deux à
    10 kg. Retourner None est une information utile — cela signifie qu'aucune
    combinaison poids/séries/répétitions disponible n'y parvient.
    """
    total = nombre_paliers(nom_exercice)
    if total is None:
        return None
    # Le volume est croissant le long du barème (c'est son invariant), donc le
    # premier palier qui atteint la cible est le bon. Balayage linéaire : les
    # barèmes tiennent en quelques dizaines à quelques centaines de paliers.
    for niveau in range(1, total + 1):
        if palier(nom_exercice, niveau).volume >= volume_cible:
            return niveau
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
        if restant <= longueur:
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
            # Plus haute cible de la tranche que le volume réalisé couvre.
            atteinte = depart
            while (
                atteinte + spec.pas <= spec.cible_max
                and volume(series_tranche, atteinte + spec.pas, poids_tranche)
                <= volume_realise
            ):
                atteinte += spec.pas
            candidats.append(premier_niveau + (atteinte - depart) // spec.pas)

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
