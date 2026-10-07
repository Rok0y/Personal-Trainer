import random
import time

from audio import annonces
from audio.annonces import normaliser_nom  # noqa: F401  (reexport historique)
from audio.lecteur import SILENCE_PRESENTATION, jouer, jouer_sequence  # noqa: F401

messages = {
    "rep": ["rep.wav"],
    "debut": ["debut.wav"],
    "avant_derniere": ["avant_derniere.wav"],
    "derniere_rep": ["derniere_rep.wav"],
    "fin_serie": ["fin_serie.wav"],
    "repos": ["repos.wav"],
    "changement_exercice": ["changement_exercice.wav"],
    "fin_seance": ["fin_seance.wav"],
    "debut_serie": ["debut_serie.wav"],
    "preparation": ["preparation.wav"],
    # Plusieurs variantes par cle : `coach()` en tire une au hasard, et c'est
    # ce qui evite d'entendre exactement la meme phrase a chaque serie. Le
    # suffixe `_1` existait pour ca depuis le debut, mais **les tables n'en
    # declaraient qu'une** alors que le disque en portait deux ou trois : les
    # prises etaient faites et ne sortaient jamais. Un fichier que rien ne
    # declare est aussi muet qu'un fichier absent, et se voit encore moins —
    # c'est le diff entre `audio/Fichiers/` et ce que le code reclame qui l'a
    # sorti, pas une exception.
    "encore_5": [
        "encore_5_1.wav",
        "encore_5_2.wav",
        "encore_5_3.wav",
    ],
    "encore_3": [
        "encore_3_1.wav",
        "encore_3_2.wav",
    ],
    "correction_gainage": [
        "correction_gainage_1.wav",
    ],
    "temps_20": [
        "temps_20_1.wav",
        "temps_20_2.wav",
        "temps_20_3.wav",
    ],
    "temps_10": [
        "temps_10_1.wav",
        "temps_10_2.wav",
        "temps_10_3.wav",
        "temps_10_4.wav",
    ],
    "temps_5": [
        "temps_5_1.wav",
        "temps_5_2.wav",
        "temps_5_3.wav",
    ],
    # Les trois dernieres secondes, dites une par une. Les fichiers etaient
    # sur le disque depuis le premier jet du coach, sans cle, sans priorite et
    # sans seuil qui les demande — exactement l'inverse de `temps_30`, qui
    # avait la priorite et rien d'autre. Rétablir un palier se fait avec sa
    # cle, son fichier **et** sa priorite, plus le seuil qui l'appelle dans
    # `annoncer_temps_restant` : les quatre, ou aucun.
    "temps_3": [
        "temps_3_1.wav",
    ],
    "temps_2": [
        "temps_2_1.wav",
    ],
    "temps_1": [
        "temps_1_1.wav",
    ],
    "repos_10": [
        "repos_10.wav",
    ],
    "repos_5": [
        "repos_5.wav",
    ],
    # Le fichier existait depuis toujours, la cle n'etait pas declaree :
    # `annoncer_temps_repos` demandait "repos_20" et `coach` sortait sans rien
    # jouer, le seuil des 20 secondes etant donc muet en silence.
    "repos_20": [
        "repos_20.wav",
    ],
    "bip": ["bip.wav"],
}


priorites = {
    "rep": 1,
    "debut_serie": 5,
    "avant_derniere": 5,
    "derniere_rep": 10,
    "fin_serie": 10,
    "repos": 8,
    "changement_exercice": 5,
    "fin_seance": 10,
    "encore_5": 4,
    "encore_3": 5,
    "correction_gainage": 7,
    # `temps_30` vivait ici sans fichier ni entrée dans `messages`, et sans
    # qu'aucun seuil ne la demande : `annoncer_temps_restant` s'arrête à 20.
    # Une priorité orpheline ne fait rien de mal, mais elle laisse croire qu'un
    # palier existe — c'est `scripts/verifier_annonces.py` qui l'a sortie, et
    # c'est exactement la classe de défaut pour laquelle il a été écrit :
    # `coach()` sortant en silence sur une clé inconnue, rien ne l'aurait dit.
    # Rétablir un seuil de 30 s se fait dans `annoncer_temps_restant`, avec sa
    # clé, son fichier et sa priorité — les trois, ou aucun.
    "temps_20": 6,
    "temps_10": 7,
    "temps_5": 8,
    # Meme rang que `temps_5` : c'est la meme famille, et un rang >= 5 vide
    # les petits sons en attente — donc le bip de la seconde en cours cede la
    # place au nombre prononce, plutot que de faire la queue devant lui.
    "temps_3": 8,
    "temps_2": 8,
    "temps_1": 8,
    "repos_20": 5,
    "repos_10": 6,
    "repos_5": 8,
    "bip": 2,
}

DELAIS_ENTRE_ANNONCES = {
    "correction_gainage": 8,
    # Le guidage de cadrage est réévalué à **chaque image** de la préparation :
    # sans ce délai, il se répéterait dès que la position vacille — le défaut
    # exact qu'avait la correction de gainage juste au-dessus. Six secondes
    # laissent le temps de faire le pas demandé avant qu'on le redemande.
    # Il n'y a pas de clé `messages` correspondante : la consigne est
    # **composée** de deux briques (`annonces.sequence_cadrage`), et seul le
    # délai est partagé. C'est pour ça que `Lecteur.sequence` accepte une clé.
    "cadrage": 6,
}

dernieres_annonces = {}


def coach(event, valeur=None):

    if event == "compteur":
        jouer(f"{valeur}.wav", 1)
        return

    if event not in messages:
        return

    maintenant = time.monotonic()
    delai = DELAIS_ENTRE_ANNONCES.get(event, 0)
    derniere_annonce = dernieres_annonces.get(event)

    if derniere_annonce is not None and maintenant - derniere_annonce < delai:
        return

    son = random.choice(messages[event])

    dernieres_annonces[event] = maintenant

    jouer(son, priorites.get(event, 5))


def annoncer_prochaine_etape(
    etape,
    nombre_halteres=0,
    orientation=None,
    amorce="prochain_exercice",
    silence_avant=0.0,
):
    """« Prochain exercice. Curl biceps droit. Prépare un haltère de 8 kilos. »

    **Composée de briques, plus cherchée toute faite.** Cette fonction cherchait
    un `.wav` pré-enregistré par combinaison exercice × poids × séries ×
    répétitions, dans `Fichiers/annonces_etapes/` : seize fichiers pour les
    seules combinaisons déjà jouées, et rien à dire dès qu'un objectif bougeait
    — c'est-à-dire à chaque progression. Elle retombait alors sur un
    « changement d'exercice » générique, ce qui est exactement le moment où
    l'annonce servait le plus.

    Elle en profite pour rappeler **comment se placer**, qui était l'autre
    information manquante d'un changement d'exercice : on se tourne, on sort
    son matériel, et ni l'un ni l'autre ne se lit sur un écran à trois mètres.

    `nombre_halteres` et `orientation` sont **injectés** : ils viennent de
    `session.seances` et du catalogue, qu'`audio.annonces` ne peut pas importer
    sans perdre sa légèreté d'imports (voir son en-tête).

    `amorce` l'est pour une raison de plus : elle dépend de la **place du bloc
    dans la séance**, que ce module ne voit pas. C'est `Circuit.amorce_annonce`
    qui la tranche, et l'appelant qui la transmet — une séance n'est pas un
    argument qu'un lecteur de sons ait à connaître.

    La priorité vaut celle d'un événement important : une annonce longue doit
    chasser les petits sons en attente plutôt que de faire la queue derrière
    eux, et surtout ne pas être coupée en son milieu.

    `silence_avant` est le blanc qui la précède. Il vaut `SILENCE_PRESENTATION`
    quand elle suit un « repose-toi » — les deux collées s'entendent comme une
    seule phrase hachée — et zéro en début de séance, où elle est la première
    chose dite et n'a rien derrière quoi respirer.
    """
    if etape is None:
        return

    sons = annonces.sequence_prochain_exercice(etape, nombre_halteres, amorce)
    sons += annonces.sequence_orientation(orientation)

    jouer_sequence(sons, priorites.get("changement_exercice", 5), silence_avant)


def annoncer_progression(repetitions, cible):
    restantes = cible - repetitions

    if restantes == 0:
        coach("fin_serie")
        return

    if restantes == 1:
        coach("avant_derniere")
        return

    if restantes == 3:
        coach("encore_3")
        return

    if restantes == 5:
        coach("encore_5")

    # **« À la moitié » a été retiré**, et ses trois prises restent sur le
    # disque sans clé ni priorité — la règle « la clé, le fichier et la
    # priorité : les trois, ou aucun » vaut dans ce sens-là aussi. Une clé qui
    # ne sert plus laisse croire qu'un palier existe, et c'est exactement ce
    # que `temps_30` avait fait croire. Elle tombait en plein milieu de la
    # série, entre deux chiffres, et n'apprenait rien qu'on ne sache déjà :
    # le coach comptait par-dessus lui-même.


def annoncer_temps_restant(bloc, secondes_restantes):

    if bloc.temps_restant_precedent is None:
        bloc.temps_restant_precedent = secondes_restantes
        return

    seuils = [
        (20, "temps_20"),
        (10, "temps_10"),
        (5, "temps_5"),
        (3, "temps_3"),
        (2, "temps_2"),
        (1, "temps_1"),
    ]

    for seuil, message in seuils:

        if bloc.temps_restant_precedent > seuil and secondes_restantes <= seuil:
            coach(message)
            break

    bloc.temps_restant_precedent = secondes_restantes


def annoncer_temps_repos(seance, state, annoncer_exercice=False):

    secondes_restantes = int(seance.temps_restant)

    if (
        not hasattr(seance, "repos_restant_precedent")
        or seance.repos_restant_precedent is None
    ):
        seance.repos_restant_precedent = secondes_restantes
        return

    seuils = [
        (20, "repos_20"),
        (10, "repos_10"),
        (5, "repos_5"),
    ]

    for seuil, message in seuils:

        if seance.repos_restant_precedent > seuil and secondes_restantes <= seuil:
            coach(message)
            break

    seance.repos_restant_precedent = secondes_restantes
