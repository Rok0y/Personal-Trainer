// Une serie comptee attend-elle qu'on soit en place, et dit-elle alors
// « c'est parti » ?
//
// Les scenarios figes de `comparer_seances` coupent l'attente (`mise_en_place:
// false`) : leurs poses tirees au hasard ne restent jamais immobiles, et plus
// rien n'y compterait. La regle est donc verifiee ici, sur des corps ecrits a
// la main — un jeton et un buste qu'on deplace ou non.
//
//     node scripts/verifier_mise_en_place.mjs

import {
  Circuit, BlocExercice, Exercice, MODE_AMRAP, MODE_CHRONO, MODE_REPETITIONS,
} from "../web/static/js/circuit.js";
import { CompteurMouvement } from "../web/static/js/compteur.js";
import { creer_etat } from "../web/static/js/etat.js";
import { ajuster_repetitions, executer_mode } from "../web/static/js/moteur.js";
import { texte, libelle_etape } from "../web/static/js/messages.js";

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

// Un quart de seconde par image : un nombre exact en virgule flottante, donc
// des franchissements de seuil sans arrondi a deviner.
const PAS = 0.25;
// Images d'immobilite avant l'ouverture : la premiere ne mesure pas encore de
// vitesse (il en faut deux), la deuxieme ouvre le decompte d'une seconde et
// demie, soit six images. **Ecrit ici, pas relu dans le moteur** : calcule a
// partir de `DUREE_MISE_EN_PLACE`, le test suivait la constante, et une duree
// mise a zero passait inapercue.
const IMAGES_POUR_OUVRIR = 2 + 6;

/** Un corps : le jeton que rend la detection, et un buste decale de `x`. */
function corps(jeton, x = 0.5) {
  const point = (dx, y) => ({ x: x + dx, y });
  return {
    jeton,
    epaule_gauche: point(0.1, 0.3), epaule_droite: point(-0.1, 0.3),
    hanche_gauche: point(0.08, 0.6), hanche_droite: point(-0.08, 0.6),
  };
}

/** Une seance d'un bloc, deja dans sa premiere serie, a horloge manuelle. */
function seance({ mode = MODE_REPETITIONS, depart = null, repetitions = 3, duree = 30, mise_en_place = true } = {}) {
  const exercice = new Exercice({ nom: "Essai", detection: (c) => c.jeton, depart });
  const horloge = { t: 100 };
  const circuit = new Circuit([new BlocExercice({
    exercice, poids: 0, mode, nombre_series: 2, repetitions_par_serie: repetitions,
    duree, repos_entre_series: 10, repos_apres: 0,
  })]);
  circuit.maintenant = () => horloge.t;
  circuit.debut = horloge.t;
  circuit.commencer_exercice();
  const s = {
    circuit, horloge, dites: [], compteur: new CompteurMouvement(), etat: creer_etat(),
    derniere_rep: 0,
    image(c, pas = PAS) {
      horloge.t += pas;
      s.etat.consigne = null;
      const [rep] = executer_mode({
        seance: circuit, corps: c, compteur: s.compteur, etat: s.etat,
        coach: (...a) => s.dites.push(a[0]), derniere_rep: s.derniere_rep,
        messages: { texte, libelle_etape }, mise_en_place,
      });
      s.derniere_rep = rep;
    },
    images(n, fabrique) {
      for (let i = 0; i < n; i++) s.image(fabrique(i));
    },
    get ouverte() { return circuit.bloc_actuel?.serie_ouverte === true; },
  };
  return s;
}

// --- Immobile en position : ouverte a la duree pile, « c'est parti » une fois
{
  const s = seance();
  s.images(IMAGES_POUR_OUVRIR - 1, () => corps("debut"));
  egal("une image avant la duree : pas encore ouverte", s.ouverte, false);
  egal("en attendant, la consigne de se mettre en place", s.etat.consigne, texte("mise_en_place"));
  s.image(corps("debut"));
  egal("a la duree : ouverte", s.ouverte, true);
  egal("« c'est parti » est dit", s.dites, ["debut_serie"]);
  s.images(4, () => corps("debut"));
  egal("et une seule fois", s.dites, ["debut_serie"]);
  s.image(corps("fin"));
  egal("la premiere repetition compte apres", s.etat.repetitions, 1);
}

// Marcher : deux cinquiemes de la largeur de l'image par seconde, au-dessus
// du seuil d'immobilite.
const marche = (jeton) => (i) => corps(jeton, i % 2 ? 0.3 : 0.4);

// --- Marcher bras ballant : le jeton tient, le buste bouge
{
  const s = seance();
  s.images(20, marche("debut"));
  egal("en marchant bras ballant, rien ne s'ouvre", s.ouverte, false);
  s.images(20, (i) => (i % 4 < 2 ? marche("debut") : marche("fin"))(i));
  egal("ni repetition, ni voix", [s.etat.repetitions, s.dites], [0, []]);
}

// --- Immobile hors position (un jeton intermediaire) : rien
{
  const s = seance();
  s.images(20, () => corps("milieu"));
  egal("immobile entre deux positions : rien ne s'ouvre", s.ouverte, false);
}

// --- Le jeton doit rester le meme : changer d'extremite relance l'attente
{
  const s = seance();
  s.images(IMAGES_POUR_OUVRIR - 1, () => corps("debut"));
  s.images(IMAGES_POUR_OUVRIR - 2, () => corps("fin"));
  egal("passer de debut a fin relance la duree", s.ouverte, false);
  s.image(corps("fin"));
  egal("puis la duree pleine sur fin ouvre", s.ouverte, true);
}

// --- La position tenue devient le depart du compteur
{
  const s = seance();
  s.images(IMAGES_POUR_OUVRIR, () => corps("fin")); // debout, pour un squat
  s.image(corps("debut")); s.image(corps("fin"));
  egal("tenu en fin : descendre puis remonter compte une repetition", s.etat.repetitions, 1);
}

// --- Un depart declare : seul lui ouvre la serie
{
  const s = seance({ depart: "fin" });
  s.images(20, () => corps("debut"));
  egal("depart = fin : immobile en debut ne s'ouvre pas", s.ouverte, false);
  s.images(IMAGES_POUR_OUVRIR, () => corps("fin"));
  egal("depart = fin : immobile en fin s'ouvre", s.ouverte, true);
}

// --- Une absence remet l'attente a zero
{
  const s = seance();
  s.images(IMAGES_POUR_OUVRIR - 2, () => corps("debut"));
  s.image(corps("debut"), 3); // trois secondes sans image (hors champ)
  egal("revenir apres une absence ne compte pas le temps hors champ", s.ouverte, false);
}

// --- Chaque serie se rouvre
{
  const s = seance({ repetitions: 1 });
  s.images(IMAGES_POUR_OUVRIR, () => corps("debut"));
  s.image(corps("fin"));
  egal("la serie se termine", s.circuit.phase, "recuperation_serie");
  s.circuit.passer_pause();
  egal("la serie suivante attend de nouveau", [s.circuit.phase, s.ouverte], ["exercice", false]);
  s.images(IMAGES_POUR_OUVRIR, () => corps("debut"));
  egal("et redit « c'est parti »", s.dites.filter((d) => d === "debut_serie").length, 2);
}

// --- Un geste ±1 ouvre la serie, en silence
{
  const s = seance();
  s.image(corps("debut"));
  s.derniere_rep = ajuster_repetitions({
    seance: s.circuit, compteur: s.compteur, etat: s.etat, coach: (...a) => s.dites.push(a[0]),
    delta: 1, derniere_rep: s.derniere_rep,
  });
  egal("le geste ouvre la serie sans « c'est parti »", [s.ouverte, s.dites], [true, []]);
}

// --- AMRAP : le chrono part a l'ouverture
{
  const s = seance({ mode: MODE_AMRAP, duree: 60 });
  s.images(8, marche("debut")); // on se met en place
  egal("pendant l'attente, le chrono n'a pas commence", s.etat.temps_amrap_restant, 60);
  s.images(IMAGES_POUR_OUVRIR, () => corps("debut"));
  s.images(4, () => corps("debut"));
  egal("une seconde apres l'ouverture, une seconde est ecoulee", s.circuit.bloc_actuel.temps_amrap, 1);
}

// --- Ce qui ne compte pas s'ouvre a la premiere image
{
  const s = seance({ mode: MODE_CHRONO });
  s.image(corps("milieu", 0.2));
  egal("un chrono s'ouvre tout de suite", [s.ouverte, s.dites], [true, ["debut_serie"]]);
}

// --- Le rejeu des scenarios coupe l'attente
{
  const s = seance({ mise_en_place: false });
  s.image(corps("debut", 0.2));
  egal("sans attente, ouverte a la premiere image", [s.ouverte, s.dites], [true, ["debut_serie"]]);
  s.image(corps("fin", 0.4));
  egal("et le compte part de la", s.etat.repetitions, 1);
}

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : une serie comptee s'ouvre quand on est immobile en position.`);
}
