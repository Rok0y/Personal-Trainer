// Les fichiers de `web/static/donnees/` se tiennent-ils ?
//
// Ces fichiers sont des **sources** editees a la main (ou depuis les pages
// `dev/`) : rien ne les fabrique plus, donc rien ne les valide en les
// fabriquant. L'application, elle, ne leve jamais sur une donnee bancale —
// elle tait une fiche manquante, ignore un exercice inconnu, refuse de
// demarrer une seance. Ce controle pose les memes questions **a froid**,
// avant le deploiement plutot qu'en seance :
//
//  - reglages : chaque bareme a ses champs, et le materiel de son exercice ;
//    chaque mouvement compte a son bareme, et son tempo s'il compte en
//    repetitions ;
//  - fiches : chaque mouvement a sa fiche, chaque champ a sa forme ;
//  - mouvements : chaque fonction nommee existe dans `detections.js`, chaque
//    variante designe un mouvement du catalogue ; `aussi_exercice`,
//    `delai_min_reps`, `voix_tous_les` et `en_developpement` sont bien formes ;
//  - seances : chaque seance passe `problemes_des_blocs`, le controle que fait
//    l'editeur de l'application a l'enregistrement ;
//  - programmes : chaque exigence vise un exercice qui a un bareme, et chaque
//    libelle est lie a une seance qui existe ;
//  - categories : les tables muscle → partie → region se tiennent, et chaque
//    mouvement porte des muscles et une chaine connus ;
//  - videos : chaque `.mp4` de `videos/` porte le nom (`fichier_video`) d'un
//    mouvement. Un mouvement renomme rend sa video orpheline, et une video que
//    rien ne lit est aussi invisible qu'une video absente. Une video
//    **manquante**, elle, n'est pas une erreur : on les tourne par lots, et
//    `dev/fiches.html` dit lesquelles restent a faire.
//
//     node scripts/verifier_donnees.mjs

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { DETECTIONS } from "../web/static/js/detections.js";
import { DELAI_MIN_ENTRE_REPS } from "../web/static/js/compteur.js";
import { est_compte } from "../web/static/js/nature.js";
import { PREFIXE_PROGRAMME_PERSO, est_programme_perso } from "../web/static/js/historique.js";
import { Baremes, composer_baremes } from "../web/static/js/paliers.js";
import { problemes_du_programme } from "../web/static/js/programmes.js";
import { avec_fiches, problemes_des_blocs } from "../web/static/js/seance.js";
import { fichier_video } from "../web/static/js/videos.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const DONNEES = join(ICI, "..", "web", "static", "donnees");
const VIDEOS = join(ICI, "..", "web", "static", "videos");
const lire = (nom) => JSON.parse(readFileSync(join(DONNEES, nom), "utf-8"));

//: Les champs de texte d'une fiche, et leur forme.
const CHAMPS_FICHE = {
  description: "string",
  mise_en_place: "liste",
  instructions: "liste",
  erreurs_frequentes: "liste",
  sensations: "liste",
};

function main() {
  const problemes = [];
  const signaler = (fichier, message) => problemes.push(`${fichier} : ${message}`);

  const reglages = lire("reglages.json");
  const socle = lire("baremes.json");
  const fiches = lire("fiches.json");
  const bruts = lire("mouvements.json");
  const seances = lire("seances.json");
  const programmes = lire("programmes.json");
  const categories = lire("categories.json");

  // --- reglages ---
  for (const section of ["specs", "ligues", "xp", "note_athlete"]) {
    if (!reglages[section]) signaler("reglages.json", `section « ${section} » absente`);
  }
  const specs = reglages.specs ?? {};
  if (!Object.keys(specs).length) signaler("reglages.json", "aucun bareme, le moteur n'aurait rien a proposer");
  for (const [nom, spec] of Object.entries(specs)) {
    for (const champ of ["series", "cible_min"]) {
      if (typeof spec[champ] !== "number") signaler("reglages.json", `« ${nom} » : ${champ} doit etre un nombre`);
    }
    if (!socle.materiel?.[nom]) signaler("baremes.json", `« ${nom} » a un bareme mais pas d'entree dans materiel`);
    if (!bruts[nom]) signaler("reglages.json", `« ${nom} » a un bareme mais n'est pas dans mouvements.json`);
  }
  // Les programmes se valident sur le bareme lui-meme ; une composition
  // impossible le remplace par la seule liste des specs, pour dire quand
  // meme ce qui cloche ailleurs.
  let baremes = { est_suivi_par_le_moteur: (nom) => nom in specs };
  try {
    baremes = new Baremes(composer_baremes(socle, reglages), null);
  } catch (erreur) {
    signaler("reglages.json", `composition impossible : ${erreur.message}`);
  }
  // Les bornes de ligue : sans elles, l'exercice retombe sur la table
  // relative, un repli qui masque le branchement oublie. Dix-huit, croissantes
  // strictement (deux bornes egales rendraient un rang inatteignable).
  const bornes = reglages.ligues?.seuils_par_exercice ?? {};
  for (const nom of Object.keys(specs)) {
    const table = bornes[nom];
    if (!table) signaler("reglages.json", `« ${nom} » n'a pas de bornes de ligue (seuils_par_exercice)`);
    else if (table.length !== 18 || table.some((v, i) => i > 0 && !(v > table[i - 1]))) {
      signaler("reglages.json", `« ${nom} » : il faut dix-huit bornes de ligue strictement croissantes`);
    }
  }
  for (const nom of Object.keys(bornes)) {
    if (!specs[nom]) signaler("reglages.json", `bornes de ligue pour « ${nom} », qui n'a pas de bareme`);
  }
  // Les corrections de palier (`surcharges`, ecrites depuis
  // dev/progression.html) : une cle inconnue fait lever `Baremes.palier`, donc
  // planter l'exercice partout dans l'application.
  for (const [nom, spec] of Object.entries(specs)) {
    for (const [niveau, surcharge] of Object.entries(spec.surcharges ?? {})) {
      if (!(Number.isInteger(Number(niveau)) && Number(niveau) >= 1)) {
        signaler("reglages.json", `« ${nom} » : surcharge sur un palier qui n'existe pas (« ${niveau} »)`);
      }
      for (const [cle, valeur] of Object.entries(surcharge ?? {})) {
        if (!["series", "cible", "poids"].includes(cle)) {
          signaler("reglages.json", `« ${nom} », palier ${niveau} : « ${cle} » ne se surcharge pas (series, cible ou poids)`);
        } else if (!(typeof valeur === "number" && valeur >= (cle === "poids" ? 0 : 1))) {
          signaler("reglages.json", `« ${nom} », palier ${niveau} : ${cle} doit etre un nombre positif`);
        }
      }
    }
  }

  // Les variantes : une performance de retour ne sert qu'a un mouvement qui a
  // une variante plus dure ; la table de depart nomme, pour la tete d'une
  // chaine, des mouvements de cette chaine et des notes de 1 a 10.
  for (const [nom, seuil] of Object.entries(reglages.variantes?.retour ?? {})) {
    if (!bruts[nom]?.variante_difficile) {
      signaler("reglages.json", `retour de « ${nom} » : ce mouvement n'a pas de variante plus dure`);
    }
    if (!Array.isArray(seuil) || seuil.length !== 2 || !seuil.every((v) => v > 0)) {
      signaler("reglages.json", `retour de « ${nom} » : il faut [series, cible] positifs`);
    }
  }
  const chaine_de = (tete) => {
    const noms = [tete];
    for (let n = bruts[tete]?.variante_facile; n && bruts[n] && !noms.includes(n); n = bruts[n].variante_facile) noms.push(n);
    return noms;
  };
  for (const [tete, seuils] of Object.entries(reglages.variantes?.depart ?? {})) {
    if (!bruts[tete] || bruts[tete].variante_difficile) {
      signaler("reglages.json", `depart de « ${tete} » : ce n'est pas la tete d'une chaine de variantes`);
      continue;
    }
    const chaine = chaine_de(tete);
    for (const [nom, note] of Object.entries(seuils ?? {})) {
      if (!chaine.includes(nom)) signaler("reglages.json", `depart de « ${tete} » : « ${nom} » n'est pas dans sa chaine`);
      if (!Number.isInteger(note) || note < 1 || note > 10) {
        signaler("reglages.json", `depart de « ${tete} » : la note de « ${nom} » doit etre un entier de 1 a 10`);
      }
    }
    // Plus dur dans la chaine, plus haute la note : sinon une note plus haute
    // ferait partir sur une variante plus facile.
    const ordonnes = chaine.filter((nom) => nom in seuils).reverse();
    for (let i = 1; i < ordonnes.length; i += 1) {
      if (!(seuils[ordonnes[i]] > seuils[ordonnes[i - 1]])) {
        signaler("reglages.json", `depart de « ${tete} » : « ${ordonnes[i]} » doit demander une note plus haute que « ${ordonnes[i - 1]} »`);
      }
    }
  }

  // Le tempo (duree estimee d'une seance) : pas de valeur par defaut dans
  // `duree.js`, qui masquerait l'oubli. Un mouvement compte en repetitions
  // sans tempo efface donc l'estimation de toute seance qui le joue — d'ou
  // l'exigence ici. Un tempo sur un nom inconnu est un renommage oublie.
  const tempo = reglages.tempo?.secondes_par_repetition ?? {};
  for (const [nom, mouvement] of Object.entries(bruts)) {
    if (!est_compte(mouvement)) continue;
    if (specs[nom]?.unite === "secondes") continue;
    if (!(typeof tempo[nom] === "number" && tempo[nom] > 0)) {
      signaler("reglages.json", `« ${nom} » n'a pas de tempo (tempo.secondes_par_repetition, en secondes)`);
    }
  }
  for (const nom of Object.keys(tempo)) {
    if (!bruts[nom]) signaler("reglages.json", `tempo de « ${nom} », qui n'est pas dans mouvements.json`);
  }

  // Un mouvement compte sans bareme : l'application le joue quand meme, hors
  // moteur — ni objectif, ni niveau, ni ligue —, et rien ne dirait que c'est
  // un oubli. Le reste de la chaine (materiel, bornes) se verifie depuis la
  // spec : sans elle, c'est ici que l'ajout d'un exercice se fait rappeler.
  for (const [nom, mouvement] of Object.entries(bruts)) {
    if (!est_compte(mouvement)) continue;
    if (!specs[nom]) signaler("reglages.json", `« ${nom} » est compte (detection) mais n'a pas de bareme (specs)`);
  }

  // --- fiches et mouvements ---
  for (const [nom, mouvement] of Object.entries(bruts)) {
    if (mouvement.nom !== nom) signaler("mouvements.json", `cle « ${nom} » mais nom « ${mouvement.nom} »`);
    const fiche = fiches[nom];
    if (!fiche) {
      signaler("fiches.json", `« ${nom} » n'a pas de fiche`);
    } else {
      for (const [champ, forme] of Object.entries(CHAMPS_FICHE)) {
        const valeur = fiche[champ];
        const bonne = forme === "liste"
          ? Array.isArray(valeur) && valeur.every((l) => typeof l === "string")
          : typeof valeur === "string";
        if (!bonne) signaler("fiches.json", `« ${nom} » : ${champ} doit etre ${forme === "liste" ? "une liste de textes" : "un texte"}`);
      }
    }
    const fonctions = [mouvement.detection, ...(mouvement.erreurs ?? []), mouvement.amplitude?.[0]];
    for (const fonction of fonctions) {
      if (fonction && !DETECTIONS[fonction]) {
        signaler("mouvements.json", `« ${nom} » nomme ${fonction}, absente de detections.js`);
      }
    }
    // Une position de depart hors vocabulaire n'armerait jamais le compteur :
    // plus une seule repetition comptee, en silence.
    if (mouvement.depart != null && !(["debut", "fin"].includes(mouvement.depart) && mouvement.detection)) {
      signaler("mouvements.json", `« ${nom} » : depart « ${mouvement.depart} » — "debut" ou "fin", et seulement avec une detection`);
    }
    // Un echauffement aussi exercice doit pouvoir etre compte : sans
    // detection, il serait un exercice au chrono, ce qu'un mouvement qui n'est
    // pas un echauffement dit deja.
    if (mouvement.aussi_exercice !== undefined
      && !(mouvement.aussi_exercice === true && mouvement.est_echauffement && mouvement.detection)) {
      signaler("mouvements.json", `« ${nom} » : aussi_exercice vaut true, et seulement sur un echauffement qui a une detection`);
    }
    if (mouvement.en_developpement !== undefined && mouvement.en_developpement !== true) {
      signaler("mouvements.json", `« ${nom} » : en_developpement vaut true, ou n'est pas ecrit`);
    }
    // Un delai trop court laisse passer l'echo d'une detection (une ou deux
    // images, ~0,06 s) ; au-dela du delai par defaut, il ne sert a rien.
    if (mouvement.delai_min_reps != null) {
      const delai = mouvement.delai_min_reps;
      if (!(typeof delai === "number" && delai >= 0.1 && delai <= DELAI_MIN_ENTRE_REPS && mouvement.detection)) {
        signaler("mouvements.json", `« ${nom} » : delai_min_reps « ${delai} » — un nombre de 0,1 a ${DELAI_MIN_ENTRE_REPS} s, et seulement avec une detection`);
      }
    }
    // Le pas de la voix : un entier, sur un mouvement compte (`nombre_a_dire`).
    if (mouvement.voix_tous_les != null) {
      const pas = mouvement.voix_tous_les;
      if (!(Number.isInteger(pas) && pas >= 2 && mouvement.detection)) {
        signaler("mouvements.json", `« ${nom} » : voix_tous_les « ${pas} » — un entier d'au moins 2, et seulement avec une detection`);
      }
    }
    for (const sens of ["variante_facile", "variante_difficile"]) {
      if (mouvement[sens] && !bruts[mouvement[sens]]) {
        signaler("mouvements.json", `« ${nom} » : ${sens} « ${mouvement[sens]} » n'est pas un mouvement`);
      }
    }
    // L'autre cote d'un mouvement unilateral : sans detection des deux cotes,
    // ou sans reciproque, le mauvais cote ne se dirait que dans un sens — en
    // silence dans l'autre (`autre_cote_pour` rend null).
    const autre = mouvement.autre_cote;
    if (autre != null) {
      const en_face = bruts[autre.mouvement];
      if (!en_face) {
        signaler("mouvements.json", `« ${nom} » : autre_cote « ${autre.mouvement} » n'est pas un mouvement`);
      } else {
        if (!mouvement.detection || !en_face.detection) {
          signaler("mouvements.json", `« ${nom} » : autre_cote sans detection des deux cotes`);
        }
        if (en_face.autre_cote?.mouvement !== nom || en_face.autre_cote?.membre !== autre.membre) {
          signaler("mouvements.json", `« ${nom} » : « ${autre.mouvement} » ne le designe pas en retour (meme membre)`);
        }
      }
      if (!["bras", "jambe", "cote"].includes(autre.membre)) {
        signaler("mouvements.json", `« ${nom} » : membre « ${autre.membre} » — "bras", "jambe" ou "cote"`);
      }
    }
  }
  for (const nom of Object.keys(fiches)) {
    if (!bruts[nom]) signaler("fiches.json", `fiche « ${nom} » pour un mouvement inconnu`);
  }

  // --- categories ---
  // Les tables se tiennent (tout muscle a une partie, toute partie une
  // region), et chaque mouvement porte des muscles et une chaine connus :
  // sans eux, il disparait des etiquettes de zone sans que rien ne le dise.
  for (const [cle, muscle] of Object.entries(categories.muscles ?? {})) {
    if (!categories.parties?.[muscle.partie]) signaler("categories.json", `muscle « ${cle} » : partie « ${muscle.partie} » inconnue`);
  }
  for (const [cle, partie] of Object.entries(categories.parties ?? {})) {
    if (!categories.regions?.[partie.region]) signaler("categories.json", `partie « ${cle} » : region « ${partie.region} » inconnue`);
  }
  for (const [cle, region] of Object.entries(categories.regions ?? {})) {
    if (!region.nom) signaler("categories.json", `region « ${cle} » sans nom`);
  }
  if (!categories.plusieurs_regions) signaler("categories.json", "« plusieurs_regions » manque (le nom d'une zone a plusieurs regions)");
  for (const [nom, mouvement] of Object.entries(bruts)) {
    const c = mouvement.categories;
    if (!c || !Array.isArray(c.muscles) || !c.muscles.length) {
      signaler("mouvements.json", `« ${nom} » : categories.muscles manquant`);
      continue;
    }
    for (const muscle of c.muscles) {
      if (!categories.muscles?.[muscle]) signaler("mouvements.json", `« ${nom} » : muscle « ${muscle} » absent de categories.json`);
    }
    if (!categories.chaines?.[c.chaine]) signaler("mouvements.json", `« ${nom} » : chaine « ${c.chaine} » absente de categories.json`);
  }

  // --- seances ---
  const mouvements = avec_fiches(bruts, fiches);
  for (const [nom, blocs] of Object.entries(seances)) {
    for (const probleme of problemes_des_blocs(mouvements, blocs)) signaler("seances.json", `« ${nom} » : ${probleme}`);
  }

  // --- programmes ---
  for (const [cle, programme] of Object.entries(programmes)) {
    if (est_programme_perso(cle)) signaler("programmes.json", `« ${cle} » : le prefixe « ${PREFIXE_PROGRAMME_PERSO} » est reserve aux programmes perso`);
    // Les memes refus que les createurs posent a l'enregistrement : une seule
    // regle, qu'un programme vienne de l'outil maitre ou d'un profil.
    for (const probleme of problemes_du_programme(baremes, programme, seances)) {
      signaler("programmes.json", `« ${cle} » : ${probleme}`);
    }
  }

  // --- videos ---
  const attendues = new Set(Object.keys(bruts).map(fichier_video));
  const videos = existsSync(VIDEOS) ? readdirSync(VIDEOS).filter((f) => f.endsWith(".mp4")) : [];
  for (const fichier of videos) {
    if (!attendues.has(fichier)) {
      signaler("videos/", `${fichier} ne porte le nom d'aucun mouvement (renomme ?) : aucune fiche ne la montrera`);
    }
  }

  if (problemes.length) {
    console.log(`${problemes.length} problemes :\n`);
    for (const p of problemes) console.log(`  - ${p}`);
    process.exitCode = 1;
    return;
  }
  console.log(
    `${Object.keys(bruts).length} mouvements, ${Object.keys(specs).length} baremes, ` +
      `${Object.keys(seances).length} seances, ${Object.keys(programmes).length} programmes, ` +
      `${videos.length} videos : les donnees se tiennent.`
  );
}

main();
