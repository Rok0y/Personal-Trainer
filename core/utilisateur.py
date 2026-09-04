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
"""Profil courant : `{"id": int, "nom": str}`, ou None si personne."""


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
    _connecte = {"id": profil["id"], "nom": profil["nom"]}
    return _connecte


def deconnecter():
    global _connecte
    _connecte = None


def rafraichir():
    """Recharge le nom du profil connecté depuis la base (après un renommage)."""
    if _connecte is None:
        return None
    return connecter(_connecte["id"])
