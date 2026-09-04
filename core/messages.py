"""Tout ce que l'application dit à l'utilisateur par écrit, en un seul endroit.

**Une clé, un message.** C'est la même convention que le coach vocal
(`audio/coach.py`, où `"debut_serie"` désigne un `.wav`) : un message est
désigné par une clé stable, qui rend un texte aujourd'hui et rendra un son
demain. C'est la raison d'être de ce module — les textes étaient écrits en dur
là où ils étaient produits (libellés de phase dans `main.py`, fautes de forme
dans `mouvements/exercices.py`), donc introuvables autrement qu'à la main le
jour où il faudra les faire prononcer.

Deux conséquences pratiques, à respecter en ajoutant un message :

- une fonction d'erreur d'exercice retourne une **clé**, jamais une phrase.
  `session.moteur.mettre_a_jour_erreur` la résout. Un détecteur inachevé qui
  retournerait `True` produit alors une clé inconnue, donc rien — alors qu'il
  affichait auparavant le texte « true » dans le bandeau ;
- `texte()` ne lève jamais. Elle est appelée depuis la boucle caméra, où une
  exception non rattrapée emporte le thread et gèle le flux vidéo : un message
  manquant doit rester un silence, pas une panne.
"""

MESSAGES = {
    # --- Fautes de forme, signalées en temps réel pendant l'effort -----------
    "forme_buste_pas_assez_penche": "Penche-toi davantage vers l'avant",
    "forme_genoux_trop_plies": (
        "Garde les jambes presque tendues, plie moins les genoux"
    ),
    "forme_coudes_trop_tendus": (
        "Garde les coudes légèrement fléchis, ne tends pas complètement les bras"
    ),
    "forme_coudes_trop_plies": "Ne plie pas trop les coudes",
    "forme_coude_qui_part_en_avant": (
        "Garde le coude collé au buste, ne le laisse pas partir en avant"
    ),
    # --- Consignes d'état : ce qu'il faut faire, pas ce qui est mal fait -----
    "corps_absent": "Place-toi devant la caméra, bien en pied.",
    "preparation_bras_en_x": "Croise les bras devant toi pour lancer la série.",
    "preparation_decompte": "C'est parti ! Redescends les bras et mets-toi en place.",
    "pause": "Séance en pause. Reprends quand tu veux depuis le site.",
}

# Traduction des jetons rendus par les fonctions de détection. Le front
# affichait ces jetons bruts (« debut », « casse ») dans la carte « Étape » et
# devinait la posture en comparant des chaînes : un débutant n'a rien à faire
# du vocabulaire interne du détecteur.
LIBELLES_ETAPE = {
    "debut": "Position de départ",
    "milieu": "En mouvement",
    "fin": "Position basse",
    "maintien": "Position tenue",
    "repos": "Position relâchée",
    "casse": "Position incorrecte",
    "echauffement": "Échauffement en cours",
    # Étapes du circuit, pas du mouvement : elles passent par le même champ
    # parce que c'est la même question à l'écran — « où en suis-je ? ».
    "preparation": "Préparation",
    "preparation_prete": "Prêt !",
    "recuperation": "Récupération",
    "repos": "Repos",
    "pause": "En pause",
    "termine": "Terminé",
    "cassee": "Position incorrecte",
}


def texte(cle, **valeurs):
    """Message correspondant à une clé, ou None si la clé est inconnue.

    Le format nommé (`{secondes}`) est appliqué quand des valeurs sont
    fournies ; une clé de format absente du message est ignorée plutôt que
    fatale, pour la même raison que l'absence de clé.
    """
    message = MESSAGES.get(cle)
    if message is None:
        return None
    if not valeurs:
        return message
    try:
        return message.format(**valeurs)
    except (KeyError, IndexError, ValueError):
        return message


def libelle_etape(jeton):
    """Nom lisible d'une étape de mouvement, ou le jeton brut à défaut.

    Retomber sur le jeton plutôt que sur du vide : une étape non traduite reste
    visible à l'écran, donc se corrige, alors qu'un champ vide passe inaperçu.
    """
    if not jeton:
        return None
    return LIBELLES_ETAPE.get(jeton, jeton)
