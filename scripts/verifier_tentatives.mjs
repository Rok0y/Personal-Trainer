// Le coach dit-il pourquoi une repetition n'a pas compte, et seulement alors ?
//
// Les scenarios figes de `comparer_seances` rejouent des poses tirees au
// hasard : ils montrent qu'une explication finit par etre dite, pas qu'elle
// donne la bonne raison, ni qu'elle se tait hors position. Ces cas sont ecrits
// ici a la main, sur un instrument minimal ecrit dans le script — un reglage
// de seuil des vrais instruments ne doit pas faire rougir une regle.
//
//     node scripts/verifier_tentatives.mjs

import { SuiviTentatives, jeton_des_valeurs, role_mesure } from "../web/static/js/instruments.js";
import { expliquer_tentative } from "../web/static/js/moteur.js";
import { Lecteur } from "../web/static/js/lecteur.js";
import { texte } from "../web/static/js/messages.js";

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

// Un mouvement de poussee : un angle de chemin (bas sous 90, haut au-dela de
// 140), une condition de position sans raison (allonge : sous 0), une
// condition de forme avec raison (ecart des coudes sous 1,6).
const INSTRUMENT = {
  ordre: ["debut", "fin"],
  defaut: "milieu",
  mesures: [
    { zones: { debut: ["<", 90], fin: [">", 140] }, raisons: { debut: "raison_descendre", fin: "raison_tendre_bras" } },
    { zones: { debut: ["<", 0], fin: ["<", 0] } },
    { zones: { debut: ["<", 1.6], fin: ["<", 1.6] }, raisons: { debut: "raison_coudes_ecartes", fin: "raison_coudes_ecartes" } },
  ],
};
const SANS_RAISON = {
  ordre: ["debut", "fin"],
  defaut: "milieu",
  mesures: [{ zones: { debut: ["<", 90], fin: [">", 140] } }],
};

// Une image : [angle, position, ecart] ; allonge et coudes serres par defaut.
const img = (angle, position = -1, ecart = 1) => [angle, position, ecart];

/** Les demi-cycles clos par une suite d'images, resumes. */
function rejouer(images, { instrument = INSTRUMENT, depart = null } = {}) {
  const suivi = new SuiviTentatives(instrument, { depart });
  const clos = [];
  images.forEach((valeurs, i) => {
    const entree = suivi.observer(jeton_des_valeurs(instrument, valeurs), valeurs, i / 10);
    if (entree) clos.push([entree.type, entree.complet, entree.significatif, entree.raison]);
  });
  return clos;
}

// --- Les roles se lisent sur les zones
egal("roles d'un retour (fin -> debut)",
  INSTRUMENT.mesures.map((m) => role_mesure(m, "fin", "debut")), ["chemin", "position", "forme"]);
egal("une zone de la seule cible est une condition d'arrivee",
  role_mesure({ zones: { fin: ["<", 0] } }, "debut", "fin"), "cible");

// --- Ce qui compte ne s'explique pas
egal("une repetition complete : rien a dire",
  rejouer([img(150), img(80), img(150)]),
  [["retour", true, true, null], ["aller", true, true, null]]);

// --- Une hesitation se tait
egal("descendre de 10 % du chemin et remonter : hesitation",
  rejouer([img(150), img(135), img(150)]), [["retour", false, false, "raison_descendre"]]);

// --- Pas assez bas : le compteur ne se rearme pas
egal("une pompe pas assez descendue : « tu ne descends pas assez bas »",
  rejouer([img(150), img(120), img(100), img(150)]), [["retour", false, true, "raison_descendre"]]);

// --- Pas assez haut
egal("un aller interrompu : « tes bras ne sont pas completement tendus »",
  rejouer([img(150), img(80), img(110), img(80)]),
  [["retour", true, true, null], ["aller", false, true, "raison_tendre_bras"]]);

// --- Hors position, rien ne progresse
egal("debout, plier les bras ne fait pas une tentative",
  rejouer([img(150), img(100, 1), img(80, 1), img(150)]), [["retour", false, false, "raison_descendre"]]);

// --- La forme : le chemin est alle au bout, coudes ouverts a la meme image
egal("descendu coudes ouverts : « tes coudes sont trop ecartes »",
  rejouer([img(150), img(110, -1, 1.2), img(80, -1, 1.8), img(150)]),
  [["retour", false, true, "raison_coudes_ecartes"]]);
egal("des coudes ouverts en chemin seulement ne sont pas la raison",
  rejouer([img(150), img(110, -1, 1.8), img(100, -1, 1.2), img(150)]),
  [["retour", false, true, "raison_descendre"]]);

// --- Sans raison declaree : la phrase generique du demi-cycle
egal("une mesure sans raison laisse la phrase generique",
  rejouer([[150], [100], [150]], { instrument: SANS_RAISON }), [["retour", false, true, "amplitude_retour_incomplet"]]);

// --- La position de depart, comme le compteur
egal("depart = fin : la mise en place coudes plies ne s'explique pas",
  rejouer([img(80), img(110), img(80), img(150)], { depart: "fin" }), []);
egal("depart = fin : une fois bras tendus, le suivi commence",
  rejouer([img(80), img(150), img(100), img(150)], { depart: "fin" }), [["retour", false, true, "raison_descendre"]]);

// --- Dans la seance : la voix une fois, le bandeau jusqu'a la repetition suivante
{
  const exercice = { instrument: { ...INSTRUMENT, mesures: INSTRUMENT.mesures.map((m, i) => ({ ...m, valeur: (c) => c[i] })) } };
  const bloc = {};
  const etat = { erreur: null };
  const dites = [];
  const pas = (corps, { rep_comptee = false, faute = null } = {}) => {
    etat.erreur = null;
    return expliquer_tentative({
      exercice, corps, bloc, etat, coach: (...a) => dites.push(a),
      jeton: jeton_des_valeurs(exercice.instrument, corps), maintenant: dites.length, rep_comptee, faute, texte,
    });
  };
  pas(img(150)); pas(img(100));
  egal("la raison est dite quand la tentative echoue", pas(img(150)), "raison_descendre");
  egal("par la cle composee du lecteur", dites, [["repetition_non_comptee", "raison_descendre"]]);
  egal("le bandeau la compose", etat.erreur, "Ça ne compte pas : tu ne descends pas assez bas.");
  pas(img(150));
  egal("le bandeau la garde, la voix ne la redit pas", [etat.erreur, dites.length], ["Ça ne compte pas : tu ne descends pas assez bas.", 1]);
  pas(img(150), { faute: "forme_coudes_trop_ecartes" });
  egal("une faute du moment passe devant", etat.erreur, null);
  pas(img(80)); pas(img(150), { rep_comptee: true });
  egal("une repetition comptee l'efface", [etat.erreur, "non_comptee" in bloc], [null, false]);
  egal("sans instrument, rien", expliquer_tentative({ exercice: {}, bloc: {}, etat }), null);
}

// --- Le lecteur compose « Ca ne compte pas » et la raison en une entree
{
  const lecteur = new Lecteur("sons", {
    fichiers: { repetition_non_comptee: ["ca.wav"], raison_descendre: ["bas.wav"] },
    priorites: { repetition_non_comptee: 6 },
    delais: { repetition_non_comptee: 4 },
  });
  const empiles = [];
  lecteur.contexte = {};
  lecteur._empiler = (fichiers, priorite) => empiles.push([fichiers, priorite]);
  lecteur.coach("repetition_non_comptee", "raison_descendre");
  egal("une seule entree, l'amorce puis la raison", empiles, [[["ca.wav", "bas.wav"], 6]]);
  lecteur.coach("repetition_non_comptee", "raison_descendre");
  egal("le delai de la cle empeche de la redire aussitot", empiles.length, 1);
}

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : une repetition refusee dit pourquoi, et une hesitation se tait.`);
}
