"""Programmes sportifs : une liste d'exigences par-dessus le moteur de niveaux.

Un programme ne stocke **aucune donnée de progression**. Il déclare, pour
chaque exercice, la performance à atteindre ; le niveau requis en est déduit,
le niveau acquis vient de l'historique, et l'écart se recalcule à chaque
lecture. Rien à migrer, rien à tenir à jour : supprimer un programme
n'efface aucune progression, en ajouter un n'en crée aucune.

**La conversion des prescriptions.** Un programme est écrit avec le matériel
de son auteur, pas avec le tien : « développé 4x12 à 28 kg » n'a pas de palier
correspondant si tes haltères s'arrêtent à 10 kg. C'est le **volume** qui sert
de traduction — une répétition à 20 kg en vaut deux à 10 kg —, exactement
l'invariant sur lequel le barème est construit. L'exigence devient donc « le
premier palier qui atteint ce volume », atteignable avec le matériel dont on
dispose réellement.

Une seule convention de charge, partout : **le poids d'un haltère**, celui
qu'on prend dans une main. Un programme se transcrit souvent depuis un tableau
qui annonce la charge totale, et l'éditeur a longtemps accepté cette
convention-là — mais faire coexister les deux rendait le même nombre ambigu
d'un écran à l'autre, au point qu'un curl à 20 kg pouvait désigner 10 kg par
bras ou 20. La conversion se fait donc à la lecture du tableau d'origine, pas
dans l'application.

Quand même le sommet du barème n'atteint pas ce volume, l'exigence est
déclarée **hors d'atteinte** plutôt que silencieusement plafonnée : cela veut
dire qu'il faut du matériel en plus, et c'est une information, pas une erreur.
"""

import json
from pathlib import Path

from progression.niveaux import etats_niveaux
from progression.paliers import (
    UNITE_SECONDES,
    est_suivi_par_le_moteur,
    niveau_pour_volume,
    palier,
    unite,
    volume,
)

#: Intitulé du champ de charge, défini une fois : écrit en dur dans le
#: template, il finirait par mentir le jour où la convention bougerait.
LIBELLE_CHARGE = "Charge par haltère (kg)"


FICHIER_PROGRAMMES_PERSONNALISES = Path(__file__).with_name(
    "programmes_personnalises.json"
)


def _exigence(seance, exercice, series, cible, poids=0):
    """Une ligne de programme, telle qu'elle est prescrite sur le papier.

    Les exigences sont une **liste plate** : chacune porte le libellé de la
    séance à laquelle elle appartient, et le regroupement se fait à
    l'affichage. Une structure imbriquée serait plus jolie à lire ici, mais
    beaucoup plus lourde à éditer depuis un formulaire — or un programme se
    modifie depuis le site.
    """
    return {
        "seance": seance,
        "exercice": exercice,
        "series": series,
        "cible": cible,
        "poids": poids,
    }


#: Aucun programme livré avec l'application : `programmes_personnalises.json`
#: est la **seule** source. Le dict a longtemps contenu « Road to TKT », dont
#: une copie divergente vivait aussi sur le disque — et comme le disque masque
#: le code, éditer les valeurs ici n'avait aucun effet au runtime, ce qui n'a
#: rien d'évident à la lecture. Une seule vérité vaut mieux qu'une règle de
#: précédence à retenir.
#:
#: Le mécanisme de masquage reste en place pour un futur programme livré : y
#: réintroduire une clé qui existe déjà sur le disque recréerait exactement le
#: piège qu'on vient de retirer. Conséquence directe du vidage : tout programme
#: est désormais `est_personnalise`, donc supprimable depuis le site — et cette
#: suppression est définitive, là où elle restaurait avant la version du code.
#:
#: Les mouvements unilatéraux sont deux exercices dans le catalogue : une
#: prescription « 4x12 par côté » devient donc deux exigences.
PROGRAMMES = {}


def _lire_programmes_personnalises():
    if not FICHIER_PROGRAMMES_PERSONNALISES.exists():
        return {}
    with FICHIER_PROGRAMMES_PERSONNALISES.open(encoding="utf-8") as fichier:
        return json.load(fichier)


def _ecrire_programmes_personnalises(donnees):
    with FICHIER_PROGRAMMES_PERSONNALISES.open("w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, ensure_ascii=False, indent=2)


def tous_les_programmes():
    """Programmes du code, écrasés par ceux du disque quand la clé existe.

    Même convention que `seances_personnalisees.json` : le fichier **masque**
    le catalogue Python, ce qui permet de modifier un programme livré avec
    l'app sans toucher au code.
    """
    return {**PROGRAMMES, **_lire_programmes_personnalises()}


def est_personnalise(cle):
    """Ce programme existe-t-il sur le disque ?

    Point d'entrée unique de la règle « ce programme est-il supprimable ? » :
    un programme livré dans le code et jamais modifié n'a rien à supprimer, et
    proposer de le faire mènerait à une erreur.
    """
    return cle in _lire_programmes_personnalises()


def _cale_sur_le_bareme(exercice, series, cible, poids):
    """Ramène une prescription sur le palier de même volume. Le barème fait foi.

    Une exigence qui ne correspond à aucun palier est indéfendable : elle
    demandait « 6x10 à 20 kg » quand l'haltère le plus lourd fait 18, ou une
    combinaison séries/répétitions que le barème ne propose à aucun niveau. On
    la remplace donc par le premier palier qui atteint son volume — même effort
    total, forme réalisable — plutôt que de la stocker telle quelle et de la
    traduire à chaque affichage.

    Traduire au lieu de caler laissait deux valeurs vivre côte à côte : celle
    qu'on relit dans l'éditeur et celle que la page de programme calcule. Elles
    n'étaient jamais les mêmes, et rien ne disait laquelle faisait autorité.

    Retourne le triplet inchangé si le barème ne sait pas répondre — mieux vaut
    conserver la saisie que la remplacer par rien.
    """
    niveau = niveau_pour_volume(exercice, volume(series, cible, poids))
    if niveau is None:
        return series, cible, poids
    cale = palier(exercice, niveau)
    if cale is None:
        return series, cible, poids
    return cale.series, cale.cible, cale.poids


def valider_programme(donnees):
    """Refuse un programme incohérent avant qu'il n'atteigne le disque.

    Mieux vaut un refus à l'enregistrement qu'une page de programme qui
    plante ou qui affiche des exigences impossibles à évaluer.
    """
    nom = (donnees.get("nom") or "").strip()
    if not nom:
        raise ValueError("Le nom du programme est requis")

    exigences = donnees.get("exigences") or []
    if not exigences:
        raise ValueError("Au moins une exigence est requise")

    propres = []
    for ligne in exigences:
        exercice = ligne.get("exercice")
        if not est_suivi_par_le_moteur(exercice):
            raise ValueError(f"{exercice or 'Exercice vide'} n'a pas de barème")
        try:
            series = int(ligne.get("series") or 0)
            cible = float(ligne.get("cible") or 0)
            poids = float(ligne.get("poids") or 0)
        except (TypeError, ValueError):
            raise ValueError(f"Valeurs invalides pour {exercice}")
        if series < 1 or cible <= 0:
            raise ValueError(f"Séries et cible doivent être positives ({exercice})")
        propres.append(
            _exigence(
                (ligne.get("seance") or "Séance").strip(),
                exercice,
                *_cale_sur_le_bareme(exercice, series, cible, poids),
            )
        )

    return {
        "nom": nom,
        "description": (donnees.get("description") or "").strip(),
        "exigences": propres,
        # Libellé de séance -> nom de la séance de l'application. Une **donnée**
        # du programme et non un calcul : c'est ce qui permet à un libellé
        # d'être joué par une séance qui ne porte pas son nom (« Push » joué par
        # `upper_push`) sans avoir à le redeviner à chaque lecture.
        # `synchroniser_seances` la remplit, l'éditeur ne la saisit pas.
        "seances": dict(donnees.get("seances") or {}),
    }


#: Repos par défaut d'une séance générée, en secondes. Deux valeurs qu'un
#: programme ne dit jamais — il prescrit un effort, pas un chronomètre — et
#: qu'on n'écrase donc plus une fois qu'elles ont été ajustées à la main.
REPOS_ENTRE_SERIES_PAR_DEFAUT = 60
REPOS_APRES_PAR_DEFAUT = 90


def enregistrer_programme(cle, donnees):
    """Crée ou remplace un programme personnalisé, et ses séances avec lui."""
    cle = (cle or "").strip()
    if not cle:
        raise ValueError("La clé du programme est requise")
    programmes = _lire_programmes_personnalises()
    programmes[cle] = valider_programme(donnees)
    _ecrire_programmes_personnalises(programmes)
    synchroniser_seances(cle)
    return cle


def _normaliser(texte):
    """Comparaison de noms tolérante aux accents, à la casse et aux séparateurs."""
    import unicodedata

    sans_accents = unicodedata.normalize("NFKD", texte or "")
    sans_accents = "".join(c for c in sans_accents if not unicodedata.combining(c))
    return "".join(c for c in sans_accents.lower() if c.isalnum())


#: Part des exercices d'un libellé qu'une séance doit contenir pour être
#: reconnue comme étant *cette* séance. La moitié : en dessous, deux séances qui
#: partagent un ou deux mouvements (des curls dans « bras » comme dans « Pull »)
#: seraient confondues, et le programme piloterait la mauvaise.
RECOUVREMENT_MINIMAL = 0.5


def seance_correspondante(libelle, exercices_attendus, catalogue_seances):
    """La séance existante qui *est* déjà ce libellé, ou None.

    Deux épreuves, de la plus sûre à la plus faible : le nom exact (aux accents
    et à la casse près), puis le meilleur **recouvrement d'exercices** au-dessus
    de `RECOUVREMENT_MINIMAL`.

    C'est l'ancienne `liaison_seances`, qui s'exécutait à *chaque affichage* et
    pouvait donc changer d'avis en silence — d'où le « via *upper_push* » qu'il
    fallait afficher partout pour la rendre vérifiable. Elle ne sert plus
    qu'**une fois**, au moment de lier ; le lien est ensuite écrit dans le
    programme, et c'est lui qui fait foi.
    """
    attendus = set(exercices_attendus)
    if not attendus:
        return None

    cible = _normaliser(libelle)
    for nom in catalogue_seances:
        if _normaliser(nom) == cible:
            return nom

    meilleur, meilleur_score = None, 0.0
    for nom, seance in catalogue_seances.items():
        contenu = {
            exercice.get("nom") or exercice.get("exercice")
            for exercice in seance.get("exercices", [])
        }
        score = len(attendus & contenu) / len(attendus)
        if score > meilleur_score:
            meilleur, meilleur_score = nom, score
    return meilleur if meilleur_score >= RECOUVREMENT_MINIMAL else None


def synchroniser_seances(cle):
    """Relie chaque libellé de séance du programme à une séance jouable.

    **Adopter d'abord, créer ensuite.** Un programme s'écrit presque toujours
    après coup, sur des séances qui existent déjà — montées avec leurs
    échauffements, leurs repos, leur entrelacement. En fabriquer des copies
    nommées d'après les libellés (« Push » à côté d'`upper_push`) laisserait
    deux séances jumelles dont une seule est complète, et c'est la vide que le
    programme lancerait. On cherche donc l'existante (`seance_correspondante`),
    et on ne crée que si rien ne correspond.

    **Une séance adoptée n'est jamais réécrite.** Ses blocs sont à elle : repos,
    échauffements, entrelacement et commentaires ne viennent pas du programme et
    ne doivent pas en dépendre. Un exercice exigé qu'elle ne contient pas lui est
    simplement **ajouté** ; rien n'est modifié ni retiré. Une séance créée, elle,
    est construite entièrement depuis les exigences.

    **Les cibles écrites ne sont pas jouées telles quelles**, et il ne faut pas
    les lire comme une prescription du jour : une exigence est l'objectif de
    *fin* de programme (« 6x22 »). Ces blocs n'étant pas marqués
    `cible_manuelle`, `appliquer_a_blocs` les réécrit au palier du moment à
    chaque chargement — le fichier ne fait autorité que sur la structure.
    """
    programmes = _lire_programmes_personnalises()
    programme = programmes.get(cle) or tous_les_programmes().get(cle)
    if programme is None:
        return {}

    # Import différé : `session.seances` consomme déjà ce module.
    from session.seances import (
        _lire_seances_personnalisees,
        catalogue,
        enregistrer_seance_personnalisee,
    )

    catalogue_seances = catalogue()
    stockees = _lire_seances_personnalisees()
    liens = dict(programme.get("seances") or {})

    for libelle in libelles_seances(programme):
        exigences = [
            exigence
            for exigence in programme["exigences"]
            if (exigence.get("seance") or "Séance") == libelle
        ]
        attendus = [exigence["exercice"] for exigence in exigences]

        # Un lien déjà posé fait foi tant que sa séance existe : c'est ce qui
        # rend l'association stable, et corrigeable à la main.
        nom_seance = liens.get(libelle)
        if nom_seance not in catalogue_seances:
            nom_seance = seance_correspondante(libelle, attendus, catalogue_seances)

        if nom_seance is None:
            nom_seance = libelle
            enregistrer_seance_personnalisee(
                nom_seance, [_bloc_depuis_exigence(e, {}) for e in exigences]
            )
        elif nom_seance in stockees:
            # Adoptée : on ne complète que ce qui manque. Une séance du
            # catalogue Python n'est pas touchée du tout — l'écrire créerait au
            # passage une surcharge personnalisée que personne n'a demandée.
            blocs = stockees[nom_seance]
            presents = {bloc.get("exercice") for bloc in blocs}
            manquants = [e for e in exigences if e["exercice"] not in presents]
            if manquants:
                enregistrer_seance_personnalisee(
                    nom_seance,
                    blocs + [_bloc_depuis_exigence(e, {}) for e in manquants],
                )

        liens[libelle] = nom_seance

    if cle in programmes and programmes[cle].get("seances") != liens:
        programmes[cle]["seances"] = liens
        _ecrire_programmes_personnalises(programmes)

    return liens


def _bloc_depuis_exigence(exigence, ancien):
    """Un bloc de séance depuis une exigence, en conservant l'existant.

    Le mode se déduit de l'unité du barème : un exercice mesuré en secondes ne
    peut pas recevoir une cible en répétitions, même contrainte que celle qui
    fait qu'un bloc en `chrono` échappe au moteur d'objectifs.
    """
    from session.circuit import MODE_MAINTIEN, MODE_REPETITIONS

    exercice = exigence["exercice"]
    en_secondes = unite(exercice) == UNITE_SECONDES
    return {
        **ancien,
        "exercice": exercice,
        "mode": MODE_MAINTIEN if en_secondes else MODE_REPETITIONS,
        "poids": exigence["poids"],
        "series": exigence["series"],
        "repetitions": 0 if en_secondes else exigence["cible"],
        "duree": exigence["cible"] if en_secondes else 0,
        "repos_entre_series": ancien.get(
            "repos_entre_series", REPOS_ENTRE_SERIES_PAR_DEFAUT
        ),
        "repos_apres": ancien.get("repos_apres", REPOS_APRES_PAR_DEFAUT),
        "commentaire": ancien.get("commentaire", ""),
    }


def supprimer_programme(cle):
    """Supprime un programme personnalisé.

    Les séances qu'il a créées ou adoptées lui survivent : elles sont jouables
    en dehors de lui, et un programme n'en est pas propriétaire.
    """
    programmes = _lire_programmes_personnalises()
    if cle not in programmes:
        raise KeyError(f"Programme inconnu : {cle}")
    del programmes[cle]
    _ecrire_programmes_personnalises(programmes)


def volume_exige(exigence):
    """Volume que la prescription représente, dans l'unité du barème."""
    return volume(exigence["series"], exigence["cible"], exigence["poids"])


def prescription(exigence):
    """La ligne telle qu'elle est écrite dans le programme, pour l'affichage."""
    nom = exigence["exercice"]
    suffixe = " s" if unite(nom) == UNITE_SECONDES else ""
    charge = f" à {exigence['poids']:g} kg" if exigence["poids"] else ""
    return f"{exigence['series']}x{exigence['cible']:g}{suffixe}{charge}"


def etat_exigence(exigence, niveaux):
    """Confronte une exigence au niveau acquis."""
    nom = exigence["exercice"]
    etat = niveaux.get(nom)
    acquis = etat["niveau"] if etat else None
    requis = niveau_pour_volume(nom, volume_exige(exigence))

    return {
        "exercice": nom,
        "seance": exigence.get("seance") or "Séance",
        "series": exigence["series"],
        "cible": exigence["cible"],
        "poids": exigence["poids"],
        "prescription": prescription(exigence),
        "volume": volume_exige(exigence),
        "niveau_requis": requis,
        "palier_requis": palier(nom, requis) if requis else None,
        "niveau_actuel": acquis,
        "actuel_resume": (
            etat["actuel"].resume() if etat and etat.get("actuel") else None
        ),
        # Hors d'atteinte : même le sommet du barème n'atteint pas ce volume.
        # Il faut du matériel en plus, aucun entraînement n'y suffira.
        "hors_atteinte": requis is None,
        "atteint": bool(requis and acquis and acquis >= requis),
        # Avancement vers l'exigence, borné à 100 %. Un niveau au-dessus du
        # requis ne « dépasse » pas la barre : l'exigence est simplement
        # remplie.
        "avancement": (
            min(100, round(100 * (acquis or 0) / requis)) if requis else 0
        ),
        "restant": max(0, requis - (acquis or 0)) if requis else None,
    }


def etat_programme(cle, seances=None, niveaux=None):
    """Avancement d'un programme, entièrement recalculé à la lecture."""
    programme = tous_les_programmes().get(cle)
    if programme is None:
        return None

    niveaux = etats_niveaux(seances) if niveaux is None else niveaux
    par_seance = {}
    exigences = []

    for ligne in programme.get("exigences", []):
        if not est_suivi_par_le_moteur(ligne.get("exercice")):
            continue
        etat = etat_exigence(ligne, niveaux)
        # Regroupement à l'affichage seulement : l'ordre des séances suit
        # l'ordre d'apparition des exigences, donc celui de l'éditeur.
        par_seance.setdefault(etat["seance"], []).append(etat)
        exigences.append(etat)

    atteintes = [etat for etat in exigences if etat["atteint"]]
    return {
        "cle": cle,
        "nom": programme["nom"],
        "description": programme.get("description", ""),
        "personnalise": est_personnalise(cle),
        "exigences_brutes": programme.get("exigences", []),
        "seances": par_seance,
        "total": len(exigences),
        "atteintes": len(atteintes),
        "hors_atteinte": len([e for e in exigences if e["hors_atteinte"]]),
        # Moyenne des avancements, et non part des exigences remplies : le
        # second reste à zéro tant qu'aucune n'est *entièrement* atteinte, ce
        # qui donne une barre vide alors que tout a avancé. Les deux chiffres
        # sont affichés côte à côte, ils ne disent pas la même chose.
        "pourcentage": (
            round(sum(etat["avancement"] for etat in exigences) / len(exigences))
            if exigences
            else 0
        ),
        "battu": bool(exigences) and len(atteintes) == len(exigences),
    }


def libelles_seances(programme):
    """Libellés de séance du programme, dans leur ordre d'apparition."""
    ordre = []
    for exigence in programme.get("exigences", []):
        libelle = exigence.get("seance") or "Séance"
        if libelle not in ordre:
            ordre.append(libelle)
    return ordre


def liaison_seances(cle, catalogue_seances=None):
    """Associe chaque libellé de séance du programme à une séance de l'app.

    Simple lecture du lien que `synchroniser_seances` a posé et écrit dans le
    programme. C'était auparavant une heuristique par recouvrement d'exercices,
    rejouée à chaque affichage : elle pouvait se tromper, obligeait l'accueil à
    annoncer la séance retenue (« via *upper_push* ») pour rester vérifiable, et
    rendait None dès que le recouvrement était nul. L'heuristique vit toujours
    dans `seance_correspondante`, mais ne sert plus qu'une fois, au moment de
    lier.

    Un programme jamais réenregistré depuis ce changement n'a pas encore ses
    liens : ils se posent au premier appel de `synchroniser_seances`.
    """
    programme = tous_les_programmes().get(cle)
    if programme is None:
        return {}

    if catalogue_seances is None:
        # Import différé : `session.seances` consomme déjà le moteur.
        from session.seances import catalogue

        catalogue_seances = catalogue()

    liens = programme.get("seances") or {}
    return {
        libelle: (
            liens.get(libelle) if liens.get(libelle) in catalogue_seances else None
        )
        for libelle in libelles_seances(programme)
    }


def prochaine_seance(cle, historique, catalogue_seances=None):
    """Séance du programme à enchaîner maintenant.

    Le programme se parcourt en boucle : la prochaine est celle qui suit la
    dernière effectivement réalisée. Une séance abandonnée ne compte pas — on
    la repropose plutôt que de la considérer faite.
    """
    programme = tous_les_programmes().get(cle)
    if programme is None:
        return None

    ordre = libelles_seances(programme)
    if not ordre:
        return None

    liaison = liaison_seances(cle, catalogue_seances)
    par_seance = {nom: libelle for libelle, nom in liaison.items() if nom}

    # `recuperer_historique` rend les séances de la plus récente à la plus
    # ancienne : la première qui appartient au programme est donc la dernière
    # faite.
    index = 0
    for seance in historique:
        if seance.get("statut") == "abandoned":
            continue
        libelle = par_seance.get(seance.get("nom"))
        if libelle in ordre:
            index = (ordre.index(libelle) + 1) % len(ordre)
            break

    libelle = ordre[index]
    return {
        "libelle": libelle,
        "seance": liaison.get(libelle),
        "position": index + 1,
        "total": len(ordre),
    }


def etats_programmes(seances=None):
    """Tous les programmes, en une seule lecture de l'historique."""
    niveaux = etats_niveaux(seances)
    return {
        cle: etat_programme(cle, niveaux=niveaux) for cle in tous_les_programmes()
    }
