"""Prepare les pages statiques : catalogues exportes et sons rapatries.

La demo est volontairement **statique** — aucun Flask, aucun profil, aucune
base. Elle peut donc etre deposee telle quelle sur un hebergeur gratuit, avec
une adresse stable, sans que le PC de personne reste allume ; c'est ce qui
rend des testeurs autonomes.

Le catalogue reste pour autant la propriete du Python : il est *exporte* ici,
jamais recopie a la main. Un exercice ajoute a CATALOGUE_EXERCICES apparait
dans la demo a la prochaine execution, avec sa fiche.

    python -m scripts.preparer_demo
"""

import ast
import json
import shutil
from pathlib import Path

from audio import annonces
from core.materiel import POIDS_REFERENCE
from session.seances import (
    CATALOGUE_EXERCICES,
    _lire_seances_personnalisees,
    catalogue_mouvements,
)

RACINE = Path(__file__).resolve().parent.parent
DEMO = RACINE / "web" / "static" / "demo"
#: Donnees partagees par la demo et l'application. Un dossier a part parce
#: qu'elles ne servent pas la meme page et n'ont pas le meme contenu : la demo
#: ne liste que les exercices testables, l'application a besoin de *tous* les
#: mouvements, echauffements compris.
DONNEES = RACINE / "web" / "static" / "donnees"
SONS_SOURCE = RACINE / "audio" / "Fichiers"

SONS_DEMO = ["bip"] + [str(n) for n in range(1, 21)]
"""Le socle strictement necessaire : le bip et les nombres annonces. La
bibliotheque s'arrete a 20, et la demo se tait au-dela plutot que d'inventer.
Les annonces combinatoires (`prochain_*`) ne servent qu'en seance complete."""


def exporter_catalogue():
    """Les exercices que la demo sait faire : ceux qui analysent la pose.

    Le nom de la fonction de detection est exporte pour que le JS retrouve sa
    jumelle dans detections.js — les deux portent le meme nom, c'est ce qui
    dispense d'une table de correspondance.
    """
    exercices = []
    sans_detection = []

    for nom, exercice in CATALOGUE_EXERCICES.items():
        if exercice.detection is None:
            sans_detection.append(nom)
            continue
        fiche = exercice.fiche()
        fiche["detection"] = exercice.detection.__name__
        # Les vérifications de forme temps réel, exportées par *nom* comme la
        # détection. Elles ne passent pas par `Exercice.fiche()`, qui décrit ce
        # qu'on affiche d'un mouvement : `erreurs` est une liste de fonctions
        # qui s'exécutent, à ne pas confondre avec `erreurs_frequentes`, qui
        # est de la pédagogie écrite. Six exercices sur vingt-trois en ont.
        fiche["erreurs"] = [verifier.__name__ for verifier in exercice.erreurs]
        exercices.append(fiche)

    exercices.sort(key=lambda f: f["nom"])
    return exercices, sans_detection


def decrire(nom, mouvement):
    """Un mouvement sous la forme que le JavaScript sait relire.

    Les fonctions sont exportees par **nom** : `detections.js` porte les
    memes, c'est ce qui dispense d'une table de correspondance qui
    deriverait. `detection` peut valoir None — un echauffement guide sans
    analyse de pose, et `circuit.js` le sait.
    """
    from session.seances import CATALOGUE_ECHAUFFEMENTS, materiel_exercice

    fiche = mouvement.fiche()
    fiche["detection"] = (
        None if mouvement.detection is None else mouvement.detection.__name__
    )
    fiche["erreurs"] = [verifier.__name__ for verifier in mouvement.erreurs]
    # Les deux champs que `fiche_mouvement` ajoute cote Flask, et dont les
    # fiches de l'application ont besoin : quel materiel il faut, et si le
    # mouvement compte quelque part. Un echauffement n'a ni niveau, ni record,
    # ni ligne d'historique — l'ecran doit pouvoir le dire.
    fiche["materiel"] = materiel_exercice(nom, 0)
    fiche["est_echauffement"] = nom in CATALOGUE_ECHAUFFEMENTS
    return fiche


def exporter_programmes():
    """Les programmes, tels quels, pour l'application du navigateur.

    Aucune transformation : le fichier est deja la seule source de verite
    (`PROGRAMMES` est vide cote code), et l'application n'en porte que la
    **lecture** — l'editeur reste sur le poste fixe, comme pour les seances.
    Exporter la structure brute plutot qu'un etat calcule est indispensable :
    l'avancement depend de l'historique *local* et des halteres declares sur
    l'appareil, donc il se recalcule la-bas, jamais ici.

    Import differe comme celui des baremes : ce module n'a que des imports de
    bibliotheque standard en tete de fichier, mais le garder hors du niveau
    module rend visible que l'export ne tire rien de lourd — c'est ce qui
    permet au workflow de deploiement de n'installer que numpy.
    """
    from progression.programmes import tous_les_programmes

    return tous_les_programmes()


def exporter_baremes():
    """Les baremes de progression, exportes tels que le Python les definit.

    `progression/paliers.py` n'a que des imports de bibliotheque standard au
    niveau module — ses dependances au profil et au catalogue sont differees —,
    donc l'importer ici ne tire ni pygame ni opencv, et le workflow de
    deploiement (numpy seul) continue de passer.

    Les echelles de reference partent avec : ce sont elles que le JS restreint
    ensuite au materiel declare, exactement comme `echelle_disponible`.
    """
    from dataclasses import asdict

    from core.materiel import (
        ACCESSOIRES,
        MATERIEL_PAR_DEFAUT,
        POIDS_REFERENCE,
        POIDS_SUPPOSES,
    )
    from progression import ligues, paliers
    from progression.reglages import CHEMIN as CHEMIN_REGLAGES

    # Le fichier de reglages voyage **tel quel** jusqu'au site : c'est lui que
    # `dev/baremes.html` edite et rend pret a coller. Le recomposer depuis
    # `baremes.json` obligerait a traduire dans les deux sens, et la traduction
    # finirait par deriver de la source qu'elle pretend reproduire.
    (DONNEES / "reglages.json").write_text(
        CHEMIN_REGLAGES.read_text(encoding="utf-8"), encoding="utf-8"
    )
    from session.seances import MATERIEL_EXERCICES, nombre_halteres

    return {
        # Les echelles de ligue et la table d'XP voyagent avec le bareme : ce
        # sont des reglages, pas des donnees de profil, et `ligues.js` ne doit
        # en reecrire aucune valeur.
        "ligues": {
            "ligues": list(ligues.LIGUES),
            "divisions": list(ligues.DIVISIONS),
            "seuils_volume": list(ligues.SEUILS_VOLUME),
            "seuils_par_exercice": {
                nom: list(valeurs)
                for nom, valeurs in ligues.SEUILS_PAR_EXERCICE.items()
            },
            "paliers_xp": [list(tranche) for tranche in ligues.PALIERS_XP],
            "xp_base_niveau_general": ligues.XP_BASE_NIVEAU_GENERAL,
            "xp_increment_niveau_general": ligues.XP_INCREMENT_NIVEAU_GENERAL,
        },
        "specs": {nom: asdict(spec) for nom, spec in paliers.SPECS.items()},
        "echelles": {
            "un_haltere": list(paliers.ECHELLE_UN_HALTERE),
            "deux_halteres": list(paliers.ECHELLE_DEUX_HALTERES),
            "sans_charge": list(paliers.SANS_CHARGE),
            "reference": list(POIDS_REFERENCE),
            # Et la gamme **supposee**, qui n'est pas la meme : `reference`
            # dit ce que le questionnaire propose de cocher, `supposes` ce
            # qu'on suppose a qui n'a rien declare. Les confondre donnerait
            # d'un coup un bareme de culturiste a tout profil muet.
            "supposes": list(POIDS_SUPPOSES),
        },
        # Le descriptif **brut** et non une liste d'accessoires deja
        # deduite : `core.materiel.accessoires_manquants` cherche une
        # sous-chaine dedans, et refaire cette regle en JavaScript serait la
        # dupliquer. Le nombre d'halteres, lui, vient d'une fonction dont la
        # logique de decoupage n'a pas a traverser.
        "materiel": {
            nom: {
                "halteres": nombre_halteres(nom),
                "brut": MATERIEL_EXERCICES.get(nom, "") or "",
            }
            for nom in paliers.SPECS
        },
        "accessoires": ACCESSOIRES,
        "materiel_par_defaut": MATERIEL_PAR_DEFAUT,
        "series_max_par_defaut": paliers.SERIES_MAX_PAR_DEFAUT,
    }


def exporter_pour_application():
    """Tous les mouvements et toutes les seances, pour l'ecran de seance.

    Separe de `exporter_catalogue` et pas une extension de celui-ci : la demo
    ne montre que ce qu'elle sait faire tourner seule, l'application doit
    pouvoir jouer une seance entiere — donc les echauffements aussi, qui n'ont
    parfois aucune detection.

    Les seances sont exportees **telles qu'elles sont sur le disque**, sans
    passer par le moteur de progression : celui-ci lit l'historique, qui vit
    desormais dans le navigateur de chaque personne. C'est l'etape 4 du
    portage qui posera les cibles ; d'ici la, le fichier fait autorite.
    """
    mouvements = {
        nom: decrire(nom, mouvement)
        for nom, mouvement in catalogue_mouvements().items()
    }
    return mouvements, _lire_seances_personnalisees()


def tables_du_coach():
    """Les quatre tables du coach vocal, pour le navigateur.

    Les trois premieres (`fichiers`, `priorites`, `delais`) vivent dans
    `audio/coach.py` et sont **lues sans importer le module** : celui-ci
    importe `audio.lecteur`, donc pygame, que le workflow de deploiement
    n'installe pas — il n'installe que numpy, parce que ce script ne touchait
    jusqu'ici qu'au catalogue. L'importer ferait echouer le deploiement pour
    une raison sans rapport avec le son. Elles sont donc analysees
    syntaxiquement : la table reste **derivee** du Python et jamais recopiee a
    la main, et le jour ou une cle y est ajoutee elle apparait ici toute seule.

    La quatrieme (`briques`) vient d'`audio/annonces.py`, qui **s'importe
    normalement** : ce module n'a que des imports de bibliotheque standard,
    precisement pour ca. Un import vaut mieux qu'une analyse syntaxique — il
    fait passer les fonctions en plus des tables, donc `fichier()` resout ici
    les noms et le navigateur ne recoit que des `.wav`, jamais du texte a
    normaliser lui-meme.
    """
    voulues = {"messages": "fichiers", "priorites": "priorites",
               "DELAIS_ENTRE_ANNONCES": "delais"}
    arbre = ast.parse((RACINE / "audio" / "coach.py").read_text(encoding="utf-8"))
    tables = {}
    for noeud in arbre.body:
        cibles = getattr(noeud, "targets", [])
        nom = getattr(cibles[0], "id", None) if cibles else None
        if nom in voulues:
            tables[voulues[nom]] = ast.literal_eval(noeud.value)
    manquantes = set(voulues.values()) - set(tables)
    if manquantes:
        raise RuntimeError(f"Tables introuvables dans audio/coach.py : {manquantes}")

    # `BRIQUES` **et** `FRAGMENTS` dans la meme table, a dessein : le
    # navigateur n'en connait que des noms de fichiers, dont il assemble les
    # morceaux (`fichier_assemble`), et la distinction — « est-ce une prise ou
    # un morceau de nom ? » — ne lui sert a rien. Elle vit du cote du texte,
    # ou elle decide de ce qu'on enregistre.
    tables["briques"] = {
        cle: annonces.fichier(texte)
        for cle, texte in {**annonces.BRIQUES, **annonces.FRAGMENTS}.items()
    }
    # Le **texte** des memes briques, pour que le bandeau affiche exactement ce
    # que la voix prononce. Sans lui, ces phrases devraient etre recopiees dans
    # `messages.js` — deux sources pour le meme contenu, dont l'une derive.
    # C'est la meme raison qui fait qu'une brique n'a pas de cle distincte de
    # son texte : pour un son, le texte *est* l'identite de la prise.
    # Les `FRAGMENTS` n'y sont pas : rien ne les affiche, puisqu'ils ne sont
    # jamais une phrase a eux seuls.
    tables["textes"] = dict(annonces.BRIQUES)
    return tables


def sons_des_annonces():
    """Un `.wav` par nom de mouvement, plus un par charge.

    Le nom **est** le texte prononce, donc aucune table a tenir a jour a cote
    du catalogue : un exercice ajoute reclame sa prise a la prochaine
    execution, et `A_ENREGISTRER.md` la signale. Il reste un fichier a part
    parce qu'il se dit derriere chacune des trois amorces.

    Les charges, elles, sont des phrases entieres, enumerees sur
    `POIDS_REFERENCE` — ce que le questionnaire propose de posseder. Au-dela,
    la prise n'existe pas et l'annonce reste breve, jamais muette.
    """
    noms = {annonces.fichier(nom) for nom in catalogue_mouvements()}
    return noms | annonces.fichiers_charges(POIDS_REFERENCE)


def copier_sons():
    """Rapatrie les sons dans les deux pages qui en jouent.

    Copies et non references croisees : la demo et l'application ne dependent
    alors pas l'une de l'autre, et deplacer l'une ne casse pas l'autre en
    silence. Les dossiers ne sont pas versionnes, ce sont des derives.
    """
    demo = DEMO / "sons"
    application = RACINE / "web" / "static" / "sons"
    demo.mkdir(parents=True, exist_ok=True)
    application.mkdir(parents=True, exist_ok=True)

    # La demo se contente du socle : le bip et les nombres annonces. L'appli
    # joue en plus les evenements de seance (« encore 3 », « repos »…), donc
    # tout ce que la table du coach designe.
    tables = tables_du_coach()
    fichiers_application = {f"{n}.wav" for n in SONS_DEMO}
    for variantes in tables["fichiers"].values():
        fichiers_application.update(variantes)
    # Les briques et les phrases assemblees : c'est avec elles que le coach
    # nomme le prochain exercice et guide le cadrage, la ou il n'avait jusqu'ici
    # qu'un « changement d'exercice » generique.
    #
    # `BRIQUES` et non `tables["briques"]`, qui porte en plus les `FRAGMENTS` :
    # ceux-la n'auront **jamais** de fichier, et les faire figurer ici les
    # compterait manquants a chaque execution — un manque qui ne se comblera
    # pas est du bruit, et le bruit finit par masquer un vrai manque.
    fichiers_application.update(
        annonces.fichier(texte) for texte in annonces.BRIQUES.values()
    )
    fichiers_application.update(sons_des_annonces())
    # Les nombres jusqu'au plafond dicible : le compteur de repetitions dit
    # « 23 » sur une cible que le socle de la demo ne couvre pas.
    fichiers_application.update(
        f"{n}.wav" for n in range(1, annonces.NOMBRE_MAXIMAL_DIT + 1)
    )

    copies, manquants = 0, []
    for fichier in sorted(fichiers_application):
        source = SONS_SOURCE / fichier
        if not source.exists():
            manquants.append(fichier)
            continue
        shutil.copy2(source, application / fichier)
        if fichier in {f"{n}.wav" for n in SONS_DEMO}:
            shutil.copy2(source, demo / fichier)
        copies += 1

    # Les trois tables partent avec les sons : le JS choisit un fichier, une
    # priorite et un delai comme le Python, au lieu de refaire ces decisions
    # dans son coin — ce qui est exactement ce qui faisait se chevaucher les
    # annonces avant que la file d'attente ne soit portee.
    (DONNEES / "sons.json").write_text(
        json.dumps(tables, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return copies, manquants


def main():
    DEMO.mkdir(parents=True, exist_ok=True)

    exercices, sans_detection = exporter_catalogue()
    cible = DEMO / "catalogue.json"
    cible.write_text(
        json.dumps(exercices, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    DONNEES.mkdir(parents=True, exist_ok=True)
    mouvements, seances = exporter_pour_application()
    (DONNEES / "mouvements.json").write_text(
        json.dumps(mouvements, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (DONNEES / "seances.json").write_text(
        json.dumps(seances, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    baremes = exporter_baremes()
    (DONNEES / "baremes.json").write_text(
        json.dumps(baremes, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    programmes = exporter_programmes()
    (DONNEES / "programmes.json").write_text(
        json.dumps(programmes, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    copies, manquants = copier_sons()

    print(f"{len(exercices)} exercices exportes vers {cible}")
    if sans_detection:
        print(f"  ecartes (pas de detection de pose) : {', '.join(sans_detection)}")
    print(f"{len(mouvements)} mouvements et {len(seances)} seances vers {DONNEES}")
    print(f"{len(baremes['specs'])} baremes exportes")
    print(f"{len(programmes)} programmes exportes")
    print(f"{copies} sons copies (demo + application)")
    if manquants:
        print(f"  manquants : {', '.join(manquants)}")


if __name__ == "__main__":
    main()
