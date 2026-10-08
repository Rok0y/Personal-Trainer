"""Jouer une variante plus facile à la place d'un mouvement, et en revenir.

Le catalogue décrit déjà ses variantes (`Exercice.variante_facile` /
`variante_difficile`) : pompes → pompes sur les genoux → pompes inclinées,
planche → planche sur les genoux, squat → squat sur chaise. Chacune a son
propre barème. Ce qui manquait est le **branchement** : une séance qui ne
contient que « Pompes » laissait bloqué quelqu'un qui n'en fait pas une, parce
qu'un « trop dur » au palier 1 ne peut plus rien faire descendre
(`ressenti.evaluation` borne l'objectif à 1).

**Une substitution est une préférence du profil, jamais une donnée de
séance.** Les séances sont partagées entre profils, alors que « je ne sais pas
encore faire une pompe » ne vaut que pour une personne — même raison que celle
qui a fait de `cible_manuelle` une liste d'identifiants. La table vit donc sur
le profil (`utilisateurs.variantes`, JSON `{original: joué}`), et vaut pour
toutes les séances où l'original apparaît. La clé est toujours le mouvement
**écrit dans la séance** : descendre encore réécrit la valeur, remonter jusqu'à
l'original efface l'entrée.

**Elle ne doit jamais atteindre le fichier des séances.** Le formulaire
« Objectifs » de l'accueil et les éditeurs réécrivent *tous* les blocs : un bloc
affiché avec la variante y écrirait son nom dans une séance partagée — ou y
poserait les cibles de la variante sous le nom de l'original, que
`marquer_cibles_manuelles` marquerait aussitôt comme figées. D'où deux
fonctions et non une : `appliquer_au_circuit`, appelée sur le seul chemin **de
jeu** (`session.seances.creer_seance`, `demarrer()` dans l'application), et
`substitution`, que l'affichage interroge sans rien réécrire.

L'historique enregistre le nom **réellement joué** : la variante gagne d'elle-
même son niveau, ses ligues et son XP, et rien dans `niveaux.py` ne change.

**On remonte la chaîne tout seul** (`montees`), un cran à la fois : quand une
séance menée à son terme prouve la performance de retour de la variante jouée
— `variantes.retour` dans `reglages.json`, `{nom de la variante: [séries,
cible]}` —, la table passe à la variante plus difficile, et l'entrée
s'efface quand on retrouve le mouvement écrit. **Une performance, jamais un
numéro de niveau** (personne ne sait ce que vaut « niveau 12 ») : `niveau_pour`
la traduit sur le barème de la variante. Une variante absente de cette table
ne monte jamais, ce qui reste possible à la main (« Ta version », la fiche).
Le cran suivant part du palier 1 (`objectifs.objectifs_par_exercice`) : on
vient de maîtriser le précédent, on est au bas de celui-ci.

Toutes les fonctions sont pures, dépendances injectées : le catalogue est un
dictionnaire `{nom: {"variante_facile", "variante_difficile",
"analyse_la_pose"}}` — ce que `Exercice.fiche()` rend déjà —, et la jumelle
`web/static/js/variantes.js` le reçoit de `mouvements.json`.
"""

from progression.paliers import est_suivi_par_le_moteur, niveau_pour, unite
from progression.reglages import REGLAGES

MODE_ECHAUFFEMENT = "echauffement"

#: Performance qui fait proposer le retour au mouvement plus dur.
SEUILS_RETOUR = {
    nom: tuple(performance)
    for nom, performance in REGLAGES.get("variantes", {}).get("retour", {}).items()
}


def normaliser(variantes):
    """La table d'un profil sous une forme toujours exploitable.

    « Pas de table », une valeur illisible et une table vide se valent : il
    n'y a alors aucune variante. Une entrée qui se désigne elle-même est
    retirée — elle ne remplacerait rien.
    """
    if not isinstance(variantes, dict):
        return {}
    return {
        str(original): str(joue)
        for original, joue in variantes.items()
        if original and joue and original != joue
    }


def catalogue_depuis(mouvements):
    """Le catalogue de ce module, depuis des `Exercice` (`{nom: Exercice}`)."""
    return {
        nom: {
            "variante_facile": exercice.variante_facile,
            "variante_difficile": exercice.variante_difficile,
            "analyse_la_pose": exercice.detection is not None,
        }
        for nom, exercice in mouvements.items()
    }


def _compatibles(original, joue):
    """Une variante doit se mesurer dans la même unité que l'original.

    Un bloc en répétitions ne peut pas recevoir un maintien en secondes : le
    mode du bloc ne bouge pas, seul le mouvement change.
    """
    if est_suivi_par_le_moteur(original) and est_suivi_par_le_moteur(joue):
        return unite(original) == unite(joue)
    return True


def _jouable(nom, catalogue):
    fiche = catalogue.get(nom)
    return bool(fiche and fiche.get("analyse_la_pose"))


def substitution(nom, mode, variantes, catalogue):
    """Le mouvement à jouer à la place de `nom` dans un bloc, ou None.

    None quand le profil n'a rien retenu pour ce mouvement, pour un
    échauffement (il ne compte nulle part, rien à faciliter), et quand la
    variante retenue ne saurait pas jouer ce bloc — inconnue du catalogue,
    sans détection, ou dans une autre unité. Un refus laisse jouer l'original
    plutôt que de casser la séance.
    """
    if mode == MODE_ECHAUFFEMENT:
        return None
    joue = normaliser(variantes).get(nom)
    if not joue or not _jouable(joue, catalogue) or not _compatibles(nom, joue):
        return None
    return joue


def appliquer_au_circuit(circuit, variantes, catalogue, exercice_pour):
    """Remplace, dans une séance **qu'on va jouer**, les mouvements substitués.

    `exercice_pour(nom)` rend l'`Exercice` à jouer. Chaque bloc remplacé garde
    le nom de l'original dans `remplace`, et perd sa marque de cible figée :
    elle concernait l'original, la variante est rendue au moteur. Un
    `entrelace_avec` qui nommait un mouvement remplacé est réécrit — les
    paires du circuit sont déjà calculées par index, mais c'est ce nom qui
    part en base.

    À appeler **avant** `objectifs.appliquer_a_circuit`, pour que l'objectif
    soit celui de la variante. Jamais sur des blocs destinés au disque.
    """
    remplaces = {}
    for bloc in circuit.exercices:
        joue = substitution(bloc.exercice.nom, bloc.mode, variantes, catalogue)
        if joue is None:
            continue
        remplaces[bloc.exercice.nom] = joue
        bloc.remplace = bloc.exercice.nom
        bloc.exercice = exercice_pour(joue)
        bloc.cible_manuelle = None
    for bloc in circuit.exercices:
        if bloc.entrelace_avec in remplaces:
            bloc.entrelace_avec = remplaces[bloc.entrelace_avec]
    return circuit


def chaine(original, catalogue):
    """L'original puis ses variantes de plus en plus faciles.

    Suit `variante_facile` jusqu'au bout, et s'arrête sur une boucle plutôt
    que de tourner : le catalogue n'en a pas, mais une faute de saisie en
    créerait une.
    """
    noms = [original]
    suivant = (catalogue.get(original) or {}).get("variante_facile")
    while suivant and suivant not in noms and suivant in catalogue:
        noms.append(suivant)
        suivant = (catalogue.get(suivant) or {}).get("variante_facile")
    return noms


def versions(original, mode, catalogue):
    """Les mouvements entre lesquels choisir pour un bloc, avant de le jouer.

    L'original d'abord, puis chaque variante de sa chaîne que `definir`
    accepterait — même filtre, pour qu'aucun choix proposé à l'écran ne soit
    refusé à l'écriture. Vide quand il n'y a rien à choisir : un échauffement,
    un mouvement inconnu, ou une chaîne réduite à l'original.
    """
    if mode == MODE_ECHAUFFEMENT or original not in catalogue:
        return []
    noms = [original] + [
        nom
        for nom in chaine(original, catalogue)[1:]
        if _jouable(nom, catalogue) and _compatibles(original, nom)
    ]
    return noms if len(noms) > 1 else []


def definir(variantes, original, joue, catalogue):
    """La table après « pour `original`, je joue `joue` ».

    Point d'entrée unique de l'écriture, des deux applications : `joue` à None
    ou égal à l'original efface l'entrée. Sinon il doit appartenir à la chaîne
    de l'original, se jouer, et se mesurer dans la même unité — c'est ce qui
    empêche une requête de faire jouer un curl à la place d'une pompe. Lève
    sur un refus.
    """
    nouvelles = normaliser(variantes)
    if joue is None or joue == original:
        nouvelles.pop(original, None)
        return nouvelles
    if joue not in chaine(original, catalogue)[1:]:
        raise ValueError(f"{joue} n'est pas une variante de {original}")
    if not _jouable(joue, catalogue) or not _compatibles(original, joue):
        raise ValueError(f"{joue} ne peut pas remplacer {original}")
    nouvelles[original] = joue
    return nouvelles


def original_de(nom_joue, variantes):
    """Le mouvement que `nom_joue` remplace pour ce profil, ou None."""
    for original, joue in normaliser(variantes).items():
        if joue == nom_joue:
            return original
    return None


def retour_prouve_par(ligne):
    """Cette ligne d'historique prouve-t-elle la performance de retour ?

    Lue sur **la séance**, jamais sur le record : un retour en arrière vers la
    variante, alors que son record dépasse déjà le seuil, remonterait sinon de
    lui-même à la séance suivante — « rester sur cette version » ne tiendrait
    pas une séance. Mêmes règles que tout niveau : maillon faible, séries
    menées au bout seulement (`niveaux.niveau_prouve_par`).
    """
    from progression.niveaux import niveau_prouve_par

    nom = ligne.get("nom")
    seuil = SEUILS_RETOUR.get(nom)
    if seuil is None:
        return False
    requis = niveau_pour(nom, 0, seuil[0], seuil[1])
    prouve = niveau_prouve_par(ligne)
    return requis is not None and prouve is not None and prouve >= requis


def montees(variantes, seance, catalogue):
    """La table après cette séance, et les crans qu'elle a fait monter.

    `(table, [{"original", "depuis", "vers"}])`. Pour chaque mouvement joué
    à la place d'un autre (`original_de`) dont la ligne prouve la performance
    de retour, la clé passe à `variante_difficile` ; quand c'est l'original
    lui-même, l'entrée disparaît. **Un cran par séance et par clé**, jamais
    deux : on joue le nouveau cran avant d'en franchir un autre.

    Une séance **abandonnée** ne fait rien monter — elle ne prouve rien, même
    règle que l'entérinement des cibles figées. Une bascule vers une variante
    plus facile en pleine séance non plus, et sans règle de plus : la variante
    jouée n'est alors pas celle de la table, donc `original_de` ne la reconnaît
    pas, et la ligne de la table, quittée en cours de route, est incomplète.

    Pure, comme le reste du module : l'appelant écrit la table du profil.
    """
    table = normaliser(variantes)
    seance = seance or {}
    if seance.get("statut") == "abandoned":
        return table, []
    faites = []
    vues = set()
    for ligne in seance.get("exercices", []):
        nom = ligne.get("nom")
        cle = original_de(nom, table)
        if cle is None or cle in vues:
            continue
        dur = (catalogue.get(nom) or {}).get("variante_difficile")
        if not dur or not retour_prouve_par(ligne):
            continue
        try:
            table = definir(table, cle, dur, catalogue)
        except ValueError:
            continue
        vues.add(cle)
        faites.append({"original": cle, "depuis": nom, "vers": dur})
    return table, faites


def propositions(seances, jugements, variantes, catalogue):
    """Ce qu'il faut proposer sous chaque ligne d'historique.

    `{seance_id: {nom: {"sens", "original", "vers"}}}`, où `sens` vaut
    `"facile"` ou `"difficile"`, `original` est la clé de la table et `vers`
    le mouvement proposé. `seances` est l'historique, le plus récent en tête ;
    `jugements` est `ressenti.jugements_par_seance(seances)`.

    Une règle, et une restriction. **Plus facile** sous un exercice raté,
    quand c'était au palier 1 — le seul cas où « trop dur » n'a plus rien à
    faire descendre — ou quand on est passé à sa variante pendant la séance
    (la variante y a sa ligne). Le mouvement remplacé se retrouve par la
    table, puis par la séance elle-même : après une bascule en séance, la
    ligne de la variante doit proposer de descendre **la clé de l'original**,
    pas d'en créer une sous son propre nom, qui ne remplacerait rien dans
    aucune séance.

    Il y avait une seconde règle, « plus dur » une fois la performance de
    retour prouvée : `montees` la remplace, et la garder reproposerait la
    montée juste après qu'on a choisi de rester sur la variante.

    On ne propose que sur la **dernière** séance où l'exercice apparaît : une
    vieille ligne ratée reproposerait sinon une variante qu'on a quittée
    depuis. Et une seule proposition par clé et par séance, sur la ligne la
    plus avancée : après une bascule en séance, si la variante a raté elle
    aussi, c'est elle qu'il faut faciliter.
    """
    variantes = normaliser(variantes)
    vues = set()
    resultat = {}
    for seance in seances:
        identifiant = seance.get("id")
        lignes = [exercice["nom"] for exercice in seance.get("exercices", [])]
        par_cle = {}
        for nom in lignes:
            if nom in vues:
                continue
            proposition = _proposition(
                nom, lignes, jugements.get(identifiant, {}).get(nom),
                variantes, catalogue,
            )
            if proposition is not None:
                # La dernière ligne d'une même clé l'emporte : c'est la plus
                # avancée dans la chaîne.
                par_cle[proposition["original"]] = (nom, proposition)
        vues.update(lignes)
        if par_cle:
            resultat[identifiant] = {nom: prop for nom, prop in par_cle.values()}
    return resultat


def _racine(nom, lignes, variantes, catalogue):
    """La clé de table d'un mouvement, vu depuis une séance."""
    original = original_de(nom, variantes)
    if original is not None:
        return original
    for autre in lignes:
        if autre != nom and (catalogue.get(autre) or {}).get("variante_facile") == nom:
            return _racine(autre, [l for l in lignes if l != nom], variantes, catalogue)
    return nom


def _proposition(nom, lignes, jugement, variantes, catalogue):
    if jugement is None or jugement.get("reussi"):
        return None
    facile = (catalogue.get(nom) or {}).get("variante_facile")
    if not facile or not (jugement.get("base") == 1 or facile in lignes):
        return None
    cle = _racine(nom, lignes, variantes, catalogue)
    if variantes.get(cle) == facile:
        return None
    try:
        definir(variantes, cle, facile, catalogue)
    except ValueError:
        return None
    return {"sens": "facile", "original": cle, "vers": facile}


def via_variante(nom, variantes, niveaux):
    """Ce qu'un programme dit d'une exigence jouée sous une variante.

    `{"nom", "niveau"}` ou None. L'avancement de l'exigence n'en est pas
    modifié : le volume d'une variante ne se compare pas à celui du mouvement
    complet, et inventer une équivalence entre deux barèmes serait mentir sur
    la distance qui reste.
    """
    joue = normaliser(variantes).get(nom)
    if joue is None:
        return None
    return {"nom": joue, "niveau": (niveaux.get(joue) or {}).get("niveau")}


def catalogue_des_variantes():
    """Le catalogue réel, pour les appelants Python (import différé)."""
    from session.seances import catalogue_mouvements

    return catalogue_depuis(catalogue_mouvements())


def variantes_du_profil(profil=None):
    """La table du profil connecté (ou de `profil`), normalisée."""
    if profil is None:
        from core.utilisateur import utilisateur_connecte

        profil = utilisateur_connecte()
    return normaliser((profil or {}).get("variantes"))
