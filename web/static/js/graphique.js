// Le graphique de progression d'un exercice, partage par les deux
// applications.
//
// Un point par seance, du plus ancien a gauche au plus recent a droite. Il
// vivait dans le <script> de `records.html` ; l'ecran des records de
// l'application n'en avait aucun, ce qui lui retirait la seule vue d'ensemble
// du projet — un niveau dit ou l'on en est, ce graphe dit **comment on y est
// arrive**.
//
// Ce module rend une **chaine de SVG** et ne touche jamais au document : c'est
// ce qui lui permet de servir a une page Flask comme a un ecran de
// l'application, et ce qui le rend verifiable sans navigateur.
//
// La seule chose qui differe entre les deux appelants est le **lien d'un
// point** : le poste fixe pointe vers `/historique/<id>`, l'application n'a pas
// d'URL a offrir. D'ou `lien`, une fonction qui peut rendre null — les points
// deviennent alors de simples groupes, sans cible cliquable.

//: Geometrie du trace, en unites du viewBox. Le SVG se met a l'echelle tout
//: seul : ces valeurs ne sont pas des pixels et n'ont pas a suivre la taille
//: de l'ecran.
const L = 1000;
const H = 440;
const MARGE_GAUCHE = 56;
const MARGE_DROITE = 24;
const MARGE_HAUT = 24;
const MARGE_BAS = 100;

//: Ecart minimal entre deux etiquettes de date, pour qu'elles ne se
//: chevauchent jamais meme avec beaucoup de points. Au-dela, on n'en affiche
//: qu'une sur n.
const ESPACEMENT_MINIMUM = 70;

/** « 12/09/2026 08:00 » et « 2026-09-12T08:00 » rendent tous deux leur date. */
export function date_seule(valeur) {
  if (!valeur) return "";
  const t = valeur.indexOf("T");
  if (t !== -1) return valeur.slice(0, t);
  const espace = valeur.indexOf(" ");
  return espace === -1 ? valeur : valeur.slice(0, espace);
}

function echapper(texte) {
  return String(texte).replace(
    /[&<>"']/g,
    (caractere) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[caractere]
  );
}

/**
 * Le graphique, sous forme de chaine SVG.
 *
 * `donnees` est la liste `progression` de `statistiques_exercices` : une entree
 * par seance, **du plus recent au plus ancien** — l'ordre de l'historique. On
 * l'inverse ici, une chronologie se lisant de gauche a droite.
 *
 * `cle` designe ce qu'on trace : `volume`, `repetitions` ou `duree`. C'est
 * l'appelant qui choisit, parce que le record qui compte depend du mode —
 * tracer le volume d'un exercice au poids du corps donnerait une ligne plate a
 * zero.
 */
export function graphique_progression(donnees, { cle, unite, lien = () => null } = {}) {
  if (!donnees?.length) {
    return '<p class="vide">Pas encore assez de données pour un graphique.</p>';
  }

  const points_bruts = [...donnees].reverse();
  const valeurs = points_bruts.map((p) => Number(p[cle]) || 0);
  // **L'axe part de zero et se cale sur le maximum**, jamais sur le minimum :
  // un graphe qui commence a la plus mauvaise valeur transforme une variation
  // de trois pour cent en falaise. Le plancher a 0,0001 evite une division par
  // zero quand tout vaut zero.
  const maximum = Math.max(...valeurs, 0.0001);

  const largeur = L - MARGE_GAUCHE - MARGE_DROITE;
  const hauteur = H - MARGE_HAUT - MARGE_BAS;
  const n = points_bruts.length;
  const x_de = (i) => (n === 1 ? MARGE_GAUCHE + largeur / 2 : MARGE_GAUCHE + (largeur * i) / (n - 1));
  const y_de = (v) => MARGE_HAUT + hauteur - (hauteur * v) / maximum;

  const points = points_bruts.map((p, i) => ({
    ...p,
    x: x_de(i),
    y: y_de(Number(p[cle]) || 0),
    date_affichee: date_seule(p.date),
  }));

  const ligne = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");
  const bas = (MARGE_HAUT + hauteur).toFixed(1);
  const aire =
    `${ligne} L ${points.at(-1).x.toFixed(1)} ${bas} ` +
    `L ${points[0].x.toFixed(1)} ${bas} Z`;

  const espacement_reel = n > 1 ? largeur / (n - 1) : largeur;
  const pas_etiquette = Math.max(1, Math.ceil(ESPACEMENT_MINIMUM / espacement_reel));

  let svg =
    `<svg viewBox="0 0 ${L} ${H}" class="progression-svg" role="img" ` +
    `aria-label="Graphique de progression">` +
    `<line x1="${MARGE_GAUCHE}" y1="${MARGE_HAUT}" x2="${MARGE_GAUCHE}" y2="${bas}" ` +
    `stroke="var(--border-strong)" stroke-width="1"/>` +
    `<line x1="${MARGE_GAUCHE}" y1="${bas}" x2="${L - MARGE_DROITE}" y2="${bas}" ` +
    `stroke="var(--border-strong)" stroke-width="1"/>` +
    `<text class="chart-axis-label" x="${MARGE_GAUCHE - 10}" y="${MARGE_HAUT + 5}" ` +
    `text-anchor="end">${maximum.toFixed(1)}</text>` +
    `<text class="chart-axis-label" x="${MARGE_GAUCHE - 10}" y="${bas}" text-anchor="end">0</text>` +
    `<path d="${aire}" class="chart-area"></path>` +
    `<path d="${ligne}" class="chart-line"></path>`;

  points.forEach((p, i) => {
    const valeur = (Number(p[cle]) || 0).toFixed(1);
    const cible = lien(p);
    const description = `${p.date_affichee} · ${valeur} ${unite ?? ""}`.trim();

    svg += cible
      ? `<a class="chart-point" href="${echapper(cible)}" ` +
        `aria-label="Voir la séance du ${echapper(description)}">`
      : `<g class="chart-point">`;
    svg +=
      `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="6">` +
      `<title>${echapper(description)}</title></circle>` +
      `<text class="chart-axis-label" x="${p.x.toFixed(1)}" y="${(p.y - 14).toFixed(1)}" ` +
      `text-anchor="middle">${valeur}</text>`;
    svg += cible ? `</a>` : `</g>`;

    if (i % pas_etiquette === 0 || i === n - 1) {
      svg +=
        `<text class="chart-date-label" x="0" y="0" text-anchor="end" ` +
        `transform="translate(${p.x.toFixed(1)}, ${(Number(bas) + 34).toFixed(1)}) rotate(-35)">` +
        `${echapper(p.date_affichee)}</text>`;
    }
  });

  return `${svg}</svg>`;
}

//: Ce qu'on trace selon le mode de l'exercice, et pourquoi. Meme raisonnement
//: que le `pb` de `statistiques_exercices` : le volume est structurellement
//: nul au poids du corps, la duree n'a de sens que pour un maintien.
export function cle_de_progression(mode, a_de_la_charge) {
  if (mode === "maintien" || mode === "chrono") return { cle: "duree", unite: "s" };
  if (a_de_la_charge) return { cle: "volume", unite: "kg" };
  return { cle: "repetitions", unite: "rép." };
}
