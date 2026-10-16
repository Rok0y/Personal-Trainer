// Un mouvement unilateral fait du mauvais cote se dit-il, et seulement alors ?
//
// Deux regles. (1) Le bas d'une fente exige que la jambe mesuree soit devant :
// le genou arriere se plie aussi, et une fente faite de l'autre pied
// comptait. (2) La detection de l'autre cote alimente un compteur fantome
// (`surveiller_autre_cote`) : quand il compte seul, le coach dit « Ca ne
// compte pas : c'est l'autre jambe ». Les scenarios figes ne connaissent pas
// l'autre cote (le catalogue fige n'a pas le champ) et leurs poses au hasard
// ne font jamais une fente du mauvais pied : ces cas sont ecrits ici a la main.
//
//     node scripts/verifier_cotes.mjs

import {
  Circuit, BlocExercice, Exercice, MODE_MAINTIEN, MODE_REPETITIONS,
} from "../web/static/js/circuit.js";
import { CompteurMouvement } from "../web/static/js/compteur.js";
import { creer_etat } from "../web/static/js/etat.js";
import {
  FENTE_GENOU_AVANT_MIN, fente_droite_detection, fente_gauche_detection,
} from "../web/static/js/detections.js";
import { jeton_des_valeurs } from "../web/static/js/instruments.js";
import {
  FENETRE_AUTRE_COTE, SILENCE_APRES_AUTRE_COTE, TENUE_AUTRE_COTE, executer_mode,
} from "../web/static/js/moteur.js";
import { texte, libelle_etape } from "../web/static/js/messages.js";

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

egal("les reglages dont dependent les cas ci-dessous",
  [FENTE_GENOU_AVANT_MIN, FENETRE_AUTRE_COTE, SILENCE_APRES_AUTRE_COTE, TENUE_AUTRE_COTE],
  [0.3, 0.5, 1, 1]);

// --- (1) Le pied avant d'une fente, vu de profil
//
// Un tibia de 0,2 de haut. La jambe avant : hanche au-dessus du genou, genou
// a 90 degres, tibia vertical. La jambe arriere : genou presque au sol, pied
// derriere. Les deux genoux sont a 90 degres — seule leur hauteur les distingue.
function fente(avant) {
  const jambe_avant = {
    hanche: { x: 0.5, y: 0.5 }, genou: { x: 0.7, y: 0.5 }, cheville: { x: 0.7, y: 0.7 },
  };
  const jambe_arriere = {
    hanche: { x: 0.5, y: 0.5 }, genou: { x: 0.5, y: 0.68 }, cheville: { x: 0.3, y: 0.68 },
  };
  const [droite, gauche] = avant === "droite" ? [jambe_avant, jambe_arriere] : [jambe_arriere, jambe_avant];
  return {
    hanche_droite: droite.hanche, genou_droit: droite.genou, cheville_droite: droite.cheville,
    hanche_gauche: gauche.hanche, genou_gauche: gauche.genou, cheville_gauche: gauche.cheville,
  };
}
egal("pied droit devant : le bas d'une fente droite", fente_droite_detection(fente("droite")), "debut");
egal("pied gauche devant : pas le bas d'une fente droite, meme genou droit plie",
  fente_droite_detection(fente("gauche")), "milieu");
egal("pied gauche devant : le bas d'une fente gauche", fente_gauche_detection(fente("gauche")), "debut");
egal("pied droit devant : pas le bas d'une fente gauche", fente_gauche_detection(fente("droite")), "milieu");
{
  // Debout, pieds joints : les genoux a la meme hauteur, la position de depart
  // reste lisible des deux cotes.
  const jambe = (x) => ({ hanche: { x, y: 0.5 }, genou: { x, y: 0.7 }, cheville: { x, y: 0.9 } });
  const [d, g] = [jambe(0.48), jambe(0.52)];
  const debout = {
    hanche_droite: d.hanche, genou_droit: d.genou, cheville_droite: d.cheville,
    hanche_gauche: g.hanche, genou_gauche: g.genou, cheville_gauche: g.cheville,
  };
  egal("debout, pieds joints : la fin des deux cotes",
    [fente_droite_detection(debout), fente_gauche_detection(debout)], ["fin", "fin"]);
}

// --- (2) Le compteur fantome, en seance
//
// Un mouvement minimal : un angle de chemin (bas sous 100, haut au-dela de
// 150, avec ses raisons) et la condition du pied avant (bas seulement, sans
// raison), comme la vraie fente. Le jeton de l'autre cote est donne tel quel.
const INSTRUMENT = {
  ordre: ["debut", "fin"],
  defaut: "milieu",
  mesures: [
    {
      zones: { debut: ["<", 100], fin: [">", 150] },
      raisons: { debut: "raison_descendre", fin: "raison_remonter" },
      valeur: (c) => c.angle,
    },
    { zones: { debut: [">", 0.3] }, valeur: (c) => c.devant },
  ],
};
const detection = (c) => jeton_des_valeurs(INSTRUMENT, INSTRUMENT.mesures.map((m) => m.valeur(c)));
const PAS = 0.25;

/** Une image : l'angle du genou mesure, s'il est devant, le jeton de l'autre cote. */
const img = (angle, devant, autre) => ({ angle, devant, autre });

function seance({ mode = MODE_REPETITIONS, membre = "jambe", repetitions = 5, duree = 30 } = {}) {
  const exercice = new Exercice({
    nom: "Essai", detection, instrument: INSTRUMENT,
    autre_cote: { detection: (c) => c.autre, membre },
  });
  if (mode === MODE_MAINTIEN) exercice.detection = (c) => c.jeton;
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
    image(c) {
      horloge.t += PAS;
      const [rep] = executer_mode({
        seance: circuit, corps: c, compteur: s.compteur, etat: s.etat,
        coach: (cle, valeur = null) => s.dites.push([horloge.t - 100, cle, valeur]),
        derniere_rep: s.derniere_rep, messages: { texte, libelle_etape }, mise_en_place: false,
      });
      s.derniere_rep = rep;
    },
    jouer(images) { for (const c of images) s.image(c); },
    // Ce qui a ete dit, sans les « c'est parti » ni les comptes.
    get paroles() {
      return s.dites.filter(([, cle]) => !["debut_serie", "compteur", "bip"].includes(cle));
    },
  };
  return s;
}

// Une fente du mauvais pied : le genou mesure (l'arriere) descend sous 100
// sans etre devant, pendant que l'autre cote fait une fente complete.
const MAUVAIS_PIED = [
  img(170, 0, "fin"), img(130, -0.5, "milieu"), img(90, -0.9, "debut"), img(90, -0.9, "debut"),
  img(130, -0.5, "milieu"), img(170, 0, "fin"), img(170, 0, "fin"), img(170, 0, "fin"),
  img(170, 0, "fin"), img(170, 0, "fin"),
];
{
  const s = seance();
  s.jouer(MAUVAIS_PIED);
  // L'autre cote compte a 1,5 s ; l'erreur se confirme une demi-seconde apres.
  egal("une fente du mauvais pied : « c'est l'autre jambe », et rien d'autre",
    s.paroles, [[2, "repetition_non_comptee", "raison_autre_jambe"]]);
  egal("elle ne compte pas", s.compteur.repetitions, 0);
  egal("le bandeau le dit", s.etat.erreur, texte("repetition_non_comptee", { raison: texte("raison_autre_jambe") }));
}

// Sans l'autre cote, le meme mouvement fait dire le seul echec du chemin : ce
// que le silence ci-dessus a fait taire.
{
  const s = seance();
  s.circuit.bloc_actuel.exercice.autre_cote = null;
  s.jouer(MAUVAIS_PIED);
  egal("sans autre cote, l'echec du genou arriere se dirait a tort",
    s.paroles.map(([, cle, valeur]) => [cle, valeur]), [["repetition_non_comptee", "amplitude_retour_incomplet"]]);
}

// Le bon pied : rien que le compte.
{
  const s = seance();
  s.jouer([
    img(170, 0, "fin"), img(130, 0.5, "milieu"), img(90, 0.9, "milieu"), img(130, 0.5, "milieu"),
    img(170, 0, "fin"), img(170, 0, "fin"), img(170, 0, "fin"),
  ]);
  egal("le bon pied compte, sans un mot de trop", [s.compteur.repetitions, s.paroles], [1, []]);
}

// Les deux bras a la fois : le bon cote compte aussi, a la meme image ou dans
// la demi-seconde.
{
  const s = seance({ membre: "bras" });
  s.jouer([
    img(170, 0, "debut"), img(90, 0.9, "debut"), img(170, 0, "fin"), img(170, 0, "fin"),
    img(170, 0, "fin"), img(170, 0, "fin"),
  ]);
  egal("les deux cotes ensemble : rien a dire", [s.compteur.repetitions, s.paroles], [1, []]);
}
{
  const s = seance({ membre: "bras" });
  s.jouer([
    img(170, 0, "debut"), img(90, 0.9, "debut"), img(90, 0.9, "fin"), img(170, 0, "fin"),
    img(170, 0, "fin"), img(170, 0, "fin"), img(170, 0, "fin"),
  ]);
  egal("le bon cote compte un quart de seconde apres l'autre : rien a dire",
    [s.compteur.repetitions, s.paroles], [1, []]);
}
{
  // Le bon cote a compte juste avant : l'autre suit d'un quart de seconde.
  const s = seance({ membre: "bras" });
  s.jouer([
    img(170, 0, "debut"), img(90, 0.9, "debut"), img(170, 0, "debut"), img(170, 0, "fin"),
    img(170, 0, "fin"), img(170, 0, "fin"), img(170, 0, "fin"),
  ]);
  egal("le bon cote compte un quart de seconde avant l'autre : rien a dire",
    [s.compteur.repetitions, s.paroles], [1, []]);
}
{
  // Le bon cote compte trop tard : l'erreur est deja dite.
  const s = seance({ membre: "bras" });
  s.jouer([
    img(170, 0, "debut"), img(170, 0, "fin"), img(170, 0, "fin"), img(170, 0, "fin"),
    img(90, 0.9, "fin"), img(170, 0, "fin"),
  ]);
  egal("l'autre bras seul, puis le bon bien apres : l'erreur a la demi-seconde pile",
    s.paroles, [[1, "repetition_non_comptee", "raison_autre_bras"]]);
  egal("et la repetition du bon bras efface le bandeau", s.etat.erreur, null);
}

// --- Un maintien de l'autre cote (planche laterale)
{
  const s = seance({ mode: MODE_MAINTIEN, membre: "cote" });
  const maintien_autre = { jeton: "repos", autre: "maintien" };
  s.jouer([maintien_autre, maintien_autre, maintien_autre]);
  egal("trois quarts de seconde de l'autre cote : rien encore", s.paroles, []);
  egal("mais le bandeau le dit deja", s.etat.erreur,
    texte("repetition_non_comptee", { raison: texte("raison_autre_cote") }));
  s.jouer([maintien_autre, maintien_autre, maintien_autre, maintien_autre]);
  // Vu a 0,25 s, dit une seconde plus tard.
  egal("une seconde pile : « c'est l'autre cote », une fois par episode",
    s.paroles, [[1.25, "repetition_non_comptee", "raison_autre_cote"]]);
  s.jouer([{ jeton: "repos", autre: "repos" }]);
  egal("l'episode fini, le bandeau s'efface", s.etat.erreur, null);
  s.jouer([maintien_autre, maintien_autre, maintien_autre, maintien_autre, maintien_autre]);
  egal("un nouvel episode se redit", s.paroles.length, 2);
}
{
  const s = seance({ mode: MODE_MAINTIEN, membre: "cote" });
  const les_deux = { jeton: "maintien", autre: "maintien" };
  s.jouer([les_deux, les_deux, les_deux, les_deux, les_deux, les_deux]);
  egal("tenu du bon cote, l'autre ne dit rien", [s.paroles, s.etat.erreur], [[], null]);
}

if (problemes.length) {
  console.log(`${problemes.length} probleme(s) sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exit(1);
}
console.log(`${controles} controles : le mauvais cote se dit, et seulement lui.`);
