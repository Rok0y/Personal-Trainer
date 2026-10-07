"""Le matériel dont dispose un profil, et ce qu'il autorise.

**Un inventaire, pas deux échelles.** `progression.paliers` raisonne sur deux
échelles de charge — une paire d'haltères ne monte pas aussi haut qu'un haltère
seul — mais ce sont deux *vues* d'un même stock : « j'ai une paire jusqu'à
10 kg, et des haltères seuls jusqu'à 18 ». Déclarer le stock une fois
(`{poids: quantité}`) et en dériver les deux échelles (`quantité >= 1`,
`quantité >= 2`) évite qu'un profil puisse déclarer une paire de 12 kg sans
déclarer l'haltère de 12 kg.

**Le matériel restreint le barème, il ne le supprime jamais.** Un inventaire
vide rendrait une échelle vide, et `echelle_exercice` (qui finit par
`retenue or echelle[:1]`) n'aurait plus rien à retenir : tout le moteur de
progression planterait sur un profil qui n'a coché aucun haltère. La règle est
donc en deux temps — l'échelle se réduit à ce qui est possédé *tant qu'il reste
quelque chose*, et la question « puis-je faire cet exercice ? » vit à part, dans
`exercice_realisable`.

Les imports de `historique.database` et `session.seances` sont différés dans les
fonctions, comme dans `core/utilisateur.py` et `progression/paliers.py` : ces
modules consomment celui-ci.
"""

import json

#: Les poids que le questionnaire **propose** de cocher. Ce n'est ni ce que
#: quelqu'un possède, ni ce qu'il a le droit de déclarer : c'est une liste de
#: raccourcis, celle des haltères qu'on trouve couramment. Quelqu'un qui a du
#: 17,5 kg le saisit à la main (`poids_declarable`) — la gamme n'est là que
#: pour éviter de taper onze nombres.
POIDS_REFERENCE = (
    2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18,
    20, 22, 24, 25, 28, 30, 35, 40,
)

#: **Et surtout pas `POIDS_REFERENCE`.** Le matériel par défaut doit rester
#: figé sur la gamme d'avant l'extension : il est construit par compréhension,
#: si bien qu'allonger la liste ci-dessus donnerait d'un coup, à tout profil
#: qui n'a rien déclaré, des haltères jusqu'à 40 kg — donc un barème différent
#: du jour au lendemain, silencieusement, sur tout l'historique déjà
#: interprété. Les deux listes ne répondent pas à la même question : l'une dit
#: ce qu'on peut cocher, l'autre ce qu'on suppose à qui n'a rien dit.
POIDS_SUPPOSES = (2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18)

#: Bornes d'un poids saisi à la main. Larges à dessein — il ne s'agit pas de
#: juger ce que quelqu'un soulève, seulement d'écarter une faute de frappe qui
#: ferait sortir le barème de tout sens (un « 200 » pour « 20 »).
POIDS_MIN_DECLARABLE = 1
POIDS_MAX_DECLARABLE = 60

#: Accessoires reconnus par `session.seances._decomposer_materiel`. La clé sert
#: au stockage et au formulaire, le libellé à l'affichage.
ACCESSOIRES = {"tapis": "Un tapis", "chaise": "Une chaise"}

#: Ce que voit un profil qui n'a rien déclaré : exactement le matériel que le
#: barème supposait avant que cette feature n'existe (paire jusqu'à 10 kg,
#: haltère seul jusqu'à 18, tapis et chaise). Un profil d'avant la migration ne
#: change donc pas de niveau du jour au lendemain.
MATERIEL_PAR_DEFAUT = {
    "halteres": {poids: (2 if poids <= 10 else 1) for poids in POIDS_SUPPOSES},
    "accessoires": list(ACCESSOIRES),
}


def poids_declarable(valeur):
    """Un poids d'haltère utilisable, ou None.

    Remplace le `poids in POIDS_REFERENCE` d'avant, qui confondait « ce que le
    questionnaire propose » et « ce qui est acceptable » : quelqu'un possédant
    des haltères de 20 kg ne pouvait ni les cocher ni les faire accepter, et
    son inventaire était silencieusement amputé au chargement.

    Arrondi au demi-kilo, parce que c'est le pas réel du matériel et que rien
    dans le barème ne tire profit d'une précision plus fine.
    """
    try:
        poids = float(valeur)
    except (TypeError, ValueError):
        return None
    poids = round(poids * 2) / 2
    if not POIDS_MIN_DECLARABLE <= poids <= POIDS_MAX_DECLARABLE:
        return None
    # Un entier reste un entier : il traverse le JSON, les clés de dict et
    # l'affichage sans jamais devenir « 8.0 kg ».
    return int(poids) if poids == int(poids) else poids


def normaliser(brut):
    """Un inventaire propre depuis ce que porte la base (JSON, None, ou pire).

    `None` veut dire « rien de déclaré » et rend le matériel par défaut : c'est
    le cas des profils créés avant cette colonne, et leur barème ne doit pas
    bouger. Un inventaire *déclaré* mais vide, lui, est une réponse valide et
    reste vide — quelqu'un qui ne coche aucun haltère n'en a pas.
    """
    if brut is None:
        return {
            "halteres": dict(MATERIEL_PAR_DEFAUT["halteres"]),
            "accessoires": list(MATERIEL_PAR_DEFAUT["accessoires"]),
        }
    if isinstance(brut, str):
        try:
            brut = json.loads(brut)
        except (ValueError, TypeError):
            return normaliser(None)
    if not isinstance(brut, dict):
        return normaliser(None)

    halteres = {}
    for poids, quantite in (brut.get("halteres") or {}).items():
        poids = poids_declarable(poids)
        try:
            quantite = int(quantite)
        except (TypeError, ValueError):
            continue
        if poids is not None and quantite > 0:
            halteres[poids] = min(2, quantite)

    accessoires = [
        cle for cle in (brut.get("accessoires") or []) if cle in ACCESSOIRES
    ]
    return {"halteres": halteres, "accessoires": accessoires}


def materiel_du_profil(utilisateur_id=None):
    """L'inventaire du profil connecté, ou d'un profil nommé.

    Le paramètre explicite suit la convention de `historique.database` : `None`
    veut dire « le profil connecté ». Sans personne de connecté on retombe sur
    le matériel par défaut plutôt que de lever — ce module est appelé depuis le
    barème, donc depuis la boucle caméra, où une exception gèle le flux vidéo.
    """
    from core.utilisateur import utilisateur_connecte

    if utilisateur_id is None:
        profil = utilisateur_connecte()
    else:
        from historique.database import recuperer_utilisateur

        profil = recuperer_utilisateur(utilisateur_id)
    return normaliser((profil or {}).get("materiel"))


def echelle_disponible(nb_halteres, utilisateur_id=None):
    """Les charges praticables avec `nb_halteres` haltères identiques.

    Tuple croissant, **et il peut être vide** : un stock qui ne couvre pas ce
    besoin ne rend plus la gamme supposée par défaut. La réponse honnête à
    « avec quoi peut-il charger ce mouvement ? » est parfois « rien », et
    `normaliser` distingue déjà un inventaire *non déclaré* (qui reçoit le
    matériel complet d'avant la colonne) d'un inventaire *déclaré vide*.
    Effacer cette distinction ici la perdait là où elle compte.

    Ce que ça coûtait, mesuré : quelqu'un qui coche « aucun haltère » recevait
    quand même l'échelle supposée, donc `calibration.charge_de_test` prenait
    son milieu — **8 kg au squat**. L'écran et la voix lui réclamaient deux
    haltères de 8 kg, il faisait le test à vide faute d'autre choix, et
    `cloturer_test` ancrait 15 squats au poids du corps au **niveau 36** au lieu
    de 8. Un ancrage faisant table rase *et* plancher, et `base_apres_echec`
    redemandant la même cible après un échec, il lui fallait ensuite vingt-huit
    séances de « c'était trop dur » pour rejoindre la réalité.

    Le garde « le barème reste calculable pour tout le monde » n'a pas disparu,
    il a **déménagé dans `paliers.echelle_exercice`** — seul endroit qui sache
    si l'exercice a un cran au poids du corps sur lequel se rabattre. Un squat
    sans haltères rend `(0,)`, ce qui est sa vraie échelle ; un curl sans
    haltères retombe sur la gamme supposée, parce qu'il n'a rien d'autre et
    qu'un barème vide casserait jusqu'à l'écran des records.
    """
    if nb_halteres <= 0:
        return None
    stock = materiel_du_profil(utilisateur_id)["halteres"]
    # On parcourt le **stock declare** et non la gamme du questionnaire :
    # depuis qu'un poids se saisit a la main, un halteres de 17,5 kg peut
    # exister sans figurer dans `POIDS_REFERENCE`, et le filtrer par la gamme
    # le ferait disparaitre du bareme sans rien dire.
    return tuple(
        sorted(poids for poids, nombre in stock.items() if nombre >= nb_halteres)
    )


def accessoires_manquants(nom_exercice, utilisateur_id=None):
    """Accessoires que cet exercice réclame et que le profil n'a pas cochés."""
    from session.seances import MATERIEL_EXERCICES

    brut = MATERIEL_EXERCICES.get(nom_exercice, "") or ""
    possedes = materiel_du_profil(utilisateur_id)["accessoires"]
    return [
        libelle
        for cle, libelle in ACCESSOIRES.items()
        if cle in brut.lower() and cle not in possedes
    ]


def exercice_realisable(nom_exercice, utilisateur_id=None):
    """Le profil a-t-il de quoi faire ce mouvement ?

    Retourne `(réalisable, [ce qui manque])` — la liste sert à l'expliquer à
    l'écran plutôt que de se contenter de griser une ligne.
    """
    from progression.paliers import charge_facultative
    from session.seances import nombre_halteres

    manquants = accessoires_manquants(nom_exercice, utilisateur_id)

    # Strict, contrairement à `echelle_disponible` : là-bas une échelle vide
    # casserait tout le moteur de progression, ici rien ne casse. Quelqu'un qui
    # ne possède qu'un haltère ne fait pas un développé couché « en dégradé »,
    # il ne le fait pas.
    #
    # Sauf quand le barème admet un palier sans charge : un squat ou une fente
    # se font à vide, et la question est posée **au barème** plutôt que
    # redemandée au matériel. `MATERIEL_EXERCICES` dit ce qu'il faut pour
    # charger le mouvement, `charge_facultative` dit s'il faut le
    # charger — deux questions distinctes, une seule réponse chacune.
    besoin = nombre_halteres(nom_exercice)
    if besoin > 0 and not charge_facultative(nom_exercice):
        stock = materiel_du_profil(utilisateur_id)["halteres"]
        if not any(quantite >= besoin for quantite in stock.values()):
            manquants.append("Un haltère" if besoin == 1 else "Deux haltères")

    return not manquants, manquants
