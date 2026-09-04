"""Confronte le barème de progression à l'historique réel.

Outil de vérification manuelle, hors chemin critique de l'application : il ne
touche à rien, il lit. Il sert à recaler les specs de `progression/paliers.py`
avant que le moteur ne pilote quoi que ce soit.

    python -m scripts.script_niveaux            # premier profil
    python -m scripts.script_niveaux Sophie     # un profil précis (nom ou id)

Le profil compte : niveaux, objectifs et historique sont cloisonnés, et il n'y
a pas d'écran de connexion en ligne de commande.
"""

import sys

from progression.niveaux import niveau_prouve_par, niveaux_par_exercice
from progression.paliers import (
    SPECS,
    est_suivi_par_le_moteur,
    niveau_pour,
    dernier_palier_borne,
    palier,
    tranches,
    unite,
)
from core.utilisateur import connecter
from progression.ressenti import evaluation
from historique.database import lister_utilisateurs, recuperer_historique
from session.seances import CATALOGUE_EXERCICES, catalogue

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def titre(texte):
    print()
    print(texte)
    print("-" * len(texte))


def afficher_bareme():
    titre("BARÈME (tranches, et volume tenu à chaque bascule de poids)")
    for nom, spec in SPECS.items():
        if spec.cible_max is None:
            print(f"  {nom:<34} {palier(nom, 1).resume()} puis sans fin, par {spec.pas}")
            continue
        def decrire(tranche):
            if tranche["niveau_max"] is None:
                # Tranche ouverte : plus de plafond de répétitions.
                return (
                    f"{tranche['series']}x{tranche['cible_min']}+ à"
                    f" {tranche['poids']:g}kg (n{tranche['niveau_min']} et au-delà)"
                )
            return (
                f"{tranche['series']}x{tranche['cible_min']}-{tranche['cible_max']}"
                f" à {tranche['poids']:g}kg"
                f" (n{tranche['niveau_min']}-{tranche['niveau_max']},"
                f" vol {tranche['volume_max']:g})"
            )

        decoupage = " | ".join(
            decrire(tranche)
            for tranche in tranches(nom, series_max=spec.series_max)
        )
        print(f"  {nom}  ({dernier_palier_borne(nom)} paliers bornés, puis sans fin)")
        print(f"      {decoupage}")


def verifier_monotonie_volume():
    """Le volume ne doit jamais redescendre d'un palier au suivant."""
    titre("VÉRIFICATION : LE VOLUME NE REDESCEND JAMAIS")
    for nom, spec in SPECS.items():
        # Tout le barème borné, plus quelques paliers de la tranche ouverte
        # pour vérifier que le raccord ne fait pas redescendre le volume.
        borne = dernier_palier_borne(nom)
        dernier = (borne + 5) if borne else 40
        precedent = None
        regressions = []
        for niveau in range(1, dernier + 1):
            actuel = palier(nom, niveau)
            if precedent is not None and actuel.volume < precedent.volume:
                regressions.append(
                    f"n{precedent.niveau} ({precedent.resume()}, {precedent.volume:g})"
                    f" -> n{actuel.niveau} ({actuel.resume()}, {actuel.volume:g})"
                )
            precedent = actuel
        etat = "OK" if not regressions else "REGRESSION : " + " ; ".join(regressions)
        print(f"  {nom:<34} {dernier:>3} paliers testés  {etat}")


def afficher_niveaux(seances):
    titre("NIVEAUX DÉDUITS DE L'HISTORIQUE")
    niveaux = niveaux_par_exercice(seances)

    hors_bareme = []
    for nom in SPECS:
        entree = niveaux.get(nom)
        if entree is None:
            hors_bareme.append(nom)
            continue
        suivant = palier(nom, entree["niveau"] + 1)
        print(
            f"  {nom:<34} niveau {entree['niveau']:<4} "
            f"{entree['palier'].resume():<20} "
            f"(le {entree['date']}) -> prochain : {suivant.resume()}"
        )

    if hors_bareme:
        titre("HORS BARÈME (aucune performance n'atteint le palier 1)")
        for nom in hors_bareme:
            print(f"  {nom:<34} palier 1 = {palier(nom, 1).resume()}")

    sans_spec = [nom for nom in CATALOGUE_EXERCICES if not est_suivi_par_le_moteur(nom)]
    if sans_spec:
        titre("SANS SPEC (non suivis par le moteur)")
        for nom in sans_spec:
            print(f"  {nom}")


def afficher_cibles_actuelles(seances):
    """Ce que valent les objectifs actuels des séances, traduits en niveaux."""
    titre("CIBLES ACTUELLES DES SÉANCES, TRADUITES EN NIVEAUX")
    niveaux = niveaux_par_exercice(seances)

    for nom_seance, seance in sorted(catalogue().items()):
        lignes = []
        for exercice in seance["exercices"]:
            nom = exercice["nom"]
            if not est_suivi_par_le_moteur(nom):
                continue
            cible = (
                exercice.get("duree")
                if unite(nom) == "secondes"
                else exercice.get("repetitions")
            )
            niveau_cible = niveau_pour(
                nom,
                exercice.get("poids") or 0,
                exercice.get("series") or 0,
                cible or 0,
            )
            entree = niveaux.get(nom)
            acquis = entree["niveau"] if entree else None
            lignes.append(
                f"    {nom:<34} cible {exercice.get('series')}x{cible}"
                f"@{exercice.get('poids')}kg = niveau {niveau_cible} "
                f"| acquis : {acquis}"
            )
        if lignes:
            print(f"  == {nom_seance}")
            print("\n".join(lignes))


def afficher_lignes_ignorees(seances):
    """Lignes d'historique qu'aucun palier ne valide : le détail qui explique
    un « hors barème » (trop peu de séries, poids nul, mode incompatible)."""
    titre("LIGNES D'HISTORIQUE SANS NIVEAU")
    compteur = {}
    for seance in seances:
        for exercice in seance.get("exercices", []):
            if not est_suivi_par_le_moteur(exercice["nom"]):
                continue
            if niveau_prouve_par(exercice) is not None:
                continue
            series = [
                serie
                for serie in exercice.get("series_detaillees", [])
                if serie.get("completee")
            ]
            cle = (
                exercice["nom"],
                exercice.get("mode"),
                len(series),
                exercice.get("poids") or 0,
                min((serie.get("repetitions", 0) for serie in series), default=0),
                min((serie.get("duree", 0) for serie in series), default=0),
            )
            compteur[cle] = compteur.get(cle, 0) + 1

    for (nom, mode, nb, poids, reps, duree), occurrences in sorted(compteur.items()):
        print(
            f"  {nom:<34} {mode:<12} {nb} série(s) @{poids}kg "
            f"min={reps} reps / {duree:.0f} s  (x{occurrences})"
        )


def afficher_decision_objectifs(seances):
    """Comment chaque objectif a été décidé : repère, réussite, ressenti.

    C'est la lecture qui explique un objectif surprenant. Les trois colonnes
    se lisent ensemble : `demandé` est le palier de la dernière séance,
    `issue` dit s'il a été validé, `ressenti` ce qui a été répondu, et
    `objectif` en est la somme. Un exercice absent d'ici est piloté par la
    règle de repli (premier palier non validé) faute de repère exploitable.
    """
    titre("DÉCISION DE L'OBJECTIF (repère, réussite, ressenti)")
    reperes = evaluation(seances)

    for nom in sorted(SPECS):
        repere = reperes.get(nom)
        if repere is None:
            print(f"  {nom:<34} pas de repère : premier palier non validé")
            continue
        issue = "réussi" if repere["reussi"] else "échoué"
        ressenti = repere["ressenti"] or "—"
        vise = palier(nom, repere["vise"])
        print(
            f"  {nom:<34} demandé {repere['base']:>3} ({issue:>7})"
            f" | ressenti {ressenti:<12} {repere['ajustement']:+d}"
            f" -> objectif {repere['vise']:>3}  {vise.resume() if vise else '?'}"
        )


def choisir_profil(argument=None):
    """Connecte un profil : celui demandé, sinon le premier."""
    profils = lister_utilisateurs()
    if not profils:
        raise SystemExit(
            "Aucun profil : lance l'application une fois pour en créer un."
        )
    if argument is None:
        profil = profils[0]
    else:
        profil = next(
            (
                candidat
                for candidat in profils
                if str(candidat["id"]) == argument
                or candidat["nom"].lower() == argument.lower()
            ),
            None,
        )
        if profil is None:
            noms = ", ".join(candidat["nom"] for candidat in profils)
            raise SystemExit(f"Profil inconnu : {argument}. Disponibles : {noms}")
    connecter(profil["id"])
    return profil


def principal(argument=None):
    profil = choisir_profil(argument)
    seances = recuperer_historique()
    print(f"Profil : {profil['nom']}")
    print(f"{len(seances)} séance(s) dans l'historique.")
    afficher_bareme()
    verifier_monotonie_volume()
    afficher_niveaux(seances)
    afficher_lignes_ignorees(seances)
    afficher_decision_objectifs(seances)
    afficher_cibles_actuelles(seances)


if __name__ == "__main__":
    principal(sys.argv[1] if len(sys.argv) > 1 else None)
