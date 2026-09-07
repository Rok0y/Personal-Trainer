# ==========================================
# ÉTAT DU PROGRAMME
# ==========================================

position_actuelle = "Aucune"
exercice_actuel = "Aucun"
mode = "Aucun"
stage = "Aucune"
"""Jeton brut rendu par la fonction de détection ("debut", "fin", "casse"...).

Reste volontairement brut : `etape_libelle` en porte la traduction française,
et le front n'a plus à deviner la posture en comparant des chaînes.
"""
etape_libelle = None
"""Traduction lisible de `stage` (core.messages.libelle_etape)."""
erreur = None
"""Faute de forme détectée pendant l'effort : ce qui est mal fait."""
consigne = None
"""Message d'accompagnement : ce qu'il faut faire.

Distinct d'`erreur`, qui reproche ; celui-ci guide (« place-toi devant la
caméra », « croise les bras pour démarrer »). Les deux peuvent coexister à
l'écran, dans deux bandeaux de couleurs différentes.
"""
fiche = None
"""Fiche de l'exercice courant (description, mise en place, consignes).

Alimentée depuis `Exercice` : les consignes existaient depuis toujours dans le
catalogue sans jamais atteindre l'écran.
"""

fiche_suivante = None
"""Fiche du prochain exercice, pour la lire pendant le repos qui le précède.

Champ séparé de `fiche` et non son remplaçant : les deux pauses n'ont pas le
même besoin. Pendant `recuperation_serie` on refait le même mouvement et c'est
`fiche` qu'il faut relire ; pendant `repos_exercice` on prépare le suivant, et
le matériel comme le cadrage caméra se décident avant la première répétition,
pas après. Un champ unique obligerait à le faire redevenir la fiche courante à
la reprise.
"""
repetitions = 0
repetitions_cibles = 10
temps_maintien = 0
duree_maintien = 0
temps_chrono = 0
chrono_termine = False
temps_echauffement = 0
duree_echauffement = 0
prochaine_etape = None
# ==========================================
# CIRCUIT
# ==========================================

serie_actuelle = 1
nombre_series = 1
phase = "exercice"
temps_repos_restant = 0
temps_amrap_restant = 0
poids = 0

# ==========================================
# MAINTIEN
# ==========================================

maintien_termine = False
progression_maintien = 0
progression_preparation = 0


# ==========================================
# VIDEO
# ==========================================

latest_frame = None
frame_id = 0
"""Incrémenté à chaque nouvelle frame encodée : permet au flux
web de n'envoyer une image que lorsqu'elle a réellement changé."""
