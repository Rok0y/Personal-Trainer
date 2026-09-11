"""Oracle Python du portage de `session/circuit.py` en JavaScript.

Pendant du harnais des détections, pour une classe qui a de la mémoire.
`generer_fixtures.py` peut tirer des poses au hasard parce qu'une détection est
une fonction pure : même entrée, même sortie, toujours. `Circuit` n'a pas cette
propriété — ce que répond `terminer_serie()` dépend de tout ce qui l'a précédé,
de la série en cours, de l'entrelacement, d'un éventuel « refaire ». On ne peut
donc pas lui jeter une entrée au hasard : il faut lui jeter une **histoire**.

Un scénario est cette histoire : une suite de commandes horodatées, jouées sur
une séance réelle, avec l'état du circuit relevé après chaque pas. Python le
joue et note ses réponses ; le JavaScript rejouera exactement les mêmes pas et
`scripts/comparer_seances.mjs` diffusera les écarts.

Deux sources de scénarios, pour deux raisons qui ne se remplacent pas. La
**marche aléatoire** tire à chaque pas une commande au hasard : elle explore des
enchaînements que personne n'écrirait, et c'est là que vivent les bugs de
machine à états. Les **scénarios nommés** visent les pièges que `CLAUDE.md`
désigne déjà — l'entrelacement des supersets, les cinq sorties de
`terminer_serie`, le repère de « refaire la dernière série » — et quand l'un
d'eux casse, il dit tout de suite lequel.

Les séances viennent de `seances_personnalisees.json`, c'est-à-dire des vraies.
Elles sont construites par `construire_circuit` et **non** par `creer_seance` :
celle-ci passe par le moteur de progression, donc par l'historique, et les
cibles changeraient à chaque séance jouée — un oracle doit rendre deux fois le
même verdict.

Usage : `python -m scripts.generer_scenarios`
Sortie : scripts/fixtures_seances.jsonl, un pas par ligne.
"""

import json
import random
from pathlib import Path

from session.seances import construire_circuit

RACINE = Path(__file__).resolve().parent.parent
SEANCES = RACINE / "session" / "seances_personnalisees.json"
DESTINATION = Path(__file__).parent / "fixtures_seances.jsonl"

#: Graine fixe : deux exécutions doivent produire exactement le même fichier,
#: sinon le diff JavaScript compare des histoires différentes.
GRAINE = 20260911

#: Pas de marche aléatoire par séance. Assez pour traverser plusieurs fois une
#: séance de 17 blocs, y compris en revenant en arrière.
PAS_PAR_SEANCE = 900

#: Instant de départ de l'horloge fictive. Arbitraire : seules les différences
#: comptent, mais une valeur non nulle attrape un code qui confondrait
#: « instant » et « durée ».
INSTANT_INITIAL = 1000.0


def observer(circuit):
    """L'état complet du circuit, réduit à des valeurs comparables.

    Tout ce qui sort d'ici doit être un scalaire ou None : c'est ce qui se
    sérialise, se compare champ par champ, et se lit dans un diff. Un objet
    (`bloc_actuel`, `exercice_actuel`) est donc réduit à son nom.

    Y ajouter un champ élargit la surface vérifiée du portage — c'est le levier
    principal de ce harnais, bien avant le nombre de pas.
    """
    bloc = circuit.bloc_actuel
    # `prochain_bloc` est la seule de ces lectures à être une méthode et non
    # une propriété — à ne pas oublier au moment de porter la classe.
    prochain = circuit.prochain_bloc()
    exercice = circuit.exercice_actuel
    return {
        "phase": circuit.phase,
        "index_exercice": circuit.index_exercice,
        "serie_actuelle": circuit.serie_actuelle,
        "serie_actuelle_locale": circuit.serie_actuelle_locale,
        "exercice": getattr(exercice, "nom", None),
        "bloc": None if bloc is None else bloc.exercice.nom,
        "prochain_bloc": None if prochain is None else prochain.exercice.nom,
        "mode": None if bloc is None else bloc.mode,
        "nombre_series": circuit.nombre_series,
        "repetitions_cibles": circuit.repetitions_cibles,
        "poids": circuit.poids,
        # Arrondi : le décompte de repos est un flottant, et deux langages ne
        # s'accordent pas au dernier bit. La seconde est la précision que
        # l'utilisateur voit, donc la seule qui doive coïncider.
        "temps_restant": round(circuit.temps_restant, 3),
        "duree_totale": circuit.duree_totale,
        "dans_echauffement": circuit.dans_echauffement,
        # `blocs_comptabilises` et `blocs_echauffement` rendent les blocs
        # eux-mêmes, pas leur nombre : on relève les noms, qui disent la même
        # chose tout en restant lisibles dans un diff.
        "blocs_comptabilises": [b.exercice.nom for b in circuit.blocs_comptabilises],
        "series_terminees": circuit.series_terminees,
        "nombre_series_total": circuit.nombre_series_total,
        "blocs_echauffement": [b.exercice.nom for b in circuit.blocs_echauffement],
        "nombre_series_echauffement": circuit.nombre_series_echauffement,
        "series_echauffement_terminees": circuit.series_echauffement_terminees,
        "peut_refaire": circuit.peut_refaire_derniere_serie(),
        # Les deux états internes qui pilotent les cas délicats. Sans eux, un
        # sabotage volontaire de `refaire_derniere_serie` — oublier de
        # restaurer l'entrelacement, la ligne même que `CLAUDE.md` signale
        # comme indispensable — traversait les 141 312 comparaisons sans être
        # vu : leurs conséquences n'apparaissent que dans une fenêtre étroite
        # qu'une marche aléatoire touche rarement, alors que l'état, lui, est
        # faux immédiatement. Observer la cause plutôt que d'attendre l'effet.
        "entrelace_en_cours": (
            None if circuit._exercice_precedent_entrelace is None
            else dict(circuit._exercice_precedent_entrelace)
        ),
        "repere_derniere_serie": (
            None if circuit._derniere_serie_terminee is None
            else {
                "index_exercice": circuit._derniere_serie_terminee["index_exercice"],
                "serie": circuit._derniere_serie_terminee["serie"],
                "entrelace": circuit._derniere_serie_terminee["entrelace"],
            }
        ),
        "resultats": len(circuit.resultats_series),
        "a_des_resultats": circuit.a_des_resultats(),
    }


def _cible(circuit):
    bloc = circuit.bloc_actuel
    if bloc is None:
        return 10
    return bloc.duree if bloc.mode in ("maintien", "chrono") else bloc.repetitions_par_serie


def _performance(circuit, tirage):
    """Une performance plausible, de part et d'autre de la consigne.

    Tirée autour de la cible et non au hasard absolu : c'est le franchissement
    du seuil qui fait basculer `completee`, donc tout ce que le moteur en
    déduit. Des valeurs toujours très au-dessus ne testeraient qu'une branche.
    """
    cible = _cible(circuit)
    valeur = tirage.randint(max(0, cible - 3), cible + 2)
    bloc = circuit.bloc_actuel
    if bloc is not None and bloc.mode in ("maintien", "chrono"):
        return {"repetitions": 0, "duree": valeur}
    return {"repetitions": valeur, "duree": 0}


#: Les commandes que le harnais sait jouer. Chacune rend (libellé, arguments),
#: les arguments étant relevés dans le scénario pour que le JavaScript rejoue
#: exactement les mêmes valeurs plutôt que d'en tirer d'autres.
def _commandes(circuit, tirage):
    return [
        ("update", {}),
        # Faire avancer l'horloge est une commande comme une autre : c'est elle
        # qui fait expirer un repos, et donc qui déclenche les transitions que
        # `update` se contente de constater.
        ("avancer", {"secondes": tirage.choice([1, 5, 20, 65])}),
        ("commencer_exercice", {}),
        ("terminer_serie_manuellement", _performance(circuit, tirage)),
        ("terminer_serie", {}),
        ("passer_exercice_suivant", {}),
        ("passer_pause", {}),
        ("serie_precedente", {}),
        ("serie_suivante", {}),
        ("recommencer_serie", {}),
        ("remettre_serie_a_zero", {}),
        ("refaire_derniere_serie", {}),
    ]


#: Poids du tirage. `avancer` et `terminer_serie_manuellement` dominent parce
#: que c'est ainsi qu'une séance se déroule vraiment ; les commandes de
#: navigation restent rares, comme dans l'usage, mais jamais absentes.
POIDS = {
    "update": 5,
    "avancer": 6,
    "commencer_exercice": 2,
    "terminer_serie_manuellement": 6,
    "terminer_serie": 1,
    "passer_exercice_suivant": 1,
    "passer_pause": 1,
    "serie_precedente": 1,
    "serie_suivante": 1,
    "recommencer_serie": 1,
    "remettre_serie_a_zero": 1,
    "refaire_derniere_serie": 2,
}


def jouer(circuit, horloge, nom, arguments):
    """Exécute un pas et rend ce qu'il a produit.

    Une exception est un comportement, pas un incident : si Python refuse une
    commande dans un état donné, le JavaScript doit la refuser aussi. Elle est
    donc relevée au même titre qu'une valeur de retour.
    """
    if nom == "avancer":
        horloge["t"] += arguments["secondes"]
        return None, None
    if nom == "aller_au_superset":
        # Commande du harnais, pas du circuit : elle amène à la première paire
        # entrelacée de la séance. Pilotée par les données et non par un
        # nombre de sauts en dur, pour qu'un superset déplacé dans une séance
        # ne rende pas le scénario muet sans prévenir.
        for _ in range(len(circuit.exercices)):
            if circuit.bloc_actuel is None or circuit._est_entrelace(circuit.index_exercice):
                break
            circuit.passer_exercice_suivant()
        return None, None
    try:
        resultat = getattr(circuit, nom)(**arguments)
    except Exception as erreur:  # noqa: BLE001 - le type est la donnée
        return None, type(erreur).__name__
    # Les booléens et None se comparent ; le reste est ramené à son nom.
    if resultat is None or isinstance(resultat, (bool, int, float, str)):
        return resultat, None
    return type(resultat).__name__, None


#: Déroulements écrits à la main, joués sur chaque séance. Ils visent
#: nommément les chemins que `CLAUDE.md` signale comme délicats.
SCENARIOS_NOMMES = {
    "nominal": [
        ("commencer_exercice", None),
        *[(c, None) for _ in range(12) for c in
          ("terminer_serie_manuellement", "avancer", "avancer", "update")],
    ],
    "series_manquees": [
        ("commencer_exercice", None),
        *[(c, None) for _ in range(8) for c in
          ("terminer_serie_manuellement", "avancer", "avancer", "update")],
    ],
    "refaire_la_derniere": [
        ("commencer_exercice", None),
        ("terminer_serie_manuellement", None),
        ("refaire_derniere_serie", None),
        ("terminer_serie_manuellement", None),
        ("refaire_derniere_serie", None),
        ("avancer", None), ("avancer", None), ("update", None),
        ("terminer_serie_manuellement", None),
        ("refaire_derniere_serie", None),
    ],
    "navigation": [
        ("commencer_exercice", None),
        ("terminer_serie_manuellement", None),
        ("avancer", None), ("avancer", None), ("update", None),
        ("serie_precedente", None),
        ("serie_suivante", None),
        ("recommencer_serie", None),
        ("remettre_serie_a_zero", None),
        ("passer_exercice_suivant", None),
        ("serie_precedente", None),
    ],
    # Le chemin que la marche aléatoire n'atteint jamais : refaire une série
    # au milieu d'un aller-retour de superset. Mesuré avant de l'écrire — sur
    # 408 « refaire » réussis tirés au hasard, zéro n'avait d'entrelacement à
    # restaurer, et 13 pas sur 6144 seulement passaient au milieu d'un
    # superset. C'est pourtant la ligne que `CLAUDE.md` désigne comme
    # indispensable, et un sabotage volontaire de cette ligne traversait tout
    # le harnais sans être vu.
    "superset_refaire": [
        ("aller_au_superset", None),
        ("commencer_exercice", None),
        ("terminer_serie_manuellement", None),   # part chez le partenaire
        ("passer_pause", None),
        ("terminer_serie_manuellement", None),   # revient : repère entrelacé
        ("refaire_derniere_serie", None),
        ("terminer_serie_manuellement", None),
        ("refaire_derniere_serie", None),
        ("passer_pause", None),
        ("terminer_serie_manuellement", None),
        ("passer_pause", None),
        ("terminer_serie_manuellement", None),
        ("refaire_derniere_serie", None),
        ("terminer_serie_manuellement", None),
    ],
    "sauter_les_repos": [
        ("commencer_exercice", None),
        *[(c, None) for _ in range(10) for c in
          ("terminer_serie_manuellement", "passer_pause")],
    ],
}


def _nouveau_circuit(blocs):
    circuit = construire_circuit(blocs)
    horloge = {"t": INSTANT_INITIAL}
    circuit.maintenant = lambda: horloge["t"]
    circuit.debut = horloge["t"]
    return circuit, horloge


def _ecrire(fichier, seance, scenario, pas, nom, arguments, circuit, horloge, resultat, erreur):
    fichier.write(json.dumps({
        "seance": seance,
        "scenario": scenario,
        "pas": pas,
        "commande": nom,
        "arguments": arguments,
        "instant": round(horloge["t"] - INSTANT_INITIAL, 3),
        "resultat": resultat,
        "erreur": erreur,
        "etat": observer(circuit),
    }, ensure_ascii=False) + "\n")


def main():
    seances = json.loads(SEANCES.read_text(encoding="utf-8"))
    tirage = random.Random(GRAINE)
    lignes = 0

    with DESTINATION.open("w", encoding="utf-8") as fichier:
        for nom_seance, blocs in seances.items():

            # --- Scénarios écrits ---
            for nom_scenario, etapes in SCENARIOS_NOMMES.items():
                circuit, horloge = _nouveau_circuit(blocs)
                for pas, (commande, _) in enumerate(etapes):
                    arguments = ({"secondes": 40} if commande == "avancer"
                                 else _performance(circuit, tirage)
                                 if commande == "terminer_serie_manuellement" else {})
                    resultat, erreur = jouer(circuit, horloge, commande, arguments)
                    _ecrire(fichier, nom_seance, nom_scenario, pas, commande,
                            arguments, circuit, horloge, resultat, erreur)
                    lignes += 1

            # --- Marche aléatoire ---
            circuit, horloge = _nouveau_circuit(blocs)
            noms = list(POIDS)
            poids = [POIDS[n] for n in noms]
            for pas in range(PAS_PAR_SEANCE):
                commande = tirage.choices(noms, weights=poids)[0]
                arguments = dict(_commandes(circuit, tirage))[commande]
                resultat, erreur = jouer(circuit, horloge, commande, arguments)
                _ecrire(fichier, nom_seance, "hasard", pas, commande,
                        arguments, circuit, horloge, resultat, erreur)
                lignes += 1

    champs = len(observer(_nouveau_circuit(next(iter(seances.values())))[0]))
    print(f"{len(seances)} seances x ({len(SCENARIOS_NOMMES)} scenarios ecrits "
          f"+ {PAS_PAR_SEANCE} pas au hasard)")
    print(f"{lignes} pas, {champs} champs par pas, {lignes * champs} valeurs a comparer")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


if __name__ == "__main__":
    main()
