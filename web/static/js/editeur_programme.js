// L'editeur d'un programme, partage par l'application et l'outil maitre.
//
// Un programme, c'est un nom, une description, des **libelles lies a des
// seances** (`seances`, dans l'ordre de la semaine) et des **exigences** —
// une performance a atteindre par exercice. Les exigences sont
// **preremplies** depuis les seances liees (`exigences_depuis_seances`) a
// chaque changement de lien, sans ecraser ce qui a ete ecrit a la main
// (`completer_exigences`) ; elles se corrigent ensuite une par une.
//
// Comme `editeur_seance.js`, il edite et ne decide de rien : la page fournit
// le catalogue des seances choisissables (le fichier dans l'outil maitre, le
// catalogue du profil dans l'application) et fait ce qu'elle veut du
// programme rendu. Les refus sont ceux de `problemes_du_programme`, montres
// en direct.

import {
  completer_exigences, exigences_depuis_seances, problemes_du_programme,
} from "./programmes.js";
import { UNITE_SECONDES } from "./paliers.js";

const echapper = (texte) =>
  String(texte).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/** Un programme vide, de la forme de `programmes.json`. */
export function programme_vide() {
  return { nom: "", description: "", seances: {}, exigences: [] };
}

/** Un libelle libre : `base`, ou `base 2`, `base 3`… s'il est deja pris. */
function libelle_libre(base, pris) {
  if (!pris.includes(base)) return base;
  let n = 2;
  while (pris.includes(`${base} ${n}`)) n += 1;
  return `${base} ${n}`;
}

/**
 * Un editeur de programme dans `racine`.
 *
 * Rend `{programme, problemes, redessiner, definir_catalogue}`.
 * `programme()` rend une copie propre, prete a enregistrer.
 */
export function creer_editeur_programme(racine, { programme, catalogue, baremes, au_changement = () => {} }) {
  const travail = { ...programme_vide(), ...structuredClone(programme ?? {}) };
  // Les liens en liste ordonnee : l'ordre est celui de la semaine, et un
  // dictionnaire ne se reordonne pas sur place.
  let liens = Object.entries(travail.seances ?? {}).map(([libelle, seance]) => ({ libelle, seance }));
  let exigences = (travail.exigences ?? []).map((e) => ({ ...e }));
  let seances = catalogue;

  const en_dictionnaire = () => Object.fromEntries(liens.map(({ libelle, seance }) => [libelle, seance]));
  const courant = () => ({
    nom: travail.nom.trim(),
    description: travail.description.trim(),
    seances: en_dictionnaire(),
    exigences: exigences.map((e) => ({ ...e })),
  });

  /** Recale les exigences sur les seances liees : ce qui est ecrit gagne. */
  function recaler() {
    exigences = completer_exigences(exigences, exigences_depuis_seances(baremes, en_dictionnaire(), seances));
  }

  function changer() {
    dessiner_problemes();
    au_changement();
  }

  function dessiner_problemes() {
    const zone = racine.querySelector(".prog-problemes");
    const liste = problemes_du_programme(baremes, courant(), seances);
    zone.hidden = !liste.length;
    zone.innerHTML = liste.map((p) => `<li>${echapper(p)}</li>`).join("");
  }

  function options_seances(choisie) {
    const noms = Object.keys(seances).sort((a, b) => a.localeCompare(b, "fr"));
    if (choisie && !noms.includes(choisie)) noms.unshift(choisie);
    return noms
      .map((n) => `<option value="${echapper(n)}"${n === choisie ? " selected" : ""}>${echapper(n)}${n in seances ? "" : " (introuvable)"}</option>`)
      .join("");
  }

  function dessiner_liens() {
    const zone = racine.querySelector(".prog-liens");
    zone.replaceChildren();
    liens.forEach((lien, index) => {
      const ligne = document.createElement("div");
      ligne.className = "prog-lien";
      ligne.innerHTML =
        `<div class="champ"><label>Libellé</label><input class="prog-libelle" value="${echapper(lien.libelle)}"></div>` +
        `<div class="champ"><label>Séance</label><select class="prog-seance">${options_seances(lien.seance)}</select></div>` +
        `<button type="button" data-sens="-1" title="Avancer"${index === 0 ? " disabled" : ""}>▲</button>` +
        `<button type="button" data-sens="1" title="Reculer"${index === liens.length - 1 ? " disabled" : ""}>▼</button>` +
        `<button type="button" class="prog-retirer" aria-label="Retirer cette séance">X</button>`;

      ligne.querySelector(".prog-libelle").addEventListener("change", (evenement) => {
        const pris = liens.filter((l) => l !== lien).map((l) => l.libelle);
        const nouveau = libelle_libre(evenement.target.value.trim() || lien.seance, pris);
        // Les exigences portent le libelle : elles le suivent.
        for (const e of exigences) if (e.seance === lien.libelle) e.seance = nouveau;
        lien.libelle = nouveau;
        dessiner();
        changer();
      });
      ligne.querySelector(".prog-seance").addEventListener("change", (evenement) => {
        const ancienne = lien.seance;
        lien.seance = evenement.target.value;
        // Un libelle qui n'etait que le nom de la seance la suit.
        if (lien.libelle === ancienne) {
          const pris = liens.filter((l) => l !== lien).map((l) => l.libelle);
          const nouveau = libelle_libre(lien.seance, pris);
          for (const e of exigences) if (e.seance === lien.libelle) e.seance = nouveau;
          lien.libelle = nouveau;
        }
        // Une autre seance, d'autres exercices : les exigences de ce libelle
        // repartent de la nouvelle seance.
        exigences = exigences.filter((e) => e.seance !== lien.libelle);
        recaler();
        dessiner();
        changer();
      });
      for (const bouton of ligne.querySelectorAll("[data-sens]")) {
        bouton.addEventListener("click", () => {
          const vers = index + Number(bouton.dataset.sens);
          if (vers < 0 || vers >= liens.length) return;
          [liens[index], liens[vers]] = [liens[vers], liens[index]];
          recaler();
          dessiner();
          changer();
        });
      }
      ligne.querySelector(".prog-retirer").addEventListener("click", () => {
        liens.splice(index, 1);
        recaler();
        dessiner();
        changer();
      });
      zone.appendChild(ligne);
    });
  }

  function dessiner_exigences() {
    const zone = racine.querySelector(".prog-exigences");
    zone.replaceChildren();
    if (!exigences.length) {
      zone.innerHTML = `<p class="muet">Ajoute une séance : ses exercices proposent leur performance.</p>`;
      return;
    }
    let libelle_courant = null;
    exigences.forEach((exigence, index) => {
      if (exigence.seance !== libelle_courant) {
        libelle_courant = exigence.seance;
        const titre = document.createElement("h4");
        titre.textContent = libelle_courant;
        zone.appendChild(titre);
      }
      const unite = baremes.unite(exigence.exercice) === UNITE_SECONDES ? "secondes" : "répétitions";
      const ligne = document.createElement("div");
      ligne.className = "prog-exigence";
      ligne.innerHTML =
        `<span class="prog-exercice">${echapper(exigence.exercice)}</span>` +
        `<div class="champ"><label>Séries</label><input type="number" min="1" data-champ="series" value="${exigence.series}"></div>` +
        `<div class="champ"><label>Cible <span>${unite}</span></label><input type="number" min="1" data-champ="cible" value="${exigence.cible}"></div>` +
        `<div class="champ"><label>Poids <span>en kg</span></label><input type="number" min="0" step="0.5" data-champ="poids" value="${exigence.poids ?? 0}"></div>` +
        `<button type="button" class="prog-retirer" aria-label="Retirer cette performance">X</button>`;
      for (const champ of ligne.querySelectorAll("input")) {
        champ.addEventListener("change", () => {
          exigence[champ.dataset.champ] = Number(champ.value) || 0;
          changer();
        });
      }
      ligne.querySelector(".prog-retirer").addEventListener("click", () => {
        exigences.splice(index, 1);
        dessiner_exigences();
        changer();
      });
      zone.appendChild(ligne);
    });
  }

  function dessiner() {
    dessiner_liens();
    dessiner_exigences();
    dessiner_problemes();
  }

  racine.innerHTML =
    `<div class="champ prog-champ"><label>Nom du programme</label><input class="prog-nom" maxlength="60" value="${echapper(travail.nom)}"></div>` +
    `<div class="champ prog-champ"><label>Description</label><textarea class="prog-description" rows="2">${echapper(travail.description)}</textarea></div>` +
    `<h3>Séances de la semaine</h3>` +
    `<div class="prog-liens"></div>` +
    `<div class="actions" style="justify-content:flex-start"><button type="button" class="bouton secondaire prog-ajouter">+ Ajouter une séance</button></div>` +
    `<h3>Performances à atteindre</h3>` +
    `<p class="muet">Chaque exercice suivi propose ce que sa séance prescrit. Corrige-les : ce que tu écris est gardé quand tu ajoutes, retires ou réordonnes des séances.</p>` +
    `<div class="prog-exigences"></div>` +
    `<ul class="prog-problemes erreur" hidden></ul>`;

  racine.querySelector(".prog-nom").addEventListener("input", (evenement) => {
    travail.nom = evenement.target.value;
    changer();
  });
  racine.querySelector(".prog-description").addEventListener("input", (evenement) => {
    travail.description = evenement.target.value;
    changer();
  });
  racine.querySelector(".prog-ajouter").addEventListener("click", () => {
    const noms = Object.keys(seances).sort((a, b) => a.localeCompare(b, "fr"));
    if (!noms.length) return;
    // La premiere seance pas encore liee, a defaut la premiere.
    const seance = noms.find((n) => !liens.some((l) => l.seance === n)) ?? noms[0];
    liens.push({ seance, libelle: libelle_libre(seance, liens.map((l) => l.libelle)) });
    recaler();
    dessiner();
    changer();
  });

  dessiner();
  return {
    programme: courant,
    problemes: () => problemes_du_programme(baremes, courant(), seances),
    redessiner: dessiner,
    definir_catalogue(nouveau) {
      seances = nouveau;
      dessiner();
    },
  };
}
