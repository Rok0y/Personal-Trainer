"""Pose la seance « Full body sans materiel » et le programme qui la pilote.

Un full body jouable sans un gramme de fonte : un tapis, une chaise, et c'est
tout. Ce que ce script ajoute est **de la donnee** — il n'ecrit rien lui-meme,
il appelle les deux points d'entree qui savent deja le faire, et c'est ce qui
lui vaut d'etre rejouable sans risque.

Perimetre assume : poussee, jambes, gainage. **Pas de tirage** — les quatre
mouvements de dos du catalogue (les deux rowings, le rowing penche, l'oiseau)
exigent tous des halteres et aucun des seize echauffements n'en est un. Le
combler demanderait un nouvel `Exercice` avec sa detection Python *et* sa
jumelle JavaScript, une spec de bareme et des seuils de ligue ; la description
du programme le dit plutot que de le taire.

**L'ordre des deux ecritures porte tout le sens.** `enregistrer_programme`
appelle `synchroniser_seances`, qui *cree* une seance a partir des exigences
quand aucune ne correspond au libelle — une seance sans le moindre
echauffement, en repos 60/90. La seance existant deja sous exactement ce nom,
`seance_correspondante` la reconnait et bascule en **adoption** : rien n'est
modifie ni retire. Inverser les deux appels ne leverait aucune erreur, ca
donnerait simplement une seance nue.

Les cibles ecrites ici ne sont pas celles qui seront jouees : aucun bloc n'est
marque `cible_manuelle`, donc `objectifs.appliquer_a_circuit` les reecrit au
palier du moment a chaque chargement. Sur un profil neuf tout est a calibrer et
la premiere seance se joue en test. Ce fichier ne fait autorite que sur la
**structure** — quel exercice, quel mode, quels repos, quel entrelacement.

Usage :
    python -m scripts.creer_full_body --essai        # dit ce qu'il ferait
    python -m scripts.creer_full_body                # le fait
    python -m scripts.creer_full_body --profil Mimi  # sous un profil precis
"""

import argparse
import sys

from core.utilisateur import connecter
from historique.database import initialiser, lister_utilisateurs
from progression.objectifs import appliquer_a_blocs
from progression.programmes import enregistrer_programme
from session.controleur import SessionManager
from session.seances import construire_circuit

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NOM_SEANCE = "Full body sans matériel"
CLE_PROGRAMME = "full-body-sans-materiel"

#: Tete de seance : de la tete aux pieds, puis on active. Tous en mode
#: `echauffement`, donc au chrono — leur detection est facultative et n'alimente
#: que l'affichage, un echauffement ne devant jamais pouvoir se bloquer.
ECHAUFFEMENT = [
    ("Rotation du cou", 20),
    ("Rotation des épaules", 30),
    ("Rotation des poignets", 20),
    ("Rotation des genoux", 30),
    ("Rotation des chevilles", 30),
    ("Jumping jacks", 30),
    ("Squat lent", 30),
]

#: Le travail. `poids` a 0 partout : c'est ce qui rend la seance jouable sans
#: halteres, et le bareme de Squat et des deux fentes vient d'etre ouvert pour
#: l'accepter (`paliers.charge_facultative`).
#:
#: Ce sont les mouvements complets, pas les variantes assistees. Le filet n'a
#: pas a etre ecrit ici : `Pompes` declare `variante_facile="Pompes sur les
#: genoux"`, `Squat` declare `Squat sur chaise`, et le test de calibration
#: redirige de lui-meme qui ne tient pas le premier palier.
#:
#: (exercice, mode, series, cible, repos_apres, entrelace_avec)
TRAVAIL = [
    ("Pompes", "repetitions", 4, 8, 90, None),
    ("Squat", "repetitions", 4, 12, 90, None),
    ("Fente droite", "repetitions", 4, 8, 45, "Fente gauche"),
    ("Fente gauche", "repetitions", 4, 8, 90, None),
    ("Crunches", "repetitions", 3, 12, 90, None),
    ("Gainage planche", "maintien", 3, 20, 90, None),
    (
        "Gainage planche laterale droite",
        "maintien",
        1,
        15,
        45,
        "Gainage planche laterale gauche",
    ),
    ("Gainage planche laterale gauche", "maintien", 1, 15, 0, None),
]

#: L'objectif de **fin** de programme, pas de depart. `_cale_sur_le_bareme`
#: reecrit silencieusement chaque triplet sur le premier palier de meme volume :
#: ce qu'on relit apres enregistrement peut donc differer de ce qui est ecrit
#: ici, et c'est voulu — le bareme fait foi.
#:
#: (exercice, series, cible) — `poids` vaut 0 partout, par definition.
EXIGENCES = [
    ("Pompes", 4, 15),
    ("Squat", 4, 15),
    ("Fente droite", 4, 10),
    ("Fente gauche", 4, 10),
    ("Crunches", 4, 15),
    ("Gainage planche", 3, 45),
    ("Gainage planche laterale droite", 2, 30),
    ("Gainage planche laterale gauche", 2, 30),
]

DESCRIPTION = (
    "Un full body jouable sans matériel : un tapis, une chaise, et c'est tout. "
    "Il couvre la poussée, les jambes et le gainage. Pas de tirage — aucun "
    "mouvement de dos du catalogue ne se fait sans haltères."
)

#: `MODES_CIBLE_TEMPORELLE` decide quel champ est *joue*. Un bloc porte les deux
#: valeurs en meme temps, et seul le mode dit laquelle compte : ecrire la cible
#: dans le mauvais champ laisse une cible nulle dans l'unite jouee, donc une
#: serie achevee des la premiere image et une seance qui defile entierement en
#: une fraction de seconde. `construire_circuit` le refuse, et c'est pour ca
#: qu'on le lui fait relire meme en essai.
MODES_EN_SECONDES = ("maintien", "chrono", "amrap", "echauffement")


def _bloc(exercice, mode, series, cible, repos_entre, repos_apres, entrelace=None):
    en_secondes = mode in MODES_EN_SECONDES
    bloc = {
        "exercice": exercice,
        "mode": mode,
        "poids": 0,
        "series": series,
        "repetitions": 0 if en_secondes else cible,
        "duree": cible if en_secondes else 0,
        "repos_entre_series": repos_entre,
        "repos_apres": repos_apres,
        "commentaire": "",
    }
    if entrelace:
        bloc["entrelace_avec"] = entrelace
    return bloc


def blocs_de_la_seance():
    """La seance entiere, echauffement compris."""
    blocs = []
    for rang, (exercice, duree) in enumerate(ECHAUFFEMENT):
        dernier = rang == len(ECHAUFFEMENT) - 1
        # Le dernier echauffement porte le repos qui mene au travail : cinq
        # secondes entre deux rotations, une minute avant la premiere serie.
        blocs.append(
            _bloc(exercice, "echauffement", 1, duree, 30, 60 if dernier else 5)
        )
    for exercice, mode, series, cible, repos_apres, entrelace in TRAVAIL:
        blocs.append(_bloc(exercice, mode, series, cible, 45, repos_apres, entrelace))
    return _caler_sur_le_moteur(blocs)


def _caler_sur_le_moteur(blocs):
    """Remplace les cibles ecrites ci-dessus par celles que le moteur propose.

    **Sans ce passage, chaque bloc ressort marque `cible_manuelle`**, et c'est
    la pire facon de rater ce script. `marquer_cibles_manuelles` ne demande a
    personne de declarer une exception : elle *detecte* l'ecart entre la cible
    ecrite et le palier propose, et un profil qui a de l'historique sur ces
    mouvements en a forcement un. La marque est collante — le moteur ne
    toucherait plus jamais ces blocs, un badge orange resterait sur l'accueil,
    et rien n'expliquerait pourquoi. Mesure faite : les huit blocs de travail
    ressortaient marques.

    C'est la lecon deja payee par l'editeur de seances de l'application : **on
    part des valeurs du moteur, jamais de celles du fichier.** Les valeurs de
    `TRAVAIL` ne servent donc qu'a decrire la structure et a donner un repere
    lisible ; ce qui est ecrit sur le disque est ce que le moteur propose au
    moment ou on lance le script — et de toute facon reecrit a chaque
    chargement par `appliquer_a_circuit`.
    """
    appliquer_a_blocs(blocs)
    for bloc in blocs:
        # `test_max` est un drapeau d'**affichage** pose par le moteur sur les
        # exercices a calibrer (badge bleu « a tester »). Il n'existe dans aucun
        # bloc du fichier et n'a rien a y faire : la cible reelle d'un test est
        # posee sur le `Circuit`, jamais sur le dictionnaire, qui repart en
        # ecriture depuis le formulaire de l'accueil.
        bloc.pop("test_max", None)
    return blocs


def donnees_du_programme():
    return {
        "nom": "Full body sans matériel",
        "description": DESCRIPTION,
        "exigences": [
            {
                "seance": NOM_SEANCE,
                "exercice": exercice,
                "series": series,
                "cible": cible,
                "poids": 0,
            }
            for exercice, series, cible in EXIGENCES
        ],
    }


def _profil(nom_ou_id):
    """Le profil sous lequel ecrire, comme `scripts/script_niveaux.py`.

    Il en faut un : `creer_seance_personnalisee` appelle
    `marquer_cibles_manuelles`, qui relit l'historique, et `_profil_courant`
    **leve** sans personne de connectee plutot que de retomber sur un defaut.
    """
    profils = lister_utilisateurs()
    if not profils:
        raise SystemExit("Aucun profil en base : lance l'application une fois.")
    if nom_ou_id is None:
        return profils[0]
    for profil in profils:
        if str(profil["id"]) == str(nom_ou_id) or profil["nom"] == nom_ou_id:
            return profil
    connus = ", ".join(p["nom"] for p in profils)
    raise SystemExit(f"Profil « {nom_ou_id} » introuvable. Connus : {connus}")


def _decrire(blocs, programme, profil):
    print(f"Profil : {profil['nom']}")
    print(f"Séance « {NOM_SEANCE} » : {len(blocs)} blocs")
    for bloc in blocs:
        cible = bloc["duree"] or bloc["repetitions"]
        unite = " s" if bloc["duree"] else ""
        suffixe = f"   avec {bloc['entrelace_avec']}" if bloc.get("entrelace_avec") else ""
        print(
            f"  {bloc['exercice']:34} {bloc['mode']:12} "
            f"{bloc['series']}x{cible}{unite}{suffixe}"
        )
    print(f"Programme « {CLE_PROGRAMME} » : {len(programme['exigences'])} exigences")
    for exigence in programme["exigences"]:
        print(f"  {exigence['exercice']:34} {exigence['series']}x{exigence['cible']}")


def main():
    analyseur = argparse.ArgumentParser(description="Pose la séance full body.")
    analyseur.add_argument(
        "--essai",
        action="store_true",
        help="décrit ce qui serait écrit, sans rien écrire",
    )
    analyseur.add_argument("--profil", help="nom ou identifiant du profil")
    options = analyseur.parse_args()

    initialiser()
    profil = _profil(options.profil)
    connecter(profil["id"])

    blocs = blocs_de_la_seance()
    programme = donnees_du_programme()
    _decrire(blocs, programme, profil)

    # Valide dans les deux cas : un essai qui ne verifierait rien ne dirait pas
    # grand-chose de ce qui se passerait sans lui.
    construire_circuit(blocs)
    print()
    print("La séance passe les validations de construire_circuit.")

    if options.essai:
        print("Essai : rien n'a été écrit.")
        return

    SessionManager().creer_seance_personnalisee(NOM_SEANCE, blocs)
    print(f"Séance écrite sous « {NOM_SEANCE} ».")

    # **Ensuite**, jamais avant : c'est ce qui fait adopter la seance existante
    # au lieu d'en fabriquer une nue.
    enregistrer_programme(CLE_PROGRAMME, programme)
    print(f"Programme écrit sous « {CLE_PROGRAMME} ».")


if __name__ == "__main__":
    main()
