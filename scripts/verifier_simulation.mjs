// Le simulateur de progression tourne-t-il, et le moteur y tient-il ses
// promesses pour tous les profils de materiel ?
//
// `dev/progression.html` est fait pour etre relu par une personne : il montre
// les baisses de volume, il ne les interdit pas (les corriger, c'est son
// role). Mais certaines choses ne sont pas affaire de reglage, et celles-la
// se verifient ici, sur les donnees deployees, pour chaque profil de
// materiel, a plusieurs notes, l'athlete reussissant toujours :
//
// - le simulateur rend un point par seance, toujours le meme ;
// - un niveau ne recule jamais ;
// - **aucune seance ne demande un haltere que le profil n'a pas**, des que
//   la famille offre un mouvement qu'il peut faire (un curl sans halteres
//   n'a pas d'autre forme : son bareme retombe sur la gamme supposee, faute
//   de mieux, et l'ecran dit ce qui manque) ;
// - une note plus haute ne fait jamais partir plus bas sur le meme mouvement ;
// - une montee de variante va au cran voisin, joue a la seance suivante ;
// - a la premiere montee vers une forme chargee, la seance suivante ne
//   demande pas moins de volume que la derniere a vide (la repetition a vide
//   pesant la part du corps) : on entre au palier equivalent, pas au palier 1.
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
const FAMILLES = sim.familles(catalogue_depuis(mouvements), neutres);
// Le parcours coute : les chaines de variantes, ou vivent les regles a
// verifier, et pas les exercices seuls.
const CHAINES = FAMILLES.filter((f) => f.mouvements.length > 1);
const PROFILS = sim.profils_materiel(tables);
const NOTES = [1, 6];
const SEANCES = 40;

const problemes = [];
let controles = 0;
let entrees_chargees = 0;
function verifier(nom, condition, detail = "") {
  controles += 1;
  if (!condition) problemes.push(detail ? `${nom}\n      ${detail}` : nom);
}

/**
 * Le palier demande-t-il un haltere que ce profil ne possede pas assez,
 * alors que sa famille offrait un mouvement faisable ?
 */
function haltere_manquant(profil, joue, palier, famille) {
  if (!palier || !(palier.poids > 0) || profil.materiel === null) return false;
  const baremes = new Baremes(tables, profil.materiel);
  if (!famille.mouvements.some((nom) => baremes.chargeable(nom))) return false;
  const besoin = Math.max(1, neutres.nombre_halteres(joue));
  return (profil.materiel.halteres[palier.poids] ?? 0) < besoin;
}

function verifier_parcours(profil, note, famille, points) {
  const ou = `${profil.libelle}, note ${note}, ${famille.tete}`;
  verifier(`${ou} : un point par seance`, points.length === SEANCES, `${points.length} points`);
  const niveaux = {};
  points.forEach((p, i) => {
    verifier(`${ou} : le mouvement joue appartient a la famille`, famille.mouvements.includes(p.joue), p.joue);
    if (p.niveau !== null) {
      const avant = niveaux[p.joue] ?? 0;
      verifier(`${ou} : un niveau ne recule jamais`, p.niveau >= avant, `seance ${p.n}, ${p.joue} : ${avant} puis ${p.niveau}`);
      niveaux[p.joue] = Math.max(avant, p.niveau);
    }
    verifier(`${ou} : aucun haltere absent n'est demande`, !haltere_manquant(profil, p.joue, p.palier, famille),
      `seance ${p.n} : ${p.joue} a ${p.palier?.poids} kg`);
    const suivant = points[i + 1];
    if (!p.evenement) return;
    const de = famille.mouvements.indexOf(p.evenement.depuis);
    const vers = famille.mouvements.indexOf(p.evenement.vers);
    verifier(`${ou} : une variante change d'un cran`, de >= 0 && vers === de + 1,
      `seance ${p.n} : ${p.evenement.depuis} → ${p.evenement.vers}`);
    if (!suivant) return;
    verifier(`${ou} : la variante choisie est jouee a la seance suivante`, suivant.joue === p.evenement.vers,
      `seance ${suivant.n} : ${suivant.joue} au lieu de ${p.evenement.vers}`);
    const part = neutres.equivalence_a_vide(p.evenement.depuis, p.evenement.vers);
    const premiere = !points.slice(0, i + 1).some((q) => q.joue === p.evenement.vers);
    if (part !== null && premiere && suivant.palier && p.palier) {
      entrees_chargees += 1;
      const avant = neutres.volume(p.palier.series, p.palier.cible, 0, part);
      const apres = neutres.volume_exercice(suivant.joue, suivant.palier.series, suivant.palier.cible, suivant.palier.poids);
      verifier(`${ou} : on entre dans la forme chargee au palier equivalent`, apres >= avant,
        `seance ${suivant.n} : ${suivant.palier.series}x${suivant.palier.cible} a ${suivant.palier.poids} kg (volume ${apres}) apres ${p.palier.series}x${p.palier.cible} a vide (${avant})`);
    }
  });
}

for (const profil of PROFILS) {
  // --- Le depart, note par note, pour tous les exercices
  const par_note = sim.departs({ tables, mouvements, materiel: profil.materiel, choisies: FAMILLES });
  FAMILLES.forEach((famille, k) => {
    for (let note = 1; note <= 10; note += 1) {
      const d = par_note[note - 1][k];
      verifier(`${profil.libelle}, ${famille.tete} : aucun haltere absent au depart`,
        !haltere_manquant(profil, d.joue, d.palier, famille), `note ${note} : ${d.joue} a ${d.palier?.poids} kg`);
      if (note === 1) continue;
      const avant = par_note[note - 2][k];
      if (avant.joue === d.joue && avant.palier && d.palier) {
        verifier(`${profil.libelle}, ${famille.tete} : une note plus haute ne part pas plus bas`,
          d.palier.niveau >= avant.palier.niveau,
          `note ${note - 1} : niveau ${avant.palier.niveau}, note ${note} : niveau ${d.palier.niveau}`);
      }
    }
  });

  // --- Le parcours, pour chaque chaine de variantes
  for (const note of NOTES) {
    for (const famille of CHAINES) {
      const reglage = { tables, mouvements, materiel: profil.materiel, famille, note, seances: SEANCES };
      const points = sim.parcours(reglage);
      verifier_parcours(profil, note, famille, points);
      if (note === NOTES[0] && famille === CHAINES[0]) {
        verifier(`${profil.libelle} : la simulation est deterministe`,
          JSON.stringify(points) === JSON.stringify(sim.parcours(reglage)));
      }
    }
  }
}

// Une regle qu'aucun parcours ne visite ne prouve rien.
verifier("au moins un parcours monte vers une forme chargee", entrees_chargees > 0, `${entrees_chargees} entrees`);

// Les baisses de volume, sur un cas ecrit a la main.
{
  const b = sim.baisses([{ volume: 10 }, { volume: 12 }, { volume: 9 }, { volume: 9 }, { volume: null }, { volume: 4 }]);
  verifier("baisses : seule une vraie baisse compte, un trou ne casse rien",
    JSON.stringify(b.map((x) => [x.index, Math.round(x.part * 100)])) === "[[2,-25]]", JSON.stringify(b));
}

// La saisie libre d'un inventaire.
{
  const { materiel, illisibles } = sim.inventaire_depuis_texte("4x2 8 2,5x1 dix", tables);
  verifier("inventaire : poids, quantite, virgule decimale",
    JSON.stringify(materiel.halteres) === JSON.stringify({ 4: 2, 8: 2, 2.5: 1 }), JSON.stringify(materiel.halteres));
  verifier("inventaire : morceau illisible signale", JSON.stringify(illisibles) === '["dix"]', JSON.stringify(illisibles));
  verifier("inventaire : saisie vide = rien", sim.inventaire_depuis_texte("  ", tables).materiel === null);
}

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes.slice(0, 30)) console.log(`  - ${p}`);
  if (problemes.length > 30) console.log(`  … et ${problemes.length - 30} autres`);
  process.exitCode = 1;
} else {
  console.log(
    `${controles} controles sur ${PROFILS.length} profils de materiel et ${FAMILLES.length} exercices : ` +
    `le simulateur tourne et le moteur tient ses promesses.`,
  );
}
