// Les gestes de controle ne se font-ils que de face, et leur anneau
// attend-il qu'on les tienne ?
//
// Les familles construites des poses figees (bras leves, buste oriente…) ont
// ete faites par l'ancien desktop, dont la capture etait en miroir : l'epaule
// gauche y est a gauche de l'image et la visibilite du nez tiree au hasard.
// Avec `de_face`, elles rendent donc toutes « faux », et le jeu fige ne dit
// plus rien du geste fait de face ni de dos. Ces cas sont ecrits ici a la main.
//
//     node scripts/verifier_gestes.mjs

import { DELAI_AFFICHAGE_GESTE, HoldPosition } from "../web/static/js/outils.js";
import {
  bras_en_x, de_face, deux_bras_leves, seul_bras_droit_leve, seul_bras_gauche_leve,
} from "../web/static/js/positions.js";

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

/**
 * Un corps debout face a la camera, video brute : son cote gauche est a
 * droite de l'image. `de_dos` echange les cotes, `nez` regle la visibilite du
 * nez, `allonge` couche le buste. `poignets` place les deux poignets.
 */
function corps({ poignets = "croises", de_dos = false, nez = 0.95, allonge = false } = {}) {
  const sens = de_dos ? -1 : 1;
  const p = (x, y) => (allonge ? { x: y, y: x } : { x: 0.5 + sens * x, y });
  const bras = {
    croises: { poignet_gauche: p(-0.05, 0.45), poignet_droit: p(0.05, 0.45) },
    // Chaque main de son cote, rapprochees devant le ventre : pas croisees.
    joints: { poignet_gauche: p(0.05, 0.45), poignet_droit: p(-0.05, 0.45) },
    leves: { poignet_gauche: p(0.1, 0.05), poignet_droit: p(-0.1, 0.05) },
    droit_leve: { poignet_gauche: p(0.1, 0.55), poignet_droit: p(-0.1, 0.05) },
    gauche_leve: { poignet_gauche: p(0.1, 0.05), poignet_droit: p(-0.1, 0.55) },
  }[poignets];
  const coudes = poignets === "croises" || poignets === "joints"
    ? { coude_gauche: p(0.12, 0.42), coude_droit: p(-0.12, 0.42) }
    : {
      coude_gauche: p(0.1, bras.poignet_gauche.y < 0.3 ? 0.17 : 0.42),
      coude_droit: p(-0.1, bras.poignet_droit.y < 0.3 ? 0.17 : 0.42),
    };
  return {
    nez: { ...p(0, 0.2), visibility: nez },
    epaule_gauche: p(0.1, 0.3), epaule_droite: p(-0.1, 0.3),
    hanche_gauche: p(0.08, 0.6), hanche_droite: p(-0.08, 0.6),
    ...coudes, ...bras,
  };
}

// --- De face, chaque geste se fait
egal("de face, debout, nez visible", de_face(corps()), true);
egal("bras croises de face", bras_en_x(corps()), true);
egal("deux bras leves de face", deux_bras_leves(corps({ poignets: "leves" })), true);
egal("bras droit seul leve de face", seul_bras_droit_leve(corps({ poignets: "droit_leve" })), true);
egal("bras gauche seul leve de face", seul_bras_gauche_leve(corps({ poignets: "gauche_leve" })), true);

// --- De dos, aucun : deux mains ramenees entre les epaules passaient la pause
egal("de dos : pas de face", de_face(corps({ de_dos: true })), false);
egal("de face, mains rapprochees sans se croiser : pas des bras croises",
  bras_en_x(corps({ poignets: "joints" })), false);
// Le cas qui a fait sauter une pause : de dos, l'image inverse la gauche et la
// droite, et deux mains simplement rapprochees se lisent comme croisees.
egal("de dos, mains rapprochees entre les epaules : pas des bras croises",
  bras_en_x(corps({ poignets: "joints", de_dos: true })), false);
egal("de dos, bras vraiment croises : rien non plus", bras_en_x(corps({ de_dos: true })), false);
egal("de dos, deux bras leves : rien", deux_bras_leves(corps({ poignets: "leves", de_dos: true })), false);
egal("de dos, un bras leve : rien",
  [seul_bras_droit_leve(corps({ poignets: "droit_leve", de_dos: true })),
    seul_bras_gauche_leve(corps({ poignets: "gauche_leve", de_dos: true }))], [false, false]);

// --- Un nez que le modele devine, et un corps allonge
egal("nez a peine vu (le modele devine un visage de dos)", bras_en_x(corps({ nez: 0.3 })), false);
egal("nez vu a 0,5 pile : de face", de_face(corps({ nez: 0.5 })), true);
egal("allonge : pas de geste", bras_en_x(corps({ allonge: true })), false);

// --- L'anneau attend trois quarts de seconde, la duree du geste ne change pas
egal("le reglage dont dependent les cas ci-dessous", DELAI_AFFICHAGE_GESTE, 0.75);
{
  const horloge = { t: 10 };
  const geste = new HoldPosition(() => true, 3, () => horloge.t);
  const a = (t) => { horloge.t = 10 + t; return geste.update({}); };
  egal("a la premiere image, rien", a(0), [0, false]);
  egal("a 0,7 s, toujours rien", a(0.7), [0, false]);
  egal("lu sans update, rien non plus", geste.progression_visible(), 0);
  egal("a 0,75 s, l'anneau part de zero", a(0.75), [0, false]);
  egal("a mi-chemin du reste, la moitie", a(1.875), [50, false]);
  egal("a 3 s pile, le geste est pris", a(3), [100, true]);
  egal("et l'anneau reste plein", geste.progression_visible(), 100);
}
{
  const horloge = { t: 0 };
  let tenu = true;
  const geste = new HoldPosition(() => tenu, 1.5, () => horloge.t);
  geste.update({});
  horloge.t = 1.125;
  egal("un geste d'une seconde et demie : la moitie a 1,125 s", geste.update({}), [50, false]);
  tenu = false;
  horloge.t = 1.2;
  egal("lache, tout repart de zero", [geste.update({}), geste.progression_visible()], [[0, false], 0]);
}

if (problemes.length) {
  console.log(`${problemes.length} probleme(s) sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exit(1);
}
console.log(`${controles} controles : un geste se fait de face, et son anneau attend qu'on le tienne.`);
