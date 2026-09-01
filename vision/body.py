class LandmarkPoint:
    """
    Représente un point du corps.
    """

    def __init__(self, x, y, z, visibilite):
        self.x = x
        self.y = y
        self.z = z
        self.visibilite = visibilite

    def __repr__(self):
        return (
            f"x={self.x:.3f}, "
            f"y={self.y:.3f}, "
            f"z={self.z:.3f}, "
            f"visibilite={self.visibilite:.2f}"
        )


class Body:
    """
    Représente le corps complet.
    """

    def __init__(self, points):
        self.points = points

    def __getattr__(self, name):
        """
        Permet d'écrire :
        corps.poignet_gauche
        au lieu de :
        corps.points["poignet_gauche"]
        """

        if name in self.points:
            return self.points[name]

        raise AttributeError(f"Le point '{name}' n'existe pas")

    def get_point(self, name):
        """
        Alternative :
        corps.get_point("poignet_gauche")
        """

        return self.points.get(name)

    def __repr__(self):
        return f"Body({len(self.points)} points)"
