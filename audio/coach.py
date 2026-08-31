import random
import time

from audio.lecteur import jouer, jouer_texte


PHRASES = {
    "debut": ["C'est parti !"],
    "repos": ["Récupération."],
    "changement_exercice": ["Changement d'exercice."],
    "fin_seance": ["Séance terminée, beau travail !"],
    "debut_serie": ["Prêt ? Go !"],
    "preparation": ["Mets-toi en position."],
    "avant_derniere": ["Encore une !"],
    "derniere_rep": ["Dernière répétition !"],
    "fin_serie": ["Série terminée."],
    "mi_parcours": ["Tu es à la moitié."],
    "encore_5": ["Encore cinq."],
    "encore_3": ["Encore trois."],
    "correction_gainage": ["Attention, tu casses la position."],
    "temps_20": ["Vingt secondes."],
    "temps_10": ["Dix secondes."],
    "temps_5": ["Cinq secondes."],
    "repos_10": ["Dix secondes de repos."],
    "repos_5": ["Cinq secondes de repos."],
}

priorites = {
    "debut": 5, "debut_serie": 5, "avant_derniere": 5, "derniere_rep": 10,
    "fin_serie": 10, "repos": 8, "changement_exercice": 5, "fin_seance": 10,
    "mi_parcours": 3, "encore_5": 4, "encore_3": 5, "correction_gainage": 7,
    "temps_20": 6, "temps_10": 7, "temps_5": 8, "repos_10": 6, "repos_5": 8,
    "bip": 2,
}

DELAIS_ENTRE_ANNONCES = {"correction_gainage": 8}

dernieres_annonces = {}
dernieres_erreurs = {}
DELAI_ERREUR = 4  # secondes avant de répéter la même erreur de forme


def coach(event, valeur=None):

    if event == "compteur":
        jouer_texte(str(valeur), priorite=1)
        return

    if event == "bip":
        jouer("bip.wav", priorites.get("bip", 2))
        return

    if event not in PHRASES:
        return

    maintenant = time.monotonic()
    delai = DELAIS_ENTRE_ANNONCES.get(event, 0)
    derniere_annonce = dernieres_annonces.get(event)

    if derniere_annonce is not None and maintenant - derniere_annonce < delai:
        return

    dernieres_annonces[event] = maintenant
    texte = random.choice(PHRASES[event])
    jouer_texte(texte, priorites.get(event, 5))


def annoncer_erreur(message):
    """Prononce directement le texte renvoyé par une fonction 'erreurs' d'un exercice."""
    if not message:
        return

    maintenant = time.monotonic()
    derniere = dernieres_erreurs.get(message)

    if derniere is not None and maintenant - derniere < DELAI_ERREUR:
        return

    dernieres_erreurs[message] = maintenant
    jouer_texte(message, priorite=6)


def construire_phrase_etape(etape):
    exercice = etape["exercice"]
    series = etape["series"]
    mot_series = "série" if series == 1 else "séries"
    poids = etape.get("poids", 0)

    phrase = f"Prochain exercice : {exercice}"

    if poids > 0:
        phrase += f", avec un haltère de {poids} kilos"

    phrase += f", {series} {mot_series}"

    if etape["mode"] == "repetitions":
        phrase += f", {etape['repetitions']} répétitions."
    elif etape["mode"] == "maintien":
        phrase += f", maintien de {etape['duree']} secondes."
    elif etape["mode"] == "chrono":
        phrase += f", chrono de {etape['duree']} secondes."
    elif etape["mode"] == "amrap":
        phrase += f", en amrap pendant {etape['duree']} secondes."

    if etape.get("commentaire"):
        phrase += f" {etape['commentaire']}"

    return phrase


def annoncer_prochaine_etape(etape, annonce_secours=None):
    if etape is None:
        return
    jouer_texte(construire_phrase_etape(etape), priorite=5)


def annoncer_progression(repetitions, cible):
    restantes = cible - repetitions

    if restantes == 0:
        coach("fin_serie")
    elif restantes == 1:
        coach("avant_derniere")
    elif restantes == 3:
        coach("encore_3")
    elif restantes == 5:
        coach("encore_5")
    elif cible >= 8 and repetitions == cible // 2:
        coach("mi_parcours")


def annoncer_temps_restant(bloc, secondes_restantes):
    if bloc.temps_restant_precedent is None:
        bloc.temps_restant_precedent = secondes_restantes
        return

    seuils = [(20, "temps_20"), (10, "temps_10"), (5, "temps_5")]

    for seuil, message in seuils:
        if bloc.temps_restant_precedent > seuil and secondes_restantes <= seuil:
            coach(message)
            break

    bloc.temps_restant_precedent = secondes_restantes


def annoncer_temps_repos(seance, state, annoncer_exercice=False):
    secondes_restantes = int(seance.temps_restant)

    if not hasattr(seance, "repos_restant_precedent") or seance.repos_restant_precedent is None:
        seance.repos_restant_precedent = secondes_restantes
        return

    seuils = [(20, "repos_20"), (10, "repos_10"), (5, "repos_5")]

    for seuil, message in seuils:
        if seance.repos_restant_precedent > seuil and secondes_restantes <= seuil:
            coach(message)
            break

    seance.repos_restant_precedent = secondes_restantes