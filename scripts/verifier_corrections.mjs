// Le coach dit-il une faute de forme au bon moment ?
//
// Les scenarios figes de `comparer_seances` rejouent des poses tirees au
// hasard : ils montrent qu'une faute finit par etre dite, pas *quand*. Une
// pose au hasard ne tombe jamais pile sur 0,6 s de faute ni sur 6 s de
// rappel, si bien qu'un `<` devenu `<=` passerait inapercu. Ces cas sont
// ecrits ici a la main, avec leur reponse attendue.
//
//     node scripts/verifier_corrections.mjs

import { Circuit } from "../web/static/js/circuit.js";
import {
  DUREE_AVANT_CORRECTION,
  RAPPEL_CORRECTION,
  annoncer_faute,
  gerer_mode_maintien,
  suivre_amplitude,
} from "../web/static/js/moteur.js";

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

/**
 * Rejoue une suite d'images `[instant, cle]` sur un bloc neuf et rend les
 * instants ou le coach a parle, avec ce qu'il a dit.
 */
function rejouer(images, bloc = {}) {
  const dites = [];
  for (const [instant, cle] of images) {
    annoncer_faute((son) => dites.push([instant, son]), bloc, cle, instant);
  }
  return dites;
}

// Des images toutes les 0,1 s, de `debut` a `fin` compris.
function images(debut, fin, cle) {
  const sortie = [];
  for (let i = Math.round(debut * 10); i <= Math.round(fin * 10); i += 1) sortie.push([i / 10, cle]);
  return sortie;
}

const GENOU = "forme_genou_avant_trop_avance";
const COUDE = "forme_coude_qui_part_en_avant";

egal("les reglages dont dependent les cas ci-dessous", [DUREE_AVANT_CORRECTION, RAPPEL_CORRECTION], [0.6, 6]);

// --- Une faute doit durer
egal("une faute de 0,5 s se tait", rejouer(images(0, 0.5, GENOU)), []);
egal("une faute dite a 0,6 s pile, une seule fois avant le rappel",
  rejouer(images(0, 1.5, GENOU)), [[0.6, GENOU]]);
egal("sans faute, rien", rejouer(images(0, 10, null)), []);

// --- Une faute qui persiste est redite tous les RAPPEL_CORRECTION
egal("rappel a 6,6 s puis 12,6 s, jamais entre",
  rejouer(images(0, 13, GENOU)), [[0.6, GENOU], [6.6, GENOU], [12.6, GENOU]]);

// --- Un episode qui s'interrompt repart de zero
egal("une image sans faute remet le chrono a zero",
  rejouer([...images(0, 0.5, GENOU), [0.55, null], ...images(0.6, 1.1, GENOU)]), []);
egal("puis la faute qui reprend se dit 0,6 s apres sa reprise",
  rejouer([...images(0, 0.5, GENOU), [0.55, null], ...images(0.6, 1.3, GENOU)]), [[1.2, GENOU]]);
egal("une autre faute ouvre un nouvel episode",
  rejouer([...images(0, 0.5, GENOU), ...images(0.6, 1.3, COUDE)]), [[1.2, COUDE]]);
// (Des instants qui se soustraient juste : 1,7 - 1,1 vaut 0,5999… en flottant.)
egal("un nouvel episode n'attend pas le rappel du precedent",
  rejouer([...images(0, 0.9, GENOU), [0.95, null], ...images(1, 2, GENOU)]), [[0.6, GENOU], [1.6, GENOU]]);

// --- L'amplitude se dit a la repetition comptee, une fois
{
  const exercice = { amplitude: [(corps) => corps.profond, "forme_pompe_pas_assez_profonde"] };
  const etat = { erreur: null };
  const texte = (cle) => cle;
  const bloc = {};
  const pas = (corps, avant, stage, comptee) =>
    suivre_amplitude(exercice, corps, bloc, etat, avant, stage, comptee, texte);
  pas({ profond: false }, "fin", "debut", false);
  egal("repetition peu profonde : dite quand elle compte",
    pas({ profond: false }, "debut", "fin", true), "forme_pompe_pas_assez_profonde");
  egal("puis tue a l'image suivante, l'ecran la garde",
    [pas({ profond: false }, "fin", "fin", false), etat.erreur], [null, "forme_pompe_pas_assez_profonde"]);
  pas({ profond: true }, "fin", "debut", false);
  egal("repetition profonde : rien a dire", pas({ profond: true }, "debut", "fin", true), null);
  egal("sans amplitude declaree, rien",
    suivre_amplitude({ amplitude: null }, {}, {}, etat, "debut", "fin", true, texte), null);
}

// --- Le repere ne survit pas a la serie
{
  const bloc = {};
  rejouer(images(0, 1, GENOU), bloc);
  Circuit.prototype.reinitialiser_etat_serie.call({}, bloc);
  egal("reinitialiser_etat_serie efface le repere de faute",
    ["faute_en_cours", "faute_depuis", "faute_dite_a"].filter((champ) => champ in bloc), []);
}

// --- Un gainage ne se corrige pas avant d'avoir ete tenu
//
// « Reprends la position » et toute faute de forme attendent le premier
// maintien de la serie. Le drapeau survivait a la serie, et la correction
// partait des la serie 2, pendant qu'on se remettait en planche.
{
  const horloge = { t: 0 };
  const bloc = {
    exercice: { erreurs: [(c) => c.faute], detection: (c) => c.jeton },
    temps_maintien: 0, duree: 30,
  };
  const seance = { maintenant: () => horloge.t };
  const dites = [];
  const pas = (jeton, faute = null) => {
    horloge.t += 0.25;
    gerer_mode_maintien({
      corps: { jeton, faute }, bloc, seance, etat: { erreur: null }, coach: (cle) => dites.push(cle),
      messages: { texte: (cle) => cle, libelle_etape: (j) => j },
    });
  };
  const paroles = () => dites.filter((cle) => cle !== "bip");
  for (let i = 0; i < 8; i++) pas("repos", GENOU);
  egal("on se met en place, faute visible : rien n'est dit", paroles(), []);
  for (let i = 0; i < 4; i++) pas("maintien", GENOU);
  egal("une fois tenu, la faute qui dure se dit", paroles(), [GENOU]);
  pas("repos");
  egal("et la position perdue se dit", paroles(), [GENOU, "correction_gainage"]);

  Circuit.prototype.reinitialiser_etat_serie.call({}, bloc);
  dites.length = 0;
  for (let i = 0; i < 8; i++) pas("repos", GENOU);
  egal("serie suivante : rien avant d'etre de nouveau en place", paroles(), []);
}

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : une faute se dit quand elle dure, et se redit sans couvrir le compte.`);
}
