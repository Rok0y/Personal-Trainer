"""Oracle Python du portage de `progression/variantes.py`.

Le module répond à trois questions, et chacune demande des entrées que le
hasard ordinaire ne produit pas.

- **Quoi jouer à la place** (`substitution`, `appliquer_au_circuit`) : il faut
  des tables de variantes, valides ou non, croisées avec de vraies séances.
  C'est le seul harnais de `progression/` qui compare un circuit **avant et
  après** — la fonction écrit sur place, comme `appliquer_a_circuit` — et les
  séances fabriquées entrelacent exprès un mouvement remplacé avec le suivant,
  pour éprouver la réécriture de `entrelace_avec`.
- **Ce qui est acceptable** (`chaine`, `definir`) : il faut un catalogue
  **tordu** à côté du vrai — une boucle, une variante inconnue, une variante
  sans détection, une variante dans une autre unité. Le catalogue réel n'en a
  aucune, si bien qu'une garde retirée d'un seul côté passerait vert.
- **Quoi proposer** (`propositions`) : il faut des lignes ratées **au palier
  1** et des séances où l'on est passé à la variante en cours de route, que
  les historiques au hasard ne visitent presque jamais. Elles sont construites
  ici, palier par palier.
- **Quand remonter** (`montees`, `retour_prouve_par`) : des séances
  construites **au seuil de retour**, au niveau près des deux côtés — c'est
  exactement là où `>=` se distingue de `>` —, abandonnées ou non, avec ou
  sans bascule en pleine séance, et jusqu'à la dernière marche, où l'entrée
  de la table doit disparaître.

L'inventaire est figé (non déclaré) : `niveau_pour` dépend des haltères, et un
oracle qui lirait le profil ne rendrait pas deux fois le même verdict.

Usage : `python -m scripts.generer_variantes` (après `preparer_demo`, dont le
comparateur lit `baremes.json`)
Sortie : scripts/fixtures_variantes.jsonl
"""

import copy
import json
import random
from pathlib import Path

from progression import niveaux, paliers, ressenti, variantes
from scripts.historiques_au_hasard import (
    exercice as exercice_au_hasard,
    injecter_inventaire,
)
from session.circuit import MODES_CONNUS
from session.seances import (
    _lire_seances_personnalisees,
    catalogue_mouvements,
    construire_circuit,
)

RACINE = Path(__file__).resolve().parent.parent
DESTINATION = Path(__file__).parent / "fixtures_variantes.jsonl"

GRAINE = 20261007
TABLES = 60
SEANCES_FABRIQUEES = 40
HISTORIQUES = 160

#: Les chaînes du catalogue, par leur racine.
RACINES = ("Pompes", "Gainage planche", "Squat")


def catalogue_tordu(reel):
    """Le vrai catalogue, avec les quatre défauts qu'il n'a pas.

    Que des noms réels : une substitution qui passerait doit pouvoir être
    jouée par `exercice_pour` des deux côtés.
    """
    tordu = copy.deepcopy(reel)
    # Une boucle : la chaîne doit s'arrêter, pas tourner.
    tordu["Pompes inclinées"]["variante_facile"] = "Pompes"
    # Une autre unité : des répétitions remplacées par un maintien.
    tordu["Squat sur chaise"]["variante_facile"] = "Gainage sur les genoux"
    # Sans détection : un échauffement guidé au chrono.
    tordu["Gainage sur les genoux"]["variante_facile"] = "Rotation du cou"
    # Inconnue du catalogue.
    tordu["Crunches"]["variante_facile"] = "Mouvement inexistant"
    return tordu


def table_au_hasard(tirage, catalogue):
    """Une table de variantes, le plus souvent valide, parfois non."""
    table = {}
    for racine in RACINES:
        tirage_racine = tirage.random()
        if tirage_racine < 0.35:
            continue
        chaine = variantes.chaine(racine, catalogue)
        if tirage_racine < 0.85 and len(chaine) > 1:
            table[racine] = tirage.choice(chaine[1:])
        else:
            # Une entrée qui ne devrait pas être là : la racine elle-même, un
            # mouvement sans rapport, un nom inconnu.
            table[racine] = tirage.choice(
                [racine, "Curl biceps droit", "Gainage planche", "Inconnu"]
            )
    if tirage.random() < 0.15:
        table["Crunches"] = "Mouvement inexistant"
    return table


def seance_fabriquee(tirage, mouvements, table):
    """Des blocs jouables qui croisent la table : originaux, partenaires."""
    noms = [nom for nom, ex in mouvements.items() if ex.detection is not None]
    blocs = []
    for _ in range(tirage.randint(2, 6)):
        nom = tirage.choice(list(table) + noms if table and tirage.random() < 0.6 else noms)
        if nom not in mouvements or mouvements[nom].detection is None:
            nom = tirage.choice(noms)
        unite = paliers.unite(nom) if paliers.est_suivi_par_le_moteur(nom) else None
        mode = tirage.choice(
            ["repetitions"] * 3 + ["maintien"] * 2 + ["amrap", "echauffement"]
        )
        if tirage.random() < 0.6:
            mode = "maintien" if unite == paliers.UNITE_SECONDES else "repetitions"
        blocs.append({
            "exercice": nom,
            "mode": mode,
            "poids": 0,
            "series": tirage.randint(1, 4),
            "repetitions": tirage.randint(1, 12),
            "duree": tirage.randint(10, 60),
            "repos_entre_series": 30,
            "repos_apres": 60,
            "cible_manuelle": tirage.choice([False, False, [1], [2], True]),
        })
    # Entrelacer un bloc avec le suivant, quand le suivant est un mouvement
    # remplacé : c'est le nom réécrit par `appliquer_au_circuit`.
    for index in range(len(blocs) - 1):
        if tirage.random() < 0.35:
            blocs[index]["entrelace_avec"] = blocs[index + 1]["exercice"]
    return blocs


def relever(circuit):
    return [
        {
            "exercice": bloc.exercice.nom,
            "mode": bloc.mode,
            "remplace": bloc.remplace,
            "cible_manuelle": bloc.cible_manuelle,
            "entrelace_avec": bloc.entrelace_avec,
        }
        for bloc in circuit.exercices
    ]


def ligne_au_palier(tirage, nom, niveau, reussi, mode=None):
    """Une ligne d'historique jouée à un palier précis, réussie ou non."""
    palier = paliers.palier(nom, niveau)
    en_secondes = palier.unite == paliers.UNITE_SECONDES
    series = []
    for numero in range(1, palier.series + 1):
        realise = palier.cible if reussi else max(0, palier.cible - tirage.randint(1, 3))
        if not reussi and numero > 1 and tirage.random() < 0.5:
            realise = palier.cible
        series.append({
            "serie": numero,
            "repetitions": 0 if en_secondes else realise,
            "poids": palier.poids,
            "duree": realise if en_secondes else 0,
            "completee": reussi or realise >= palier.cible,
        })
    if not reussi and all(s["completee"] for s in series):
        series[0]["completee"] = False
        if en_secondes:
            series[0]["duree"] = max(0, palier.cible - 1)
        else:
            series[0]["repetitions"] = max(0, palier.cible - 1)
    return {
        "nom": nom,
        "mode": mode or ("maintien" if en_secondes else "repetitions"),
        "poids": palier.poids,
        "series": palier.series,
        "repetitions": sum(s["repetitions"] for s in series),
        "duree": sum(s["duree"] for s in series),
        "series_cibles": palier.series,
        "repetitions_cibles": 0 if en_secondes else palier.cible,
        "duree_cible": palier.cible if en_secondes else 0,
        "commentaire": "",
        "entrelace_avec": None,
        "repos_entre_series": 45,
        "repos_apres": 60,
        "ressenti": tirage.choice(["", "trop_dur", "facile"]),
        "series_detaillees": series,
    }


def seances_de_montee(tirage, catalogue):
    """Des séances jouées sous une variante, autour de son seuil de retour.

    Chaque cas est une table et **une** séance : `montees` ne regarde que la
    séance qui vient de se jouer, c'est toute sa règle. La table fait jouer la
    variante une fois sur six seulement depuis une autre clé que la racine, et
    manque une fois sur huit — la variante est alors jouée telle qu'écrite, et
    rien ne doit monter.
    """
    cas = []
    for racine in RACINES:
        chaine = [
            nom for nom in variantes.chaine(racine, catalogue)
            if paliers.est_suivi_par_le_moteur(nom)
        ]
        for index, nom in enumerate(chaine[1:], start=1):
            seuil = variantes.SEUILS_RETOUR.get(nom)
            requis = paliers.niveau_pour(nom, 0, seuil[0], seuil[1]) if seuil else None
            for decalage in (-1, 0, 1, 2):
                niveau = max(1, (requis or 4) + decalage)
                reussi = tirage.random() < 0.8
                lignes = [ligne_au_palier(tirage, nom, niveau, reussi)]
                if tirage.random() < 0.25 and index + 1 < len(chaine):
                    # Une bascule en pleine séance : la variante de la table
                    # quittée, une plus facile jouée et réussie ensuite.
                    lignes = [
                        ligne_au_palier(tirage, nom, niveau, False),
                        ligne_au_palier(tirage, chaine[index + 1], max(1, niveau), True),
                    ]
                if tirage.random() < 0.3:
                    lignes.append(ligne_au_palier(tirage, "Crunches", 2, True))
                tirage_table = tirage.random()
                if tirage_table < 0.125:
                    table = {}
                elif tirage_table < 0.3 and index > 1:
                    table = {chaine[1]: nom}
                else:
                    table = {racine: nom}
                seance = {
                    "statut": "abandoned" if tirage.random() < 0.2 else "finished",
                    "exercices": lignes,
                }
                cas.append({
                    "table": table,
                    "seance": seance,
                    "reponse": list(variantes.montees(table, seance, catalogue)),
                })
            if requis is not None and index >= 2:
                # Le cran du dessus, réussi lui aussi, plus loin dans la même
                # séance — un second bloc qui l'écrit tel quel. Il ne doit pas
                # monter à son tour : un cran par séance. Construit à coup sûr,
                # le hasard ne le réunissant presque jamais.
                dessus = chaine[index - 1]
                seuil_dessus = variantes.SEUILS_RETOUR.get(dessus)
                niveau_dessus = (
                    paliers.niveau_pour(dessus, 0, *seuil_dessus) if seuil_dessus else None
                ) or 3
                table = {racine: nom}
                seance = {"statut": "finished", "exercices": [
                    ligne_au_palier(tirage, nom, requis, True),
                    ligne_au_palier(tirage, dessus, niveau_dessus, True),
                ]}
                cas.append({
                    "table": table,
                    "seance": seance,
                    "reponse": list(variantes.montees(table, seance, catalogue)),
                })
    return cas


def historique_construit(tirage, catalogue, noms):
    """Un historique qui visite les propositions, le plus récent en tête."""
    nombre = tirage.randint(1, 6)
    seances = []
    for identifiant in range(nombre, 0, -1):
        lignes = []
        for _ in range(tirage.randint(1, 3)):
            racine = tirage.choice(RACINES)
            # Seuls les mouvements à barème ont des paliers à jouer : la
            # chaîne tordue finit sur un échauffement qui n'en a pas.
            chaine = [
                nom for nom in variantes.chaine(racine, catalogue)
                if paliers.est_suivi_par_le_moteur(nom)
            ]
            nom = tirage.choice(chaine)
            cas = tirage.random()
            if cas < 0.35:
                # Raté au palier 1 : le seul cas où « trop dur » n'a plus
                # rien à faire descendre.
                lignes.append(ligne_au_palier(tirage, nom, 1, False))
            elif cas < 0.55 and len(chaine) > 1:
                # Une bascule en séance : l'original raté plus haut, puis sa
                # variante dans la même séance.
                index = chaine.index(nom)
                if index + 1 < len(chaine):
                    lignes.append(ligne_au_palier(tirage, nom, tirage.randint(2, 9), False))
                    lignes.append(ligne_au_palier(
                        tirage, chaine[index + 1], tirage.randint(1, 4), tirage.random() < 0.5
                    ))
                else:
                    lignes.append(ligne_au_palier(tirage, nom, 1, False))
            elif cas < 0.85:
                # Autour du seuil de retour d'une variante.
                seuil = variantes.SEUILS_RETOUR.get(nom)
                requis = (
                    paliers.niveau_pour(nom, 0, seuil[0], seuil[1]) if seuil else None
                )
                niveau = max(1, (requis or 5) + tirage.randint(-2, 2))
                lignes.append(ligne_au_palier(tirage, nom, niveau, tirage.random() < 0.7))
            else:
                lignes.append(exercice_au_hasard(tirage, noms))
        seances.append({
            "id": identifiant,
            "date": f"{identifiant:02d}/09/2026 08:00",
            "duree": 1200,
            "statut": tirage.choice(["finished", "finished", "abandoned"]),
            "nom": "Upper Push",
            "exercices": lignes,
        })
    return seances


def main():
    tirage = random.Random(GRAINE)
    injecter_inventaire(None)
    mouvements = catalogue_mouvements()
    catalogues = {
        "reel": variantes.catalogue_depuis(mouvements),
    }
    catalogues["tordu"] = catalogue_tordu(catalogues["reel"])
    noms_suivis = list(paliers.exercices_suivis())
    lignes = 0

    with DESTINATION.open("w", encoding="utf-8") as fichier:
        def ecrire(objet):
            nonlocal lignes
            fichier.write(json.dumps(objet, ensure_ascii=False) + "\n")
            lignes += 1

        # Les catalogues voyagent avec l'oracle : un jeu d'entrées redéclaré
        # côté JavaScript aurait le même défaut que le code qu'il surveille.
        ecrire({"genre": "catalogues", "catalogues": catalogues,
                "seuils_retour": {n: list(s) for n, s in variantes.SEUILS_RETOUR.items()}})

        ecrire({"genre": "normaliser", "questions": [
            {"entree": entree, "reponse": variantes.normaliser(entree)}
            for entree in (None, {}, [], "Pompes", {"Pompes": "Pompes"},
                           {"Pompes": "Pompes sur les genoux", "": "x", "Squat": ""},
                           {"Squat": "Squat sur chaise"})
        ]})

        for nom_catalogue, catalogue in catalogues.items():
            noms = sorted(catalogue) + ["Mouvement inexistant"]
            ecrire({"genre": "chaines", "catalogue": nom_catalogue, "questions": [
                {"original": nom, "reponse": variantes.chaine(nom, catalogue)}
                for nom in noms
            ]})

            for numero in range(TABLES):
                table = table_au_hasard(tirage, catalogue)
                questions = []
                for original in list(RACINES) + ["Crunches", "Pompes sur les genoux"]:
                    candidats = variantes.chaine(original, catalogue) + [
                        None, "Curl biceps droit", "Rotation du cou", "Inconnu",
                    ]
                    for joue in candidats:
                        try:
                            reponse = variantes.definir(table, original, joue, catalogue)
                        except ValueError:
                            reponse = "refus"
                        questions.append({"original": original, "joue": joue, "reponse": reponse})
                substitutions = [
                    {"nom": nom, "mode": mode,
                     "reponse": variantes.substitution(nom, mode, table, catalogue)}
                    for nom in list(RACINES) + ["Crunches", "Curl biceps droit"]
                    for mode in MODES_CONNUS
                ]
                choix = [
                    {"nom": nom, "mode": mode,
                     "reponse": variantes.versions(nom, mode, catalogue)}
                    for nom in list(RACINES) + ["Crunches", "Pompes sur les genoux",
                                                 "Squat sur chaise", "Inconnu"]
                    for mode in MODES_CONNUS
                ] if numero == 0 else []
                originaux = [
                    {"nom": nom, "reponse": variantes.original_de(nom, table)}
                    for nom in sorted(set(table.values())) + ["Pompes"]
                ]

                circuits = []
                sources = list(_lire_seances_personnalisees().values())
                for index in range(3):
                    blocs = (
                        copy.deepcopy(tirage.choice(sources))
                        if index == 0 and sources
                        else seance_fabriquee(tirage, mouvements, table)
                    )
                    try:
                        circuit = construire_circuit(copy.deepcopy(blocs))
                    except (KeyError, ValueError):
                        continue
                    avant = relever(circuit)
                    variantes.appliquer_au_circuit(
                        circuit, table, catalogue, mouvements.__getitem__
                    )
                    circuits.append({"blocs": blocs, "avant": avant, "apres": relever(circuit)})

                ecrire({
                    "genre": "table", "catalogue": nom_catalogue, "numero": numero,
                    "table": table, "definir": questions,
                    "substitution": substitutions, "original_de": originaux,
                    "versions": choix,
                    "circuits": circuits,
                })

            for numero in range(HISTORIQUES // len(catalogues)):
                seances = historique_construit(tirage, catalogue, noms_suivis)
                table = table_au_hasard(tirage, catalogue)
                jugements = ressenti.jugements_par_seance(seances)
                ecrire({
                    "genre": "historique", "catalogue": nom_catalogue, "numero": numero,
                    "seances": seances, "table": table,
                    "propositions": {
                        str(cle): valeur
                        for cle, valeur in variantes.propositions(
                            seances, jugements, table, catalogue
                        ).items()
                    },
                })

            ecrire({"genre": "montees", "catalogue": nom_catalogue,
                    "cas": seances_de_montee(tirage, catalogue)})

        # Le seuil de retour, au niveau près, de part et d'autre, sur des
        # lignes réussies et une ratée.
        bornes = []
        for nom, seuil in variantes.SEUILS_RETOUR.items():
            requis = paliers.niveau_pour(nom, 0, seuil[0], seuil[1])
            if requis is None:
                continue
            for niveau, reussi in ((requis - 1, True), (requis, True),
                                   (requis + 1, True), (requis + 1, False)):
                if niveau < 1:
                    continue
                ligne = ligne_au_palier(tirage, nom, niveau, reussi)
                bornes.append({"ligne": ligne, "reponse": variantes.retour_prouve_par(ligne)})
        ligne = ligne_au_palier(tirage, "Pompes", 30, True)
        bornes.append({"ligne": ligne, "reponse": variantes.retour_prouve_par(ligne)})
        ecrire({"genre": "retour", "questions": bornes})

    print(f"{lignes} lignes, {len(catalogues)} catalogues")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


if __name__ == "__main__":
    main()
