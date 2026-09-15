// L'habillage des ligues, cote navigateur.
//
// Meme decoupage que `ressentis_ui.js` : ce module **ne decide rien**. La
// regle — quel rang, quelle division, combien d'XP — vit dans `ligues.js` et
// dans `progression/ligues.py`. Ici il n'y a que la traduction d'une ligue en
// attributs de style, et le balisage des trois elements que les deux
// applications montrent : le badge, la jauge d'avancement, le jalon de montee.
//
// Le jumeau Jinja est `web/templates/_ligue.html`, qui rend exactement le meme
// balisage pour les pages du poste fixe. Les deux ne peuvent pas partager de
// code — l'un rend cote serveur, l'autre cote client — mais ils partagent
// `ligues.css`, et c'est la que vit l'apparence.

/**
 * Les variables que `ligues.css` lit : la couleur, son reflet, et la division.
 *
 * `cle` et `division_index` viennent du module de ligues, jamais recalcules
 * ici : c'est ce qui evite d'ecrire deux fois la translitteration de
 * « Maitre » en `maitre`, une fois par interface.
 */
export function style_ligue(ligue) {
  if (!ligue) return "";
  return (
    `--ligue: var(--ligue-${ligue.cle}); ` +
    `--ligue-reflet: var(--ligue-${ligue.cle}-reflet); ` +
    `--division: ${ligue.division_index}`
  );
}

/** Les classes de la surface teintee. Sans ligue, la surface reste neutre. */
export function classe_ligue(ligue) {
  return ligue ? "ligue-teinte" : "ligue-teinte sans-ligue";
}

/**
 * Le badge « Or II ».
 *
 * Sans ligue il rend « a tester » plutot que rien : l'absence de badge se
 * confondrait avec un oubli d'affichage, alors que « pas encore classe » est
 * une information — c'est la meme distinction en trois situations que porte
 * `etat_niveau`.
 */
export function badge_ligue(ligue, { grand = false } = {}) {
  const taille = grand ? " grand" : "";
  if (!ligue) {
    return `<span class="badge-ligue sans-ligue${taille}">A tester</span>`;
  }
  return (
    `<span class="badge-ligue${taille}" style="${style_ligue(ligue)}">` +
    `${ligue.libelle}</span>`
  );
}

/**
 * Une jauge d'avancement aux couleurs de la ligue.
 *
 * **L'avancement est un argument, jamais lu sur la ligue.** Les deux appelants
 * ne mesurent pas la meme chose : une fiche d'exercice montre la part du cran
 * parcourue, le bandeau de profil la part du prochain niveau general. Lire
 * `ligue.avancement` marchait pour le premier et rendait une jauge vide — sans
 * rien signaler — pour le second, ou la ligue vient de `ligue_pour_rang`, qui
 * ne porte pas ce champ.
 */
export function jauge_ligue(ligue, avancement) {
  if (!ligue) return "";
  const part = Math.round((avancement ?? 0) * 100);
  return (
    `<div class="ligue-jauge" style="${style_ligue(ligue)}">` +
    `<i style="width:${part}%"></i></div>`
  );
}

/** « Argent I → Or III », le jalon d'une montee de ligue. */
export function jalon_ligue(nom_exercice, montee) {
  const style = style_ligue(montee.vers);
  const depuis = montee.depuis ? `${montee.depuis.libelle} ` : "";
  return (
    `<span class="jalon-ligue" style="${style}">${nom_exercice} : ` +
    `${depuis}<span class="fleche">&rarr;</span> ${badge_ligue(montee.vers)}</span>`
  );
}
