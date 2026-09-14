// Chaque `this.methode()` appelée existe-t-elle vraiment ?
//
// Ce script répond à un défaut réel et embarrassant : une méthode retirée de
// `camera.js` pendant que deux appels subsistaient dans la même classe, et
// l'application refusait de démarrer — « this.relacher_ecran is not a
// function », en pleine séance, sur l'iPad de quelqu'un.
//
// Trois choses l'ont laissé passer, et aucune n'est un hasard.
//
// 1. **`node --check` ne le voit pas.** La syntaxe est parfaite ; c'est une
//    résolution à l'exécution, et JavaScript ne la fait qu'au moment de
//    l'appel.
// 2. **Aucun harnais ne couvre `camera.js`**, et ne le peut : il importe
//    MediaPipe depuis un CDN, que Node refuse de charger. C'est le seul
//    module du dossier dans ce cas.
// 3. **La recherche qui devait le trouver l'a masqué.** Un `grep` filtré par
//    `grep -v "camera.js:2"`, destiné à écarter la ligne de *définition*,
//    écartait aussi les deux lignes d'*appel* — elles étaient aux lignes 226
//    et 238. Un filtre par numéro de ligne ne distingue pas ce qu'il cache.
//
// La vérification est volontairement **syntaxique et bornée** : on relève les
// méthodes déclarées dans chaque classe et les `this.xxx(` qui y figurent, et
// on signale les seconds sans les premiers. Elle ne comprend ni l'héritage ni
// les appels dynamiques — il n'y en a aucun ici, et le jour où il y en aura,
// c'est cette limite qu'il faudra lever plutôt que le script qu'il faudra
// jeter.
//
// Usage : node scripts/verifier_methodes.mjs

import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ICI = dirname(fileURLToPath(import.meta.url));
const MODULES = join(ICI, "..", "web", "static", "js");

//: Ce qui ressemble à `this.xxx(` sans être un appel de méthode de la classe.
//: `constructor` n'est jamais appelé ainsi ; les autres sont des objets natifs
//: portés par l'instance (`this.video.play()`, `this.flux.getTracks()`), que
//: la forme `this.a.b(` distingue déjà — on ne garde que `this.b(`.
const IGNOREES = new Set(["constructor", "super"]);

/** Les classes d'un fichier, avec leur corps. */
function classes(source) {
  const trouvees = [];
  const debut = /class\s+(\w+)[^{]*\{/g;
  let entete;
  while ((entete = debut.exec(source)) !== null) {
    // On suit les accolades pour delimiter le corps : une recherche non
    // equilibree s'arreterait a la premiere methode.
    let profondeur = 1;
    let i = debut.lastIndex;
    while (i < source.length && profondeur > 0) {
      if (source[i] === "{") profondeur += 1;
      else if (source[i] === "}") profondeur -= 1;
      i += 1;
    }
    trouvees.push({ nom: entete[1], corps: source.slice(debut.lastIndex, i - 1) });
  }
  return trouvees;
}

/** Les methodes declarees au premier niveau du corps d'une classe. */
function methodes(corps) {
  const noms = new Set();
  // `nom(args) {`, `async nom(`, `get nom(`, `set nom(`, en debut de ligne.
  // `*nom(` compris : une methode generatrice se declare ainsi, et
  // `_iterer_tranches` en est une — le motif sans l'etoile la declarait
  // manquante alors qu'elle est la regle centrale du bareme.
  const motif = /^\s{2}(?:async\s+|get\s+|set\s+|static\s+)*\*?\s*([A-Za-z_$][\w$]*)\s*\(/gm;
  let trouve;
  while ((trouve = motif.exec(corps)) !== null) noms.add(trouve[1]);
  // Les champs assignes dans le constructeur peuvent porter des fonctions.
  const champ = /this\.([A-Za-z_$][\w$]*)\s*=/g;
  while ((trouve = champ.exec(corps)) !== null) noms.add(trouve[1]);
  return noms;
}

/** Les `this.xxx(` appeles, hors `this.a.b(`. */
function appels(corps) {
  const trouves = new Map();
  const motif = /this\.([A-Za-z_$][\w$]*)\s*\(/g;
  let trouve;
  while ((trouve = motif.exec(corps)) !== null) {
    if (IGNOREES.has(trouve[1])) continue;
    const avant = corps.slice(0, trouve.index);
    trouves.set(trouve[1], (avant.match(/\n/g) ?? []).length + 1);
  }
  return trouves;
}

function main() {
  const fichiers = readdirSync(MODULES).filter((f) => f.endsWith(".js"));
  const problemes = [];
  let verifiees = 0;

  for (const fichier of fichiers) {
    const source = readFileSync(join(MODULES, fichier), "utf-8");
    for (const { nom, corps } of classes(source)) {
      const declarees = methodes(corps);
      for (const [appelee, ligne] of appels(corps)) {
        verifiees += 1;
        if (!declarees.has(appelee)) {
          problemes.push(
            `${fichier} · classe ${nom} · ligne ~${ligne} : ` +
              `this.${appelee}() est appelee mais n'existe pas`
          );
        }
      }
    }
  }

  if (problemes.length) {
    console.log(`${problemes.length} appels sans definition :\n`);
    for (const probleme of problemes) console.log(`  - ${probleme}`);
    process.exitCode = 1;
    return;
  }

  console.log(`${verifiees} appels de methode verifies dans ${fichiers.length} modules`);
  console.log("\nAucun appel orphelin.");
}

main();
