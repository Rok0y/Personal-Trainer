// Le simulateur de progression tourne-t-il, et le moteur y tient-il ses
// promesses pour tous les profils de materiel ?
//
// `dev/progression.html` est fait pour etre relu par une personne : il ne
// juge pas si un saut est trop brusque. Mais certaines choses ne sont pas
// affaire de reglage, et celles-la se verifient ici, sur les donnees
// deployees, pour chaque profil de materiel et chaque athlete type :
//
// - la simulation tourne, et rend un point par seance et par famille ;
// - elle est deterministe (deux passages, le meme resultat) ;
// - un niveau ne recule jamais ;
// - **aucune seance ne demande un haltere que le profil n'a pas** ;
// - une note plus haute ne fait jamais partir plus bas sur le meme mouvement ;
// - une montee ou une descente de variante va au cran voisin de la chaine ;
// - apres une montee vers une forme chargee, la seance suivante ne demande
//   pas moins de volume que la derniere a vide (la repetition a vide pesant
//   la part du corps) : on entre au palier equivalent, pas au palier 1.
//
//     node scripts/verifier_simulation.mjs

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { Baremes, composer_baremes } from "../web/static/js/paliers.js";
import { catalogue_depuis } from "../web/static/js/variantes.js";
import * as sim from "../web/static/js/simulation.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const lire = (nom) => JSON.parse(readFileSync(join(ICI, "..", "web", "static", "donnees", nom), "utf-8"));

const tables = composer_baremes(lire("baremes.json"), lire("reglages.json"));
const mouvements = lire("mouvements.json");
const neutres = new Baremes(tables, null);
// Les familles de la page : les chaines de variantes, et les fentes.
const choisies = sim.familles(catalogue_depuis(mouvements), neutres)
  .filter((f) => f.mouvements.length > 1 || f.tete.startsWith("Fente"));
const PROFILS = sim.profils_materiel(tables);
const SEANCES = 20;

const problemes = [];
let controles = 0;
let entrees_chargees = 0;
function verifier(nom, condition, detail = "") {
  controles += 1;
  if (!condition) problemes.push(detail ? `${nom}\n      ${detail}` : nom);
}

/** Le palier demande-t-il un haltere que ce profil ne possede pas assez ? */
function haltere_manquant(profil, joue, palier) {
  if (!palier || !(palier.poids > 0) || profil.materiel === null) return false;
  const besoin = Math.max(1, neutres.nombre_halteres(joue));
  return (profil.materiel.halteres[palier.poids] ?? 0) < besoin;
}

function verifier_parcours(profil, etiquette, traces) {
  for (const trace of traces) {
    const ou = `${etiquette}, ${profil.libelle}, ${trace.tete}`;
    verifier(`${ou} : un point par seance`, trace.points.length === SEANCES, `${trace.points.length} points`);
    const records = {};
    trace.points.forEach((p, i) => {
      verifier(`${ou} : le mouvement joue appartient a la famille`, trace.mouvements.includes(p.joue), p.joue);
      if (p.record !== null) {
        const avant = records[p.joue] ?? 0;
        verifier(`${ou} : un niveau ne recule jamais`, p.record >= avant,
          `seance ${p.n}, ${p.joue} : ${avant} puis ${p.record}`);
        records[p.joue] = Math.max(avant, p.record);
      }
      verifier(`${ou} : aucun haltere absent n'est demande`, !haltere_manquant(profil, p.joue, p.palier),
        `seance ${p.n} : ${p.joue} a ${p.palier?.poids} kg`);
      if (p.evenement) {
        const de = trace.mouvements.indexOf(p.evenement.depuis);
        const vers = trace.mouvements.indexOf(p.evenement.vers);
        verifier(`${ou} : une variante change d'un cran`, de >= 0 && vers >= 0 && Math.abs(de - vers) === 1,
          `seance ${p.n} : ${p.evenement.depuis} → ${p.evenement.vers}`);
      }
      // Le mouvement joue a la seance suivante est celui qu'annonce l'evenement.
      const suivant = trace.points[i + 1];
      const part = p.evenement?.sens === "montée" ? neutres.equivalence_a_vide(p.evenement.depuis, p.evenement.vers) : null;
      if (part !== null && suivant?.palier && p.palier) {
        entrees_chargees += 1;
        const avant = neutres.volume(p.palier.series, p.palier.cible, 0, part);
        const apres = neutres.volume_exercice(suivant.joue, suivant.palier.series, suivant.palier.cible, suivant.palier.poids);
        verifier(`${ou} : on entre dans la forme chargee au palier equivalent`, apres >= avant,
          `seance ${suivant.n} : ${suivant.palier.series}x${suivant.palier.cible} a ${suivant.palier.poids} kg (volume ${apres}) apres ${p.palier.series}x${p.palier.cible} a vide (${avant})`);
      }
      if (p.evenement && suivant) {
        verifier(`${ou} : la variante choisie est jouee a la seance suivante`, suivant.joue === p.evenement.vers,
          `seance ${suivant.n} : ${suivant.joue} au lieu de ${p.evenement.vers}`);
      }
    });
  }
}

const capacite = sim.COMPORTEMENT_CAPACITE;
for (const profil of PROFILS) {
  // --- Le depart, note par note
  const par_note = sim.departs({ tables, mouvements, materiel: profil.materiel, choisies, athlete: sim.ATHLETES[0] });
  choisies.forEach((famille, k) => {
    for (let note = 2; note <= 10; note += 1) {
      const [avant, apres] = [par_note[note - 2][k], par_note[note - 1][k]];
      if (avant.joue === apres.joue && avant.palier && apres.palier) {
        verifier(`${profil.libelle}, ${famille.tete} : une note plus haute ne part pas plus bas`,
          apres.palier.niveau >= avant.palier.niveau,
          `note ${note - 1} : niveau ${avant.palier.niveau}, note ${note} : niveau ${apres.palier.niveau}`);
      }
      verifier(`${profil.libelle}, ${famille.tete} : aucun haltere absent au depart`,
        !haltere_manquant(profil, apres.joue, apres.palier), `note ${note} : ${apres.palier?.poids} kg`);
    }
  });

  // --- Chaque athlete type, sur sa force
  for (const athlete of sim.ATHLETES) {
    const reglage = { tables, mouvements, materiel: profil.materiel, choisies, athlete, comportement: capacite, seances: SEANCES };
    const traces = sim.simuler(reglage);
    verifier_parcours(profil, athlete.libelle, traces);
    if (athlete === sim.ATHLETES[0]) {
      verifier(`${profil.libelle} : la simulation est deterministe`,
        JSON.stringify(traces) === JSON.stringify(sim.simuler(reglage)));
    }
  }
  // --- Chaque scenario ecrit
  for (const scenario of sim.SCENARIOS) {
    const traces = sim.simuler({
      tables, mouvements, materiel: profil.materiel, choisies,
      athlete: sim.ATHLETES[0], comportement: scenario.cle, seances: SEANCES,
    });
    verifier_parcours(profil, scenario.libelle, traces);
  }
}

// Le bilan d'un parcours, sur un cas ecrit a la main.
{
  const b = sim.bilan([
    { n: 1, exige: 100, reussi: true, evenement: null },
    { n: 2, exige: 130, reussi: false, evenement: { sens: "descente" } },
    { n: 3, exige: 104, reussi: true, evenement: { sens: "montée" } },
    { n: 4, exige: 110, reussi: true, evenement: null },
  ]);
  verifier("bilan : plus gros saut", b.saut?.n === 2 && Math.abs(b.saut.part - 0.3) < 1e-9, JSON.stringify(b.saut));
  verifier("bilan : plus gros recul", b.recul?.n === 3 && Math.abs(b.recul.part + 0.2) < 1e-9, JSON.stringify(b.recul));
  verifier("bilan : echecs, montees, descentes", b.echecs === 1 && b.montees === 1 && b.descentes === 1);
}

// La saisie libre d'un inventaire.
{
  const { materiel, illisibles } = sim.inventaire_depuis_texte("4x2 8 2,5x1 dix", tables);
  verifier("inventaire : poids, quantite, virgule decimale",
    JSON.stringify(materiel.halteres) === JSON.stringify({ 4: 2, 8: 2, 2.5: 1 }), JSON.stringify(materiel.halteres));
  verifier("inventaire : morceau illisible signale", JSON.stringify(illisibles) === '["dix"]', JSON.stringify(illisibles));
  verifier("inventaire : saisie vide = rien", sim.inventaire_depuis_texte("  ", tables).materiel === null);
}

// Une regle qu'aucun parcours ne visite ne prouve rien.
verifier("au moins un parcours monte vers une forme chargee", entrees_chargees > 0, `${entrees_chargees} entrees`);

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes.slice(0, 30)) console.log(`  - ${p}`);
  if (problemes.length > 30) console.log(`  … et ${problemes.length - 30} autres`);
  process.exitCode = 1;
} else {
  console.log(
    `${controles} controles sur ${PROFILS.length} profils de materiel, ${sim.ATHLETES.length} athletes ` +
    `et ${sim.SCENARIOS.length} scenarios : le simulateur tourne et le moteur tient ses promesses.`,
  );
}
