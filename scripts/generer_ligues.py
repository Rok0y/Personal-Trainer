"""Oracle Python du portage de `progression/ligues.py`.

Le module mélange deux natures, et le harnais les interroge séparément.

**Des fonctions pures**, qu'on peut donc bombarder d'entrées au hasard : la
ligue d'un niveau, le rang d'un volume relatif, l'XP d'un niveau, le niveau
général d'une XP. Trois précautions y comptent :

- **on monte jusqu'au niveau 200**, bien au-delà du dernier palier borné de
  n'importe quel barème (le plus long tourne autour de 120), parce que la
  tranche ouverte est une *autre règle* : un port qui s'arrêterait plus tôt
  passerait vert sans jamais l'atteindre ;
- **les seuils sont visités des deux côtés**, à un epsilon près. Un seuil est
  exactement l'endroit où une comparaison `>=` se distingue d'un `>`, et des
  ratios tirés uniformément n'y tombent jamais ;
- **les inventaires sont balayés**, parce que l'échelle de poids décale toutes
  les tranches, donc tous les volumes, donc toutes les ligues. Ce sont les
  mêmes cinq que le harnais des paliers, et les mêmes exercices fictifs
  (`Surcharge`, `SansFin`) : le catalogue réel n'exerce ni les surcharges de
  palier ni le barème sans fin, et c'est exactement ce trou qui avait masqué
  un sabotage sur ce harnais-là.

**Et des fonctions qui lisent une histoire** — `ligues_par_exercice`,
`xp_totale`, `montees_de_ligue`, `xp_gagnee` — auxquelles il faut jeter des
historiques tordus, par le générateur partagé.

Ni la base ni le profil ne sont lus : l'inventaire est injecté et les ancrages
sont détournés, sinon l'oracle dépendrait de ce que la machine contient ce
jour-là.

Usage : `python -m scripts.generer_ligues`
Sortie : scripts/fixtures_ligues.jsonl, une question par ligne.
"""

import json
import random
from dataclasses import asdict
from pathlib import Path

import core.materiel as materiel
from progression import ligues, niveaux, paliers
from scripts.generer_paliers import SPECS_DU_HARNAIS, inventaires, specs_du_harnais
from scripts.historiques_au_hasard import (
    ancrages as tirer_ancrages,
    historique as tirer_historique,
    injecter_inventaire,
)

RACINE = Path(__file__).resolve().parent.parent
DESTINATION = Path(__file__).parent / "fixtures_ligues.jsonl"

GRAINE = 20260915

#: Jusqu'où monter dans les niveaux — voir la docstring : la tranche ouverte
#: commence bien avant, et c'est elle qu'il faut atteindre.
NIVEAU_MAX = 200

#: Niveaux généraux dont le coût est relevé.
NIVEAU_GENERAL_MAX = 40

#: Ratios tirés au hasard, en plus des abords de chaque seuil.
RATIOS_AU_HASARD = 200

#: Historiques tirés, pour les fonctions qui lisent une histoire.
#:
#: Mesuré : à 40 historiques, le sabotage qui fait passer *toute* montée de
#: niveau pour une montée de ligue ne sortait que 3 divergences — une montée
#: qui reste dans le même cran est justement le cas rare, puisqu'un historique
#: au hasard produit surtout de grands sauts et des premiers niveaux. Le même
#: sabotage en sort 9 à 120.
HISTORIQUES = 120

#: Inventaire sous lequel sont relevées les questions qui n'en dépendent pas
#: (rangs, XP, niveau général). Les poser une fois suffit ; les poser cinq
#: fois n'ajouterait que du volume de fichier.
INVENTAIRE_NEUTRE = "non_declare"


def _injecter_specs_fictives():
    """Les mêmes barèmes fictifs que le harnais des paliers, pour les mêmes raisons.

    Écrit le même fichier avec le même contenu : les deux générateurs peuvent
    donc être lancés dans n'importe quel ordre, et le comparateur fusionne ce
    fichier comme le fait `comparer_paliers.mjs`.
    """
    from session.seances import MATERIEL_EXERCICES

    supplementaires = specs_du_harnais()
    paliers.SPECS.update(supplementaires)
    MATERIEL_EXERCICES["Surcharge"] = "Deux haltères"
    MATERIEL_EXERCICES["SansFin"] = ""
    SPECS_DU_HARNAIS.write_text(
        json.dumps(
            {
                "specs": {nom: asdict(spec) for nom, spec in supplementaires.items()},
                "materiel": {
                    "Surcharge": {"halteres": 2, "brut": "Deux haltères"},
                    "SansFin": {"halteres": 0, "brut": ""},
                },
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )


def _volumes(tirage, seuils):
    """Les volumes interrogés : les abords de chaque borne, puis du hasard.

    Une borne est exactement l'endroit où `>=` se distingue de `>`, et un
    tirage uniforme n'y tombe jamais : sans les points posés autour de chacune,
    un portage qui déplacerait une borne d'un cran resterait invisible.
    """
    points = [None, 0.0, seuils[0] / 2, seuils[0] - 1e-9]
    for seuil in seuils:
        points.extend([seuil - 1e-9, seuil, seuil + 1e-9, seuil - 0.5, seuil + 0.5])
    points.extend(tirage.uniform(0.0, seuils[-1] * 1.5) for _ in range(RATIOS_AU_HASARD))
    points.append(1e9)
    return points


def main():
    _injecter_specs_fictives()

    tirage = random.Random(GRAINE)
    noms = list(paliers.exercices_suivis())
    lignes = 0

    with DESTINATION.open("w", encoding="utf-8") as fichier:

        def relever(question):
            nonlocal lignes
            fichier.write(json.dumps(question, ensure_ascii=False) + "\n")
            lignes += 1

        # --- Ce qui ne dépend pas du matériel : rangs, XP, niveau général ---
        # Les bornes interrogées sont celles d'un exercice réellement réglé,
        # pas une échelle inventée : c'est sur des bornes en volume absolu que
        # la comparaison `>=` se joue désormais.
        bornes = list(ligues.seuils_exercice("Pompes"))
        for volume in _volumes(tirage, bornes):
            relever({
                "inventaire": INVENTAIRE_NEUTRE,
                "question": "rang_pour_volume",
                "volume": volume,
                "seuils": bornes,
                "reponse": ligues.rang_pour_volume(volume, bornes),
            })

        for rang in [None, -1, 0] + list(range(1, ligues.RANG_MAX + 5)):
            relever({
                "inventaire": INVENTAIRE_NEUTRE,
                "question": "ligue_pour_rang",
                "rang": rang,
                "reponse": ligues.ligue_pour_rang(rang),
            })

        for niveau in [None, 0] + list(range(1, NIVEAU_MAX + 1)):
            relever({
                "inventaire": INVENTAIRE_NEUTRE,
                "question": "xp",
                "niveau": niveau,
                "reponse": {
                    "du_niveau": ligues.xp_du_niveau(niveau),
                    "cumulee": ligues.xp_cumulee(niveau),
                },
            })

        for niveau in range(1, NIVEAU_GENERAL_MAX + 1):
            relever({
                "inventaire": INVENTAIRE_NEUTRE,
                "question": "cout_du_niveau_general",
                "niveau": niveau,
                "reponse": ligues.cout_du_niveau_general(niveau),
            })

        # Les abords de chaque palier de niveau général, plus du hasard : le
        # franchissement est une boucle de soustraction, donc c'est juste
        # au-dessus et juste en dessous du coût qu'elle se trompe d'un cran.
        xp_seuil = 0
        valeurs_xp = [None, 0, -50]
        for niveau in range(1, NIVEAU_GENERAL_MAX + 1):
            xp_seuil += ligues.cout_du_niveau_general(niveau)
            valeurs_xp.extend([xp_seuil - 1, xp_seuil, xp_seuil + 1])
        valeurs_xp.extend(tirage.randrange(0, 60000) for _ in range(RATIOS_AU_HASARD))
        for xp in valeurs_xp:
            relever({
                "inventaire": INVENTAIRE_NEUTRE,
                "question": "niveau_general",
                "xp": xp,
                "reponse": ligues.niveau_general(xp),
            })

        # --- Ce qui dépend du matériel : le volume d'un palier, donc sa ligue ---
        for nom_inventaire, inventaire in inventaires().items():
            materiel.materiel_du_profil = (
                lambda _=None, brut=inventaire: materiel.normaliser(brut)
            )

            for nom in paliers.SPECS:
                # Les bornes d'un exercice dependent de son palier 1 quand
                # elles ne sont pas posees a la main : elles bougent donc avec
                # l'inventaire, et se comparent sous chacun.
                seuils = ligues.seuils_exercice(nom)
                relever({
                    "inventaire": nom_inventaire,
                    "exercice": nom,
                    "question": "seuils_exercice",
                    "reponse": list(seuils) if seuils else None,
                })
                for niveau in range(1, NIVEAU_MAX + 1):
                    relever({
                        "inventaire": nom_inventaire,
                        "exercice": nom,
                        "question": "ligue_exercice",
                        "niveau": niveau,
                        "reponse": {
                            "volume_relatif": ligues.volume_relatif(nom, niveau),
                            "ligue": ligues.ligue_exercice(nom, niveau),
                        },
                    })
                # Un exercice sans niveau n'a pas de ligue — pas un Bronze III
                # offert. La distinction ne se voit que si on la demande.
                relever({
                    "inventaire": nom_inventaire,
                    "exercice": nom,
                    "question": "ligue_exercice",
                    "niveau": None,
                    "reponse": {
                        "volume_relatif": ligues.volume_relatif(nom, None),
                        "ligue": ligues.ligue_exercice(nom, None),
                    },
                })

        # --- Ce qui lit une histoire ---
        for nom_inventaire, inventaire in inventaires().items():
            if nom_inventaire not in ("non_declare", "debutant", "complet"):
                # Le générateur partagé ne connaît que ces trois inventaires,
                # et ce sont eux que rejoue le comparateur.
                continue
            injecter_inventaire(inventaire)

            for numero in range(HISTORIQUES):
                seances = tirer_historique(tirage, noms)
                ancrages = tirer_ancrages(tirage, noms, seances)
                niveaux.recuperer_ancrages = lambda *_, **__: ancrages

                etats = niveaux.etats_niveaux(seances)
                montees = niveaux.montees_de_niveau(seances, ancrages)
                relever({
                    "inventaire": nom_inventaire,
                    "numero": numero,
                    "question": "historique",
                    "seances": seances,
                    "ancrages": ancrages,
                    "reponse": {
                        "ligues_par_exercice": ligues.ligues_par_exercice(etats),
                        "xp_totale": ligues.xp_totale(etats),
                        "montees_de_ligue": {
                            str(cle): valeur
                            for cle, valeur in ligues.montees_de_ligue(montees).items()
                        },
                        "xp_gagnee": {
                            str(cle): ligues.xp_gagnee(valeur)
                            for cle, valeur in montees.items()
                        },
                    },
                })

    print(f"{lignes} lignes")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


if __name__ == "__main__":
    main()
