"""Oracle Python du portage de `session/circuit.py` et `session/moteur.py`.

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
Sortie : scripts/fixtures_seances.jsonl (un pas par ligne),
         scripts/fixtures_poses.jsonl (la banque de poses partagée),
         scripts/fixtures_catalogue.json (les mouvements utilisés).
"""

import hashlib
import json
import random
from pathlib import Path

import audio.coach

from mouvements.compteur import CompteurMouvement
from scripts.generer_fixtures import pose_au_hasard, serialiser
from session.moteur import executer_mode
from session.seances import catalogue_mouvements, construire_circuit
from core.state import EtatSeance

RACINE = Path(__file__).resolve().parent.parent
SEANCES = RACINE / "session" / "seances_personnalisees.json"
DESTINATION = Path(__file__).parent / "fixtures_seances.jsonl"
#: Banque de poses partagee avec le JS. Les poses ne sont pas recopiees dans
#: chaque pas (132 flottants la piece) mais referencees par index : le fichier
#: reste lisible, et les deux langages travaillent forcement sur les memes
#: images.
POSES = Path(__file__).parent / "fixtures_poses.jsonl"
NOMBRE_DE_POSES = 400
#: Catalogue propre au harnais : les séances contiennent aussi des
#: échauffements, absents du `catalogue.json` de la démo — qui, lui, ne liste
#: que les exercices testables et n'a pas à changer pour nous. Il porte le nom
#: des fonctions (détection et vérifications de forme), le JS retrouvant les
#: siennes dans `detections.js` sous les mêmes noms.
CATALOGUE = Path(__file__).parent / "fixtures_catalogue.json"

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

#: Rempli par `main()` avant la première écriture (voir `empreinte`).
EMPREINTE = None


#: Ce que le moteur ecrit dans l'etat, releve au meme titre que le circuit.
#: C'est la surface verifiee du portage de `moteur.py`.
CHAMPS_ETAT = (
    "mode", "stage", "etape_libelle", "erreur", "repetitions",
    "temps_maintien", "duree_maintien", "temps_chrono", "chrono_termine",
    "temps_echauffement", "duree_echauffement", "temps_amrap_restant",
    "prochaine_etape", "fiche_suivante",
)


def observer_etat(etat):
    releve = {}
    for champ in CHAMPS_ETAT:
        valeur = getattr(etat, champ)
        # Les flottants accumules image par image ne s'accordent pas au
        # dernier bit entre deux langages : la milliseconde suffit largement,
        # et c'est bien plus fin que ce que l'utilisateur percoit.
        releve[champ] = round(valeur, 6) if isinstance(valeur, float) else valeur
    return releve


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
        ("image", {"secondes": 0}),
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
    "image": 30,
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


def jouer(circuit, horloge, nom, arguments, contexte=None,
          compteur=None, etat=None, coach=None, banque_corps=None):
    """Exécute un pas et rend ce qu'il a produit.

    Une exception est un comportement, pas un incident : si Python refuse une
    commande dans un état donné, le JavaScript doit la refuser aussi. Elle est
    donc relevée au même titre qu'une valeur de retour.
    """
    if nom == "avancer":
        horloge["t"] += arguments["secondes"]
        return None, None
    if nom == "image":
        # Une image complete de la boucle camera : detection, comptage, voix,
        # avancement du mode. C'est ce qui verifie `moteur.py`, la ou les
        # autres commandes ne verifient que `circuit.py`.
        #
        # Le garde reproduit celui de `main.py` : les modes ne tournent que
        # pendant la phase « exercice » et sur un bloc existant. Sans lui, le
        # harnais testerait un appel que l'application ne fait jamais.
        if circuit.phase != "exercice" or circuit.bloc_actuel is None:
            return None, None
        corps = banque_corps[arguments["pose"]]
        try:
            triplet = executer_mode(
                circuit, corps, compteur, etat, coach, contexte["derniere_rep"]
            )
        except Exception as erreur:  # noqa: BLE001 - le type est la donnee
            return None, type(erreur).__name__
        contexte["derniere_rep"] = triplet[0]
        if triplet[2]:
            # Serie terminee : `main.py` remet le compteur a zero, faute de
            # quoi la serie suivante demarrerait deja armee.
            compteur.reset()
            contexte["derniere_rep"] = 0
        return list(triplet), None

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
    """Un circuit neuf, plus tout ce que la boucle caméra transporte avec lui.

    Le compteur, l'état et `derniere_rep` survivent d'une image à l'autre et
    d'une série à l'autre — c'est précisément ce que `main.py` fait, et ce qui
    rend les défauts de réinitialisation visibles. Les recréer à chaque pas
    masquerait la moitié de ce que le moteur doit gérer.
    """
    circuit = construire_circuit(blocs)
    horloge = {"t": INSTANT_INITIAL}
    circuit.maintenant = lambda: horloge["t"]
    circuit.debut = horloge["t"]
    annonces = []

    def coach(cle, valeur=None):
        # Asymétrie assumée entre les deux implémentations, et relevée ici
        # parce qu'elle se voit mal autrement : `session/moteur.py` reçoit un
        # `coach` en paramètre, mais `annoncer_progression` et
        # `annoncer_temps_restant`, importées d'`audio.coach`, appellent le
        # coach **global de leur module**. Le harnais détourne donc les deux
        # chemins vers la même liste (voir `audio.coach.coach` remplacé plus
        # bas), sinon ces annonces-là joueraient réellement — ce qui fait
        # planter un processus sans carte son — et surtout n'apparaîtraient
        # nulle part dans la comparaison. Côté JavaScript les deux fonctions
        # vivent dans `moteur.js` et reçoivent le coach injecté : *quand*
        # annoncer est une décision, *comment* jouer n'en est pas une.
        # Le coach est enregistré, jamais joué : *quand* l'application parle
        # est une décision qui doit coïncider entre les deux langages, alors
        # que jouer le son ne l'est pas. C'est aussi la seule façon de vérifier
        # « encore 3 » ou le bip de chaque seconde.
        annonces.append([cle, valeur])

    audio.coach.coach = coach

    return circuit, horloge, {
        "compteur": CompteurMouvement(),
        "etat": EtatSeance(),
        "coach": coach,
        "annonces": annonces,
        "contexte": {"derniere_rep": 0},
    }


def _ecrire(fichier, seance, scenario, pas, nom, arguments, circuit, horloge,
            resultat, erreur, boucle):
    annonces = list(boucle["annonces"])
    boucle["annonces"].clear()
    fichier.write(json.dumps({
        "empreinte_seances": EMPREINTE,
        "seance": seance,
        "scenario": scenario,
        "pas": pas,
        "commande": nom,
        "arguments": arguments,
        "instant": round(horloge["t"] - INSTANT_INITIAL, 3),
        "resultat": resultat,
        "erreur": erreur,
        "annonces": annonces,
        "etat": observer(circuit),
        "etat_seance": observer_etat(boucle["etat"]),
    }, ensure_ascii=False) + "\n")


def _jouer(circuit, horloge, commande, arguments, boucle, banque):
    return jouer(
        circuit, horloge, commande, arguments,
        contexte=boucle["contexte"], compteur=boucle["compteur"],
        etat=boucle["etat"], coach=boucle["coach"], banque_corps=banque,
    )


def _arguments(commande, circuit, tirage):
    if commande == "avancer":
        return {"secondes": 40}
    if commande == "image":
        return {"pose": tirage.randrange(NOMBRE_DE_POSES)}
    if commande == "terminer_serie_manuellement":
        return _performance(circuit, tirage)
    return {}


def main():
    texte_des_seances = SEANCES.read_text(encoding="utf-8")
    seances = json.loads(texte_des_seances)
    # Empreinte du fichier de séances, relue par le comparateur. Sans elle, une
    # séance modifiée entre la génération et la comparaison — ce qui arrive dès
    # qu'on joue une séance, la fin de séance réécrivant ce fichier — produit un
    # diff parfaitement authentique et parfaitement trompeur (« poids 5 contre
    # 6 »), qu'on met un moment à reconnaître pour ce qu'il est : des fixtures
    # périmées, pas un portage infidèle.
    # Les retours chariot sont retires avant de hacher : Python les traduit a
    # la lecture, Node les garde, et l'empreinte porterait sinon sur les fins
    # de ligne autant que sur le contenu — deux verdicts opposes sur un fichier
    # identique.
    empreinte = hashlib.sha256(
        texte_des_seances.replace("\r", "").encode("utf-8")
    ).hexdigest()[:16]
    tirage = random.Random(GRAINE)

    # La banque de poses est écrite avant tout le reste, et tirée sur la même
    # graine : le JS lit ce fichier plutôt que de retirer les siennes.
    poses = random.Random(GRAINE + 1)
    banque = [pose_au_hasard(poses) for _ in range(NOMBRE_DE_POSES)]
    with POSES.open("w", encoding="utf-8") as fichier:
        for corps in banque:
            fichier.write(json.dumps(serialiser(corps)) + "\n")

    mouvements = catalogue_mouvements()
    CATALOGUE.write_text(json.dumps({
        nom: {
            "nom": exercice.nom,
            "detection": (
                None if exercice.detection is None else exercice.detection.__name__
            ),
            "erreurs": [verifier.__name__ for verifier in exercice.erreurs],
            "description": exercice.description,
            "instructions": list(exercice.instructions),
            "mise_en_place": list(exercice.mise_en_place),
            "erreurs_frequentes": list(exercice.erreurs_frequentes),
            "variante_facile": exercice.variante_facile,
            "variante_difficile": exercice.variante_difficile,
        }
        for nom, exercice in mouvements.items()
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    global EMPREINTE
    EMPREINTE = empreinte

    lignes = 0
    with DESTINATION.open("w", encoding="utf-8") as fichier:
        for nom_seance, blocs in seances.items():

            # --- Scénarios écrits ---
            for nom_scenario, etapes in SCENARIOS_NOMMES.items():
                circuit, horloge, boucle = _nouveau_circuit(blocs)
                for pas, (commande, _) in enumerate(etapes):
                    args = _arguments(commande, circuit, tirage)
                    resultat, erreur = _jouer(circuit, horloge, commande, args, boucle, banque)
                    _ecrire(fichier, nom_seance, nom_scenario, pas, commande,
                            args, circuit, horloge, resultat, erreur, boucle)
                    lignes += 1

            # --- Marche aléatoire ---
            circuit, horloge, boucle = _nouveau_circuit(blocs)
            noms = list(POIDS)
            poids = [POIDS[n] for n in noms]
            for pas in range(PAS_PAR_SEANCE):
                commande = tirage.choices(noms, weights=poids)[0]
                args = _arguments(commande, circuit, tirage)
                resultat, erreur = _jouer(circuit, horloge, commande, args, boucle, banque)
                _ecrire(fichier, nom_seance, "hasard", pas, commande,
                        args, circuit, horloge, resultat, erreur, boucle)
                lignes += 1

    circuit, _, boucle = _nouveau_circuit(next(iter(seances.values())))
    champs = len(observer(circuit)) + len(observer_etat(boucle["etat"]))
    print(f"{len(seances)} seances x ({len(SCENARIOS_NOMMES)} scenarios ecrits "
          f"+ {PAS_PAR_SEANCE} pas au hasard)")
    print(f"{NOMBRE_DE_POSES} poses dans la banque partagee")
    print(f"{lignes} pas, {champs} champs par pas, {lignes * champs} valeurs a comparer")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


if __name__ == "__main__":
    main()
