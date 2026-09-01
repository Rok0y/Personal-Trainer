import sqlite3
from datetime import datetime


CHEMIN_DB = "historique/personaltrainer.db"



def connexion():

    return sqlite3.connect(
        CHEMIN_DB
    )



def initialiser():

    conn = connexion()

    curseur = conn.cursor()


    # Table des séances
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS seances (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            date TEXT NOT NULL,

            duree INTEGER DEFAULT 0

        )
    """)

    colonnes_seances = {
        ligne[1] for ligne in curseur.execute("PRAGMA table_info(seances)")
    }
    if "statut" not in colonnes_seances:
        curseur.execute("ALTER TABLE seances ADD COLUMN statut TEXT DEFAULT 'finished'")
    if "nom_seance" not in colonnes_seances:
        curseur.execute("ALTER TABLE seances ADD COLUMN nom_seance TEXT")

    # Table des exercices réalisés
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS exercices (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            seance_id INTEGER,

            nom TEXT,

            series INTEGER,

            repetitions INTEGER,

            FOREIGN KEY(seance_id)
            REFERENCES seances(id)

        )
    """)

    colonnes_exercices = {
        ligne[1] for ligne in curseur.execute("PRAGMA table_info(exercices)")
    }
    if "poids" not in colonnes_exercices:
        curseur.execute("ALTER TABLE exercices ADD COLUMN poids REAL DEFAULT 0")
    if "mode" not in colonnes_exercices:
        curseur.execute("ALTER TABLE exercices ADD COLUMN mode TEXT")
    if "duree" not in colonnes_exercices:
        curseur.execute("ALTER TABLE exercices ADD COLUMN duree REAL DEFAULT 0")
    if "commentaire" not in colonnes_exercices:
        curseur.execute("ALTER TABLE exercices ADD COLUMN commentaire TEXT DEFAULT ''")
    if "series_cibles" not in colonnes_exercices:
        curseur.execute("ALTER TABLE exercices ADD COLUMN series_cibles INTEGER")
    if "repetitions_cibles" not in colonnes_exercices:
        curseur.execute("ALTER TABLE exercices ADD COLUMN repetitions_cibles INTEGER")
    if "duree_cible" not in colonnes_exercices:
        curseur.execute("ALTER TABLE exercices ADD COLUMN duree_cible REAL")

    curseur.execute("""
        CREATE TABLE IF NOT EXISTS series_realisees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercice_id INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            repetitions INTEGER DEFAULT 0,
            poids REAL DEFAULT 0,
            duree REAL DEFAULT 0,
            completee INTEGER DEFAULT 1,
            FOREIGN KEY(exercice_id) REFERENCES exercices(id)
        )
    """)

    curseur.execute("""
        CREATE INDEX IF NOT EXISTS index_series_exercice
        ON series_realisees(exercice_id)
    """)


    conn.commit()

    conn.close()



def enregistrer_seance(
    duree,
    exercices,
    statut="finished",
    nom_seance=None
):

    conn = connexion()

    curseur = conn.cursor()


    date = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )


    # Création séance

    curseur.execute(
        """
        INSERT INTO seances
        (date, duree, statut, nom_seance)

        VALUES (?, ?, ?, ?)
        """,
        (
            date,
            duree,
            statut,
            nom_seance
        )
    )


    seance_id = curseur.lastrowid



    # Ajout exercices

    for exercice in exercices:

        curseur.execute(
            """
            INSERT INTO exercices

            (
                seance_id,
                nom,
                series,
                repetitions,
                poids,
                mode,
                duree,
                commentaire,
                series_cibles,
                repetitions_cibles,
                duree_cible
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            """,

            (
                seance_id,
                exercice["nom"],
                exercice["series"],
                exercice["repetitions"],
                exercice.get("poids", 0),
                exercice.get("mode"),
                exercice.get("duree", 0),
                exercice.get("commentaire", ""),
                exercice.get("series_cibles", exercice["series"]),
                exercice.get("repetitions_cibles", 0),
                exercice.get("duree_cible", exercice.get("duree", 0)),
            )
        )

        exercice_id = curseur.lastrowid
        for serie in exercice.get("series_detaillees", []):
            curseur.execute(
                """
                INSERT INTO series_realisees
                (exercice_id, numero, repetitions, poids, duree, completee)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    exercice_id,
                    serie.get("serie", 0),
                    serie.get("repetitions", 0),
                    serie.get("poids", exercice.get("poids", 0)),
                    serie.get("duree", 0),
                    int(serie.get("completee", True)),
                ),
            )


    conn.commit()

    conn.close()

def recuperer_historique():
    # Permet aussi la lecture d'une base créée par une version précédente,
    # même lorsque l'application n'a pas encore lancé son initialisation.
    initialiser()
    conn = connexion()

    curseur = conn.cursor()


    curseur.execute("""
        SELECT
            id,
            date,
            duree,
            statut,
            nom_seance
        FROM seances

        ORDER BY id DESC
    """)


    seances = curseur.fetchall()


    resultat = []


    for seance in seances:

        seance_id = seance[0]


        curseur.execute("""
            SELECT
            id,
                nom,
                series,
                repetitions,
                poids,
                mode,
                duree,
                commentaire,
                series_cibles,
                repetitions_cibles,
                duree_cible

            FROM exercices

            WHERE seance_id = ?

        """, (seance_id,))


        exercices = curseur.fetchall()


        resultat.append({

            "id": seance[0],
            "date": seance[1],
            "duree": seance[2],
            "statut": seance[3] or "finished",
            "nom": seance[4],
            "exercices": [
                {
                    "nom": exercice[1],
                    "series": exercice[2],
                    "repetitions": exercice[3],
                    "poids": exercice[4] or 0,
                    "mode": exercice[5] or "repetitions",
                    "duree": exercice[6] or 0,
                    "commentaire": exercice[7] or "",
                    "series_cibles": exercice[8] or exercice[2],
                    "repetitions_cibles": exercice[9] or 0,
                    "duree_cible": exercice[10] or 0,
                    "series_detaillees": recuperer_series(curseur, exercice[0]),
                }
                for exercice in exercices
            ]

        })


    conn.close()


    return resultat


def recuperer_series(curseur, exercice_id):
    curseur.execute("""
        SELECT numero, repetitions, poids, duree, completee
        FROM series_realisees
        WHERE exercice_id = ?
        ORDER BY numero
    """, (exercice_id,))
    return [
        {
            "serie": ligne[0],
            "repetitions": ligne[1] or 0,
            "poids": ligne[2] or 0,
            "duree": ligne[3] or 0,
            "completee": bool(ligne[4]),
        }
        for ligne in curseur.fetchall()
    ]


def statistiques_exercices(seances=None):
    """Calcule les records uniquement sur les séances détaillées terminées."""
    seances = recuperer_historique() if seances is None else seances
    statistiques = {}

    for seance in seances:
        if seance.get("statut") == "abandoned":
            continue
        for exercice in seance.get("exercices", []):
            series = [
                serie for serie in exercice.get("series_detaillees", [])
                if serie.get("completee")
            ]
            if not series:
                continue

            nom = exercice["nom"]
            poids = max((serie.get("poids", 0) or 0) for serie in series)
            repetitions = sum(serie.get("repetitions", 0) or 0 for serie in series)
            volume = sum(
                (serie.get("poids", 0) or 0) * (serie.get("repetitions", 0) or 0)
                for serie in series
            )
            duree = sum(serie.get("duree", 0) or 0 for serie in series)
            entree = statistiques.setdefault(nom, {
                "nom": nom,
                "mode": exercice.get("mode", "repetitions"),
                "seances": 0,
                "series": 0,
                "repetitions": 0,
                "volume": 0,
                "duree": 0,
                "meilleure_charge": {"valeur": 0, "seance_id": None, "date": None},
                "meilleures_repetitions": {"valeur": 0, "seance_id": None, "date": None},
                "meilleur_volume": {"valeur": 0, "seance_id": None, "date": None},
                "meilleure_duree": {"valeur": 0, "seance_id": None, "date": None},
                "progression": [],
            })
            entree["seances"] += 1
            entree["series"] += len(series)
            entree["repetitions"] += repetitions
            entree["volume"] += volume
            entree["duree"] += duree
            entree["progression"].append({
                "seance_id": seance["id"],
                "date": seance["date"],
                "repetitions": repetitions,
                "volume": volume,
                "duree": duree,
            })

            for cle, valeur in (
                ("meilleure_charge", poids),
                ("meilleures_repetitions", repetitions),
                ("meilleur_volume", volume),
                ("meilleure_duree", duree),
            ):
                if valeur > entree[cle]["valeur"]:
                    entree[cle] = {
                        "valeur": valeur,
                        "seance_id": seance["id"],
                        "date": seance["date"],
                    }

            if exercice.get("mode") in ("maintien", "chrono"):
                entree["pb"] = entree["meilleure_duree"]
            elif poids > 0:
                entree["pb"] = entree["meilleur_volume"]
            else:
                entree["pb"] = entree["meilleures_repetitions"]

    return statistiques


def derniere_performance(nom_seance):
    """Retourne la dernière séance terminée portant ce nom, si elle existe."""
    seances = recuperer_historique()
    for seance in seances:
        if seance.get("nom") == nom_seance and seance.get("statut") != "abandoned":
            return seance
    return None


def supprimer_seance(seance_id):
    """Supprime une séance de l'historique, avec tous ses exercices et séries."""
    conn = connexion()
    curseur = conn.cursor()

    curseur.execute("SELECT id FROM seances WHERE id = ?", (seance_id,))
    if curseur.fetchone() is None:
        conn.close()
        raise KeyError(f"Séance {seance_id} introuvable")

    curseur.execute(
        """
        DELETE FROM series_realisees
        WHERE exercice_id IN (
            SELECT id FROM exercices WHERE seance_id = ?
        )
        """,
        (seance_id,),
    )
    curseur.execute("DELETE FROM exercices WHERE seance_id = ?", (seance_id,))
    curseur.execute("DELETE FROM seances WHERE id = ?", (seance_id,))

    conn.commit()
    conn.close()


def supprimer_exercice_de_seance(seance_id, nom_exercice):
    """Supprime un exercice précis (et ses séries) d'une séance de l'historique."""
    conn = connexion()
    curseur = conn.cursor()

    curseur.execute(
        "SELECT id FROM exercices WHERE seance_id = ? AND nom = ?",
        (seance_id, nom_exercice),
    )
    ids_exercices = [ligne[0] for ligne in curseur.fetchall()]
    if not ids_exercices:
        conn.close()
        raise KeyError(f"Exercice « {nom_exercice} » introuvable pour la séance {seance_id}")

    curseur.executemany(
        "DELETE FROM series_realisees WHERE exercice_id = ?",
        [(id_exercice,) for id_exercice in ids_exercices],
    )
    curseur.executemany(
        "DELETE FROM exercices WHERE id = ?",
        [(id_exercice,) for id_exercice in ids_exercices],
    )

    conn.commit()
    conn.close()