// Lecture et ecriture des reponses figees des tests de non-regression.
//
// Les fixtures de `tests/fixtures/` ont ete produites une derniere fois par
// l'ancienne implementation Python (tag `derniere-version-desktop`), puis
// figees. Elles ne disent donc plus « ce que fait l'autre langage » mais « ce
// que faisait le code la derniere fois qu'on l'a voulu ainsi » : un rouge
// signale un changement de comportement, voulu ou non.
//
// Quand le changement est voulu, `--mettre-a-jour` reecrit les reponses avec
// ce que rend le code actuel. **Jamais pour faire taire un rouge qu'on ne
// comprend pas** : c'est exactement la regression que ces tests existent pour
// attraper. Lire d'abord les ecarts, puis mettre a jour.
//
// Les entrees sont figees elles aussi (`tests/fixtures/donnees/`) : un test qui
// lirait les `web/static/donnees/*.json` vivants virerait au rouge au premier
// reglage de bareme, sans qu'une ligne de code ait bouge.

import { readFileSync, writeFileSync } from "node:fs";
import { gunzipSync, gzipSync } from "node:zlib";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ICI = dirname(fileURLToPath(import.meta.url));
export const DOSSIER_FIXTURES = join(ICI, "..", "tests", "fixtures");

export const METTRE_A_JOUR = process.argv.includes("--mettre-a-jour");

/** Les lignes de `tests/fixtures/<nom>.jsonl.gz`, deja analysees. */
export function lire_lignes(nom) {
  const brut = gunzipSync(readFileSync(join(DOSSIER_FIXTURES, `${nom}.jsonl.gz`)));
  return brut
    .toString("utf-8")
    .split("\n")
    .filter((ligne) => ligne.trim())
    .map((ligne) => JSON.parse(ligne));
}

export function ecrire_lignes(nom, lignes) {
  const texte = lignes.map((ligne) => JSON.stringify(ligne)).join("\n") + "\n";
  // Niveau maximal : ces fichiers sont versionnes, et chaque mise a jour
  // ajoute sa copie a l'historique Git.
  writeFileSync(join(DOSSIER_FIXTURES, `${nom}.jsonl.gz`), gzipSync(texte, { level: 9 }));
}

/** Un JSON fige, par chemin relatif a `tests/fixtures/` (ex. `donnees/baremes.json`). */
export function lire_json(chemin) {
  return JSON.parse(readFileSync(join(DOSSIER_FIXTURES, chemin), "utf-8"));
}

/**
 * Compare des reponses figees a ce que rend le code, et les remplace en mode
 * mise a jour.
 *
 * La reponse figee est designee par son **emplacement** (`cible[cle]`) et non
 * par sa valeur : c'est ce qui permet de la reecrire sur place, puis de
 * reecrire le fichier entier sans savoir quelle forme ont ses lignes.
 */
export class Releve {
  constructor() {
    this.comparaisons = 0;
    this.echecs = [];
    this.remplacees = 0;
  }

  verifier(ou, cible, cle, obtenu) {
    this.comparaisons += 1;
    const attendu = JSON.stringify(cible[cle]);
    const rendu = JSON.stringify(obtenu);
    if (attendu === rendu) return true;
    if (METTRE_A_JOUR) {
      cible[cle] = rendu === undefined ? null : JSON.parse(rendu);
      this.remplacees += 1;
      return true;
    }
    this.echecs.push({ ou, attendu: String(attendu), rendu: String(rendu) });
    return false;
  }

  /**
   * Imprime le verdict et pose le code de sortie. En mise a jour, reecrit
   * `fichier` (nom sans extension) avec `lignes` s'il y a eu des remplacements.
   */
  conclure({ fichier, lignes, succes, detail = 4 }) {
    if (METTRE_A_JOUR) {
      if (this.remplacees) {
        ecrire_lignes(fichier, lignes);
        console.log(`\n${this.remplacees} reponses remplacees dans ${fichier}.jsonl.gz`);
      } else {
        console.log("\nRien a mettre a jour.");
      }
      // Ce qui reste dans `echecs` en mise a jour n'est pas une reponse figee
      // mais un invariant (ajoute a la main par l'appelant) : aucune mise a
      // jour ne le fait taire.
      if (!this.echecs.length) return;
    }
    if (!this.echecs.length) {
      console.log(`\n${succes}`);
      return;
    }
    console.log(`\n${this.echecs.length} reponses ont change. Les ${detail} premieres :\n`);
    for (const { ou, attendu, rendu } of this.echecs.slice(0, detail)) {
      // Sur un gros objet, l'ecart tombe souvent bien apres le debut : on
      // montre les deux textes a partir de la ou ils se separent.
      let i = 0;
      while (i < attendu.length && attendu[i] === rendu[i]) i++;
      const debut = Math.max(0, i - 60);
      const extrait = (t) => (debut ? "…" : "") + t.slice(debut, debut + 280);
      console.log(`  ${ou}`);
      console.log(`    fige = ${extrait(attendu)}`);
      console.log(`    code = ${extrait(rendu)}`);
      console.log();
    }
    if (!METTRE_A_JOUR) {
      console.log("Changement voulu ? Relance avec --mettre-a-jour, apres avoir lu les ecarts.");
    }
    process.exitCode = 1;
  }
}
