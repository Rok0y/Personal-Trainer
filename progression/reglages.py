"""Les nombres réglables du moteur, et l'unique endroit où ils vivent.

Barèmes, seuils de ligue, table d'XP, coût des niveaux généraux : tout ce qui
se **règle** — par opposition à ce qui se *raisonne* — est sorti du code et
rassemblé dans `reglages.json`, à côté.

Trois raisons, dans l'ordre d'importance.

**On règle là où on regarde.** Un barème se juge en le voyant produire des
paliers, c'est-à-dire sur `dev/baremes.html`, souvent depuis la tablette. Cette
page rend désormais le fichier prêt à coller : on remplace un seul fichier, on
pousse, et les deux applications changent ensemble. Tant que les valeurs
vivaient en dur dans `paliers.py`, régler demandait d'ouvrir un fichier de six
cents lignes de code et de prose sur un écran tactile.

**Une seule source, des deux côtés.** `preparer_demo` recopie ce fichier tel
quel dans `donnees/baremes.json` : le Python le lit ici, le JavaScript le lit
là, et il n'existe aucune troisième valeur à réconcilier. C'est la même règle
que pour les sons et les programmes.

**Le pourquoi reste dans le code.** JSON ne prend pas de commentaires, et les
réglages de ce projet en demandent : `cible_min` appartient au débutant,
`cible_max` fixe le volume de fin de tranche, `poids_max` empêche le barème de
proposer un curl à 18 kg. Ces explications sont restées dans la docstring de
`progression/paliers.py` et dans `CLAUDE.md`, où elles se lisent — mais elles
ne sont plus accolées aux nombres, et c'est le prix assumé de l'édition depuis
la tablette. **Changer une valeur ici sans avoir lu la note correspondante
là-bas est la façon la plus simple de casser le barème en silence.**

Le chargement **lève** si le fichier manque ou s'il est illisible, au lieu de
retomber sur un barème vide : un moteur de progression sans palier ne
proposerait plus rien, à tout le monde, sans rien signaler.
"""

from __future__ import annotations

import json
from pathlib import Path

CHEMIN = Path(__file__).resolve().parent / "reglages.json"


def charger(chemin=None):
    """Lit le fichier de réglages. Lève si quoi que ce soit cloche."""
    chemin = Path(chemin) if chemin else CHEMIN
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    for cle in ("specs", "ligues", "xp"):
        if cle not in donnees:
            raise ValueError(f"{chemin.name} : section « {cle} » absente")
    if not donnees["specs"]:
        raise ValueError(f"{chemin.name} : aucun barème, le moteur n'aurait rien à proposer")
    return donnees


#: Lu une fois au chargement du module. C'est une lecture, pas un effet de
#: bord : le fichier est déterministe et versionné, et tout le reste du
#: paquet en dépend dès l'import.
REGLAGES = charger()
