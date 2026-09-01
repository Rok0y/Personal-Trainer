#!/usr/bin/env python3
"""Exécute une requête SQL en lecture seule sur historique/personaltrainer.db.

Usage:
    python3 query_db.py "SELECT * FROM seances ORDER BY date DESC LIMIT 5"
    python3 query_db.py "PRAGMA table_info(exercices)"

La base est ouverte en mode read-only (URI ?mode=ro) : toute tentative
d'écriture échoue au niveau de SQLite lui-même, même si la requête passe
la validation ci-dessous. Deux lignes de défense plutôt qu'une.
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[4] / "historique" / "personaltrainer.db"

MOTS_CLES_ECRITURE = (
    "insert", "update", "delete", "drop", "alter", "create",
    "replace", "truncate", "attach", "detach", "vacuum", "pragma writable_schema",
)


def valider_lecture_seule(requete):
    premiere_instruction = requete.strip().split(";")[0].strip().lower()
    if not premiere_instruction:
        raise ValueError("Requête vide.")
    if not (premiere_instruction.startswith("select") or premiere_instruction.startswith("pragma") or premiere_instruction.startswith("explain")):
        raise ValueError(
            "Ce skill n'exécute que des requêtes en lecture (SELECT / PRAGMA / EXPLAIN). "
            "Pour modifier la base, utilise directement `sqlite3` ou Python en dehors du skill."
        )
    for mot in MOTS_CLES_ECRITURE:
        if mot in premiere_instruction:
            raise ValueError(f"Mot-clé d'écriture détecté ({mot!r}) : requête refusée.")


def formater_table(colonnes, lignes):
    if not lignes:
        return "(aucune ligne)"
    largeurs = [
        max(len(str(colonne)), max((len(str(ligne[i])) for ligne in lignes), default=0))
        for i, colonne in enumerate(colonnes)
    ]
    def formater_ligne(valeurs):
        return " | ".join(str(v).ljust(largeurs[i]) for i, v in enumerate(valeurs))

    separateur = "-+-".join("-" * largeur for largeur in largeurs)
    resultat = [formater_ligne(colonnes), separateur]
    resultat.extend(formater_ligne(ligne) for ligne in lignes)
    return "\n".join(resultat)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 query_db.py \"<requête SQL>\"", file=sys.stderr)
        sys.exit(1)

    requete = sys.argv[1]

    try:
        valider_lecture_seule(requete)
    except ValueError as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        sys.exit(1)

    if not DB_PATH.exists():
        print(f"Erreur : base introuvable à {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        curseur = conn.cursor()
        curseur.execute(requete)
        lignes = curseur.fetchall()
        colonnes = [description[0] for description in curseur.description] if curseur.description else []
        print(formater_table(colonnes, lignes))
        print(f"\n({len(lignes)} ligne(s))")
    except sqlite3.Error as erreur:
        print(f"Erreur SQL : {erreur}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
