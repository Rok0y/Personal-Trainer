"""État d'une séance en cours, partagé entre la boucle caméra et le serveur.

C'était un espace de noms de variables globales de module. Le passage en
classe ne change rien au desktop — il y a toujours une instance, créée par le
`SessionManager` — mais il retire l'hypothèse « une seule séance à la fois »,
qui était inscrite dans la forme du code et non dans une décision. Deux
séances simultanées ne demandent désormais qu'un second `SessionManager`.

Le flux vidéo n'est volontairement pas ici : voir `core/flux.py`.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class EtatSeance:
    """Ce que la boucle caméra écrit et ce que la route `/etat` publie.

    `dataclass` plutôt que des attributs de classe : chaque champ est assigné
    par instance, et un défaut mutable ajouté par distraction lève à l'import
    au lieu d'être silencieusement partagé entre toutes les séances.
    """

    # ==========================================
    # ÉTAT DU PROGRAMME
    # ==========================================

    position_actuelle: str = "Aucune"
    exercice_actuel: str = "Aucun"
    mode: str = "Aucun"

    stage: str = "Aucune"
    """Jeton brut rendu par la fonction de détection ("debut", "fin", "casse"...).

    Reste volontairement brut : `etape_libelle` en porte la traduction
    française, et le front n'a plus à deviner la posture en comparant des
    chaînes.
    """

    etape_libelle: str | None = None
    """Traduction lisible de `stage` (core.messages.libelle_etape)."""

    erreur: str | None = None
    """Faute de forme détectée pendant l'effort : ce qui est mal fait."""

    consigne: str | None = None
    """Message d'accompagnement : ce qu'il faut faire.

    Distinct d'`erreur`, qui reproche ; celui-ci guide (« place-toi devant la
    caméra », « croise les bras pour démarrer »). Les deux peuvent coexister à
    l'écran, dans deux bandeaux de couleurs différentes.
    """

    fiche: dict[str, Any] | None = None
    """Fiche de l'exercice courant (description, mise en place, consignes).

    Alimentée depuis `Exercice` : les consignes existaient depuis toujours dans
    le catalogue sans jamais atteindre l'écran.
    """

    fiche_suivante: dict[str, Any] | None = None
    """Fiche du prochain exercice, pour la lire pendant le repos qui le précède.

    Champ séparé de `fiche` et non son remplaçant : les deux pauses n'ont pas
    le même besoin. Pendant `recuperation_serie` on refait le même mouvement et
    c'est `fiche` qu'il faut relire ; pendant `repos_exercice` on prépare le
    suivant, et le matériel comme le cadrage caméra se décident avant la
    première répétition, pas après. Un champ unique obligerait à le faire
    redevenir la fiche courante à la reprise.
    """

    test_max: bool = False
    """La série en cours est-elle un test de calibration (maximum au premier
    passage) ? Le front s'en sert pour remplacer la cible par « max » : la
    valeur réelle est un plafond volontairement inatteignable."""

    repetitions: int = 0
    repetitions_cibles: int = 10
    temps_maintien: float = 0
    duree_maintien: float = 0
    temps_chrono: float = 0
    chrono_termine: bool = False
    temps_echauffement: float = 0
    duree_echauffement: float = 0
    prochaine_etape: str | None = None

    # ==========================================
    # CIRCUIT
    # ==========================================

    serie_actuelle: int = 1
    nombre_series: int = 1
    phase: str = "exercice"
    temps_repos_restant: float = 0
    temps_amrap_restant: float = 0
    poids: float = 0

    # ==========================================
    # MAINTIEN
    # ==========================================

    maintien_termine: bool = False
    progression_maintien: float = 0
    progression_preparation: float = 0
