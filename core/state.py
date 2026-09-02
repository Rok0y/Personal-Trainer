# ==========================================
# ÉTAT DU PROGRAMME
# ==========================================

position_actuelle = "Aucune"
exercice_actuel = "Aucun"
mode = "Aucun"
stage = "Aucune"
erreur = None
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
