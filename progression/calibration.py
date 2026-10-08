"""De la note d'athlète d'un profil au palier de départ de ses exercices.

Un nouveau profil n'a pas d'historique, donc pas de niveau : `niveau_pour`
renvoie None sur tous les exercices et le moteur n'a rien à lui proposer. Ce
trou était comblé par un **test au maximum** joué en séance ; il l'est
désormais par **une seule note**, de 1 à 10, que la personne se donne à
l'accueil (« à quel point es-tu athlète ? »). Une note générale et non une par
exercice : personne ne sait se situer au rowing penché avant d'en avoir fait,
alors que tout le monde sait dire s'il fait du sport.

**La note se traduit par les bornes de ligue, pas par un numéro de niveau.**
Le niveau 20 des pompes et le niveau 20 du curl ne demandent pas le même
effort ; les bornes de ligue, elles, ont été posées à la main exercice par
exercice pour vouloir dire la même chose partout (`ligues.seuils_exercice`).
Une note désigne donc un **rang de ligue** (`RANGS_PAR_NOTE`), et le palier de
départ d'un exercice est le premier qui atteint le volume de cette borne
(`paliers.niveau_pour_volume`, la règle même des programmes). Le matériel
déclaré entre en jeu de lui-même : l'échelle de poids est celle du profil.

**Rien n'est ancré.** La note fixe un *objectif*, jamais un *niveau* : un
exercice jamais fait reste « hors barème » tant qu'une séance ne prouve rien,
exactement comme avant. C'est ce qui permet à une note mal estimée de se
corriger d'elle-même — le ressenti et la réussite prennent la main dès la
première séance jouée.

Trois règles en découlent, et elles ne s'appliquent pas aux mêmes exercices.

1. **Un exercice jamais fait** part du palier de la note *effective*
   (`note_effective`).
2. **La note monte toute seule** quand l'historique récent la dépasse
   nettement (`note_mesuree`) — et redescend sur la note déclarée quand il
   fléchit, jamais en dessous. Elle ne sert, elle aussi, qu'aux exercices
   jamais faits : si elle monte, c'est que la plupart des exercices sont déjà
   au-dessus.
3. **Une note relevée à la main** pose son palier de départ en *plancher* de
   la prochaine séance des exercices déjà faits qui sont en dessous
   (`niveau_plancher`). Une seule fois : le repère `relevee_apres` est
   l'identifiant de la dernière séance au moment de la hausse, et une séance
   jouée après lui redonne la main au repère ordinaire. Une baisse efface ce
   repère et ne touche que les exercices jamais faits.

Les réglages vivent dans `progression/reglages.json`, clé `note_athlete` :

- `rangs` — un rang de ligue par note, de la note 1 à la note 10. **0 veut dire
  « le palier 1 »**, c'est-à-dire le bas du barème, qui appartient au débutant.
  La table doit croître : une note plus haute ne peut pas démarrer plus bas.
  Elle ne se juge pas sur ses nombres mais sur les paliers qu'elle donne, ce
  que montre `dev/baremes.html`. Démarrer trop haut décourage et fait échouer
  toutes les séries ; démarrer trop bas se corrige en une séance — en cas de
  doute, prudence.
- `part_exercices` — la part des exercices récents qui doivent atteindre une
  note pour qu'elle soit « mesurée ». Deux tiers : « la plupart ». **Un peu
  sous 2/3 et jamais au-dessus** : à 0,667, quatre exercices sur six donnaient
  4,002 et ne comptaient pas — « deux tiers » en exigeait cinq. Le produit
  n'étant alors jamais entier, `>=` et `>` y rendent la même réponse ; c'est
  le sabotage de cette comparaison, resté vert, qui l'a montré.
- `marge` — l'écart à la note déclarée à partir duquel la note mesurée prend
  le dessus. Sans marge, un bon jour ferait monter la note.
- `exercices_min` — en dessous de ce nombre d'exercices récents, rien n'est
  mesuré : deux exercices ne disent rien d'un athlète.

`CIBLE_TEST` survit au test qu'elle servait : l'historique et les ancrages
« Test en séance » en contiennent, et `ressenti.est_serie_de_test` doit
continuer de les reconnaître — une ligne de 1 x 999 relue comme un objectif
ordinaire ferait proposer un palier démesuré.
"""

from progression.ligues import seuils_exercice
from progression.niveaux import niveau_prouve_par
from progression.paliers import est_suivi_par_le_moteur, niveau_pour_volume
from progression.reglages import REGLAGES

#: Cible des anciennes séries de test : un plafond inatteignable. Plus aucune
#: séance n'en produit ; la constante ne sert qu'à relire l'historique.
CIBLE_TEST = 999

NOTE_MIN = 1
NOTE_MAX = 10

#: Ce que veulent dire quelques crans de l'échelle, pour se situer sans
#: deviner. Du texte, donc ici et pas dans `reglages.json` : ce qui se règle
#: est la table des rangs, pas la phrase. Exporté tel quel au navigateur, pour
#: que les deux accueils posent exactement la même question.
REPERES_NOTE = {
    1: "Je ne fais pas de sport",
    3: "Je bouge un peu, sans entraînement régulier",
    5: "Je fais du sport une à deux fois par semaine",
    7: "Je m'entraîne régulièrement, renforcement compris",
    10: "Je m'entraîne dur depuis des années",
}

_NOTE = REGLAGES["note_athlete"]

#: Un rang de ligue par note (0 = palier 1). Voir la docstring du module.
RANGS_PAR_NOTE = tuple(_NOTE["rangs"])
PART_EXERCICES = _NOTE["part_exercices"]
MARGE = _NOTE["marge"]
EXERCICES_MIN = _NOTE["exercices_min"]


def note_valide(note):
    """La note est-elle un entier de 1 à 10 ? Un booléen n'en est pas un."""
    return (
        isinstance(note, int)
        and not isinstance(note, bool)
        and NOTE_MIN <= note <= NOTE_MAX
    )


def note_du_profil(profil=None):
    """`{"declaree", "relevee_apres"}` du profil donné, ou du profil connecté.

    Une note absente vaut None : c'est « pas encore demandée », que l'accueil
    rattrape à la prochaine ouverture — en attendant, le moteur part du bas du
    barème, comme il le faisait avant la note.
    """
    if profil is None:
        from core.utilisateur import utilisateur_connecte

        profil = utilisateur_connecte() or {}
    return {
        "declaree": profil.get("note_athlete"),
        "relevee_apres": profil.get("note_relevee_apres"),
    }


def niveau_de_depart(nom_exercice, note):
    """Niveau du palier sur lequel un exercice jamais fait démarre, pour cette note.

    Retourne None pour un exercice sans barème. Une note absente ou invalide
    rend le palier 1 : faute de savoir, on part du bas, qui appartient au
    débutant.
    """
    if not est_suivi_par_le_moteur(nom_exercice):
        return None
    if not note_valide(note):
        return 1
    rang = RANGS_PAR_NOTE[note - 1]
    if rang <= 0:
        return 1
    seuils = seuils_exercice(nom_exercice)
    if not seuils:
        return 1
    # Une table de rangs plus longue que les ligues sature au dernier rang,
    # comme `rang_pour_volume` : le barème est ouvert, le volume existe.
    borne = seuils[min(rang, len(seuils)) - 1]
    return niveau_pour_volume(nom_exercice, borne) or 1


def niveaux_recents(seances, ancrages):
    """Ce que la dernière séance de chaque exercice a prouvé, `{nom: niveau|None}`.

    Pour la note mesurée, qui doit **suivre** l'historique et non le record :
    un exercice dont la dernière séance a échoué compte pour ce qu'elle a
    prouvé, pas pour le meilleur de toujours. Mêmes lignes que le repère du
    ressenti (`ressenti._lignes_retenues`) : une séance abandonnée ne dit rien,
    une séance antérieure à un ancrage est périmée — c'est alors l'ancrage qui
    fait foi. Un exercice présent avec None a été joué sans rien prouver : il
    compte dans le total, il n'atteint aucune note.
    """
    from progression.ressenti import _lignes_retenues

    recents = {}
    tranches = set()  # exercices dont la dernière séance est déjà trouvée
    # `recuperer_historique` rend la séance la plus récente en tête.
    for seance in seances:
        vus_ici = set()
        for exercice in _lignes_retenues(seance, ancrages):
            nom = exercice.get("nom")
            if not est_suivi_par_le_moteur(nom) or nom in tranches:
                continue
            vus_ici.add(nom)
            niveau = niveau_prouve_par(exercice)
            # Deux lignes du même exercice dans une séance : la meilleure,
            # comme partout dans `progression/`, jamais une somme.
            if niveau is not None and (recents.get(nom) or 0) < niveau:
                recents[nom] = niveau
            else:
                recents.setdefault(nom, None)
        tranches |= vus_ici

    for nom, ancrage in ancrages.items():
        if est_suivi_par_le_moteur(nom) and nom not in recents:
            recents[nom] = ancrage["niveau"]
    return recents


def note_mesuree(seances, ancrages):
    """La plus haute note que l'historique récent atteint, ou None.

    Une note est atteinte quand au moins `PART_EXERCICES` des exercices récents
    sont au moins à son palier de départ. Il faut `EXERCICES_MIN` exercices
    récents pour mesurer quoi que ce soit.
    """
    recents = niveaux_recents(seances, ancrages)
    if len(recents) < EXERCICES_MIN:
        return None

    mesuree = None
    for note in range(NOTE_MIN, NOTE_MAX + 1):
        atteints = sum(
            1
            for nom, niveau in recents.items()
            if niveau is not None and niveau >= niveau_de_depart(nom, note)
        )
        if atteints >= PART_EXERCICES * len(recents):
            mesuree = note
    return mesuree


def note_effective(declaree, mesuree):
    """La note qui fixe le départ des exercices jamais faits.

    La note mesurée ne prend le dessus qu'à partir de `MARGE` crans au-dessus
    de la note déclarée ; en deçà, c'est la déclaration qui fait foi. La note
    effective ne descend donc jamais sous ce que la personne a dit d'elle-même.
    """
    if not note_valide(declaree):
        return mesuree
    if mesuree is not None and mesuree >= declaree + MARGE:
        return mesuree
    return declaree


def niveau_plancher(nom_exercice, note, repere):
    """Niveau en dessous duquel la prochaine séance de cet exercice ne descend pas.

    None quand aucune hausse n'est en attente : pas de repère, ou une séance de
    l'exercice jouée depuis (`repere` est le repère du ressenti, dont
    `seance_id` dit quand l'exercice a été jugé pour la dernière fois). Le
    plancher vaut le départ de la note **déclarée** — c'est elle qui a été
    relevée —, jamais celui de la note mesurée.
    """
    relevee_apres = note.get("relevee_apres")
    if relevee_apres is None or not note_valide(note.get("declaree")):
        return None
    if repere and (repere.get("seance_id") or 0) > relevee_apres:
        return None
    return niveau_de_depart(nom_exercice, note["declaree"])


def etat_note(note, seances, ancrages):
    """Ce qu'un écran de profil affiche de la note : déclarée, mesurée, effective."""
    mesuree = note_mesuree(seances, ancrages)
    return {
        "declaree": note.get("declaree"),
        "mesuree": mesuree,
        "effective": note_effective(note.get("declaree"), mesuree),
    }
