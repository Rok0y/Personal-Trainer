// L'editeur des blocs d'une seance, partage par l'application et l'outil
// maitre (`dev/createur.html`).
//
// **Il edite, il ne decide de rien.** Les valeurs de depart (celles du moteur
// dans l'application, celles du fichier dans l'outil maitre) et ce que fait
// l'enregistrement (cibles figees, seance perso, fichier a coller)
// appartiennent a la page. Ici : une ligne par bloc, la recopie de la saisie,
// et l'entrelacement recalcule a chaque redessin (`normaliser_entrelacement`).
// Deux editeurs, c'etait deux facons de lire un formulaire, et la premiere
// divergence aurait ete un bloc enregistre different selon la page.
//
// `editeur.css` l'habille : pastille et liseret de couleur du mode, liseret
// d'entrelacement — des reperes qu'on lit d'un coup d'oeil.

import { chaines_entrelacees, paires_entrelacees } from "./circuit.js";
import { est_exercice, propose_en_echauffement } from "./nature.js";
import { normaliser_entrelacement } from "./seance.js";

export const LIBELLES_MODE = {
  repetitions: "Répétitions",
  maintien: "Maintien (secondes)",
  chrono: "Chrono (secondes)",
  amrap: "AMRAP",
  echauffement: "Échauffement",
};

const echapper = (texte) =>
  String(texte).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/** Un bloc neuf : le premier mouvement par ordre alphabetique, 3 x 10. */
export function bloc_par_defaut(mouvements, filtre = null) {
  const noms = Object.keys(mouvements)
    .filter((n) => !filtre || filtre(n))
    .sort((a, b) => a.localeCompare(b, "fr"));
  return {
    exercice: noms[0] ?? Object.keys(mouvements)[0],
    mode: "repetitions",
    series: 3,
    repetitions: 10,
    duree: 0,
    poids: 0,
    repos_entre_series: 30,
    repos_apres: 30,
    commentaire: "",
    entrelace_avec: null,
  };
}

/**
 * Les mouvements proposes, exercices et echauffements separes comme ailleurs.
 *
 * `filtre` (facultatif) restreint la liste — l'outil maitre filtre par
 * categorie. Le mouvement courant reste toujours propose, filtre ou pas.
 */
function options_mouvements(mouvements, courant, filtre) {
  const noms = Object.keys(mouvements)
    .filter((n) => n === courant || !filtre || filtre(n))
    .sort((a, b) => a.localeCompare(b, "fr"));
  // Un mouvement a la fois exercice et echauffement figure dans les deux
  // groupes ; seul le premier porte la selection.
  const groupe = (titre, liste, selection = true) =>
    liste.length
      ? `<optgroup label="${titre}">` +
        liste
          .map((n) => `<option value="${echapper(n)}"${selection && n === courant ? " selected" : ""}>${echapper(n)}</option>`)
          .join("") +
        `</optgroup>`
      : "";

  // Un nom orphelin — venu d'un fichier plus recent, ou renomme — doit rester
  // selectionne : sans cette option, le navigateur choisirait la premiere et
  // remplacerait silencieusement l'exercice a l'enregistrement.
  const inconnu = courant && !(courant in mouvements) ? groupe("Inconnu", [courant]) : "";

  return (
    inconnu +
    groupe("Exercices", noms.filter((n) => est_exercice(mouvements[n]))) +
    groupe(
      "Échauffements",
      noms.filter((n) => propose_en_echauffement(mouvements[n])),
      !est_exercice(mouvements[courant])
    )
  );
}

/**
 * Recopie la saisie dans le bloc.
 *
 * Appelee avant **tout** redessin, sans quoi ce qui vient d'etre tape est
 * perdu : la ligne est reconstruite a chaque reordonnancement.
 *
 * `repetitions` et `duree` sont deux champs distincts, tous deux conserves :
 * c'est ce qui permet de passer d'un mode a l'autre sans perdre la valeur de
 * l'autre unite. Le mode decide seulement lequel sera *joue*.
 */
function lire_ligne(ligne, bloc) {
  bloc.exercice = ligne.querySelector(".exercice").value;
  bloc.mode = ligne.querySelector(".mode").value;
  bloc.poids = Number(ligne.querySelector(".poids").value) || 0;
  bloc.series = Math.max(1, Number(ligne.querySelector(".series").value) || 1);
  bloc.repetitions = Number(ligne.querySelector(".repetitions").value) || 0;
  bloc.duree = Number(ligne.querySelector(".duree").value) || 0;
  bloc.repos_entre_series = Number(ligne.querySelector(".reposEntre").value) || 0;
  bloc.repos_apres = Number(ligne.querySelector(".reposApres").value) || 0;
  bloc.commentaire = ligne.dataset.commentaire ?? "";
}

/**
 * Un editeur de blocs dans `conteneur`.
 *
 * Rend `{blocs, remplacer, redessiner, ajouter_bloc, definir_filtre}`.
 * `blocs()` est la liste de travail elle-meme, recopiee depuis la saisie :
 * une **copie** de ce qu'on a donne, si bien que rien ne bouge dans le
 * catalogue affiche tant que la page n'a pas enregistre. `au_changement` est
 * appele apres chaque modification (une page qui montre un apercu le
 * recalcule).
 */
export function creer_editeur_seance(conteneur, { mouvements, blocs = [], filtre = null, au_changement = () => {} }) {
  let travail = structuredClone(blocs);
  let restriction = filtre;

  /**
   * La place de chaque bloc dans un circuit (une paire en est un de deux) :
   * `tete`, `membre`, ou absent. Lue comme le `Circuit` la lira en seance.
   */
  function roles_dans_les_circuits() {
    const chaines = chaines_entrelacees(paires_entrelacees(
      travail.map((bloc) => bloc.exercice),
      travail.map((bloc) => bloc.entrelace_avec ?? null)
    ));
    const roles = new Map();
    for (const [index, chaine] of chaines) {
      roles.set(index, index === chaine[0] ? { tete: true, taille: chaine.length } : { tete: false });
    }
    return roles;
  }

  function ligne_editeur(bloc, index, role = null) {
    const ligne = document.createElement("div");
    ligne.className = "bloc";
    ligne.dataset.mode = bloc.mode ?? "repetitions";

    const champ = (classe, libelle, unite, valeur, attributs = 'type="number" min="0"') =>
      `<div class="champ"><label>${libelle}` +
      (unite ? `<span>${unite}</span>` : "") +
      `</label><input class="${classe}" ${attributs} value="${echapper(valeur)}"></div>`;

    ligne.innerHTML =
      `<button type="button" class="move-btn" data-sens="-1" title="Monter">▲</button>` +
      `<button type="button" class="move-btn" data-sens="1" title="Descendre">▼</button>` +
      `<button type="button" class="entrelace-btn" title="Entrelacer avec l'exercice suivant">⟷</button>` +
      `<div class="champ"><label>Exercice</label>` +
      `<select class="exercice">${options_mouvements(mouvements, bloc.exercice, restriction)}</select></div>` +
      `<div class="champ"><label><span class="mode-pastille"></span> Mode</label>` +
      `<select class="mode">` +
      Object.entries(LIBELLES_MODE)
        .map(([valeur, libelle]) => `<option value="${valeur}"${valeur === bloc.mode ? " selected" : ""}>${libelle}</option>`)
        .join("") +
      `</select></div>` +
      champ("poids", "Poids", "en kg", bloc.poids ?? 0, 'type="number" min="0" step="0.5"') +
      champ("series", "Séries", "", bloc.series ?? 1, 'type="number" min="1"') +
      champ("repetitions", "Répétitions", "", bloc.repetitions ?? 0) +
      champ("duree", "Durée", "secondes", bloc.duree ?? 0) +
      // Dans un circuit, le repos avant une serie est celui du bloc qu'on va
      // jouer : sur la tete, le repos entre deux tours ; sur un membre, la
      // transition depuis le bloc precedent. Le repos apres le circuit est
      // celui de la tete, et celui d'un membre n'est jamais joue.
      champ("reposEntre", role ? (role.tete ? "Repos entre tours" : "Transition") : "Repos série", "secondes", bloc.repos_entre_series ?? 0) +
      champ("reposApres", "Repos exercice", "secondes", bloc.repos_apres ?? 0,
        role && !role.tete
          ? 'type="number" min="0" disabled title="Le repos après le circuit est celui de son premier bloc"'
          : undefined) +
      `<button type="button" class="sup-btn" aria-label="Supprimer cet exercice">X</button>`;

    // Le commentaire ne se modifie pas ici : on le transporte tel quel pour
    // ne pas l'effacer en enregistrant.
    ligne.dataset.commentaire = bloc.commentaire ?? "";

    // **L'entrelacement est un drapeau « avec le bloc suivant »**, pas un
    // nom : « ? » le pose, et `normaliser_entrelacement` le remplace par le
    // partenaire au redessin.
    const entrelace = ligne.querySelector(".entrelace-btn");
    if (bloc.entrelace_avec) entrelace.classList.add("active");
    entrelace.addEventListener("click", () => {
      if (!entrelace.classList.contains("active") && index >= travail.length - 1) {
        alert("Aucun exercice suivant à entrelacer.");
        return;
      }
      lire_ligne(ligne, bloc);
      bloc.entrelace_avec = entrelace.classList.contains("active") ? null : "?";
      redessiner();
      au_changement();
    });

    for (const bouton of ligne.querySelectorAll(".move-btn")) {
      bouton.addEventListener("click", () => {
        const vers = index + Number(bouton.dataset.sens);
        if (vers < 0 || vers >= travail.length) return;
        lire_ligne(ligne, bloc);
        [travail[index], travail[vers]] = [travail[vers], travail[index]];
        redessiner();
        au_changement();
      });
    }
    ligne.querySelector(".sup-btn").addEventListener("click", () => {
      travail.splice(index, 1);
      redessiner();
      au_changement();
    });

    for (const element of ligne.querySelectorAll("input, select")) {
      element.addEventListener("change", () => {
        const ancien_mode = bloc.mode;
        lire_ligne(ligne, bloc);
        // La pastille et la couleur du mode suivent le <select> sans redessiner.
        ligne.dataset.mode = bloc.mode;
        // Changer d'exercice change le libelle affiche sur le bloc precedent
        // s'il est entrelace avec celui-ci.
        if (bloc.mode !== ancien_mode || element.classList.contains("exercice")) redessiner();
        au_changement();
      });
    }
    return ligne;
  }

  function redessiner() {
    normaliser_entrelacement(travail);
    conteneur.replaceChildren();
    const roles = roles_dans_les_circuits();
    travail.forEach((bloc, index) => {
      const role = roles.get(index) ?? null;
      // Le nombre de tours est celui des series de la tete : il se lit en
      // tete du circuit, avant sa premiere ligne.
      if (role?.tete) {
        const titre = document.createElement("p");
        titre.className = "circuit-titre";
        const tours = bloc.series ?? 1;
        titre.textContent = `${role.taille > 2 ? "Circuit" : "Superset"} · ${tours} ${tours > 1 ? "tours" : "tour"}`;
        conteneur.appendChild(titre);
      }
      const ligne = ligne_editeur(bloc, index, role);
      ligne.classList.toggle("entrelace", Boolean(bloc.entrelace_avec));
      ligne.querySelector('.move-btn[data-sens="-1"]').disabled = index === 0;
      ligne.querySelector('.move-btn[data-sens="1"]').disabled = index === travail.length - 1;
      ligne.querySelector(".entrelace-btn").title = bloc.entrelace_avec
        ? `Entrelacé avec : ${bloc.entrelace_avec}`
        : "Entrelacer avec l'exercice suivant";
      conteneur.appendChild(ligne);

      // La paire se lit sous la ligne : « ⟷ » seul ne dit pas avec quoi.
      if (bloc.entrelace_avec) {
        const paire = document.createElement("p");
        paire.className = "paire";
        paire.textContent = `⟷ séries alternées avec ${bloc.entrelace_avec}`;
        conteneur.appendChild(paire);
      }
    });
  }

  redessiner();
  return {
    blocs: () => normaliser_entrelacement(travail),
    remplacer(blocs_neufs) {
      travail = structuredClone(blocs_neufs ?? []);
      redessiner();
    },
    redessiner,
    ajouter_bloc(bloc = bloc_par_defaut(mouvements, restriction)) {
      travail.push(bloc);
      redessiner();
      au_changement();
    },
    definir_filtre(nouveau) {
      restriction = nouveau;
      redessiner();
    },
  };
}
