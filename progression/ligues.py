"""Ligues, divisions et XP : la couche qui rend la progression lisible.

Le moteur sait déjà dire *où l'on en est* sur un exercice — un niveau, c'est-à-
dire l'index d'un palier dans `progression/paliers.py`. Mais « niveau 14 au
curl » ne se compare à rien et ne se fête pas. Ce module traduit ce nombre en
deux choses qui se lisent d'un coup d'œil : une **ligue** (Bronze → Maître),
chacune découpée en trois **divisions**, et de l'**XP** qui alimente un **niveau
général de profil**.

**Rien n'est stocké.** Comme tout `progression/`, ce module est une lecture : la
ligue d'un exercice se recalcule à chaque affichage depuis le niveau, qui se
recalcule lui-même depuis l'historique. Aucune table, aucune migration, aucun
recalcul à déclencher quand une séance est supprimée. C'est aussi ce qui rend le
jumeau JavaScript (`web/static/js/ligues.js`) possible : il n'y a pas de base à
lire, seulement des fonctions pures.

**La ligue vient du volume, pas du numéro de niveau.** Le rang se lit sur le
*volume* du palier atteint (séries x cible x poids), rapporté au volume du
palier 1 du même exercice. Ce n'est pas un détail de présentation : le volume ne
croît pas au même rythme d'un exercice à l'autre — une hausse d'haltère fait un
bond, une répétition de plus fait un pas — donc deux exercices au même niveau ne
sont pas à la même ligue. C'est précisément ce qu'on veut : le niveau dit la
position sur le barème, la ligue dit l'effort produit.

**Une seule table de seuils gouverne tout** (`SEUILS_VOLUME`), appliquée à un
volume *relatif*. Des seuils absolus auraient condamné la moitié du catalogue :
`paliers.volume` fait compter un mouvement au poids du corps pour 1 kg, donc
quatre séries de vingt pompes valent 80 quand quatre séries de douze curls à
12 kg valent 576. Rapporter chaque exercice à son propre palier 1 remet les deux
sur la même échelle sans écrire une table par mouvement — une table par exercice
se serait de toute façon désynchronisée du barème au premier réglage de spec.

**Distorsion connue et assumée** : à volume relatif égal, un exercice chargé
couvre une bien plus grande amplitude qu'un exercice au poids du corps (les
Pompes vont de 12 à 90 sur leurs paliers bornés, soit 7,5x ; le Curl biceps va
de 48 à 1080, soit 22,5x). Les mouvements au poids du corps plafonnent donc plus
bas en ligue. C'est la conséquence directe du `(poids or 1)` de `paliers.volume`,
et le correctif éventuel se ferait **ici** — jamais dans `paliers.volume`, qui
porte l'invariant du barème et dont dépend tout l'historique déjà interprété.
"""

from __future__ import annotations

from progression.paliers import est_suivi_par_le_moteur, palier
from progression.reglages import REGLAGES

#: Toutes les valeurs de ce module viennent de `progression/reglages.json` :
#: c'est la seule source, lue par le Python comme par le JavaScript, et elle
#: s'édite depuis `dev/baremes.html`. Ce qu'elles veulent dire est ici ; ce
#: qu'elles valent est là-bas.
_LIGUES = REGLAGES["ligues"]
_XP = REGLAGES["xp"]

#: Les six ligues, de la plus basse à la plus haute.
LIGUES = tuple(_LIGUES["ligues"])

#: Les trois divisions d'une ligue, dans l'ordre où on les traverse : on entre
#: dans une ligue par sa division III et on la quitte par sa division I. C'est
#: la convention des jeux compétitifs, où « I » se lit comme un premier rang.
DIVISIONS = tuple(_LIGUES["divisions"])

#: Dix-huit seuils de volume *relatif* — le volume du palier atteint divisé par
#: celui du palier 1 du même exercice. Progression géométrique de raison ~1,28 :
#: chaque cran demande environ 28 % de volume de plus que le précédent, ce qui
#: donne des montées régulières plutôt qu'un dernier cran interminable.
#:
#: Le premier seuil vaut 1.0 par construction : atteindre le palier 1 d'un
#: exercice, c'est entrer en Bronze III. En dessous il n'y a pas de « rang 0 »,
#: il n'y a pas de ligue du tout (voir `rang_pour_volume`).
SEUILS_VOLUME = tuple(_LIGUES["seuils_volume"])

#: Rang maximal, c'est-à-dire Maître I. Le barème n'ayant pas de fin (sa
#: dernière tranche est ouverte), le volume relatif n'a pas de borne
#: supérieure : le rang sature ici au lieu de déborder.
RANG_MAX = len(SEUILS_VOLUME)

#: XP rapportée par **chaque** niveau d'une tranche, sous la forme
#: (niveau à partir duquel la tranche s'applique, XP par niveau).
#:
#: Table ronde et réglable à dessein : c'est le rythme de la progression
#: générale, et on veut pouvoir le corriger en regardant la page de monitoring
#: plutôt qu'en dérivant une formule. Elle est croissante parce qu'un niveau
#: gagné haut sur le barème coûte bien plus d'entraînement qu'un niveau gagné
#: en bas, où deux répétitions suffisent.
PALIERS_XP = tuple(tuple(tranche) for tranche in _XP["paliers_xp"])

#: Coût du passage du niveau général 1 au niveau 2. Les suivants s'incrémentent
#: de `XP_INCREMENT_NIVEAU_GENERAL` : le cumul est donc quadratique, de plus en
#: plus lent, sans jamais devenir hors d'atteinte.
XP_BASE_NIVEAU_GENERAL = _XP["base_niveau_general"]
XP_INCREMENT_NIVEAU_GENERAL = _XP["increment_niveau_general"]


def volume_relatif(nom_exercice, niveau):
    """Volume du palier `niveau`, rapporté à celui du palier 1 du même exercice.

    C'est la grandeur sur laquelle se lisent les ligues. Rapporter au palier 1
    plutôt que de prendre le volume brut est ce qui rend les ligues comparables
    d'un exercice à l'autre malgré le `(poids or 1)` du calcul de volume.
    """
    if niveau is None or niveau < 1:
        return None
    atteint = palier(nom_exercice, niveau)
    depart = palier(nom_exercice, 1)
    if atteint is None or depart is None or not depart.volume:
        return None
    return atteint.volume / depart.volume


#: Bornes de ligue posées à la main, exercice par exercice, en **volume
#: absolu**. C'est la seule façon de placer un cran là où il veut dire quelque
#: chose : la table relative unique donnait un réglage sensé au curl — Or III à
#: 4x14 à 12 kg — et une absurdité aux pompes, où le même multiplicateur exige
#: 324 répétitions. La raison est arithmétique : passer de 2 à 12 kg multiplie
#: le volume par six sans changer une répétition, alors qu'au poids du corps le
#: seul levier *est* la répétition. Aucun réglage global ne rattrape ça.
SEUILS_PAR_EXERCICE = {
    nom: tuple(valeurs) for nom, valeurs in _LIGUES.get("seuils_par_exercice", {}).items()
}


def seuils_exercice(nom_exercice):
    """Les dix-huit bornes de ligue d'un exercice, en volume absolu.

    Explicites si l'exercice en porte, sinon dérivées de la table relative
    globale appliquée à son palier 1. **Ce repli n'est pas décoratif** : il
    garantit qu'un exercice ajouté au catalogue a des ligues dès le premier
    jour, au lieu de n'en avoir aucune jusqu'à ce que quelqu'un pense à le
    régler — un manque qui ne se signalerait nulle part.

    Tout le module raisonne ensuite en volume absolu : la table relative n'est
    qu'une façon de fabriquer des valeurs par défaut, pas un second chemin de
    calcul.
    """
    explicites = SEUILS_PAR_EXERCICE.get(nom_exercice)
    if explicites:
        return explicites
    depart = palier(nom_exercice, 1)
    if depart is None or not depart.volume:
        return None
    return tuple(seuil * depart.volume for seuil in SEUILS_VOLUME)


def rang_pour_volume(volume, seuils):
    """Rang de 1 à 18 pour un volume, ou None s'il n'atteint pas la première borne.

    `None` veut dire **pas de ligue**, ce qui n'est pas « rang 0 » : c'est la
    même distinction en trois situations que porte `niveaux.etat_niveau`, et un
    affichage ne doit pas la gommer en montrant un Bronze III qui n'a pas été
    gagné.
    """
    if volume is None or not seuils or volume < seuils[0]:
        return None
    rang = 1
    for index, seuil in enumerate(seuils):
        if volume >= seuil:
            rang = index + 1
    return rang


#: Ce qu'il faut retirer d'un nom de ligue pour en faire une clé utilisable
#: partout — nom de variable CSS, nom de classe, clé de dictionnaire. « Maître »
#: est le seul nom accentué aujourd'hui, mais la table évite d'avoir à s'en
#: souvenir le jour où il y en aura un second.
_SANS_ACCENT = str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc")


def cle_de_ligue(nom_ligue):
    """Clé d'une ligue : son nom en minuscules, sans accent ni espace."""
    return nom_ligue.lower().translate(_SANS_ACCENT).replace(" ", "-")


def ligue_pour_rang(rang):
    """Nom de ligue et division d'un rang de 1 à 18.

    Rend aussi deux champs que les écrans consomment tels quels : `cle`, pour
    nommer une variable CSS ou une classe, et `division_index` (0 pour III, 2
    pour I), qui gradue l'intensité de l'habillage. Les calculer ici plutôt que
    dans chaque interface évite d'écrire deux fois la même translittération
    d'accents — en Jinja et en JavaScript — et de la voir diverger au premier
    nom de ligue ajouté.
    """
    if rang is None or rang < 1:
        return None
    rang = min(rang, RANG_MAX)
    ligue = LIGUES[(rang - 1) // len(DIVISIONS)]
    index = (rang - 1) % len(DIVISIONS)
    return {
        "rang": rang,
        "ligue": ligue,
        "division": DIVISIONS[index],
        "libelle": f"{ligue} {DIVISIONS[index]}",
        "cle": cle_de_ligue(ligue),
        "division_index": index,
    }


def _avancement_dans_le_rang(volume, rang, seuils):
    """Part du cran parcourue, de 0 à 1 — vaut 1 au dernier rang, qui n'a pas de suite."""
    if rang is None or rang >= RANG_MAX:
        return 1.0
    plancher = seuils[rang - 1]
    plafond = seuils[rang]
    if plafond <= plancher:
        return 1.0
    return max(0.0, min(1.0, (volume - plancher) / (plafond - plancher)))


def ligue_exercice(nom_exercice, niveau):
    """Tout ce qu'un écran a besoin de savoir sur la ligue d'un exercice.

    Rend `None` quand il n'y a pas de ligue à montrer : exercice non suivi par
    le barème, ou niveau inconnu (hors barème). L'écran affiche alors « à
    tester », comme il le fait déjà pour le niveau.
    """
    if not est_suivi_par_le_moteur(nom_exercice):
        return None
    atteint = palier(nom_exercice, niveau) if niveau and niveau >= 1 else None
    seuils = seuils_exercice(nom_exercice)
    if atteint is None or not seuils:
        return None
    rang = rang_pour_volume(atteint.volume, seuils)
    if rang is None:
        return None

    return {
        **ligue_pour_rang(rang),
        "niveau": niveau,
        "volume": atteint.volume,
        "volume_relatif": volume_relatif(nom_exercice, niveau),
        "seuil_actuel": seuils[rang - 1],
        "seuil_suivant": seuils[rang] if rang < RANG_MAX else None,
        "avancement": _avancement_dans_le_rang(atteint.volume, rang, seuils),
        "maximum_atteint": rang == RANG_MAX,
    }


def rang_exercice(nom_exercice, niveau):
    """Rang de ligue d'un exercice à un niveau donné, ou None."""
    ligue = ligue_exercice(nom_exercice, niveau)
    return ligue["rang"] if ligue else None


def ligues_par_exercice(etats):
    """Ligue de chaque exercice, à partir du dict rendu par `etats_niveaux()`.

    Les exercices sans ligue y figurent avec la valeur None plutôt que d'être
    absents : un écran qui boucle sur le catalogue doit pouvoir distinguer
    « pas encore de ligue » de « exercice inconnu ».
    """
    return {
        nom: ligue_exercice(nom, (etat or {}).get("niveau"))
        for nom, etat in etats.items()
    }


def xp_du_niveau(niveau):
    """XP rapportée par le passage au niveau `niveau` d'un exercice."""
    if niveau is None or niveau < 1:
        return 0
    gain = PALIERS_XP[0][1]
    for depart, valeur in PALIERS_XP:
        if niveau >= depart:
            gain = valeur
    return gain


def xp_cumulee(niveau):
    """XP totale qu'un exercice rapporte une fois le niveau `niveau` atteint."""
    if niveau is None or niveau < 1:
        return 0
    return sum(xp_du_niveau(n) for n in range(1, niveau + 1))


def xp_totale(etats):
    """XP de tout un profil, sommée sur les exercices ayant un niveau."""
    return sum(xp_cumulee((etat or {}).get("niveau")) for etat in etats.values())


def cout_du_niveau_general(niveau):
    """XP à accumuler pour passer du niveau général `niveau` au suivant."""
    return XP_BASE_NIVEAU_GENERAL + XP_INCREMENT_NIVEAU_GENERAL * (max(niveau, 1) - 1)


def niveau_general(xp):
    """Niveau général du profil, et où l'on en est dans le niveau courant.

    On démarre au niveau 1 avec 0 XP : un profil vierge n'est pas « niveau 0 »,
    il est au début.

    **La ligue générale avance d'un cran par niveau général**, et non selon les
    seuils de volume des exercices. Les faire gouverner les deux échelles aurait
    été plus élégant, mais c'est faux : l'XP cumulée croît bien plus vite que le
    volume relatif, et la table calibrée sur l'une sature sur l'autre — mesuré,
    un profil tout à fait ordinaire (le catalogue entier au niveau 20) sortait
    déjà Maître III. Un cran par niveau place Maître I au niveau général 18,
    c'est-à-dire 17 000 XP, soit tout le catalogue autour du niveau 27.

    Tant qu'aucune XP n'a été gagnée il n'y a **pas de ligue** — pas un Bronze
    III offert. C'est la même distinction en trois situations que partout
    ailleurs : un profil qui n'a rien prouvé n'est pas classé.
    """
    # Le total est borné à zéro une fois pour toutes, et c'est *lui* qu'on
    # rend : un `xp or 0` laisserait passer une valeur négative, qui est
    # truthy en Python, et l'écran annoncerait « -50 XP ».
    total = max(xp or 0, 0)
    restant = total
    niveau = 1
    while restant >= cout_du_niveau_general(niveau):
        restant -= cout_du_niveau_general(niveau)
        niveau += 1

    cout = cout_du_niveau_general(niveau)
    rang = niveau if total > 0 else None
    return {
        "niveau": niveau,
        "xp": total,
        "xp_dans_le_niveau": restant,
        "xp_pour_le_suivant": cout,
        "avancement": restant / cout if cout else 0.0,
        "ligue": ligue_pour_rang(rang),
    }


def montees_de_ligue(montees_niveaux):
    """Parmi les montées de niveau, celles qui font franchir un cran de ligue.

    Prend le dict de `niveaux.montees_de_niveau()` — `{seance_id: {nom: ...}}` —
    et n'en garde que les franchissements. Une montée de niveau est fréquente ;
    une montée de ligue est un jalon, et c'est elle qui mérite d'être fêtée à
    l'écran de fin et jalonnée dans l'historique.
    """
    montees = {}
    for seance_id, exercices in montees_niveaux.items():
        for nom, montee in exercices.items():
            avant = rang_exercice(nom, montee.get("depuis"))
            apres = rang_exercice(nom, montee.get("vers"))
            if apres is None or apres == avant:
                continue
            montees.setdefault(seance_id, {})[nom] = {
                "depuis": ligue_pour_rang(avant),
                "vers": ligue_pour_rang(apres),
            }
    return montees


def xp_gagnee(montees_d_une_seance):
    """XP rapportée par une séance, d'après les niveaux qu'elle a fait franchir."""
    return sum(
        xp_cumulee(montee.get("vers")) - xp_cumulee(montee.get("depuis"))
        for montee in (montees_d_une_seance or {}).values()
    )
