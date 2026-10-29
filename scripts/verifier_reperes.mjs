// Une detection qui se lit par rapport a soi debout (`REPERES`) lit-elle bien
// le repere de la mise en place, et le moteur le lui donne-t-il ?
//
// Les poses figees de `comparer_detections` ne portent pas de repere : elles
// ne voient que le repere moyen (`REPERE_MOYEN`). Une morphologie qui s'en
// ecarte, et le repere fige a l'ouverture d'une serie, se verifient donc ici,
// sur des corps ecrits a la main.
//
//     node scripts/verifier_reperes.mjs

import { readFileSync } from "node:fs";
import { Circuit, BlocExercice, Exercice, MODE_REPETITIONS } from "../web/static/js/circuit.js";
import { exercice_pour } from "../web/static/js/seance.js";
import { CompteurMouvement } from "../web/static/js/compteur.js";
import { creer_etat } from "../web/static/js/etat.js";
import { executer_mode } from "../web/static/js/moteur.js";
import { texte, libelle_etape } from "../web/static/js/messages.js";
import {
  REPERES, repere_debout, ski_detection, power_jacks_detection,
} from "../web/static/js/detections.js";

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

/**
 * Un corps de face, epaules larges de 0,1. `descente` : la descente des
 * hanches (cuisse au-dessus du tibia, en tibias ; vers 1,3 debout). `x` : le
 * milieu du corps dans l'image. `pieds` : l'ecart des chevilles, en largeurs
 * d'epaules. `bras_hauts` : poignets au-dessus de la tete.
 */
function corps({ descente, x = 0.5, pieds = 0.2, bras_hauts = false }) {
  const genou_y = 0.75;
  const tibia = 0.2;
  const hanche_y = genou_y - descente * tibia;
  const epaule_y = hanche_y - 0.25;
  const poignet_y = bras_hauts ? epaule_y - 0.2 : hanche_y;
  const cote = (dx, y) => ({ x: x + dx, y, visibility: 1 });
  const demi = (pieds * 0.1) / 2;
  return {
    nez: cote(0, epaule_y - 0.08),
    epaule_gauche: cote(0.05, epaule_y), epaule_droite: cote(-0.05, epaule_y),
    coude_gauche: cote(0.06, epaule_y + 0.1), coude_droit: cote(-0.06, epaule_y + 0.1),
    poignet_gauche: cote(0.04, poignet_y), poignet_droit: cote(-0.04, poignet_y),
    hanche_gauche: cote(0.03, hanche_y), hanche_droite: cote(-0.03, hanche_y),
    genou_gauche: cote(Math.max(demi, 0.03), genou_y), genou_droit: cote(-Math.max(demi, 0.03), genou_y),
    cheville_gauche: cote(demi, genou_y + tibia), cheville_droite: cote(-demi, genou_y + tibia),
  };
}

// --- Les deux detections declarent leur repere, et l'Exercice le recoit
egal("le ski et les power jacks prennent un repere debout",
  [REPERES.ski_detection, REPERES.power_jacks_detection], [repere_debout, repere_debout]);
{
  // Un champ oublie dans `exercice_pour` vaut undefined sans erreur : la
  // detection retomberait sur le repere moyen, et rien d'autre ne le verrait.
  const mouvements = JSON.parse(readFileSync(new URL("../web/static/donnees/mouvements.json", import.meta.url)));
  egal("exercice_pour remet le repere au Ski", exercice_pour(mouvements, "Ski").repere === repere_debout, true);
  egal("et aucun a un mouvement qui n'en lit pas", exercice_pour(mouvements, "Squat").repere, null);
}

// --- Ski : quelqu'un qui se tient a 1,15 debout, sous le repere moyen (1,33)
{
  const debout = corps({ descente: 1.15, x: 0.45 });
  const repere = repere_debout(debout);
  egal("au repere moyen, debout a 1,15 et decale se lit comme une reception",
    ski_detection(debout), "fin");
  egal("a son propre repere, debout a 1,15 rearme", ski_detection(debout, repere), "debut");
  // Une reception flechie a 1,0 (0,87 de soi debout), d'une demi-epaule a
  // droite de sa place — au centre exact de l'image.
  const reception = corps({ descente: 1.0, x: 0.5 });
  egal("au repere moyen (centre de l'image), cette reception ne compte pas",
    ski_detection(reception), "milieu");
  egal("a sa place de depart, elle compte", ski_detection(reception, repere), "fin");
  egal("la meme reception sur place (squat saute) ne compte pas",
    ski_detection(corps({ descente: 1.0, x: 0.45 }), repere), "milieu");
  egal("une reception a peine flechie (0,92 de soi) ne compte pas",
    ski_detection(corps({ descente: 1.06, x: 0.5 }), repere), "milieu");
  egal("ni ne rearme : entre les deux seuils", ski_detection(corps({ descente: 1.06, x: 0.45 }), repere), "milieu");
}

// --- Power jacks : quelqu'un qui se tient a 1,45 debout, au-dessus du repere moyen
{
  const debout = corps({ descente: 1.45, bras_hauts: true });
  const repere = repere_debout(debout);
  egal("debout bras en haut, c'est la fin", power_jacks_detection(debout, repere), "fin");
  const squat = corps({ descente: 1.05, pieds: 1.6 });
  egal("au repere moyen, son squat a 1,05 (0,79 du moyen) ne rearme pas",
    power_jacks_detection(squat), "milieu");
  egal("a son repere (0,72 de soi debout), il rearme", power_jacks_detection(squat, repere), "debut");
  egal("le meme squat pieds joints ne rearme pas",
    power_jacks_detection(corps({ descente: 1.05, pieds: 0.2 }), repere), "milieu");
}

// --- Le moteur : la pose du moment pendant l'attente, figee a l'ouverture
{
  // Une detection qui note le repere recu et rend le jeton porte par le corps :
  // seule la plomberie est en cause ici.
  const recus = [];
  const instrument_recus = [];
  const exercice = new Exercice({
    nom: "Essai",
    detection: (c, r) => { recus.push(r?.niveau ?? null); return c.jeton; },
    repere: (c) => ({ niveau: c.niveau }),
    instrument: {
      ordre: ["fin", "debut"], defaut: "milieu",
      mesures: [{
        libelle: "essai", unite: "", echelle: [0, 1], sommet: "nez",
        zones: { fin: [">", 0.5], debut: ["<", 0.5] },
        valeur: (c, r) => { instrument_recus.push(r?.niveau ?? null); return c.jeton === "fin" ? 1 : 0; },
      }],
    },
  });
  const horloge = { t: 100 };
  const circuit = new Circuit([new BlocExercice({
    exercice, poids: 0, mode: MODE_REPETITIONS, nombre_series: 2, repetitions_par_serie: 1,
    duree: 30, repos_entre_series: 10, repos_apres: 0,
  })]);
  circuit.maintenant = () => horloge.t;
  circuit.debut = horloge.t;
  circuit.commencer_exercice();
  const compteur = new CompteurMouvement();
  const etat = creer_etat();
  const image = (jeton, niveau) => {
    horloge.t += 0.25;
    const buste = { x: 0.5, y: 0.3 };
    executer_mode({
      seance: circuit, compteur, etat, coach: () => {}, derniere_rep: 0,
      messages: { texte, libelle_etape },
      corps: {
        jeton, niveau, nez: buste,
        epaule_gauche: { x: 0.6, y: 0.3 }, epaule_droite: { x: 0.4, y: 0.3 },
        hanche_gauche: { x: 0.58, y: 0.6 }, hanche_droite: { x: 0.42, y: 0.6 },
      },
    });
  };
  // Immobile en debut, a des niveaux qui changent : huit images ouvrent.
  for (let i = 1; i <= 8; i++) image("debut", i);
  egal("pendant l'attente, chaque image lit son propre repere", recus.slice(0, 7), [1, 2, 3, 4, 5, 6, 7]);
  egal("la serie est ouverte", circuit.bloc_actuel.serie_ouverte, true);
  image("debut", 50);
  egal("apres l'ouverture, le repere reste celui de l'image d'ouverture", recus.at(-1), 8);
  egal("l'instrument qui explique un refus lit le meme repere", instrument_recus.at(-1), 8);
  image("fin", 60);
  egal("la serie se termine", circuit.phase, "recuperation_serie");
  circuit.passer_pause();
  egal("la serie suivante n'a plus de repere", "repere" in circuit.bloc_actuel, false);
  image("debut", 70);
  egal("et relit la pose du moment en attendant", recus.at(-1), 70);
}

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exit(1);
}
console.log(`${controles} controles, aucun ecart.`);
