// La lecture d'une fiche de suivi d'un ajout d'exercice (`docs/exercices/`).
//
// La fiche est la source : un Markdown que le protocole `ajouter-exercice`
// coche au fil de l'eau, versionne avec le travail. Ce module en tire ce que
// `dev/suivi.html` montre — ou en est l'ajout, quelle est la prochaine case —
// sans rien stocker a cote : une seconde liste d'etapes finirait par dire
// autre chose que la fiche.
//
// Il ne lit que le sous-ensemble de Markdown que les fiches emploient :
// titres, cases a cocher, puces, tableaux, paragraphes, et en ligne `code` et
// **gras**. Le reste passe en paragraphe, echappe.

//: Le titre d'une fiche nomme son mouvement ; un mouvement unilateral en
//: nomme deux, separes par ce signe (« Fente droite / Fente gauche »).
export const SEPARATEUR_MOUVEMENTS = " / ";

export function echapper(texte) {
  return String(texte)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/** Le HTML d'un texte en ligne : `code` et **gras**, tout le reste echappe. */
export function en_ligne(texte) {
  // Le code d'abord : ce qu'il contient ne se met jamais en forme.
  return String(texte)
    .split(/(`[^`]*`)/)
    .map((morceau) => (morceau.startsWith("`") && morceau.endsWith("`") && morceau.length > 1
      ? `<code>${echapper(morceau.slice(1, -1))}</code>`
      : echapper(morceau).replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")))
    .join("");
}

// Les cellules d'une ligne de tableau. Une barre dans du code n'en separe pas.
function cellules(ligne) {
  const sortie = [];
  let courant = "";
  let dans_code = false;
  for (const c of ligne.trim().replace(/^\|/, "").replace(/\|$/, "")) {
    if (c === "`") dans_code = !dans_code;
    if (c === "|" && !dans_code) {
      sortie.push(courant.trim());
      courant = "";
    } else {
      courant += c;
    }
  }
  sortie.push(courant.trim());
  return sortie;
}

const SEPARATEUR_TABLEAU = /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$/;

/**
 * Les blocs d'un Markdown, dans l'ordre : `titre` (niveau, texte), `case`
 * (fait, texte), `puce` (texte), `tableau` (entete, lignes), `paragraphe`
 * (texte). Les lignes d'un paragraphe sont jointes par une espace.
 */
export function blocs(markdown) {
  const sortie = [];
  let paragraphe = null;
  let tableau = null;
  const clore = () => {
    if (paragraphe) sortie.push({ type: "paragraphe", texte: paragraphe.join(" ") });
    if (tableau) sortie.push(tableau);
    paragraphe = null;
    tableau = null;
  };
  for (const brute of String(markdown).replace(/\r\n?/g, "\n").split("\n")) {
    const ligne = brute.trimEnd();
    let m;
    if (!ligne.trim()) {
      clore();
    } else if ((m = ligne.match(/^(#{1,6})\s+(.*)$/))) {
      clore();
      sortie.push({ type: "titre", niveau: m[1].length, texte: m[2].trim() });
    } else if ((m = ligne.match(/^\s*[-*]\s+\[([ xX])\]\s+(.*)$/))) {
      clore();
      sortie.push({ type: "case", fait: m[1] !== " ", texte: m[2].trim() });
    } else if ((m = ligne.match(/^\s*(?:[-*]|\d+\.)\s+(.*)$/))) {
      clore();
      sortie.push({ type: "puce", texte: m[1].trim() });
    } else if (ligne.trim().startsWith("|")) {
      if (paragraphe) clore();
      if (!tableau) tableau = { type: "tableau", entete: cellules(ligne), lignes: [] };
      else if (!SEPARATEUR_TABLEAU.test(ligne.trim())) tableau.lignes.push(cellules(ligne));
    } else {
      if (tableau) clore();
      (paragraphe ??= []).push(ligne.trim());
    }
  }
  clore();
  return sortie;
}

/**
 * Ce que dit une fiche de suivi : son titre et les mouvements qu'il nomme,
 * ses blocs, ses sections cochables, le compte des cases et la prochaine.
 *
 * Une section est le dernier titre de niveau 2 ou plus au-dessus d'une case
 * (« Jalon 1 », « Médias ») ; un titre sans case n'en fait pas une. La
 * prochaine case est la premiere non cochee **dans l'ordre de la fiche** :
 * c'est l'ordre du protocole.
 */
export function lire_suivi(markdown) {
  const tous = blocs(markdown);
  const titre = tous.find((b) => b.type === "titre" && b.niveau === 1)?.texte ?? null;
  const sections = [];
  let section_courante = null;
  let nom_section = null;
  for (const bloc of tous) {
    if (bloc.type === "titre" && bloc.niveau >= 2) {
      nom_section = bloc.texte;
      section_courante = null;
    } else if (bloc.type === "case") {
      if (!section_courante) {
        section_courante = { titre: nom_section, cases: [] };
        sections.push(section_courante);
      }
      section_courante.cases.push({ fait: bloc.fait, texte: bloc.texte });
    }
  }
  const cases = sections.flatMap((s) => s.cases.map((c) => ({ ...c, section: s.titre })));
  const prochaine = cases.find((c) => !c.fait) ?? null;
  return {
    titre,
    mouvements: titre ? titre.split(SEPARATEUR_MOUVEMENTS).map((n) => n.trim()).filter(Boolean) : [],
    blocs: tous,
    sections: sections.map((s) => ({
      ...s,
      faites: s.cases.filter((c) => c.fait).length,
      total: s.cases.length,
    })),
    faites: cases.filter((c) => c.fait).length,
    total: cases.length,
    prochaine: prochaine && { section: prochaine.section, texte: prochaine.texte },
  };
}

/** Le HTML des blocs d'une fiche, sans son titre de niveau 1 (deja affiche). */
export function rendre_blocs(liste) {
  const sortie = [];
  let liste_ouverte = false;
  const fermer_liste = () => {
    if (liste_ouverte) sortie.push("</ul>");
    liste_ouverte = false;
  };
  for (const bloc of liste) {
    if (bloc.type === "case" || bloc.type === "puce") {
      if (!liste_ouverte) sortie.push('<ul class="fiche-liste">');
      liste_ouverte = true;
      sortie.push(bloc.type === "case"
        ? `<li class="case${bloc.fait ? " faite" : ""}"><span class="coche" aria-label="${bloc.fait ? "fait" : "à faire"}">${bloc.fait ? "✓" : ""}</span>${en_ligne(bloc.texte)}</li>`
        : `<li class="puce">${en_ligne(bloc.texte)}</li>`);
      continue;
    }
    fermer_liste();
    if (bloc.type === "titre") {
      if (bloc.niveau === 1) continue;
      const niveau = Math.min(bloc.niveau + 1, 6);
      sortie.push(`<h${niveau}>${en_ligne(bloc.texte)}</h${niveau}>`);
    } else if (bloc.type === "tableau") {
      const tete = bloc.entete.map((c) => `<th>${en_ligne(c)}</th>`).join("");
      const corps = bloc.lignes
        .map((l) => `<tr>${l.map((c) => `<td>${en_ligne(c)}</td>`).join("")}</tr>`)
        .join("");
      sortie.push(`<div class="fiche-tableau"><table><thead><tr>${tete}</tr></thead><tbody>${corps}</tbody></table></div>`);
    } else {
      sortie.push(`<p>${en_ligne(bloc.texte)}</p>`);
    }
  }
  fermer_liste();
  return sortie.join("");
}
