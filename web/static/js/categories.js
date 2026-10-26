// La categorie d'un mouvement, et les etiquettes qu'on en tire.
//
// Chaque mouvement de `mouvements.json` porte `categories: {muscles, chaine}`,
// muscle principal en tete. **Partie du corps et region ne s'ecrivent pas** :
// elles se deduisent des muscles par `categories.json` (muscle → partie →
// region), une seule source par fait. Ecrites a cote, elles finiraient par
// dire « biceps, jambes ».
//
// Les categories fines (muscles, parties, chaine) ne s'affichent pas dans
// l'application : elles servent a tirer les etiquettes d'un programme (sa
// zone, son materiel), qui elles se montrent et filtrent. L'outil maitre les
// montre toutes.
//
// Un mouvement a la fois echauffement et exercice (`aussi_exercice`) compte
// ici comme un exercice : ces fonctions ne voient que des noms, pas le mode
// des blocs.

import { est_exercice } from "./nature.js";

/** Les categories d'un mouvement, ou null s'il n'en porte pas. */
export function categories_du_mouvement(tables, mouvement) {
  const brut = mouvement?.categories;
  if (!brut || !Array.isArray(brut.muscles)) return null;
  const parties = [];
  const regions = [];
  for (const muscle of brut.muscles) {
    const partie = tables.muscles?.[muscle]?.partie;
    if (!partie) continue;
    if (!parties.includes(partie)) parties.push(partie);
    const region = tables.parties?.[partie]?.region;
    if (region && !regions.includes(region)) regions.push(region);
  }
  return { muscles: [...brut.muscles], parties, regions, chaine: brut.chaine ?? null };
}

/**
 * La zone d'un ensemble d'exercices : une cle de `regions`, `"plusieurs"`,
 * ou null si aucun ne porte de categorie.
 *
 * Une region **qui accompagne** (le tronc) ne compte que seule : des abdos a
 * la fin d'une seance de jambes la laissent « bas du corps », et c'est ce
 * qu'on ecrit en la nommant. L'echauffement n'entre pas : rien ne le distingue
 * a l'appelant, c'est donc ici qu'on l'ecarte.
 */
export function zone_des_exercices(tables, mouvements, noms) {
  const vues = new Set();
  for (const nom of noms) {
    const mouvement = mouvements[nom];
    if (!est_exercice(mouvement)) continue;
    for (const region of categories_du_mouvement(tables, mouvement)?.regions ?? []) {
      vues.add(region);
    }
  }
  if (!vues.size) return null;
  const principales = [...vues].filter((r) => !tables.regions?.[r]?.accompagne);
  if (!principales.length) return vues.size === 1 ? [...vues][0] : "plusieurs";
  return principales.length === 1 ? principales[0] : "plusieurs";
}

/** Le nom affiche d'une zone. */
export function nom_zone(tables, zone) {
  if (zone === "plusieurs") return tables.plusieurs_regions ?? null;
  return tables.regions?.[zone]?.nom ?? null;
}

/**
 * Les exercices qu'un programme fait jouer : ceux de ses seances liees, dans
 * l'ordre, sans doublon. Les exigences ne suffisent pas : un exercice sans
 * bareme (un gainage tenu au chrono) n'en porte pas, et il compte pourtant
 * dans la zone et le materiel.
 */
export function exercices_du_programme(programme, catalogue_seances) {
  const noms = [];
  for (const nom_seance of Object.values(programme?.seances ?? {})) {
    for (const bloc of catalogue_seances[nom_seance] ?? []) {
      if (bloc?.exercice && !noms.includes(bloc.exercice)) noms.push(bloc.exercice);
    }
  }
  for (const exigence of programme?.exigences ?? []) {
    if (exigence?.exercice && !noms.includes(exigence.exercice)) noms.push(exigence.exercice);
  }
  return noms;
}

/**
 * Les etiquettes d'un ensemble d'exercices : `{zone, sans_haltere, jouable}`.
 *
 * `sans_haltere` et `jouable` sont des questions `(nom) => booleen` posees
 * par l'appelant (`Variantes.jouable_avec_le_materiel`, sur un moteur sans
 * haltere et sur celui du profil) : la regle du materiel vit dans
 * `variantes.js`, pas ici. Une question absente rend null — « on ne sait
 * pas », jamais « oui ». L'echauffement n'y entre pas : il ne se charge pas.
 */
export function etiquettes(tables, mouvements, noms, questions = {}) {
  const exercices = noms.filter((nom) => est_exercice(mouvements[nom]));
  const tous = (question) =>
    typeof question === "function" ? exercices.every((nom) => question(nom)) : null;
  return {
    zone: zone_des_exercices(tables, mouvements, exercices),
    sans_haltere: tous(questions.sans_haltere),
    jouable: tous(questions.jouable),
  };
}
