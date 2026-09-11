// Jumeau de progression/calibration.py — du test d'un debutant a son niveau
// de depart.
//
// Comme les ancrages, il ne pose jamais un numero de niveau : il fabrique une
// *performance* et laisse `niveau_pour` la traduire.
//
// **Le test se joue en seance, il n'y a pas de tunnel d'accueil.** Une seance
// ordinaire rencontre un exercice dont rien n'est connu (`objectifs.a_calibrer`),
// remplace sa cible par un plafond inatteignable a charge moyenne, et
// l'ancrage se pose des que la serie est terminee a la main.

//: Part d'un maximum en serie unique qu'on peut tenir serie apres serie.
//: Repere d'entraineur, pas une mesure : quelqu'un qui fait 20 pompes
//: d'affilee en tient environ 13 sur chacune de ses series de travail.
//: Volontairement prudent — un objectif de depart trop bas se corrige en une
//: seance, un objectif trop haut decourage et fait echouer toutes les series.
export const COEFFICIENT_SERIE_UNIQUE = 0.65;

//: Cible d'une serie de test : un plafond qu'on n'atteint pas. Le test se
//: termine a la main, jamais en atteignant sa consigne — c'est ce qui en fait
//: un maximum et non une serie de plus. Une valeur plutot qu'un mode dedie :
//: tous les compteurs, l'audio et l'affichage continuent de fonctionner sans
//: connaitre le test.
export const CIBLE_TEST = 999;

export class Calibration {
  constructor(baremes) {
    this.baremes = baremes;
  }

  /**
   * La charge « relativement moyenne » sur laquelle tester un exercice.
   *
   * Le milieu de l'echelle **reellement disponible**, donc du materiel
   * declare : tester a 2 kg ne dit rien de quelqu'un qui en souleve 10, et
   * tester au maximum de la gamme decourage un debutant. Zero pour un
   * mouvement au poids du corps, dont l'echelle n'a qu'une valeur.
   */
  charge_de_test(nom) {
    const echelle = this.baremes.echelle_exercice(nom);
    if (!echelle || !echelle.length) return 0;
    return echelle[Math.floor(echelle.length / 2)];
  }

  /** Nombre de series sur lequel le bareme de cet exercice raisonne. */
  series_de_reference(nom) {
    const spec = this.baremes.specification(nom);
    return spec ? spec.series : null;
  }

  /**
   * Niveau deduit d'un maximum realise en une seule serie.
   *
   * `maximum` est en repetitions ou en secondes selon l'unite de l'exercice.
   * Rend null si la performance n'atteint pas le premier palier — c'est le
   * signal « propose une variante plus facile », **pas** « niveau zero ».
   */
  niveau_estime(nom, poids, maximum) {
    if (!this.baremes.est_suivi_par_le_moteur(nom) || !maximum || maximum <= 0) {
      return null;
    }

    const series = this.series_de_reference(nom);
    if (!series) return null;

    // Le meme coefficient sert aux repetitions et aux secondes. Les deux ne
    // fatiguent pourtant pas pareil — un gainage tenu au maximum s'effondre
    // plus vite d'une serie a l'autre qu'une serie de pompes —, mais une
    // regle unique vaut mieux que deux reglages dont personne ne saura lequel
    // corriger. C'est l'ecran de confirmation qui rattrape l'ecart.
    //
    // `round` de Python arrondit **au pair le plus proche** sur un demi exact
    // (banker's rounding) : 2.5 donne 2, pas 3. `Math.round` arrondit vers le
    // haut. Sans cette traduction, un maximum dont le produit tombe pile sur
    // un demi donnerait deux cibles differentes.
    const produit = maximum * COEFFICIENT_SERIE_UNIQUE;
    const cible = Math.max(1, arrondi_python(produit));

    return this.baremes.niveau_pour(nom, poids, series, cible);
  }

  /**
   * Traduit un maximum en niveau a ancrer.
   *
   * Un maximum qui n'atteint pas le premier palier ancre quand meme au palier
   * 1 plutot que de ne rien poser : sans ancrage l'exercice resterait « sans
   * donnees » et redemanderait un test a chaque seance, ce qui est precisement
   * la boucle qu'on veut eviter. Le moteur d'objectifs redescendra de lui-meme
   * si les series echouent.
   *
   * Contrairement au Python, cette methode **n'ecrit pas** l'ancrage : la
   * persistance vit dans `historique.js`, et l'appelant decide quand ecrire.
   */
  niveau_a_ancrer(nom, poids, maximum) {
    return this.niveau_estime(nom, poids, maximum) || 1;
  }
}

/**
 * L'arrondi de Python : au pair le plus proche sur un demi exact.
 *
 * `Math.round(2.5)` vaut 3, `round(2.5)` en Python vaut 2. La difference ne
 * se voit que sur un demi exact, ce qui arrive des que le produit tombe
 * juste — et alors la cible, donc le niveau, divergent.
 */
export function arrondi_python(valeur) {
  const bas = Math.floor(valeur);
  const reste = valeur - bas;
  if (reste > 0.5) return bas + 1;
  if (reste < 0.5) return bas;
  return bas % 2 === 0 ? bas : bas + 1;
}
