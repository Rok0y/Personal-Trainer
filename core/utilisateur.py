"""Identité du profil connecté.

Ce module ne contient **que** l'identité courante : le SQL des profils vit dans
`historique/database.py`, qui possède déjà toutes les connexions. La séparation
compte pour la suite — le jour où l'application deviendra un serveur
multi-sessions, c'est ici seulement que « qui est connecté ? » changera de
réponse (une session HTTP au lieu d'une variable de processus), sans que la
couche données ni `progression/` ne bougent.

Rien n'est persisté : il n'existe pas de colonne « actif » en base, et
l'application repart sur l'écran de connexion à chaque lancement. C'est
volontaire — un profil connecté est un état de session, pas une donnée.

L'import de `historique.database` est fait **dans les fonctions** pour éviter le
cycle (la base résout le profil courant via ce module) ; c'est l'idiome déjà
employé dans `progression/paliers.py`.
"""

_connecte = None
"""Profil courant, ou None si personne.

Porte l'état du tunnel d'accueil (`onboarding_termine`, `seance_initiale`) en
plus de l'identité, pour que le garde de `web/app.py` n'ait pas à interroger la
base à chaque requête. Toute écriture sur ces colonnes doit donc appeler
`rafraichir()`, sinon la session garde une vue périmée et le tunnel se rouvre.
"""


def utilisateur_connecte():
    """Le profil connecté, ou None."""
    return _connecte


def est_connecte():
    return _connecte is not None


def identifiant_connecte():
    """L'identifiant du profil connecté, ou None."""
    return _connecte["id"] if _connecte else None


def connecter(utilisateur_id):
    """Ouvre une session sur un profil existant et le retourne.

    On relit le profil en base plutôt que de faire confiance à l'identifiant
    reçu : c'est le seul point où une valeur venue du web devient l'identité
    sous laquelle toute l'application écrira ensuite.
    """
    from historique.database import recuperer_utilisateur

    profil = recuperer_utilisateur(utilisateur_id)
    if profil is None:
        raise KeyError(f"Profil {utilisateur_id} introuvable")

    global _connecte
    _connecte = profil
    return _connecte


def deconnecter():
    global _connecte
    _connecte = None


def onboarding_a_faire():
    """Le profil connecté doit-il encore passer le tunnel d'accueil ?

    False sans personne de connecté : c'est le garde de profil qui traite ce
    cas-là, et répondre True ici enverrait un visiteur anonyme vers /bienvenue
    au lieu de /connexion.
    """
    if _connecte is None:
        return False
    return not _connecte.get("onboarding_termine", True)


def rafraichir():
    """Recharge le profil connecté depuis la base (renommage, fin du tunnel)."""
    if _connecte is None:
        return None
    return connecter(_connecte["id"])
