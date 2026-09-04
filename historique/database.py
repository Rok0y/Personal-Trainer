import sqlite3
from datetime import datetime

CHEMIN_DB = "historique/personaltrainer.db"

# Nom donné au profil créé pour recueillir l'historique d'avant les profils.
# Renommable depuis l'écran de connexion : c'est un point de départ, pas une
# identité imposée.
NOM_PROFIL_REPRIS = "Moi"


def connexion():

    return sqlite3.connect(CHEMIN_DB)


def _profil_courant(utilisateur_id=None):
    """Résout le profil auquel une requête s'applique.

    Toutes les fonctions cloisonnées prennent `utilisateur_id=None` et passent
    par ici : `None` veut dire « le profil connecté », un entier veut dire « ce
    profil-là ». C'est ce paramètre explicite qui rend la couche données
    utilisable pour un classement (`recuperer_historique(utilisateur_id=2)`)
    sans rien changer le jour où l'application deviendra multi-sessions : seule
    la *résolution* de « qui est-ce » bougera.

    L'absence de profil connecté lève plutôt que de retomber sur un profil par
    défaut : écrire une séance dans l'historique de quelqu'un d'autre est une
    corruption silencieuse, un plantage se voit.
    """
    if utilisateur_id is not None:
        return int(utilisateur_id)

    from core.utilisateur import utilisateur_connecte

    connecte = utilisateur_connecte()
    if connecte is None:
        raise RuntimeError(
            "Aucun profil connecté : impossible de lire ou d'écrire l'historique."
        )
    return int(connecte["id"])


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
    # Le cloisonnement par profil ne porte que sur les deux tables racines :
    # `exercices` et `series_realisees` héritent de leur clé étrangère, y
    # dupliquer la colonne serait une dénormalisation à maintenir.
    if "utilisateur_id" not in colonnes_seances:
        curseur.execute(
            "ALTER TABLE seances ADD COLUMN utilisateur_id INTEGER DEFAULT 1"
        )

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
    if "entrelace_avec" not in colonnes_exercices:
        curseur.execute("ALTER TABLE exercices ADD COLUMN entrelace_avec TEXT")
    if "repos_entre_series" not in colonnes_exercices:
        curseur.execute(
            "ALTER TABLE exercices ADD COLUMN repos_entre_series INTEGER DEFAULT 0"
        )
    if "repos_apres" not in colonnes_exercices:
        curseur.execute(
            "ALTER TABLE exercices ADD COLUMN repos_apres INTEGER DEFAULT 0"
        )
    # Ressenti déclaré après coup par l'utilisateur (`progression/ressenti.py`).
    # Vide tant qu'il n'a rien dit : c'est une absence de réponse, pas un « ok ».
    if "ressenti" not in colonnes_exercices:
        curseur.execute("ALTER TABLE exercices ADD COLUMN ressenti TEXT DEFAULT ''")

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

    # Ancrages de niveau : « à partir d'ici, je suis niveau N sur cet
    # exercice ». Sert à recaler un niveau que l'historique ne peut pas
    # prouver (séance faite sans l'app, reprise après blessure, démarrage d'un
    # nouvel utilisateur). C'est un journal : on ajoute, on n'écrase pas.
    #
    # `apres_seance_id` est le repère chronologique, et non la date : les dates
    # de séance sont stockées en JJ/MM/AAAA, format dans lequel une comparaison
    # de chaînes est fausse. Les identifiants, eux, sont AUTOINCREMENT, donc
    # strictement croissants dans l'ordre d'enregistrement.
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS corrections_niveaux (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_exercice TEXT NOT NULL,
            niveau INTEGER NOT NULL,
            date TEXT NOT NULL,
            apres_seance_id INTEGER DEFAULT 0,
            raison TEXT DEFAULT ''
        )
    """)

    colonnes_corrections = {
        ligne[1] for ligne in curseur.execute("PRAGMA table_info(corrections_niveaux)")
    }
    if "utilisateur_id" not in colonnes_corrections:
        curseur.execute(
            "ALTER TABLE corrections_niveaux ADD COLUMN utilisateur_id INTEGER DEFAULT 1"
        )

    # Profils. Pas de colonne « actif » : le profil connecté est un état de
    # session, pas une donnée persistée — on se reconnecte à chaque lancement.
    # Le mot de passe n'existe pas encore ; la table est faite pour en recevoir
    # un sans migration douloureuse.
    curseur.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            cree_le TEXT NOT NULL
        )
    """)

    # À l'échelle visée, toute requête filtre par profil : ces index ne sont
    # pas optionnels.
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS index_seances_utilisateur
        ON seances(utilisateur_id)
    """)
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS index_exercices_seance
        ON exercices(seance_id)
    """)
    curseur.execute("""
        CREATE INDEX IF NOT EXISTS index_corrections_utilisateur
        ON corrections_niveaux(utilisateur_id, nom_exercice)
    """)

    # Reprise d'une base d'avant les profils : l'historique existant porte
    # `utilisateur_id = 1` par le DEFAULT, il lui faut donc un profil 1 à qui
    # appartenir. On ne le crée que s'il y a quelque chose à rattacher — sur
    # une base vierge, c'est l'écran de connexion qui crée le premier profil,
    # et personne n'hérite par accident de l'historique d'un autre.
    curseur.execute("SELECT COUNT(*) FROM utilisateurs")
    if curseur.fetchone()[0] == 0:
        curseur.execute("SELECT COUNT(*) FROM seances")
        if curseur.fetchone()[0] > 0:
            curseur.execute(
                "INSERT INTO utilisateurs (id, nom, cree_le) VALUES (1, ?, ?)",
                (NOM_PROFIL_REPRIS, datetime.now().strftime("%d/%m/%Y %H:%M")),
            )

    conn.commit()

    conn.close()


def lister_utilisateurs():
    """Tous les profils, du plus ancien au plus récent."""
    initialiser()
    conn = connexion()
    curseur = conn.cursor()
    curseur.execute("SELECT id, nom, cree_le FROM utilisateurs ORDER BY id")
    profils = [
        {"id": ligne[0], "nom": ligne[1], "cree_le": ligne[2]}
        for ligne in curseur.fetchall()
    ]
    conn.close()
    return profils


def recuperer_utilisateur(utilisateur_id):
    """Un profil par son identifiant, ou None s'il n'existe pas."""
    initialiser()
    conn = connexion()
    curseur = conn.cursor()
    curseur.execute(
        "SELECT id, nom, cree_le FROM utilisateurs WHERE id = ?", (utilisateur_id,)
    )
    ligne = curseur.fetchone()
    conn.close()
    if ligne is None:
        return None
    return {"id": ligne[0], "nom": ligne[1], "cree_le": ligne[2]}


def creer_utilisateur(nom):
    """Crée un profil et retourne son dictionnaire.

    Le nom est unique : deux profils homonymes seraient indiscernables sur
    l'écran de connexion comme dans un futur classement.
    """
    nom = (nom or "").strip()
    if not nom:
        raise ValueError("Le nom du profil ne peut pas être vide.")

    initialiser()
    conn = connexion()
    curseur = conn.cursor()
    curseur.execute(
        "SELECT id FROM utilisateurs WHERE nom = ? COLLATE NOCASE", (nom,)
    )
    if curseur.fetchone() is not None:
        conn.close()
        raise ValueError(f"Un profil nommé « {nom} » existe déjà.")

    curseur.execute(
        "INSERT INTO utilisateurs (nom, cree_le) VALUES (?, ?)",
        (nom, datetime.now().strftime("%d/%m/%Y %H:%M")),
    )
    utilisateur_id = curseur.lastrowid
    conn.commit()
    conn.close()
    return {"id": utilisateur_id, "nom": nom}


def renommer_utilisateur(utilisateur_id, nouveau_nom):
    """Change le nom d'un profil sans toucher à ses données.

    Rien ne référence un profil par son nom — l'appartenance passe par l'id —
    donc un renommage est purement cosmétique, contrairement à celui d'une
    séance.
    """
    nouveau_nom = (nouveau_nom or "").strip()
    if not nouveau_nom:
        raise ValueError("Le nom du profil ne peut pas être vide.")

    initialiser()
    conn = connexion()
    curseur = conn.cursor()
    curseur.execute(
        "SELECT id FROM utilisateurs WHERE nom = ? COLLATE NOCASE AND id != ?",
        (nouveau_nom, utilisateur_id),
    )
    if curseur.fetchone() is not None:
        conn.close()
        raise ValueError(f"Un profil nommé « {nouveau_nom} » existe déjà.")

    curseur.execute(
        "UPDATE utilisateurs SET nom = ? WHERE id = ?", (nouveau_nom, utilisateur_id)
    )
    modifies = curseur.rowcount
    conn.commit()
    conn.close()
    if not modifies:
        raise KeyError(f"Profil {utilisateur_id} introuvable")
    return {"id": int(utilisateur_id), "nom": nouveau_nom}


def enregistrer_seance(
    duree, exercices, statut="finished", nom_seance=None, utilisateur_id=None
):
    """Écrit une séance complète et retourne son identifiant.

    Le retour est indispensable à l'écran de fin, qui doit pouvoir annoter les
    lignes qui viennent d'être créées (`enregistrer_ressentis`).
    """

    utilisateur_id = _profil_courant(utilisateur_id)

    conn = connexion()

    curseur = conn.cursor()

    date = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Création séance

    curseur.execute(
        """
        INSERT INTO seances
        (date, duree, statut, nom_seance, utilisateur_id)

        VALUES (?, ?, ?, ?, ?)
        """,
        (date, duree, statut, nom_seance, utilisateur_id),
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
                duree_cible,
                entrelace_avec,
                repos_entre_series,
                repos_apres
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

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
                exercice.get("entrelace_avec"),
                exercice.get("repos_entre_series", 0),
                exercice.get("repos_apres", 0),
            ),
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

    return seance_id


def recuperer_historique(utilisateur_id=None):
    # Permet aussi la lecture d'une base créée par une version précédente,
    # même lorsque l'application n'a pas encore lancé son initialisation.
    initialiser()
    utilisateur_id = _profil_courant(utilisateur_id)
    conn = connexion()

    curseur = conn.cursor()

    curseur.execute(
        """
        SELECT
            id,
            date,
            duree,
            statut,
            nom_seance
        FROM seances

        WHERE utilisateur_id = ?

        ORDER BY id DESC
        """,
        (utilisateur_id,),
    )

    seances = curseur.fetchall()

    resultat = []

    for seance in seances:

        seance_id = seance[0]

        curseur.execute(
            """
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
                duree_cible,
                entrelace_avec,
                repos_entre_series,
                repos_apres,
                ressenti

            FROM exercices

            WHERE seance_id = ?

        """,
            (seance_id,),
        )

        exercices = curseur.fetchall()

        resultat.append(
            {
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
                        "entrelace_avec": exercice[11],
                        "repos_entre_series": exercice[12] or 0,
                        "repos_apres": exercice[13] or 0,
                        "ressenti": exercice[14] or "",
                        "series_detaillees": recuperer_series(curseur, exercice[0]),
                    }
                    for exercice in exercices
                ],
            }
        )

    conn.close()

    return resultat


def recuperer_series(curseur, exercice_id):
    curseur.execute(
        """
        SELECT numero, repetitions, poids, duree, completee
        FROM series_realisees
        WHERE exercice_id = ?
        ORDER BY numero
    """,
        (exercice_id,),
    )
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


def enregistrer_ressentis(seance_id, ressentis, utilisateur_id=None):
    """Annote après coup les exercices d'une séance déjà écrite.

    C'est une mise à jour et non une insertion : la séance est enregistrée par
    le thread caméra dès le passage en phase terminale, bien avant que
    l'utilisateur n'ait vu l'écran de fin.

    `ressentis` associe un nom d'exercice à une valeur de l'échelle, ou à une
    chaîne vide pour effacer une réponse. Une valeur inconnue lève `ValueError`
    plutôt que de polluer l'historique — le calcul d'objectif la lirait comme
    une absence de réponse, silencieusement.
    """
    from progression.ressenti import est_valide

    initialiser()

    inconnues = sorted(
        {valeur for valeur in ressentis.values() if valeur and not est_valide(valeur)}
    )
    if inconnues:
        raise ValueError(f"Ressenti inconnu : {', '.join(inconnues)}")

    utilisateur_id = _profil_courant(utilisateur_id)
    conn = connexion()
    curseur = conn.cursor()
    curseur.executemany(
        """
        UPDATE exercices SET ressenti = ?
        WHERE seance_id = ? AND nom = ?
          AND seance_id IN (SELECT id FROM seances WHERE utilisateur_id = ?)
        """,
        [
            (valeur or "", seance_id, nom_exercice, utilisateur_id)
            for nom_exercice, valeur in ressentis.items()
        ],
    )
    modifiees = curseur.rowcount
    conn.commit()
    conn.close()
    return modifiees


def enregistrer_ancrage(nom_exercice, niveau, raison="", utilisateur_id=None):
    """Pose un ancrage de niveau, valable à partir de maintenant.

    L'historique antérieur cesse de compter pour cet exercice : c'est ce qui
    permet à un ancrage de corriger un niveau *vers le bas*, et pas seulement
    de le relever.
    """
    initialiser()
    utilisateur_id = _profil_courant(utilisateur_id)
    conn = connexion()
    curseur = conn.cursor()

    # Le repere chronologique doit etre la derniere seance *de ce profil* :
    # une seance faite par quelqu'un d'autre entre-temps rendrait l'ancrage
    # posterieur a des seances qu'il n'a pas vocation a effacer.
    curseur.execute(
        "SELECT COALESCE(MAX(id), 0) FROM seances WHERE utilisateur_id = ?",
        (utilisateur_id,),
    )
    derniere_seance = curseur.fetchone()[0]

    curseur.execute(
        """
        INSERT INTO corrections_niveaux
        (nom_exercice, niveau, date, apres_seance_id, raison, utilisateur_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            nom_exercice,
            int(niveau),
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            derniere_seance,
            raison or "",
            utilisateur_id,
        ),
    )

    conn.commit()
    conn.close()


def recuperer_ancrages(utilisateur_id=None):
    """Dernier ancrage de chaque exercice, indexé par nom d'exercice.

    Seul le plus récent compte : les précédents restent en base comme trace,
    mais un ancrage plus récent les remplace entièrement.
    """
    initialiser()
    utilisateur_id = _profil_courant(utilisateur_id)
    conn = connexion()
    curseur = conn.cursor()

    curseur.execute(
        """
        SELECT nom_exercice, niveau, date, apres_seance_id, raison, id
        FROM corrections_niveaux
        WHERE utilisateur_id = ?
        ORDER BY id
        """,
        (utilisateur_id,),
    )

    ancrages = {}
    for ligne in curseur.fetchall():
        ancrages[ligne[0]] = {
            "niveau": ligne[1],
            "date": ligne[2],
            "apres_seance_id": ligne[3] or 0,
            "raison": ligne[4] or "",
            "id": ligne[5],
        }

    conn.close()
    return ancrages


def supprimer_ancrages(nom_exercice, utilisateur_id=None):
    """Efface les ancrages d'un exercice : son niveau redevient purement déduit."""
    initialiser()
    utilisateur_id = _profil_courant(utilisateur_id)
    conn = connexion()
    curseur = conn.cursor()
    curseur.execute(
        """
        DELETE FROM corrections_niveaux
        WHERE nom_exercice = ? AND utilisateur_id = ?
        """,
        (nom_exercice, utilisateur_id),
    )
    supprimes = curseur.rowcount
    conn.commit()
    conn.close()
    return supprimes


def recuperer_historique_ancrages(nom_exercice, utilisateur_id=None):
    """Tous les ancrages posés sur un exercice, du plus récent au plus ancien.

    Contrairement à `recuperer_ancrages`, qui ne garde que le dernier de
    chaque exercice pour le calcul du niveau, cette fonction sert à afficher
    le journal complet.
    """
    initialiser()
    utilisateur_id = _profil_courant(utilisateur_id)
    conn = connexion()
    curseur = conn.cursor()
    curseur.execute(
        """
        SELECT id, niveau, date, apres_seance_id, raison
        FROM corrections_niveaux
        WHERE nom_exercice = ? AND utilisateur_id = ?
        ORDER BY id DESC
        """,
        (nom_exercice, utilisateur_id),
    )
    ancrages = [
        {
            "id": ligne[0],
            "niveau": ligne[1],
            "date": ligne[2],
            "apres_seance_id": ligne[3] or 0,
            "raison": ligne[4] or "",
        }
        for ligne in curseur.fetchall()
    ]
    conn.close()
    return ancrages


def supprimer_ancrage(id_ancrage, utilisateur_id=None):
    """Efface un seul ancrage du journal, par id.

    Le filtre par profil n'est pas decoratif : l'identifiant vient de l'URL,
    donc d'un utilisateur, et rien n'empecherait sinon d'effacer l'ancrage de
    quelqu'un d'autre en changeant le numero.
    """
    initialiser()
    utilisateur_id = _profil_courant(utilisateur_id)
    conn = connexion()
    curseur = conn.cursor()
    curseur.execute(
        "DELETE FROM corrections_niveaux WHERE id = ? AND utilisateur_id = ?",
        (id_ancrage, utilisateur_id),
    )
    supprimes = curseur.rowcount
    conn.commit()
    conn.close()
    return supprimes


def statistiques_exercices(seances=None):
    """Calcule les records uniquement sur les séances détaillées terminées."""
    seances = recuperer_historique() if seances is None else seances
    statistiques = {}

    for seance in seances:
        if seance.get("statut") == "abandoned":
            continue
        for exercice in seance.get("exercices", []):
            series = [
                serie
                for serie in exercice.get("series_detaillees", [])
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
            entree = statistiques.setdefault(
                nom,
                {
                    "nom": nom,
                    "mode": exercice.get("mode", "repetitions"),
                    "seances": 0,
                    "series": 0,
                    "repetitions": 0,
                    "volume": 0,
                    "duree": 0,
                    "meilleure_charge": {"valeur": 0, "seance_id": None, "date": None},
                    "meilleures_repetitions": {
                        "valeur": 0,
                        "seance_id": None,
                        "date": None,
                    },
                    "meilleur_volume": {"valeur": 0, "seance_id": None, "date": None},
                    "meilleure_duree": {"valeur": 0, "seance_id": None, "date": None},
                    "progression": [],
                },
            )
            entree["seances"] += 1
            entree["series"] += len(series)
            entree["repetitions"] += repetitions
            entree["volume"] += volume
            entree["duree"] += duree
            entree["progression"].append(
                {
                    "seance_id": seance["id"],
                    "date": seance["date"],
                    "repetitions": repetitions,
                    "volume": volume,
                    "duree": duree,
                }
            )

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


def derniere_performance(nom_seance, utilisateur_id=None):
    """Retourne la dernière séance terminée portant ce nom, si elle existe."""
    seances = recuperer_historique(utilisateur_id)
    for seance in seances:
        if seance.get("nom") == nom_seance and seance.get("statut") != "abandoned":
            return seance
    return None


def renommer_seance(ancien_nom, nouveau_nom, utilisateur_id=None):
    """Reporte l'historique sur le nouveau nom quand une séance est renommée.

    Sans cela, l'historique déjà enregistré reste attaché à l'ancien nom et
    n'apparait plus ni sur l'accueil ni dans la dernière performance.
    """
    if ancien_nom == nouveau_nom:
        return

    utilisateur_id = _profil_courant(utilisateur_id)
    conn = connexion()
    curseur = conn.cursor()
    curseur.execute(
        """
        UPDATE seances SET nom_seance = ?
        WHERE nom_seance = ? AND utilisateur_id = ?
        """,
        (nouveau_nom, ancien_nom, utilisateur_id),
    )
    conn.commit()
    conn.close()


def supprimer_seance(seance_id, utilisateur_id=None):
    """Supprime une séance de l'historique, avec tous ses exercices et séries."""
    utilisateur_id = _profil_courant(utilisateur_id)
    conn = connexion()
    curseur = conn.cursor()

    # Le filtre par profil transforme « la seance d'un autre » en « seance
    # introuvable » : l'identifiant vient de l'URL, il ne doit pas suffire a
    # atteindre l'historique de quelqu'un d'autre.
    curseur.execute(
        "SELECT id FROM seances WHERE id = ? AND utilisateur_id = ?",
        (seance_id, utilisateur_id),
    )
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


def supprimer_exercice_de_seance(seance_id, nom_exercice, utilisateur_id=None):
    """Supprime un exercice précis (et ses séries) d'une séance de l'historique."""
    utilisateur_id = _profil_courant(utilisateur_id)
    conn = connexion()
    curseur = conn.cursor()

    curseur.execute(
        """
        SELECT exercices.id FROM exercices
        JOIN seances ON seances.id = exercices.seance_id
        WHERE exercices.seance_id = ?
          AND exercices.nom = ?
          AND seances.utilisateur_id = ?
        """,
        (seance_id, nom_exercice, utilisateur_id),
    )
    ids_exercices = [ligne[0] for ligne in curseur.fetchall()]
    if not ids_exercices:
        conn.close()
        raise KeyError(
            f"Exercice « {nom_exercice} » introuvable pour la séance {seance_id}"
        )

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
