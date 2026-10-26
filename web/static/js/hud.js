// Le HUD de seance : l'affichage de l'ecran d'entrainement, partage par
// l'application (`app/index.html`).
//
// **Tout ici est une fonction de `donnees`, et rien d'autre** : l'objet que
// `payload_etat` (`seance.js`) fabrique depuis le `Circuit`. Aucune requete,
// aucune horloge, aucun acces a la camera ne doit entrer dans ce module : c'est
// ce qui le garde lisible, et peignable dans n'importe quel etat. La video de
// la fiche n'y fait pas exception : comme une image, elle se designe par le
// nom du mouvement de `donnees.fiche`, et le navigateur la charge.
//
// L'**execution** d'une commande n'est pas ici : `brancher_commandes(executer)`
// recoit l'action a faire et ne connait que des **noms** de commande (`reset`,
// `passer_pause`, ...) — ceux-la memes que `commandes_autorisees` emploie.

import { resume_series } from "./pastilles.js";
import { jouer_si_visible, montrer_video } from "./videos.js";

const $ = (id) => document.getElementById(id);

//: Circonference des anneaux (r = 70). Le trait se remplit en reduisant
//: `stroke-dashoffset` de cette valeur a zero.
const CIRCONFERENCE = 2 * Math.PI * 70;

//: Raccourcis clavier, pour un ordinateur. Sans effet sur une tablette, ou
//: aucun clavier n'est branche.
const TOUCHES = {
  r: "reset",
  e: "recommencer",
  ArrowLeft: "precedente",
  ArrowRight: "suivante",
  Enter: "terminer",
};

//: Les phases pendant lesquelles les commandes de pause remplacent celles de
//: l'exercice.
const PHASES_DE_PAUSE = ["paused", "recuperation_serie", "repos_exercice"];

//: Ce que le menu des commandes secondaires montrait au dernier passage. Meme
//: role que `fiche_affichee` : la boucle repeint trente fois par seconde, et
//: ce qui est **ouvert par l'utilisateur** ne doit etre repris en main qu'aux
//: instants ou son contenu change.
let menu_affiche = null;

/**
 * Branche les boutons `[data-commande]` et les raccourcis clavier.
 *
 * `executer` recoit un nom de commande et l'applique au circuit.
 */
export function brancher_commandes(executer) {
  document.querySelectorAll("[data-commande]").forEach((bouton) => {
    bouton.addEventListener("click", () => {
      Promise.resolve(executer(bouton.dataset.commande)).catch(console.error);
    });
  });

  document.addEventListener("keydown", (evenement) => {
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) {
      return;
    }
    const commande = TOUCHES[evenement.key];
    if (!commande) return;
    evenement.preventDefault();
    Promise.resolve(executer(commande)).catch(console.error);
  });
}

/**
 * Montre les commandes que l'etat courant autorise, cache les autres.
 *
 * Les boutons portent un `data-contexte` : ceux de la pause n'apparaissent que
 * pendant une pause, ceux de l'exercice le reste du temps. Pause et reprise
 * font exception — elles dependent du statut de la session et non de la phase.
 */
export function actualiser_commandes(autorisees, statut, phase, variante_facile = null) {
  const en_pause = PHASES_DE_PAUSE.includes(statut === "paused" ? statut : phase);
  document.querySelectorAll("[data-commande]").forEach((bouton) => {
    const nom = bouton.dataset.commande;
    // `partout` : une commande qui vaut pendant l'effort comme pendant la
    // recuperation, et qui n'a rien a dire quand elle n'est pas autorisee —
    // la cacher vaut mieux qu'un bouton grise qui n'existe que pour certains
    // mouvements.
    if (bouton.dataset.contexte === "partout") {
      bouton.hidden = !(autorisees && autorisees[nom]);
      bouton.disabled = bouton.hidden;
      if (nom === "variante_facile" && variante_facile) {
        const texte = `Plus facile : ${variante_facile}`;
        if (bouton.textContent !== texte) bouton.textContent = texte;
      }
      return;
    }
    bouton.hidden = bouton.dataset.contexte === "pause" ? !en_pause : en_pause;
    bouton.disabled =
      nom === "pause"
        ? statut !== "running"
        : nom === "reprendre"
          ? statut !== "paused"
          : !(autorisees && autorisees[nom]);
  });

  const menu = $("seriesMenu");
  if (!menu) return;

  // Un repli vide reste un bouton cliquable qui n'ouvre rien : on cache le
  // menu entier quand la phase courante ne lui laisse aucune commande.
  const utiles = [...menu.querySelectorAll("[data-commande]")].some((b) => !b.hidden);
  menu.hidden = !utiles;

  // Referme **au changement de phase**, pas a chaque image : refermer en
  // continu arracherait le menu des doigts de quelqu'un qui vient de
  // l'ouvrir, et le laisser ouvert d'une phase a l'autre afficherait des
  // commandes qui viennent d'etre cachees.
  const repere = `${en_pause ? "pause" : "exercice"}|${utiles}`;
  if (repere !== menu_affiche) {
    menu_affiche = repere;
    menu.open = false;
  }
}

// ---------------------------------------------------------------------------
// Affichage de l'entrainement (multi-modes)
// ---------------------------------------------------------------------------
// Le mode actif, les valeurs et l'etat de l'exercice viennent tous de
// `donnees.mode` : ces fonctions se contentent d'afficher, aucune regle
// metier ne doit vivre ici.
//
// Pour ajouter un mode : ecrire `afficher_mode_xxx`, l'inscrire dans
// `MODES_AFFICHES`, et ajouter le bloc `.workout-block--xxx` dans
// `app/index.html`.

let dernier_reps = null;
let dernier_maintien_entier = null;

/** Anime un nombre et son anneau lumineux, reutilise par tous les modes. */
function declencher_impact(id_valeur, id_anneau) {
  const valeur = $(id_valeur);
  const anneau = id_anneau ? $(id_anneau) : null;
  if (!valeur) return;

  valeur.classList.remove("hit");
  if (anneau) anneau.classList.remove("hit");
  void valeur.offsetWidth; // force le reflow pour rejouer l'animation
  valeur.classList.add("hit");
  if (anneau) anneau.classList.add("hit");
}

/** MODE_REPETITIONS : « 8 / 12 repetitions ». */
function afficher_mode_repetitions(donnees) {
  const actuel = Number(donnees.repetitions) || 0;
  const cible = Number(donnees.repetitions_cibles) || 0;

  const libelle = String(cible);
  if ($("repsCible").textContent.trim() !== libelle) {
    $("repsCible").textContent = libelle;
  }

  if (dernier_reps !== null && actuel !== dernier_reps) {
    declencher_impact("reps", "ring");
  }
  $("reps").textContent = actuel;
  dernier_reps = actuel;

  const part = cible > 0 ? Math.max(0, Math.min(100, (actuel / cible) * 100)) : 0;
  $("repsProgressFill").style.width = `${part}%`;
}

//: Les jetons de posture qui signalent une position perdue. Seule cette liste
//: doit changer si un detecteur en emploie d'autres.
const POSTURE_CASSEE = ["casse", "cassee", "incorrect", "mauvaise"];

/** MODE_MAINTIEN : « 7 / 15 secondes ». */
function afficher_mode_maintien(donnees) {
  const actuel = Number(donnees.temps_maintien) || 0;
  const cible = Number(donnees.duree_maintien) || 0;
  const arrondi = Math.floor(actuel);

  if (dernier_maintien_entier !== null && arrondi !== dernier_maintien_entier) {
    declencher_impact("maintienTemps", "maintienRing");
  }
  $("maintienTemps").textContent = arrondi;
  $("maintienTempsTexte").textContent = arrondi;
  $("maintienDureeTexte").textContent = cible;
  dernier_maintien_entier = arrondi;

  const part = cible > 0 ? Math.max(0, Math.min(100, (actuel / cible) * 100)) : 0;
  $("maintienProgressFill").style.width = `${part}%`;

  const statut = $("maintienStatus");
  const cassee = POSTURE_CASSEE.includes(String(donnees.stage || "").toLowerCase());
  statut.textContent = cassee ? "Position incorrecte" : "Maintenir la position";
  statut.classList.toggle("maintien-status--erreur", cassee);
}

/** MODE_CHRONO : « 45 secondes restantes ». */
function afficher_mode_chrono(donnees) {
  $("chronoTemps").textContent = Math.max(0, Math.round(Number(donnees.temps_chrono) || 0));
}

/**
 * MODE_AMRAP : « 12 repetitions en 60 secondes », et l'objectif du moteur
 * quand il y en a un — le bareme d'un AMRAP compte des repetitions, et c'est
 * le nombre a battre.
 */
function afficher_mode_amrap(donnees) {
  $("amrapReps").textContent = Number(donnees.repetitions) || 0;
  const objectif = Number(donnees.repetitions_cibles) || 0;
  $("amrapObjectif").textContent = objectif > 0 ? ` · objectif ${objectif}` : "";
  $("amrapTempsRestant").textContent = Math.max(
    0,
    Math.round(Number(donnees.temps_amrap_restant) || 0)
  );
}

/** MODE_ECHAUFFEMENT : « 18 / 30 secondes ». */
function afficher_mode_echauffement(donnees) {
  const actuel = Number(donnees.temps_echauffement) || 0;
  const cible = Number(donnees.duree_echauffement) || 0;

  // Le gros chiffre decompte le restant : pendant un echauffement on veut
  // savoir quand ca s'arrete, pas depuis combien de temps ca dure.
  $("echauffementTemps").textContent = Math.max(0, Math.ceil(cible - actuel));
  $("echauffementTempsTexte").textContent = Math.floor(actuel);
  $("echauffementDureeTexte").textContent = cible;

  const part = cible > 0 ? Math.max(0, Math.min(100, (actuel / cible) * 100)) : 0;
  $("echauffementProgressFill").style.width = `${part}%`;
}

const MODES_AFFICHES = {
  repetitions: afficher_mode_repetitions,
  maintien: afficher_mode_maintien,
  chrono: afficher_mode_chrono,
  amrap: afficher_mode_amrap,
  echauffement: afficher_mode_echauffement,
};

function afficher_entrainement(donnees) {
  // Un mode inconnu retombe sur les repetitions plutot que de laisser
  // l'interface vide.
  const mode = donnees.mode in MODES_AFFICHES ? donnees.mode : "repetitions";
  $("workoutCard").dataset.mode = mode;
  MODES_AFFICHES[mode](donnees);
}

function afficher_commentaire(donnees) {
  const carte = $("commentCard");
  const texte = $("exerciseComment");
  if (!carte || !texte) return;
  texte.textContent = donnees.commentaire_exercice || "";
  carte.hidden = !donnees.commentaire_exercice;
}

// ---------------------------------------------------------------------------
// Bandeaux, badges, fiche
// ---------------------------------------------------------------------------

/** Deux bandeaux et non un : l'erreur reproche, la consigne dit quoi faire. */
function afficher_bandeau(id_alerte, id_message, message) {
  const alerte = $(id_alerte);
  if (message) {
    $(id_message).textContent = message;
    alerte.classList.add("visible");
  } else {
    alerte.classList.remove("visible");
  }
}

//: Les consignes ne changent qu'au changement d'exercice : redessiner la liste
//: a chaque image reconstruirait le DOM dix fois par seconde pour rien. La cle
//: inclut **la phase**, parce qu'un meme nom n'affiche pas la meme chose selon
//: qu'on le fait ou qu'on s'apprete a le faire — cas reel sur un superset, ou
//: le prochain exercice peut etre celui qu'on vient de quitter.
let fiche_affichee = null;

//: Et un second repere, pour le repli. *Quoi afficher* et *ouvert ou replie*
//: ne changent pas aux memes instants : entre `exercice` et
//: `recuperation_serie` du meme mouvement, la cle de contenu ne bouge pas —
//: c'est tout l'interet de la memoisation — alors que le repli, lui, doit
//: s'inverser. Elargir `fiche_affichee` a la phase reconstruirait la liste a
//: chaque transition pour ne changer qu'un booleen.
let fiche_en_effort = null;

//: La video de la carte se lit quand on la voit et seulement alors : repliee
//: pendant l'effort, elle ne decode pas. `toggle` couvre les deux ouvertures,
//: par `afficher_fiche` comme au doigt. Branche une fois.
let video_de_fiche_branchee = false;

function lire_video_de_fiche() {
  const carte = $("ficheCard");
  jouer_si_visible($("ficheVideo").querySelector("video"), carte.open && !carte.hidden);
}

function afficher_fiche(donnees) {
  const carte = $("ficheCard");
  const liste = $("ficheInstructions");
  const etiquette = $("ficheLabel");
  if (!video_de_fiche_branchee) {
    video_de_fiche_branchee = true;
    carte.addEventListener("toggle", lire_video_de_fiche);
  }

  // Repliee pendant l'effort, depliee des qu'on souffle : c'est la meme raison
  // qui vaut a `.right-column` de passer au-dessus du voile de repos (z-index
  // 7 contre 6) — pendant une pause on a le temps de lire, pendant une serie
  // non. Pose **au changement** et jamais a chaque image, sinon on refermerait
  // sous les doigts de quelqu'un qui vient d'ouvrir.
  const en_effort = donnees.phase === "exercice";
  if (en_effort !== fiche_en_effort) {
    fiche_en_effort = en_effort;
    carte.open = !en_effort;
  }

  // Entre deux exercices on prepare le suivant ; partout ailleurs on relit
  // celui qu'on est en train de faire.
  const prepare = donnees.phase === "repos_exercice" && donnees.fiche_suivante;
  const fiche = prepare ? donnees.fiche_suivante : donnees.fiche;

  const cle = `${fiche && fiche.nom}|${prepare ? "suivant" : "courant"}`;
  if (cle === fiche_affichee) return;
  fiche_affichee = cle;

  // En preparation, la mise en place passe devant : c'est le placement camera
  // et le materiel qui se decident avant la premiere repetition, et la
  // premiere cause d'un comptage qui ne demarre pas.
  const consignes = prepare
    ? ((fiche && fiche.mise_en_place) || []).concat((fiche && fiche.instructions) || [])
    : (fiche && fiche.instructions) || [];

  etiquette.textContent = prepare
    ? `À préparer : ${(fiche && fiche.nom) || ""}`
    : "Consignes";

  liste.replaceChildren();
  consignes.forEach((consigne) => {
    const element = document.createElement("li");
    element.textContent = consigne;
    liste.appendChild(element);
  });
  // La video suit la meme cle que les consignes : pendant `repos_exercice`,
  // c'est celle du prochain mouvement. Une carte sans consigne se montre
  // quand meme si une video arrive ; sans l'une ni l'autre, rien.
  montrer_video($("ficheVideo"), (fiche && fiche.nom) || null, () => {
    carte.hidden = false;
    lire_video_de_fiche();
  });
  // Apres `montrer_video` : une video deja chargee sous le meme nom garde son
  // cadre visible, et ne rappelle pas le chargement.
  carte.hidden = consignes.length === 0 && $("ficheVideo").hidden;
}

/** Remplace un texte avec un petit fondu, et seulement s'il a change. */
function changer_champ(id, valeur, classe = "changing") {
  const element = $(id);
  if (!element || element.textContent.trim() === String(valeur)) return;
  element.classList.add(classe);
  setTimeout(() => {
    element.textContent = String(valeur);
    element.classList.remove(classe);
  }, 150);
}

/** Meme chose, mais c'est le badge entier qui s'anime autour de la valeur. */
function changer_badge(id_badge, id_valeur, valeur) {
  const badge = $(id_badge);
  const element = $(id_valeur);
  if (!element || element.textContent.trim() === String(valeur)) return;
  badge.classList.add("changing");
  setTimeout(() => {
    element.textContent = String(valeur);
    badge.classList.remove("changing");
  }, 150);
}

function formater_temps(secondes) {
  const total = Math.max(0, Math.round(Number(secondes) || 0));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

// ---------------------------------------------------------------------------
// Barre de progression de la seance
// ---------------------------------------------------------------------------

let signature_progression = "";

// Une seule barre. Le voile de repos en portait une copie, du temps ou il
// couvrait l'ecran d'un fond opaque ; devenu un panneau a gauche, il laisse
// voir celle du bas — et la copie, centree sur toute la largeur, passait
// sous le compteur de la colonne droite.
const CONTENEURS_PROGRESSION = ["sessionProgressSegments"];

//: Le groupe dont la bulle de detail est ouverte (son rang dans la liste
//: affichee), ou null. Un etat d'affichage ouvert **par l'utilisateur**, comme
//: le menu des commandes : la boucle le repeint, et ne le referme qu'a un
//: changement de liste (la bascule echauffement -> exercices).
let groupe_detaille = null;

//: La barre ou le toucher a eu lieu (`CONTENEURS_PROGRESSION`) : une bulle ne
//: s'ouvre que dans la barre touchee.
let barre_detaillee = null;

//: Ce que la barre a peint en dernier : un toucher ouvre la bulle tout de
//: suite, sans attendre l'image suivante.
let derniere_progression = null;

let bulle_branchee = false;

function initialiser_progression(exercices) {
  const signature = JSON.stringify((exercices || []).map((e) => [e.nom, e.series]));
  if (signature === signature_progression) return;

  CONTENEURS_PROGRESSION.forEach((id) => {
    const conteneur = $(id);
    conteneur.replaceChildren();
    (exercices || []).forEach((exercice, rang) => {
      const groupe = document.createElement("div");
      groupe.className = "progress-exercise";
      groupe.dataset.rang = String(rang);
      const etiquette = document.createElement("span");
      etiquette.className = "progress-exercise-label";
      etiquette.textContent = exercice.nom;
      const series = document.createElement("div");
      series.className = "progress-series";
      for (let index = 0; index < Number(exercice.series || 0); index++) {
        const segment = document.createElement("span");
        segment.className = "progress-segment";
        series.appendChild(segment);
      }
      groupe.append(etiquette, series);
      conteneur.appendChild(groupe);
    });
    const bulle = document.createElement("div");
    bulle.className = "progress-bulle";
    bulle.hidden = true;
    conteneur.appendChild(bulle);
  });
  signature_progression = signature;
  groupe_detaille = null;
  barre_detaillee = null;
}

/**
 * Un toucher sur un groupe ouvre sa bulle ; un second toucher, ou un toucher
 * ailleurs, la ferme. Delegue au document une fois pour toutes : les groupes
 * sont recrees a chaque changement de liste.
 */
function brancher_bulle() {
  if (bulle_branchee) return;
  bulle_branchee = true;
  document.addEventListener("click", (evenement) => {
    if (evenement.target.closest?.(".progress-bulle")) return;
    const groupe = evenement.target.closest?.(".progress-exercise");
    const rang = groupe ? Number(groupe.dataset.rang) : null;
    const barre = groupe?.parentElement.id ?? null;
    const meme = rang === groupe_detaille && barre === barre_detaillee;
    groupe_detaille = rang !== null && !meme ? rang : null;
    barre_detaillee = groupe_detaille === null ? null : barre;
    if (derniere_progression) peindre_bulles(...derniere_progression);
  });
}

/** La cible d'une serie, dans l'unite que son mode joue. */
function cible_de(exercice) {
  return ["maintien", "chrono", "amrap", "echauffement"].includes(exercice.mode)
    ? `${exercice.duree} s`
    : `${exercice.repetitions}`;
}

function echapper(texte) {
  const noeud = document.createElement("span");
  noeud.textContent = texte;
  return noeud.innerHTML;
}

/**
 * La bulle du groupe ouvert : le nom entier, puis une pastille par serie —
 * faite (les pastilles de l'historique, `resume_series`), en cours (le compte
 * qui monte), a faire (sa cible).
 */
function contenu_bulle(exercice, etat, repetitions_en_direct) {
  const pastilles = etat.series.map((serie, index) => {
    if (serie) return resume_series([{ ...serie, poids: exercice.poids }], exercice.mode);
    if (etat.en_cours === index + 1) {
      const direct = ["repetitions", "amrap"].includes(exercice.mode)
        ? `${Number(repetitions_en_direct) || 0}/${exercice.repetitions}`
        : cible_de(exercice);
      return `<span class="serie-puce en-cours">${direct}</span>`;
    }
    return `<span class="serie-puce a-faire">${cible_de(exercice)}</span>`;
  });
  const charge = exercice.poids ? ` · ${exercice.poids} kg` : "";
  return (
    `<strong>${echapper(exercice.nom)}</strong>` +
    `<small>${etat.series.length} × ${cible_de(exercice)}${charge}</small>` +
    `<div class="series-detail">${pastilles.join("")}</div>`
  );
}

function peindre_bulles(exercices, etats, repetitions_en_direct) {
  CONTENEURS_PROGRESSION.forEach((id) => {
    const conteneur = $(id);
    const bulle = conteneur.querySelector(".progress-bulle");
    if (!bulle) return;
    const rang = id === barre_detaillee ? groupe_detaille : null;
    conteneur.querySelectorAll(".progress-exercise").forEach((groupe) => {
      groupe.classList.toggle("detaille", Number(groupe.dataset.rang) === rang);
    });
    const exercice = rang === null ? null : exercices[rang];
    const etat = rang === null ? null : etats[rang];
    if (!exercice || !etat) {
      bulle.hidden = true;
      return;
    }
    // Repeinte a chaque image, puisque le compte bouge, mais ecrite seulement
    // quand elle change.
    const html = contenu_bulle(exercice, etat, repetitions_en_direct);
    if (bulle.innerHTML !== html) bulle.innerHTML = html;
    bulle.hidden = false;
    // Au-dessus de son groupe, sans deborder de la barre.
    const groupe = conteneur.querySelector(`.progress-exercise[data-rang="${rang}"]`);
    const gauche = groupe.offsetLeft + groupe.offsetWidth / 2 - bulle.offsetWidth / 2;
    const max = conteneur.clientWidth - bulle.offsetWidth;
    bulle.style.left = `${Math.max(0, Math.min(max, gauche))}px`;
  });
}

/**
 * Deux barres, jamais deux en meme temps.
 *
 * Celle de l'echauffement cede la place a celle des exercices des que le
 * premier exercice comptabilise commence. Meme fonction, deux jeux de donnees
 * — la memoisation d'`initialiser_progression` portant sur la liste, la
 * bascule redessine d'elle-meme.
 *
 * **Chaque segment se lit dans l'etat de sa serie** (`etat_des_series`), et
 * non dans un compte a plat : en superset, la barre remplissait le premier
 * exercice deux fois plus vite et laissait le second vide. Desormais le
 * segment orange saute d'un exercice a l'autre, comme la seance.
 */
function afficher_progression(exercices, etats, echauffement, repetitions_en_direct) {
  brancher_bulle();
  initialiser_progression(exercices);
  CONTENEURS_PROGRESSION.forEach((id) => {
    const conteneur = $(id);
    conteneur.classList.toggle("progress-echauffement", Boolean(echauffement));
    conteneur.querySelectorAll(".progress-exercise").forEach((groupe) => {
      const etat = (etats || [])[Number(groupe.dataset.rang)];
      groupe.querySelectorAll(".progress-segment").forEach((segment, index) => {
        const serie = etat?.series[index] ?? null;
        segment.classList.toggle("complete", serie !== null);
        segment.classList.toggle("ratee", serie !== null && serie.completee === false);
        segment.classList.toggle("active", serie === null && etat?.en_cours === index + 1);
      });
    });
  });
  derniere_progression = [exercices || [], etats || [], repetitions_en_direct];
  peindre_bulles(...derniere_progression);
}

// ---------------------------------------------------------------------------
// Phase : preparation / repos / exercice
// ---------------------------------------------------------------------------

/**
 * Ce que le voile annonce comme prochaine etape, en deux parts : `serie`
 * (ou l'on en est, ecrit petit) et `cible` (ce qu'on fera, ecrit grand avec
 * la charge — c'est ce qu'on lit de loin pour preparer son haltere).
 */
function consigne_prochaine_etape(etape) {
  const serie =
    etape.nombre_total_series !== undefined
      ? `Série ${etape.serie_actuelle} de ${etape.nombre_total_series}`
      : `${etape.series} ${etape.series > 1 ? "séries" : "série"}`;

  switch (etape.mode) {
    case "maintien":
      return { serie, cible: `${etape.duree} s de maintien` };
    case "chrono":
      return { serie, cible: `${etape.duree} s` };
    case "amrap":
      return {
        serie,
        cible: `AMRAP ${etape.duree} s` + (etape.repetitions > 0 ? ` · ${etape.repetitions} reps` : ""),
      };
    case "echauffement":
      return { serie: "Échauffement", cible: `${etape.duree} s` };
    default:
      return { serie, cible: `${etape.repetitions} reps` };
  }
}

function afficher_phase(donnees) {
  const voile = $("restOverlay");
  const etape = donnees.prochaine_etape || {};

  if (donnees.phase === "termine" || donnees.phase === "exercice") {
    voile.classList.remove("visible");
    return;
  }

  voile.classList.add("visible");

  if (etape.exercice) {
    $("restNextName").textContent = etape.exercice;
    $("restNextName").classList.remove("hidden-mode");
    $("restNextLabel").classList.remove("hidden-mode");
    // Deux lignes : ce qu'on fera, puis l'haltere a prendre, chacune lisible
    // de loin. Ecrit seulement quand il change : la boucle repeint a chaque
    // image.
    const { serie, cible } = consigne_prochaine_etape(etape);
    const html =
      `<span class="rest-serie">${serie}</span>` +
      `<span class="rest-cible">${cible}` +
      (etape.poids ? `<span class="rest-charge">${etape.poids} kg</span>` : "") +
      `</span>`;
    if ($("restNext").innerHTML !== html) $("restNext").innerHTML = html;
  } else {
    $("restNextName").textContent = "";
    $("restNextName").classList.add("hidden-mode");
    $("restNextLabel").classList.add("hidden-mode");
    $("restNext").textContent = "Fin de séance";
  }

  if (donnees.phase === "preparation") {
    $("restTitle").textContent = "Préparation";
    $("breatheCircle").classList.add("hidden-mode");
    $("prepRingWrap").classList.add("active");

    const part = Math.max(0, Math.min(100, Number(donnees.progression_preparation) || 0));
    $("prepRingProgress").style.strokeDashoffset = CIRCONFERENCE * (1 - part / 100);
    $("prepPercent").textContent = `${Math.round(part)}%`;
    return;
  }

  // Repos ou toute autre phase de pause : respiration et compte a rebours.
  $("restTitle").textContent =
    donnees.phase === "recuperation_serie"
      ? "Récupération"
      : donnees.phase === "repos_exercice"
        ? "Repos"
        : String(donnees.phase).charAt(0).toUpperCase() + String(donnees.phase).slice(1);
  $("breatheCircle").classList.remove("hidden-mode");
  $("prepRingWrap").classList.remove("active");
  $("restTime").textContent = formater_temps(donnees.temps_repos_restant);
}

// ---------------------------------------------------------------------------
// Bulle de progression du maintien
// ---------------------------------------------------------------------------

let dernier_maintien_termine = false;

function creer_particules() {
  const eclat = $("burst");
  eclat.replaceChildren();
  const nombre = 14;

  for (let index = 0; index < nombre; index++) {
    const particule = document.createElement("span");
    particule.className = "particle";

    const angle = (360 / nombre) * index + (Math.random() * 16 - 8);
    const distance = 55 + Math.random() * 35;
    const radians = (angle * Math.PI) / 180;

    particule.style.setProperty("--tx", `${Math.cos(radians) * distance}px`);
    particule.style.setProperty("--ty", `${Math.sin(radians) * distance}px`);

    eclat.appendChild(particule);
  }
}

function declencher_eclatement() {
  const conteneur = $("holdContainer");
  const bulle = $("holdBubble");

  bulle.classList.add("pop");
  conteneur.classList.add("flash");
  creer_particules();

  setTimeout(() => {
    bulle.classList.remove("pop");
    conteneur.classList.remove("flash", "visible");
    bulle.style.transform = "scale(0.22)";
    $("holdRingProgress").style.strokeDashoffset = CIRCONFERENCE;
    $("holdPercent").textContent = "0%";
    $("burst").replaceChildren();
  }, 600);
}

function afficher_maintien(progression, termine) {
  const conteneur = $("holdContainer");
  const bulle = $("holdBubble");
  const part = Math.max(0, Math.min(100, Number(progression) || 0));

  // L'eclatement se declenche une seule fois, a l'instant ou le maintien se
  // termine.
  if (termine && !dernier_maintien_termine) {
    dernier_maintien_termine = termine;
    declencher_eclatement();
    return;
  }
  dernier_maintien_termine = termine;

  // Pendant l'eclatement, on laisse l'animation faire son travail.
  if (bulle.classList.contains("pop")) return;

  conteneur.classList.toggle("visible", part > 0);
  $("holdRingProgress").style.strokeDashoffset = CIRCONFERENCE * (1 - part / 100);
  bulle.style.transform = `scale(${0.22 + (part / 100) * 0.78})`;
  $("holdPercent").textContent = `${Math.round(part)}%`;
}

// ---------------------------------------------------------------------------
// Le point d'entree
// ---------------------------------------------------------------------------

/**
 * Peint tout le HUD a partir d'un etat de seance.
 *
 * `donnees` est l'objet que `payload_etat` fabrique : c'est **le** contrat de
 * l'ecran, et y ajouter un champ se fait des deux cotes de ce contrat
 * (`payload_etat` qui l'ecrit, `peindre_hud` qui le lit).
 */
export function peindre_hud(donnees) {
  actualiser_commandes(
    donnees.commandes_autorisees,
    donnees.statut_session,
    donnees.phase,
    donnees.variante_facile,
  );

  // `dans_echauffement` et non « reste-t-il des echauffements ? » : une seance
  // qui n'en a aucun doit montrer la barre des exercices des la premiere image.
  const echauffement =
    Boolean(donnees.dans_echauffement) && (donnees.echauffements || []).length > 0;
  afficher_progression(
    echauffement ? donnees.echauffements : donnees.exercices,
    echauffement ? donnees.series_echauffements : donnees.series_exercices,
    echauffement,
    donnees.repetitions
  );

  const minutes = Math.floor(Math.max(0, Number(donnees.duree_session) || 0) / 60);
  $("sessionDuration").textContent = `${minutes} min`;
  $("overlaySessionDuration").textContent = formater_temps(donnees.duree_session);

  changer_badge("exerciseBadge", "exercice", donnees.exercice_actuel);
  changer_badge("seriesBadge", "series", `${donnees.serie_actuelle} / ${donnees.nombre_series}`);
  changer_badge(
    "weightBadge",
    "weight",
    donnees.poids ? `${donnees.poids} kg` : "—"
  );

  // Une faute de forme n'existe que pendant l'effort. `erreur` n'est recalculee
  // qu'en phase exercice, donc la derniere de la serie restait affichee toute
  // la pause — a reprocher des coudes ecartes a quelqu'un qui se repose.
  const en_effort = donnees.phase === "exercice" && donnees.statut_session === "running";
  afficher_bandeau("errorAlert", "errorMessage", en_effort ? donnees.erreur : null);
  afficher_bandeau("consigneAlert", "consigneMessage", donnees.consigne);
  afficher_fiche(donnees);

  changer_champ("position", donnees.position_actuelle || "Aucune");
  // `etape_libelle` est la traduction francaise de `stage`, qui reste le jeton
  // brut du detecteur : c'est le libelle qu'on montre, jamais « debut ».
  changer_champ("stage", donnees.etape_libelle || donnees.stage || "Aucune");

  afficher_entrainement(donnees);
  afficher_commentaire(donnees);
  afficher_maintien(donnees.progression_maintien || 0, donnees.maintien_termine || false);
  afficher_phase(donnees);
}
