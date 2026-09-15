// Jumeau de progression/ligues.py — ligues, divisions et XP.
//
// **La ligue vient du volume, pas du numero de niveau.** Le rang se lit sur le
// *volume* du palier atteint (series x cible x poids), rapporte au volume du
// palier 1 du meme exercice. Le volume ne croit pas au meme rythme d'un
// exercice a l'autre — une hausse d'haltere fait un bond, une repetition de
// plus fait un pas — donc deux exercices au meme niveau ne sont pas a la meme
// ligue. C'est voulu : le niveau dit la position sur le bareme, la ligue dit
// l'effort produit.
//
// **Rien n'est stocke** : tout se recalcule depuis le niveau, qui se recalcule
// depuis l'historique. Comme les autres modules de progression, celui-ci est
// une classe a dependances injectees — il n'y a pas de base a lire.
//
// Les seuils, les noms de ligue et la table d'XP viennent de
// `donnees/baremes.json`, exporte du Python : **aucune valeur n'est ecrite
// ici**.

//: Ce qu'il faut retirer d'un nom de ligue pour en faire une cle utilisable
//: partout — nom de variable CSS, nom de classe, cle de dictionnaire.
//: « Maitre » est le seul nom accentue aujourd'hui, mais la table evite
//: d'avoir a s'en souvenir le jour ou il y en aura un second.
const SANS_ACCENT = { à: "a", â: "a", ä: "a", é: "e", è: "e", ê: "e", ë: "e", î: "i", ï: "i", ô: "o", ö: "o", ù: "u", û: "u", ü: "u", ç: "c" };

/** Cle d'une ligue : son nom en minuscules, sans accent ni espace. */
export function cle_de_ligue(nom_ligue) {
  return nom_ligue
    .toLowerCase()
    .replace(/./g, (c) => SANS_ACCENT[c] ?? c)
    .replace(/ /g, "-");
}

/** Les ligues et l'XP. Une instance par application, construite avec le bareme. */
export class Ligues {
  constructor(baremes, tables) {
    this.baremes = baremes;
    this.LIGUES = tables.ligues;
    this.DIVISIONS = tables.divisions;
    this.SEUILS_VOLUME = tables.seuils_volume;
    this.PALIERS_XP = tables.paliers_xp;
    this.XP_BASE_NIVEAU_GENERAL = tables.xp_base_niveau_general;
    this.XP_INCREMENT_NIVEAU_GENERAL = tables.xp_increment_niveau_general;
    //: Maitre I. Le bareme n'ayant pas de fin (sa derniere tranche est
    //: ouverte), le volume relatif n'a pas de borne superieure : le rang
    //: sature ici au lieu de deborder.
    this.RANG_MAX = this.SEUILS_VOLUME.length;
  }

  /**
   * Volume du palier `niveau`, rapporte a celui du palier 1 du meme exercice.
   *
   * Rapporter au palier 1 plutot que de prendre le volume brut est ce qui rend
   * les ligues comparables d'un exercice a l'autre malgre le `(poids or 1)` du
   * calcul de volume, qui fait compter un mouvement au poids du corps pour
   * 1 kg.
   */
  volume_relatif(nom_exercice, niveau) {
    if (niveau === null || niveau === undefined || niveau < 1) return null;
    const atteint = this.baremes.palier(nom_exercice, niveau);
    const depart = this.baremes.palier(nom_exercice, 1);
    if (!atteint || !depart) return null;
    const volume_depart = this.baremes.volume(
      depart.series,
      depart.cible,
      depart.poids,
    );
    if (!volume_depart) return null;
    const volume_atteint = this.baremes.volume(
      atteint.series,
      atteint.cible,
      atteint.poids,
    );
    return volume_atteint / volume_depart;
  }

  /**
   * Rang de 1 a 18 pour un volume relatif, ou null s'il n'atteint rien.
   *
   * `null` veut dire **pas de ligue**, ce qui n'est pas « rang 0 » : c'est la
   * meme distinction en trois situations que porte `etat_niveau`, et un
   * affichage ne doit pas la gommer en montrant un Bronze III qui n'a pas ete
   * gagne.
   */
  rang_pour_volume(relatif) {
    if (relatif === null || relatif === undefined) return null;
    if (relatif < this.SEUILS_VOLUME[0]) return null;
    let rang = 1;
    this.SEUILS_VOLUME.forEach((seuil, index) => {
      if (relatif >= seuil) rang = index + 1;
    });
    return rang;
  }

  /**
   * Nom de ligue et division d'un rang de 1 a 18.
   *
   * Rend aussi `cle` (le nom en minuscules sans accent, pour nommer une
   * variable CSS) et `division_index` (0 pour III, 2 pour I, qui gradue
   * l'intensite de l'habillage). Les deux viennent du module et non de
   * l'interface : les calculer ici evite d'ecrire deux fois la meme
   * translitteration d'accents, en Jinja et en JavaScript.
   */
  ligue_pour_rang(rang) {
    if (rang === null || rang === undefined || rang < 1) return null;
    const borne = Math.min(rang, this.RANG_MAX);
    const ligue = this.LIGUES[Math.floor((borne - 1) / this.DIVISIONS.length)];
    const index = (borne - 1) % this.DIVISIONS.length;
    const division = this.DIVISIONS[index];
    return {
      rang: borne,
      ligue,
      division,
      libelle: `${ligue} ${division}`,
      cle: cle_de_ligue(ligue),
      division_index: index,
    };
  }

  /** Part du cran parcourue, de 0 a 1 — vaut 1 au dernier rang, qui n'a pas de suite. */
  _avancement_dans_le_rang(relatif, rang) {
    if (rang === null || rang >= this.RANG_MAX) return 1.0;
    const plancher = this.SEUILS_VOLUME[rang - 1];
    const plafond = this.SEUILS_VOLUME[rang];
    if (plafond <= plancher) return 1.0;
    return Math.max(0.0, Math.min(1.0, (relatif - plancher) / (plafond - plancher)));
  }

  /**
   * Tout ce qu'un ecran a besoin de savoir sur la ligue d'un exercice.
   *
   * Rend `null` quand il n'y a pas de ligue a montrer : exercice non suivi par
   * le bareme, ou niveau inconnu (hors bareme). L'ecran affiche alors « a
   * tester », comme il le fait deja pour le niveau.
   */
  ligue_exercice(nom_exercice, niveau) {
    if (!this.baremes.est_suivi_par_le_moteur(nom_exercice)) return null;
    const relatif = this.volume_relatif(nom_exercice, niveau);
    const rang = this.rang_pour_volume(relatif);
    if (rang === null) return null;

    return {
      ...this.ligue_pour_rang(rang),
      niveau,
      volume_relatif: relatif,
      seuil_actuel: this.SEUILS_VOLUME[rang - 1],
      seuil_suivant: rang < this.RANG_MAX ? this.SEUILS_VOLUME[rang] : null,
      avancement: this._avancement_dans_le_rang(relatif, rang),
      maximum_atteint: rang === this.RANG_MAX,
    };
  }

  /**
   * Ligue de chaque exercice, a partir du dict rendu par `etats_niveaux()`.
   *
   * Les exercices sans ligue y figurent avec la valeur null plutot que d'etre
   * absents : un ecran qui boucle sur le catalogue doit pouvoir distinguer
   * « pas encore de ligue » de « exercice inconnu ».
   */
  ligues_par_exercice(etats) {
    const sortie = {};
    for (const [nom, etat] of Object.entries(etats)) {
      sortie[nom] = this.ligue_exercice(nom, etat ? etat.niveau : null);
    }
    return sortie;
  }

  /** XP rapportee par le passage au niveau `niveau` d'un exercice. */
  xp_du_niveau(niveau) {
    if (niveau === null || niveau === undefined || niveau < 1) return 0;
    let gain = this.PALIERS_XP[0][1];
    for (const [depart, valeur] of this.PALIERS_XP) {
      if (niveau >= depart) gain = valeur;
    }
    return gain;
  }

  /** XP totale qu'un exercice rapporte une fois le niveau `niveau` atteint. */
  xp_cumulee(niveau) {
    if (niveau === null || niveau === undefined || niveau < 1) return 0;
    let total = 0;
    for (let n = 1; n <= niveau; n += 1) total += this.xp_du_niveau(n);
    return total;
  }

  /** XP de tout un profil, sommee sur les exercices ayant un niveau. */
  xp_totale(etats) {
    return Object.values(etats).reduce(
      (total, etat) => total + this.xp_cumulee(etat ? etat.niveau : null),
      0,
    );
  }

  /** XP a accumuler pour passer du niveau general `niveau` au suivant. */
  cout_du_niveau_general(niveau) {
    return (
      this.XP_BASE_NIVEAU_GENERAL +
      this.XP_INCREMENT_NIVEAU_GENERAL * (Math.max(niveau, 1) - 1)
    );
  }

  /**
   * Niveau general du profil, et ou l'on en est dans le niveau courant.
   *
   * **La ligue generale avance d'un cran par niveau general**, et non selon
   * les seuils de volume des exercices : l'XP cumulee croit bien plus vite que
   * le volume relatif, et la table calibree sur l'une sature sur l'autre —
   * mesure, le catalogue entier au niveau 20 sortait deja Maitre III.
   *
   * Tant qu'aucune XP n'a ete gagnee il n'y a **pas de ligue** — pas un Bronze
   * III offert.
   */
  niveau_general(xp) {
    const total = Math.max(xp || 0, 0);
    let restant = total;
    let niveau = 1;
    while (restant >= this.cout_du_niveau_general(niveau)) {
      restant -= this.cout_du_niveau_general(niveau);
      niveau += 1;
    }

    const cout = this.cout_du_niveau_general(niveau);
    return {
      niveau,
      xp: total,
      xp_dans_le_niveau: restant,
      xp_pour_le_suivant: cout,
      avancement: cout ? restant / cout : 0.0,
      ligue: total > 0 ? this.ligue_pour_rang(niveau) : null,
    };
  }

  /**
   * Parmi les montees de niveau, celles qui font franchir un cran de ligue.
   *
   * Une montee de niveau est frequente ; une montee de ligue est un jalon, et
   * c'est elle qui merite d'etre fetee a l'ecran de fin et jalonnee dans
   * l'historique.
   */
  montees_de_ligue(montees_niveaux) {
    const montees = {};
    for (const [seance_id, exercices] of Object.entries(montees_niveaux)) {
      for (const [nom, montee] of Object.entries(exercices)) {
        const avant = this.rang_pour_volume(
          this.volume_relatif(nom, montee.depuis),
        );
        const apres = this.rang_pour_volume(this.volume_relatif(nom, montee.vers));
        if (apres === null || apres === avant) continue;
        if (!montees[seance_id]) montees[seance_id] = {};
        montees[seance_id][nom] = {
          depuis: this.ligue_pour_rang(avant),
          vers: this.ligue_pour_rang(apres),
        };
      }
    }
    return montees;
  }

  /** XP rapportee par une seance, d'apres les niveaux qu'elle a fait franchir. */
  xp_gagnee(montees_d_une_seance) {
    return Object.values(montees_d_une_seance || {}).reduce(
      (total, montee) =>
        total + this.xp_cumulee(montee.vers) - this.xp_cumulee(montee.depuis),
      0,
    );
  }
}
