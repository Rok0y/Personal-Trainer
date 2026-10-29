// Le compteur attend-il la position de depart d'un mouvement, et suit-il son
// rythme (`delai_min_reps`) ? Et la voix, dit-elle le compte au pas du
// mouvement (`voix_tous_les`, `nombre_a_dire`) ?
//
// Les entrees figees de `comparer_seances` ne portent aucun `depart` (elles
// datent d'avant lui) : la regle n'y est jamais visitee. Ces cas sont donc
// ecrits ici a la main, avec leur reponse attendue.
//
//     node scripts/verifier_compteur.mjs

import { CompteurMouvement } from "../web/static/js/compteur.js";
import { nombre_a_dire } from "../web/static/js/moteur.js";

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

/** Les repetitions comptees apres une suite de jetons, une seconde d'ecart. */
function compter(jetons, depart = null) {
  const compteur = new CompteurMouvement();
  jetons.forEach((jeton, i) => compteur.mettre_a_jour(jeton, i, depart));
  return compteur.repetitions;
}

// --- Sans depart : le premier jeton vu fixe la position (le curl part d'en bas)
egal("sans depart, debut puis fin compte", compter(["debut", "fin"]), 1);
egal("sans depart, fin d'abord ne compte rien", compter(["fin", "debut"]), 0);

// --- Developpe couche : depart = "fin", allonge bras tendus
egal("mise en place coudes plies puis bras tendus : rien", compter(["debut", "milieu", "fin"], "fin"), 0);
egal("puis une vraie repetition compte", compter(["debut", "fin", "debut", "fin"], "fin"), 1);
egal("bras tendus d'abord : la premiere repetition compte", compter(["fin", "debut", "fin"], "fin"), 1);
egal("un passage hors position ne remplace pas le depart", compter(["milieu", "debut", "milieu", "fin"], "fin"), 0);

// --- Une fois arme, depart n'a plus rien a dire
egal("douze repetitions apres le depart", compter(["fin", ...Array(12).fill(["debut", "fin"]).flat()], "fin"), 12);

// --- Le repere se perd a la remise a zero, comme le compte
{
  const compteur = new CompteurMouvement();
  for (const [i, jeton] of ["fin", "debut", "fin"].entries()) compteur.mettre_a_jour(jeton, i, "fin");
  compteur.reset();
  for (const [i, jeton] of ["debut", "fin"].entries()) compteur.mettre_a_jour(jeton, 10 + i, "fin");
  egal("apres reset, la mise en place ne compte pas", compteur.repetitions, 0);
}

// --- Le delai minimal entre deux repetitions : par defaut, et propre au
// mouvement (`delai_min_reps`, une montee de genoux ou chaque pas compte).
/** Repetitions comptees pour des aller-retours espaces de `pas` secondes. */
function compter_au_rythme(pas, delai = null) {
  const compteur = new CompteurMouvement();
  for (let i = 0; i < 10; i++) {
    compteur.mettre_a_jour("debut", i * pas, "debut", delai);
    compteur.mettre_a_jour("fin", i * pas + pas / 2, "debut", delai);
  }
  return compteur.repetitions;
}
egal("delai par defaut : une repetition toutes les 0,2 s n'en compte qu'une sur deux", compter_au_rythme(0.2), 5);
egal("delai par defaut : toutes les 0,35 s, tout compte", compter_au_rythme(0.35), 10);
egal("delai propre de 0,15 s : toutes les 0,2 s, tout compte", compter_au_rythme(0.2, 0.15), 10);
egal("delai propre de 0,15 s : un echo a 0,1 s reste refuse", compter_au_rythme(0.1, 0.15), 5);

// --- La voix : chaque repetition par defaut, les dizaines quand chaque pas
// compte. Jamais zero (un -1 qui ramene a zero ne se dit pas).
const dites = (exercice) => [0, 1, 5, 9, 10, 11, 20].filter((n) => nombre_a_dire(exercice, n));
egal("voix : sans pas, chaque repetition", dites({ voix_tous_les: null }), [1, 5, 9, 10, 11, 20]);
egal("voix : un exercice sans le champ dit chaque repetition", dites({}), [1, 5, 9, 10, 11, 20]);
egal("voix : tous les 10, seulement les dizaines", dites({ voix_tous_les: 10 }), [10, 20]);

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : le compteur attend la position de depart du mouvement et suit son rythme.`);
}
