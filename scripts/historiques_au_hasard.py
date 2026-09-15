"""Fabrique des historiques d'entraînement pour les harnais de `progression/`.

Partagé par `generer_niveaux.py` et `generer_ressenti.py`, qui consomment le
même format — celui que rend `historique.database.recuperer_historique`.

**Les historiques sont volontairement tordus, pas plausibles.** Des séances
réalistes testent mal : des séries identiques rendent le minimum du maillon
faible équivalent à un maximum, des séries toutes menées au bout n'éprouvent
jamais le filtre `completee`, et un mode toujours cohérent avec son barème ne
déclenche jamais le refus d'unité. On tire donc des séries inégales, parfois
inachevées, et des modes mélangés.

Une exception à ce désordre, et elle est délibérée : **une cible sur deux est
prise sur le barème réel**. Tirée entièrement au hasard, elle ne correspond à
aucun palier, `niveau_pour` rend None et `ressenti.juger` abandonne la ligne —
le harnais tournerait alors sur des historiques que le moteur ne sait pas
lire, ce qui ne prouve rien de ce qui nous intéresse.
"""

import core.materiel as materiel
from progression import paliers

MODES = ("repetitions", "maintien", "chrono", "amrap", "echauffement")

RESSENTIS = ("", "ok", "dur", "facile", "trop_dur", "trop_facile")

#: Inventaires balayés : l'échelle de poids décale tous les niveaux, donc un
#: portage juste avec des haltères complets peut être faux pour un débutant —
#: c'est-à-dire pour le cas le plus probable d'un nouvel utilisateur.
INVENTAIRES = {
    "non_declare": None,
    "debutant": {"halteres": {2: 2, 3: 2, 4: 2}, "accessoires": ["tapis"]},
    "complet": {
        "halteres": {p: 2 for p in materiel.POIDS_REFERENCE},
        "accessoires": ["tapis", "chaise"],
    },
}


def injecter_inventaire(inventaire):
    """Remplace la lecture du profil par un inventaire fixe.

    `echelle_disponible` passe par `materiel_du_profil`, qui interrogerait
    sinon la base et le profil connecté : un oracle qui en dépendrait ne
    rendrait pas deux fois le même verdict.
    """
    materiel.materiel_du_profil = (
        lambda _=None, brut=inventaire: materiel.normaliser(brut)
    )


def _cible_sur_le_bareme(tirage, nom):
    """Un palier réel de l'exercice, pour que la ligne soit interprétable.

    Rend `(poids, series, cible)` — exactement ce que `_cible_visee` relit
    depuis les colonnes de consigne.
    """
    palier = paliers.palier(nom, tirage.randint(1, 45))
    if palier is None:
        return None
    return palier.poids, palier.series, palier.cible


def exercice(tirage, noms):
    nom = tirage.choice(noms)
    unite = paliers.unite(nom)
    # Le mode correspond à l'unité une fois sur deux : l'autre moitié éprouve
    # le refus d'unité, qu'un historique cohérent ne déclencherait jamais.
    if tirage.random() < 0.5:
        mode = "maintien" if unite == paliers.UNITE_SECONDES else "repetitions"
    else:
        mode = tirage.choice(MODES)
    maintien = mode in ("maintien", "chrono")

    sur_le_bareme = tirage.random() < 0.5 and _cible_sur_le_bareme(tirage, nom)
    if sur_le_bareme:
        poids, nb_series, cible = sur_le_bareme
    else:
        poids = tirage.choice([0, 2, 4, 5, 6, 8, 10, 14, 18])
        nb_series = tirage.randint(1, 6)
        cible = tirage.randint(5, 40) if maintien else tirage.randint(3, 25)

    series = []
    for numero in range(1, nb_series + 1):
        # Autour de la cible, et pas toujours au-dessus : c'est le
        # franchissement du seuil qui fait basculer « réussi », donc les deux
        # côtés doivent être visités.
        realise = max(0, cible + tirage.randint(-4, 2))
        series.append({
            "serie": numero,
            "repetitions": 0 if maintien else realise,
            "poids": poids if tirage.random() < 0.7 else max(0, poids - 2),
            "duree": realise if maintien else 0,
            "completee": tirage.random() > 0.2,
        })

    return {
        "nom": nom,
        "mode": mode,
        "poids": poids,
        "series": nb_series,
        "repetitions": sum(s["repetitions"] for s in series),
        "duree": sum(s["duree"] for s in series),
        "series_cibles": nb_series,
        "repetitions_cibles": 0 if maintien else cible,
        "duree_cible": cible if maintien else 0,
        "commentaire": "",
        "entrelace_avec": None,
        "repos_entre_series": 45,
        "repos_apres": 60,
        "ressenti": tirage.choice(RESSENTIS),
        "series_detaillees": series,
    }


def historique(tirage, noms):
    """Un historique au format de `recuperer_historique` : le plus récent en tête."""
    nombre = tirage.randint(1, 12)
    seances = []
    for index in range(nombre, 0, -1):
        seances.append({
            "id": index,
            "date": f"{index:02d}/03/2026 08:00",
            "duree": tirage.randint(300, 3600),
            # Une séance abandonnée ne sert pas de repère à `ressenti`, mais
            # reste annotable : les deux chemins doivent être visités.
            "statut": tirage.choice(["finished", "finished", "abandoned"]),
            "nom": tirage.choice(["bras", "Upper Pull", None]),
            # Un exercice peut apparaître deux fois dans la même séance : la
            # meilleure ligne l'emporte, jamais leur somme.
            "exercices": [exercice(tirage, noms) for _ in range(tirage.randint(1, 4))],
        })
    return seances


def ancrages(tirage, noms, seances):
    """Des ancrages posés **au milieu** de l'historique.

    Posés à la fin, ils ne feraient jamais table rase de rien ; posés au
    début, ils ne serviraient jamais de plancher. C'est entre les deux que
    leurs deux effets se voient — et le sabotage qui décale leur borne d'une
    séance ne sort qu'une poignée de divergences, donc sans ce placement il
    passerait inaperçu.
    """
    if tirage.random() < 0.3:
        return {}
    ids = sorted(s["id"] for s in seances)
    milieu = ids[len(ids) // 2] if ids else 0
    return {
        nom: {
            "niveau": tirage.randint(1, 40),
            "date": "15/03/2026 08:00",
            "apres_seance_id": tirage.choice([0, milieu, max(ids, default=0)]),
            "raison": "harnais",
        }
        for nom in tirage.sample(noms, k=min(3, len(noms)))
    }


def palier_serialisable(p):
    """Un `Palier` sous la forme que le JavaScript produit."""
    if p is None:
        return None
    return {
        "niveau": p.niveau,
        "poids": p.poids,
        "series": p.series,
        "cible": p.cible,
        "unite": p.unite,
    }
