// Les pastilles d'une serie : `12×5 kg`, `15`, `30 s`.
//
// Un module a part pour une seule fonction, parce qu'elle a deux maisons qui
// ne se voient pas : l'application (historique, « Derniere fois », graphique)
// et le HUD de seance (`hud.js`), dont la bulle de la barre de progression
// montre les series faites **avec les memes pastilles** — un second format
// de la meme donnee serait une seconde chose a apprendre a lire.

/**
 * Ce qu'une seance a donne, **une pastille par serie**.
 *
 * Rend du HTML — les pastilles de `.series-detail` / `.serie-puce`, exactement
 * celles de l'historique. C'est le point d'entree unique des ecrans
 * qui montrent une performance : le detail d'une seance dans
 * l'historique, le depliant « Derniere fois » des cartes de seance, la ligne
 * qui repond a un appui sur un point du graphique, et la bulle de la barre de
 * progression en pleine seance. Ils disent la meme chose de la meme donnee ;
 * des mises en forme differentes obligeraient a relire a chaque fois de quoi
 * il s'agit.
 *
 * Une case par serie, et non une phrase separee par des points medians : c'est
 * ce qui rend l'ecart visible d'un coup d'oeil, `15x8 kg` et `12x10 kg` etant
 * alors deux blocs a comparer plutot qu'un texte a lire.
 *
 * Deux regles de contenu. Une duree ne se rapporte a aucune charge — un
 * gainage se tient, il ne se souleve pas. Et un poids nul n'est pas une charge
 * de zero kilo mais un mouvement au poids du corps : `historique.js` normalise
 * a l'ecriture avec `poids ?? 0`, donc un format inconditionnel afficherait
 * « 13x0 kg » sur toutes les pompes.
 */
export function resume_series(series, mode) {
  if (!series?.length) return "";
  const au_temps = mode === "maintien" || mode === "chrono";
  return series
    .map((serie) => {
      const valeur = au_temps
        ? `${Math.round(serie.duree || 0)} s`
        : serie.repetitions || 0;
      // La charge est plus discrete que la repetition : c'est elle qu'on lit
      // en premier, le poids ne fait que la qualifier.
      const charge = !au_temps && serie.poids ? `<i>×${serie.poids}&nbsp;kg</i>` : "";
      // `=== false` et non la simple faussete : les listes deja filtrees sur
      // les series menees au bout ne portent pas toujours le champ, et elles
      // s'afficheraient alors toutes en rate.
      return (
        `<span class="serie-puce${serie.completee === false ? " ratee" : ""}">` +
        `${valeur}${charge}</span>`
      );
    })
    .join("");
}
