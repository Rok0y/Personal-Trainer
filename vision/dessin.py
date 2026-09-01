import cv2

# Toutes les connexions du squelette
CONNECTIONS = [
    # Visage
    ("nez", "oeil_gauche_interieur"),
    ("oeil_gauche_interieur", "oeil_gauche"),
    ("oeil_gauche", "oeil_gauche_exterieur"),
    ("oeil_gauche_exterieur", "oreille_gauche"),
    ("nez", "oeil_droit_interieur"),
    ("oeil_droit_interieur", "oeil_droit"),
    ("oeil_droit", "oeil_droit_exterieur"),
    ("oeil_droit_exterieur", "oreille_droite"),
    ("oreille_gauche", "oreille_droite"),
    # Bouche
    ("coin_bouche_gauche", "coin_bouche_droit"),
    # Bras gauche
    ("epaule_gauche", "coude_gauche"),
    ("coude_gauche", "poignet_gauche"),
    ("poignet_gauche", "petit_doigt_gauche"),
    ("poignet_gauche", "index_gauche"),
    ("poignet_gauche", "pouce_gauche"),
    # Bras droit
    ("epaule_droite", "coude_droit"),
    ("coude_droit", "poignet_droit"),
    ("poignet_droit", "petit_doigt_droit"),
    ("poignet_droit", "index_droit"),
    ("poignet_droit", "pouce_droit"),
    # Épaules
    ("epaule_gauche", "epaule_droite"),
    # Torse
    ("epaule_gauche", "hanche_gauche"),
    ("epaule_droite", "hanche_droite"),
    ("hanche_gauche", "hanche_droite"),
    # Jambe gauche
    ("hanche_gauche", "genou_gauche"),
    ("genou_gauche", "cheville_gauche"),
    ("cheville_gauche", "talon_gauche"),
    ("cheville_gauche", "pointe_pied_gauche"),
    # Jambe droite
    ("hanche_droite", "genou_droit"),
    ("genou_droit", "cheville_droite"),
    ("cheville_droite", "talon_droit"),
    ("cheville_droite", "pointe_pied_droite"),
]


def dessiner_squelette(frame, corps):

    hauteur, largeur, _ = frame.shape

    # --------------------------------------------------
    # Dessiner les connexions
    # --------------------------------------------------

    for nom1, nom2 in CONNECTIONS:

        point1 = corps.points.get(nom1)
        point2 = corps.points.get(nom2)

        if point1 is None or point2 is None:
            continue

        # Si les points sont trop peu visibles,
        # on ne dessine pas la connexion.
        if point1.visibilite < 0.5 or point2.visibilite < 0.5:
            continue

        x1 = int(point1.x * largeur)
        y1 = int(point1.y * hauteur)

        x2 = int(point2.x * largeur)
        y2 = int(point2.y * hauteur)

        cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # --------------------------------------------------
    # Dessiner les 33 points
    # --------------------------------------------------

    for nom, point in corps.points.items():

        if point is None:
            continue

        if point.visibilite < 0.5:
            continue

        x = int(point.x * largeur)
        y = int(point.y * hauteur)

        cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)

    return frame
