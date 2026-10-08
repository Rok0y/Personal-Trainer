// Le HUD de seance : l'affichage de l'ecran d'entrainement, partage par
// l'application (`app/index.html`).
//
// **Tout ici est une fonction de `donnees`, et rien d'autre** : l'objet que
// `payload_etat` (`seance.js`) fabrique depuis le `Circuit`. Aucune requete,
// aucune horloge, aucun acces a la camera ne doit entrer dans ce module : c'est
// ce qui le garde lisible, et peignable dans n'importe quel etat.
//
// L'**execution** d'une commande n'est pas ici : `brancher_commandes(executer)`
// recoit l'action a faire et ne connait que des **noms** de commande (`reset`,
// `passer_pause`, ...) — ceux-la memes que `commandes_autorisees` emploie.

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

/** MODE_AMRAP : « 12 repetitions en 60 secondes ». */
function afficher_mode_amrap(donnees) {
  $("amrapReps").textContent = Number(donnees.repetitions) || 0;
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

function afficher_fiche(donnees) {
  const carte = $("ficheCard");
  const liste = $("ficheInstructions");
  const etiquette = $("ficheLabel");

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
  carte.hidden = consignes.length === 0;
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

const CONTENEURS_PROGRESSION = ["sessionProgressSegments", "overlaySessionProgressSegments"];

function initialiser_progression(exercices) {
  const signature = JSON.stringify(exercices || []);
  if (signature === signature_progression) return;

  CONTENEURS_PROGRESSION.forEach((id) => {
    const conteneur = $(id);
    conteneur.replaceChildren();
    (exercices || []).forEach((exercice) => {
      const groupe = document.createElement("div");
      groupe.className = "progress-exercise";
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
  });
  signature_progression = signature;
}

/**
 * Deux barres, jamais deux en meme temps.
 *
 * Celle de l'echauffement cede la place a celle des exercices des que le
 * premier exercice comptabilise commence. Meme fonction, deux jeux de donnees
 * — la memoisation d'`initialiser_progression` portant sur la liste, la
 * bascule redessine d'elle-meme.
 */
function afficher_progression(exercices, series_terminees, echauffement) {
  initialiser_progression(exercices);
  const terminees = Number(series_terminees) || 0;
  CONTENEURS_PROGRESSION.forEach((id) => {
    const conteneur = $(id);
    conteneur.classList.toggle("progress-echauffement", Boolean(echauffement));
    conteneur.querySelectorAll(".progress-segment").forEach((segment, index) => {
      segment.classList.toggle("complete", index < terminees);
      segment.classList.toggle("active", index === terminees);
    });
  });
}

// ---------------------------------------------------------------------------
// Phase : preparation / repos / exercice
// ---------------------------------------------------------------------------

/** Ce que le voile annonce comme prochaine etape. */
function consigne_prochaine_etape(etape) {
  const serie =
    etape.nombre_total_series !== undefined
      ? `Série ${etape.serie_actuelle} de ${etape.nombre_total_series}`
      : `${etape.series} ${etape.series > 1 ? "séries" : "série"}`;

  switch (etape.mode) {
    case "maintien":
      return `${serie} × ${etape.duree} s de maintien`;
    case "chrono":
      return `${serie} × ${etape.duree} s`;
    case "amrap":
      return `${serie} × AMRAP ${etape.duree} s`;
    case "echauffement":
      return `Échauffement · ${etape.duree} s`;
    default:
      return `${serie} × ${etape.repetitions} reps`;
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
    $("restNext").innerHTML = `
      ${consigne_prochaine_etape(etape)}
      ${etape.poids ? `<br>${etape.poids} kg` : ""}
    `;
  } else {
    $("restNextName").textContent = "";
    $("restNextName").classList.add("hidden-mode");
    $("restNextLabel").classList.add("hidden-mode");
    $("restNext").innerHTML = "Fin de séance";
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
    echauffement ? donnees.echauffements_termines : donnees.series_terminees,
    echauffement
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
