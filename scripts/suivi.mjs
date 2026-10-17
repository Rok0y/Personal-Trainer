// Les fiches de suivi des ajouts d'exercice, publiees pour `dev/suivi.html`.
//
// Les fiches vivent dans `docs/exercices/` (le protocole `ajouter-exercice` les
// coche et les commite avec le travail), hors de `web/static` : le site ne les
// publie pas, et une page statique ne sait pas lister un dossier. Ce script
// les rassemble au deploiement dans `dev/suivi.json` — **derive**, jamais
// versionne, comme le sommaire. La page montre donc l'etat de la derniere
// branche poussee.
//
// Deux usages :
//
//     node scripts/suivi.mjs                  verifie (joue par tester.mjs)
//     node scripts/suivi.mjs <site> [commit]  ecrit <site>/dev/suivi.json
//
// La verification fait lire a `suivi.js` des fiches ecrites ici (ce qu'il doit
// en tirer), puis chaque fiche de `docs/exercices/` et le modele du protocole :
// une fiche sans titre ou sans case ne dirait rien sur la page.

import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { blocs, en_ligne, lire_suivi, rendre_blocs } from "../web/static/js/suivi.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE = join(ICI, "..");
const DOSSIER = join(RACINE, "docs", "exercices");
const MODELE = join(RACINE, ".claude", "skills", "ajouter-exercice", "modele_suivi.md");

function fiches() {
  if (!existsSync(DOSSIER)) return [];
  return readdirSync(DOSSIER)
    .filter((f) => f.endsWith(".md"))
    .sort()
    .map((fichier) => ({ fichier, texte: readFileSync(join(DOSSIER, fichier), "utf-8") }));
}

function verifier() {
  const problemes = [];
  const attendre = (condition, message) => {
    if (!condition) problemes.push(message);
  };

  // --- la lecture, sur une fiche ecrite ici ---
  const exemple = [
    "# Fente droite / Fente gauche",
    "",
    "Un paragraphe",
    "sur deux lignes.",
    "",
    "| Question | Réponse |",
    "|---|---|",
    "| Côté | `a | b` |",
    "",
    "## Parcours B",
    "",
    "### Jalon 1",
    "",
    "- [x] Détection",
    "- [ ] Instrument",
    "",
    "### Détection",
    "",
    "Rien à cocher ici.",
    "",
    "## Médias",
    "",
    "- [X] Vidéo",
    "- [ ] Voix",
    "- une puce",
  ].join("\r\n");
  const lu = lire_suivi(exemple);
  attendre(lu.titre === "Fente droite / Fente gauche", `titre lu « ${lu.titre} »`);
  attendre(JSON.stringify(lu.mouvements) === JSON.stringify(["Fente droite", "Fente gauche"]),
    `mouvements lus ${JSON.stringify(lu.mouvements)} : le titre d'un unilateral en nomme deux`);
  attendre(lu.faites === 2 && lu.total === 4, `${lu.faites}/${lu.total} cases, 2/4 attendues (« [X] » compte)`);
  attendre(JSON.stringify(lu.sections.map((s) => [s.titre, s.faites, s.total]))
    === JSON.stringify([["Jalon 1", 1, 2], ["Médias", 1, 2]]),
    `sections ${JSON.stringify(lu.sections.map((s) => s.titre))} : un titre sans case n'en fait pas une`);
  attendre(lu.prochaine?.texte === "Instrument" && lu.prochaine?.section === "Jalon 1",
    `prochaine case ${JSON.stringify(lu.prochaine)} : la premiere non cochee, dans l'ordre de la fiche`);
  const tableau = blocs(exemple).find((b) => b.type === "tableau");
  attendre(tableau?.lignes.length === 1 && tableau.lignes[0][1] === "`a | b`",
    "une barre dans du code ne coupe pas une cellule, et la ligne de tirets n'est pas une ligne");
  attendre(blocs(exemple).some((b) => b.type === "paragraphe" && b.texte === "Un paragraphe sur deux lignes."),
    "les lignes d'un paragraphe se joignent");
  attendre(lire_suivi("- [ ] seule").prochaine?.section === null, "une case sans titre a une section nulle");
  attendre(lire_suivi("# Fini\n\n- [x] tout").prochaine === null, "une fiche toute cochee n'a pas de prochaine case");
  attendre(en_ligne("<b> **gras** `<i>`") === "&lt;b&gt; <strong>gras</strong> <code>&lt;i&gt;</code>",
    `en ligne : ${en_ligne("<b> **gras** `<i>`")}`);
  attendre(en_ligne("`**pas gras**`") === "<code>**pas gras**</code>", "le code ne se met pas en forme");
  attendre(!rendre_blocs(blocs(exemple)).includes("<h1"), "le titre de niveau 1 n'est pas redit dans le corps");

  // --- les fiches reelles et le modele ---
  const a_lire = [...fiches(), ...(existsSync(MODELE) ? [{ fichier: "modele_suivi.md (skill)", texte: readFileSync(MODELE, "utf-8") }] : [])];
  for (const { fichier, texte } of a_lire) {
    const fiche = lire_suivi(texte);
    attendre(fiche.titre, `${fichier} : pas de titre « # Nom du mouvement »`);
    attendre(fiche.total > 0, `${fichier} : aucune case a cocher, la page n'aurait rien a suivre`);
  }

  if (problemes.length) {
    console.log(`${problemes.length} problemes :\n`);
    for (const p of problemes) console.log(`  - ${p}`);
    process.exitCode = 1;
    return;
  }
  console.log(`${fiches().length} fiches de suivi (et le modele) se lisent.`);
}

function ecrire(site, commit) {
  const dossier = join(site, "dev");
  mkdirSync(dossier, { recursive: true });
  const contenu = { commit: commit ?? null, genere: new Date().toISOString(), fiches: fiches() };
  writeFileSync(join(dossier, "suivi.json"), JSON.stringify(contenu, null, 1) + "\n");
  console.log(`${join(dossier, "suivi.json")} ecrit — ${contenu.fiches.length} fiches de suivi.`);
}

const [site, commit] = process.argv.slice(2);
if (site) ecrire(site, commit);
else verifier();
