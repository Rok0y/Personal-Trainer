---
name: db-query
description: Interroge en SQL la base SQLite de ce repo (historique/personaltrainer.db) qui stocke l'historique des séances, exercices et séries réalisées. Utilise ce skill dès que l'utilisateur veut explorer, déboguer ou vérifier des données de séances/historique/records — questions du type "combien de séances cette semaine", "montre-moi les dernières séries de pompes", "pourquoi ce record ne s'affiche pas", "vérifie ce qu'il y a en base pour la séance X", ou toute demande explicite de requête SQL sur la base. Aussi utile pour comprendre le schéma réel de la base avant de modifier historique/database.py. En lecture seule : ne sert pas à corriger ou modifier des données.
---

# Interroger la base de données du Personal Trainer

La base SQLite (`historique/personaltrainer.db`, initialisée par `historique/database.py`) garde l'historique des séances réalisées. Ce skill donne un accès SQL direct pour explorer ces données sans avoir à relire `historique/database.py` ou à réimplémenter des requêtes en Python à chaque fois.

## Pourquoi passer par le script plutôt que sqlite3 directement

`scripts/query_db.py` ouvre la base en mode read-only (`?mode=ro`) et rejette toute requête qui n'est pas un `SELECT`/`PRAGMA`/`EXPLAIN`. C'est la base réelle des séances de l'utilisateur : une requête d'exploration mal formée (un `UPDATE` sans `WHERE`, par exemple) ne doit jamais pouvoir l'abîmer. Utilise systématiquement ce script pour toute lecture, même une requête triviale.

Si l'utilisateur demande explicitement de **modifier** des données (corriger une séance erronée, supprimer un doublon), ce skill n'est pas fait pour ça — dis-le et propose d'utiliser `sqlite3 historique/personaltrainer.db` directement, ou une fonction dédiée de `historique/database.py`, en confirmant l'opération avec l'utilisateur avant de l'exécuter.

## Utilisation

```bash
python3 .claude/skills/db-query/scripts/query_db.py "SELECT * FROM seances ORDER BY date DESC LIMIT 5"
```

Le résultat est affiché en table texte (colonnes + lignes + nombre de lignes). Une requête invalide ou une tentative d'écriture renvoie une erreur explicite sur stderr plutôt que d'échouer silencieusement.

## Schéma

Trois tables, définies dans `historique/database.py::initialiser()` :

**`seances`** — une ligne par séance réalisée
| colonne | type | notes |
|---|---|---|
| id | INTEGER PK | |
| date | TEXT | format `JJ/MM/AAAA HH:MM` |
| duree | INTEGER | durée totale en secondes |
| statut | TEXT | `finished` ou `abandoned` |
| nom_seance | TEXT | nom du circuit (ex. `upper_push`) — une séance de test sur un seul exercice porte le nom de cet exercice |

**`exercices`** — un exercice réalisé au sein d'une séance
| colonne | type | notes |
|---|---|---|
| id | INTEGER PK | |
| seance_id | INTEGER | FK → `seances.id` |
| nom | TEXT | nom de l'exercice |
| series, repetitions | INTEGER | totaux agrégés |
| poids | REAL | |
| mode | TEXT | `repetitions` / `maintien` / `chrono` / `amrap` |
| duree | REAL | pertinent pour `maintien`/`chrono` |
| commentaire | TEXT | |
| series_cibles, repetitions_cibles, duree_cible | | objectifs au moment de la séance |
| entrelace_avec | TEXT | nom du partenaire si exercice entrelacé (superset) |
| repos_entre_series, repos_apres | INTEGER | |

**`series_realisees`** — le détail série par série (une ligne par série)
| colonne | type | notes |
|---|---|---|
| id | INTEGER PK | |
| exercice_id | INTEGER | FK → `exercices.id` |
| numero | INTEGER | numéro de la série dans l'exercice |
| repetitions, poids, duree | | performance réelle de cette série |
| completee | INTEGER (bool) | 0/1 |

Pour joindre les trois : `seances.id = exercices.seance_id` et `exercices.id = series_realisees.exercice_id`.

## Exemples de requêtes utiles

**Dernières séances :**
```sql
SELECT id, date, nom_seance, statut, duree FROM seances ORDER BY date DESC LIMIT 10;
```

**Détail série par série d'un exercice donné, toutes séances confondues :**
```sql
SELECT s.date, s.nom_seance, sr.numero, sr.repetitions, sr.poids, sr.completee
FROM series_realisees sr
JOIN exercices e ON e.id = sr.exercice_id
JOIN seances s ON s.id = e.seance_id
WHERE e.nom = 'Pompes'
ORDER BY s.date DESC;
```

**Vérifier le schéma réel d'une table (utile si `historique/database.py` a fait des `ALTER TABLE` conditionnels) :**
```sql
PRAGMA table_info(exercices);
```

**Volume total par séance :**
```sql
SELECT s.date, s.nom_seance, SUM(sr.repetitions * sr.poids) AS volume
FROM series_realisees sr
JOIN exercices e ON e.id = sr.exercice_id
JOIN seances s ON s.id = e.seance_id
WHERE sr.completee = 1
GROUP BY s.id
ORDER BY s.date DESC;
```

Adapte librement ces requêtes à la question posée plutôt que de t'y limiter — c'est du SQL standard sur un schéma simple.
