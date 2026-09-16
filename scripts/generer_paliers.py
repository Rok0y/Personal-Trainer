"""Oracle Python du portage de `progression/paliers.py`.

Troisième harnais du projet, et il retrouve la forme du premier : un barème
est une **fonction pure** de (spec, échelle), donc on peut lui jeter des
entrées au hasard, comme aux détections. Pas besoin d'histoire ici, contrairement
au circuit.

Ce qu'il balaie, et pourquoi chaque axe compte :

- **tous les niveaux jusqu'au-delà de la tranche ouverte** : c'est là que le
  barème change de règle, et un port qui s'arrêterait au dernier palier borné
  passerait vert sans jamais l'atteindre ;
- **plusieurs inventaires de matériel**, parce que l'échelle de poids décale
  toutes les tranches : un barème juste avec des haltères complets peut être
  faux pour quelqu'un qui n'a que des 4 kg, et c'est le cas le plus probable
  d'un nouvel utilisateur ;
- **des performances au hasard** passées à `niveau_pour`, qui est la fonction
  la plus subtile du module — le volume prime, mais pas seul.

Le profil connecté n'est **jamais** lu : l'inventaire est injecté, sinon
l'oracle dépendrait de ce que le matériel de quelqu'un contient ce jour-là.

Usage : `python -m scripts.generer_paliers`
Sortie : scripts/fixtures_paliers.jsonl, une question par ligne.
"""

import json
import random
from pathlib import Path

import core.materiel as materiel
from progression import paliers

RACINE = Path(__file__).resolve().parent.parent
DESTINATION = Path(__file__).parent / "fixtures_paliers.jsonl"
#: Specs fictives ajoutées au barème le temps du harnais, et relues par le
#: comparateur. Elles ne touchent jamais `baremes.json`, qui décrit le vrai
#: catalogue.
SPECS_DU_HARNAIS = Path(__file__).parent / "fixtures_paliers_specs.json"

GRAINE = 20260911

#: Jusqu'où monter dans les niveaux. Le dernier palier borné d'un barème
#: complet tourne autour de 120 ; aller au-delà force le passage par la
#: tranche ouverte, qui est précisément la règle qu'on risque de rater.
NIVEAU_MAX = 200

#: Performances tirées par exercice, pour `niveau_pour`.
PERFORMANCES_PAR_EXERCICE = 60


def specs_du_harnais():
    """Des barèmes fictifs, pour couvrir ce que le catalogue réel n'exerce pas.

    Aucun exercice n'a aujourd'hui de **surcharge de palier**, si bien que la
    condition de poids de `_valide` est inatteignable : un sabotage volontaire
    qui la supprimait traversait les 30 935 questions sans être vu, parce que
    `_niveaux_candidats` filtre déjà sur le poids et ne produit que des
    candidats qui la satisfont. Seules les surcharges peuvent placer un palier
    ailleurs, et c'est là que la condition sert.

    Le barème sans fin (`cible_max` à None) est dans le même cas : aucun
    exercice réel n'en a, et c'est pourtant une branche de chaque fonction.
    """
    return {
        "Surcharge": paliers.SpecProgression(
            series=3,
            cible_min=5,
            cible_max=12,
            poids_min=4,
            poids_max=10,
            # Un palier déplacé bien au-dessus de sa tranche : c'est ce qui
            # rend un candidat de surcharge plus lourd que la performance.
            surcharges={3: {"poids": 18, "cible": 20}, 7: {"series": 5}},
        ),
        "SansFin": paliers.SpecProgression(
            series=3, cible_min=10, cible_max=None, unite=paliers.UNITE_SECONDES
        ),
    }


def inventaires():
    """Les inventaires balayés, du plus pauvre au plus complet.

    `None` veut dire « rien de déclaré », et rend le matériel par défaut : ce
    n'est pas la même chose qu'un inventaire vide, et les deux doivent être
    vérifiés.

    Les deux derniers visent la règle « un poids se déclare, il ne se choisit
    pas dans une liste » — celle qui distingue la gamme du questionnaire des
    valeurs acceptables. `hors_gamme` porte des charges qui ne figurent dans
    aucune des deux listes exportées et un **demi-kilo**, parce que c'est là
    que les deux implémentations pouvaient diverger sans bruit : le JavaScript
    lisait ses poids avec `parseInt`, qui tronque « 17.5 » en 17 et invente
    donc un haltère que personne ne possède. `absurdes` vérifie l'autre bord :
    ce qui est refusé doit l'être des deux côtés, sinon un inventaire n'a pas
    le même contenu ici et là.
    """
    reference = list(materiel.POIDS_REFERENCE)
    return {
        "non_declare": None,
        "vide": {"halteres": {}, "accessoires": []},
        "debutant": {"halteres": {2: 2, 3: 2, 4: 2}, "accessoires": ["tapis"]},
        "une_paire_moyenne": {"halteres": {6: 2, 8: 2, 10: 1}, "accessoires": []},
        "complet": {
            "halteres": {poids: 2 for poids in reference},
            "accessoires": ["tapis", "chaise"],
        },
        "hors_gamme": {
            "halteres": {7: 2, 17.5: 2, 21: 1, 26: 2, 33: 2, 45: 2},
            "accessoires": ["chaise"],
        },
        "absurdes": {
            "halteres": {0: 2, -4: 2, 0.4: 2, 61: 2, 500: 2, 8: 2, "": 2},
            "accessoires": ["tapis"],
        },
    }


def _palier_serialisable(p):
    if p is None:
        return None
    return {
        "niveau": p.niveau,
        "poids": p.poids,
        "series": p.series,
        "cible": p.cible,
        "unite": p.unite,
        "volume": p.volume,
        "resume": p.resume(),
    }


def main():
    from dataclasses import asdict

    # Les specs fictives entrent dans le barème pour la durée du harnais, et
    # partent dans un fichier que le comparateur fusionne de son côté.
    supplementaires = specs_du_harnais()
    paliers.SPECS.update(supplementaires)
    # Le matériel des exercices fictifs se déclare là où le vrai est déclaré,
    # sinon `nombre_halteres` les rend à zéro haltère et l'échelle s'effondre
    # sur le poids du corps.
    from session.seances import MATERIEL_EXERCICES

    MATERIEL_EXERCICES["Surcharge"] = "Deux haltères"
    MATERIEL_EXERCICES["SansFin"] = ""
    SPECS_DU_HARNAIS.write_text(
        json.dumps(
            {
                "specs": {nom: asdict(spec) for nom, spec in supplementaires.items()},
                # Deux haltères pour l'un, poids du corps pour l'autre : les
                # deux échelles sont ainsi parcourues.
                "materiel": {
                    "Surcharge": {"halteres": 2, "brut": "Deux haltères"},
                    "SansFin": {"halteres": 0, "brut": ""},
                },
                # Les inventaires voyagent **avec l'oracle** et ne sont plus
                # redéclarés en JavaScript. Ils l'étaient, et le comparateur
                # est mécaniquement devenu muet le jour où deux inventaires
                # ont été ajoutés ici : `baremes[nom]` valait `undefined`. Il
                # a au moins échoué bruyamment — mais rien ne garantissait
                # qu'un jeu d'entrées divergent le fasse, et deux harnais qui
                # comparent des entrées différentes en croyant les trouver
                # identiques ne prouvent rien.
                "inventaires": inventaires(),
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    tirage = random.Random(GRAINE)
    lignes = 0

    with DESTINATION.open("w", encoding="utf-8") as fichier:

        def relever(question):
            nonlocal lignes
            fichier.write(json.dumps(question, ensure_ascii=False) + "\n")
            lignes += 1

        for nom_inventaire, inventaire in inventaires().items():
            # L'inventaire est injecté en remplaçant la lecture du profil :
            # `echelle_disponible` passe par `materiel_du_profil`, qui
            # interrogerait sinon la base et le profil connecté.
            materiel.materiel_du_profil = (
                lambda _=None, brut=inventaire: materiel.normaliser(brut)
            )

            for nom in paliers.exercices_suivis():
                echelle = paliers.echelle_exercice(nom)
                relever({
                    "inventaire": nom_inventaire,
                    "exercice": nom,
                    "question": "echelle",
                    "reponse": list(echelle),
                })
                relever({
                    "inventaire": nom_inventaire,
                    "exercice": nom,
                    "question": "tranches",
                    "reponse": paliers.tranches(
                        nom, series_max=paliers.SPECS[nom].series_max
                    ),
                })
                relever({
                    "inventaire": nom_inventaire,
                    "exercice": nom,
                    "question": "dernier_palier_borne",
                    "reponse": paliers.dernier_palier_borne(nom),
                })

                for niveau in range(1, NIVEAU_MAX + 1):
                    relever({
                        "inventaire": nom_inventaire,
                        "exercice": nom,
                        "question": "palier",
                        "niveau": niveau,
                        "reponse": _palier_serialisable(paliers.palier(nom, niveau)),
                    })

                spec = paliers.SPECS[nom]
                for _ in range(PERFORMANCES_PAR_EXERCICE):
                    # Des performances plausibles mais pas complaisantes : des
                    # charges hors échelle, des séries au-delà du plafond et
                    # des cibles nulles font partie de ce que la base contient
                    # vraiment.
                    poids = tirage.choice([0, 2, 3, 5, 8, 10, 14, 18, 25])
                    series = tirage.randint(0, 8)
                    cible = tirage.randint(0, 60)
                    relever({
                        "inventaire": nom_inventaire,
                        "exercice": nom,
                        "question": "niveau_pour",
                        "poids": poids,
                        "series": series,
                        "cible": cible,
                        "reponse": paliers.niveau_pour(nom, poids, series, cible),
                    })

                for volume_cible in (1, 50, 288, 1000, 5000, 40000):
                    relever({
                        "inventaire": nom_inventaire,
                        "exercice": nom,
                        "question": "niveau_pour_volume",
                        "volume": volume_cible,
                        "reponse": paliers.niveau_pour_volume(nom, volume_cible),
                    })

    print(f"{len(inventaires())} inventaires x {len(paliers.exercices_suivis())} exercices")
    print(f"{lignes} questions, jusqu'au niveau {NIVEAU_MAX}")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


if __name__ == "__main__":
    main()
