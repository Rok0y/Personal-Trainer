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
                duree
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)

            """,

            (
                seance_id,
                exercice["nom"],
                exercice["series"],
                exercice["repetitions"],
                exercice.get("poids", 0),
                exercice.get("mode"),
                exercice.get("duree", 0)
            )
        )


    conn.commit()

    conn.close()

def recuperer_historique():

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
                nom,
                series,
                repetitions,
                poids,
                mode,
                duree

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
                    "nom": exercice[0],
                    "series": exercice[1],
                    "repetitions": exercice[2],
                    "poids": exercice[3] or 0,
                    "mode": exercice[4] or "repetitions",
                    "duree": exercice[5] or 0,
                }
                for exercice in exercices
            ]

        })


    conn.close()


    return resultat