import sqlite3
from datetime import datetime


CHEMIN_DB = "historique/trackmebuddy.db"



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


    conn.commit()

    conn.close()



def enregistrer_seance(
    duree,
    exercices
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
        (date, duree)

        VALUES (?, ?)
        """,
        (
            date,
            duree
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
                repetitions
            )

            VALUES (?, ?, ?, ?)

            """,

            (
                seance_id,
                exercice["nom"],
                exercice["series"],
                exercice["repetitions"]
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
            duree
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
                repetitions

            FROM exercices

            WHERE seance_id = ?

        """, (seance_id,))


        exercices = curseur.fetchall()


        resultat.append({

            "date": seance[1],
            "duree": seance[2],
            "exercices": exercices

        })


    conn.close()


    return resultat