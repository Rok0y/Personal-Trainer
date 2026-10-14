// Le compteur attend-il la position de depart d'un mouvement ?
//
// Les entrees figees de `comparer_seances` ne portent aucun `depart` (elles
// datent d'avant lui) : la regle n'y est jamais visitee. Ces cas sont donc
// ecrits ici a la main, avec leur reponse attendue.
//
//     node scripts/verifier_compteur.mjs

import { CompteurMouvement } from "../web/static/js/compteur.js";

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

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : le compteur attend la position de depart du mouvement.`);
}
