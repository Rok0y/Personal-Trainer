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
    fiche = mouvement.fiche()
    fiche["detection"] = (
        None if mouvement.detection is None else mouvement.detection.__name__
    )
    fiche["erreurs"] = [verifier.__name__ for verifier in mouvement.erreurs]
    return fiche


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

    from core.materiel import ACCESSOIRES, MATERIEL_PAR_DEFAUT, POIDS_REFERENCE
    from progression import paliers
    from session.seances import MATERIEL_EXERCICES, nombre_halteres

    return {
        "specs": {nom: asdict(spec) for nom, spec in paliers.SPECS.items()},
        "echelles": {
            "un_haltere": list(paliers.ECHELLE_UN_HALTERE),
            "deux_halteres": list(paliers.ECHELLE_DEUX_HALTERES),
            "sans_charge": list(paliers.SANS_CHARGE),
            "reference": list(POIDS_REFERENCE),
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
    """Les trois tables du coach vocal, **lues sans importer le module**.

    `audio/coach.py` importe `audio.lecteur`, donc pygame, que le workflow de
    deploiement n'installe pas — il n'installe que numpy, parce que ce script
    ne touchait jusqu'ici qu'au catalogue. L'importer ici ferait echouer le
    deploiement pour une raison sans rapport avec le son.

    Elle est donc analysee syntaxiquement : la table reste **derivee** du
    Python et jamais recopiee a la main, ce qui est la regle du projet, et le
    jour ou une cle y est ajoutee elle apparait ici toute seule.
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
    return tables


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

    copies, manquants = copier_sons()

    print(f"{len(exercices)} exercices exportes vers {cible}")
    if sans_detection:
        print(f"  ecartes (pas de detection de pose) : {', '.join(sans_detection)}")
    print(f"{len(mouvements)} mouvements et {len(seances)} seances vers {DONNEES}")
    print(f"{len(baremes['specs'])} baremes exportes")
    print(f"{copies} sons copies (demo + application)")
    if manquants:
        print(f"  manquants : {', '.join(manquants)}")


if __name__ == "__main__":
    main()
