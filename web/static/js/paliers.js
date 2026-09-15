// Jumeau de progression/paliers.py — le bareme d'un exercice.
//
// Un palier est un triplet (poids, series, cible) et un *niveau* en est
// l'index, a partir de 1. **L'invariant est le volume** (series x cible x
// poids), qui ne redescend jamais d'un palier au suivant : apres une hausse
// de poids, la cible repart de la plus petite valeur qui tient le volume deja
// atteint, jamais de `cible_min`. Les tranches ont donc des longueurs
// inegales et le bareme se **parcourt** au lieu de se calculer par
// arithmetique modulo — ne pas « simplifier » en recalculant un index direct,
// ca casserait l'invariant.
//
// **Le bareme n'a pas de fin.** Une fois l'haltere le plus lourd et le
// plafond de series atteints, il ne reste qu'un axe : les repetitions, qui
// montent alors sans plafond. C'est la *tranche ouverte* (`longueur` a null),
// et elle garantit qu'aucun objectif n'est jamais hors d'atteinte.
//
// Les specs viennent de `donnees/baremes.json`, exporte du Python : aucune
// valeur de bareme n'est ecrite ici.

import { echelle_disponible, normaliser } from "./materiel.js";

export const UNITE_REPETITIONS = "repetitions";
export const UNITE_SECONDES = "secondes";

//: Seules ces cles peuvent etre surchargees sur un palier. Une surcharge
//: corrige un palier existant, elle n'en insere ni n'en supprime jamais :
//: sinon tous les niveaux au-dessus se decaleraient et l'historique deja
//: interprete changerait de sens retroactivement.
const CLES_SURCHARGEABLES = ["poids", "series", "cible"];

/** Le bareme charge depuis `baremes.json`. Une instance par application. */
export class Baremes {
  constructor(donnees, materiel = null) {
    this.specs = donnees.specs;
    this.echelles = donnees.echelles;
    this.materiel = donnees.materiel;
    this.accessoires = donnees.accessoires;
    this.materiel_par_defaut = donnees.materiel_par_defaut;
    //: L'inventaire est normalise ici, une fois pour toutes : `null` veut
    //: dire « rien de declare » et rend le materiel par defaut, exactement
    //: comme `normaliser(None)` cote Python. Les fonctions d'echelle
    //: recoivent donc toujours un stock concret, jamais une absence.
    this.inventaire = normaliser(donnees, materiel);
  }

  /**
   * Charge totale deplacee sur l'ensemble des series.
   *
   * Le poids du corps compte pour 1 kg : seules les repetitions font alors la
   * difference, et le bareme n'a pas besoin d'un cas particulier pour eviter
   * de tout multiplier par zero.
   */
  volume(series, cible, poids) {
    return series * cible * (poids || 1);
  }

  /** Point d'entree unique de « cet exercice a-t-il des paliers ? ». */
  est_suivi_par_le_moteur(nom) {
    return nom in this.specs;
  }

  exercices_suivis() {
    return Object.keys(this.specs);
  }

  specification(nom) {
    return this.specs[nom] ?? null;
  }

  unite(nom) {
    return this.specs[nom]?.unite ?? null;
  }

  nombre_halteres(nom) {
    return this.materiel[nom]?.halteres ?? 0;
  }

  /** Echelle du materiel : ce que les halteres du profil permettent. */
  echelle_poids(nom) {
    const nb = this.nombre_halteres(nom);
    if (nb <= 0) return this.echelles.sans_charge;
    return echelle_disponible(this.echelles, this.inventaire, nb);
  }

  /**
   * Echelle restreinte a la fourchette utile de l'exercice.
   *
   * Une fourchette qui ne retient rien (materiel absent, bornes trop
   * etroites) laisserait un bareme vide : on garde alors le cran le plus bas.
   */
  echelle_exercice(nom) {
    const echelle = this.echelle_poids(nom);
    const spec = this.specs[nom];
    if (!spec) return echelle;
    const retenue = echelle.filter(
      (poids) =>
        (spec.poids_min === null || poids >= spec.poids_min) &&
        (spec.poids_max === null || poids <= spec.poids_max)
    );
    return retenue.length ? retenue : echelle.slice(0, 1);
  }

  /**
   * Plus petite cible du bareme qui tient le volume deja atteint.
   *
   * Rend null si meme `cible_max` n'y suffit pas : ce cran de poids est alors
   * inatteignable sans regresser, et le bareme l'ignore. `plafonnee` a false
   * leve cette limite, pour la tranche ouverte.
   */
  _premiere_cible(spec, volume_a_egaler, series, poids, plafonnee = true) {
    let cible = spec.cible_min;
    while (this.volume(series, cible, poids) < volume_a_egaler) {
      cible += spec.pas;
      if (plafonnee && cible > spec.cible_max) return null;
    }
    return cible;
  }

  /**
   * Tranches successives : [series, poids, cible de depart, longueur].
   *
   * Une `longueur` a null marque la **tranche ouverte**. Generateur
   * **infini** : il se termine toujours par elle, a laquelle tout appelant
   * doit s'arreter par lui-meme.
   */
  *_iterer_tranches(spec, echelle) {
    let volume_atteint = 0;

    // Le poids monte, les series ne bougent pas.
    for (const poids of echelle) {
      const depart = this._premiere_cible(spec, volume_atteint, spec.series, poids);
      if (depart === null) continue;
      const longueur = Math.floor((spec.cible_max - depart) / spec.pas) + 1;
      yield [spec.series, poids, depart, longueur];
      volume_atteint = this.volume(spec.series, spec.cible_max, poids);
    }

    // Le poids est epuise : on reste sur l'haltere le plus lourd et c'est le
    // nombre de series qui augmente. Repartir du poids le plus leger serait
    // un recul, pas une progression.
    const poids = echelle[echelle.length - 1];
    let series = spec.series;
    while (spec.series_max === null || series < spec.series_max) {
      series += 1;
      const depart = this._premiere_cible(spec, volume_atteint, series, poids);
      if (depart === null) break;
      const longueur = Math.floor((spec.cible_max - depart) / spec.pas) + 1;
      yield [series, poids, depart, longueur];
      volume_atteint = this.volume(series, spec.cible_max, poids);
    }

    // Tout est epuise : le plafond de repetitions saute. C'est ce qui garantit
    // qu'aucun objectif n'est jamais hors d'atteinte.
    yield [
      series,
      poids,
      this._premiere_cible(spec, volume_atteint, series, poids, false),
      null,
    ];
  }

  /**
   * Decoupage lisible du bareme, pour l'affichage et l'outillage.
   *
   * `series_max` borne le parcours : indispensable puisque les tranches sont
   * un generateur infini.
   */
  tranches(nom, series_max = null) {
    const spec = this.specs[nom];
    if (!spec || spec.cible_max === null) return [];

    const plafond = series_max !== null ? series_max : spec.series;
    const resultat = [];
    let premier_niveau = 1;

    for (const [series, poids, depart, longueur] of this._iterer_tranches(
      spec,
      this.echelle_exercice(nom)
    )) {
      if (series > plafond) break;
      if (longueur === null) {
        resultat.push({
          series, poids, cible_min: depart, cible_max: null,
          niveau_min: premier_niveau, niveau_max: null, volume_max: null,
        });
        break;
      }
      resultat.push({
        series, poids, cible_min: depart, cible_max: spec.cible_max,
        niveau_min: premier_niveau,
        niveau_max: premier_niveau + longueur - 1,
        volume_max: this.volume(series, spec.cible_max, poids),
      });
      premier_niveau += longueur;
    }
    return resultat;
  }

  /** Dernier niveau avant la tranche ouverte, ou les repetitions s'envolent. */
  dernier_palier_borne(nom) {
    const spec = this.specs[nom];
    if (!spec || spec.cible_max === null) return null;
    const bornees = this.tranches(nom, spec.series_max).filter(
      (t) => t.niveau_max !== null
    );
    return bornees.length ? bornees[bornees.length - 1].niveau_max : null;
  }

  /**
   * Premier niveau dont le palier atteint ce volume.
   *
   * Sert a traduire une prescription ecrite avec un autre materiel que le
   * sien : c'est le volume qui fait foi, pas la charge. Grace a la tranche
   * ouverte, un volume est **toujours** atteignable.
   */
  niveau_pour_volume(nom, volume_cible) {
    const spec = this.specs[nom];
    if (!spec) return null;

    if (spec.cible_max === null) {
      // Bareme deja lineaire et sans fin : pas de tranches a parcourir.
      const echelle = this.echelle_exercice(nom);
      let cible = spec.cible_min;
      while (this.volume(spec.series, cible, echelle[0]) < volume_cible) {
        cible += spec.pas;
      }
      return Math.floor((cible - spec.cible_min) / spec.pas) + 1;
    }

    let premier_niveau = 1;
    for (const [series, poids, depart, longueur] of this._iterer_tranches(
      spec,
      this.echelle_exercice(nom)
    )) {
      const dernier = longueur === null ? null : depart + (longueur - 1) * spec.pas;
      // Le volume croit le long du bareme : la bonne tranche est la premiere
      // dont la cible haute suffit — et la tranche ouverte suffit toujours.
      if (dernier === null || this.volume(series, dernier, poids) >= volume_cible) {
        let cible = depart;
        while (this.volume(series, cible, poids) < volume_cible) cible += spec.pas;
        return premier_niveau + Math.floor((cible - depart) / spec.pas);
      }
      premier_niveau += longueur;
    }
    return null;
  }

  _palier_genere(spec, echelle, niveau) {
    if (spec.cible_max === null) {
      return {
        niveau,
        poids: echelle[0],
        series: spec.series,
        cible: spec.cible_min + (niveau - 1) * spec.pas,
        unite: spec.unite,
      };
    }

    let restant = niveau;
    for (const [series, poids, depart, longueur] of this._iterer_tranches(
      spec,
      echelle
    )) {
      // `longueur` a null : tranche ouverte, elle contient tous les niveaux
      // restants quels qu'ils soient.
      if (longueur === null || restant <= longueur) {
        return {
          niveau,
          poids,
          series,
          cible: depart + (restant - 1) * spec.pas,
          unite: spec.unite,
        };
      }
      restant -= longueur;
    }
    return null;
  }

  _appliquer_surcharge(spec, genere) {
    // Les cles d'un objet JSON sont des chaines : le niveau doit etre converti
    // avant la recherche, sinon aucune surcharge ne s'applique jamais — en
    // silence, ce qui est le pire cas.
    const surcharge = spec.surcharges?.[String(genere.niveau)];
    if (!surcharge) return genere;
    const inconnues = Object.keys(surcharge).filter(
      (cle) => !CLES_SURCHARGEABLES.includes(cle)
    );
    if (inconnues.length) {
      throw new Error(`Surcharge de palier invalide : ${inconnues.sort()}`);
    }
    return { ...genere, ...surcharge };
  }

  /** Le palier d'un niveau, ou null si le bareme ne va pas jusque-la. */
  palier(nom, niveau) {
    const spec = this.specs[nom];
    if (!spec || niveau < 1) return null;
    const genere = this._palier_genere(spec, this.echelle_exercice(nom), niveau);
    if (genere === null) return null;
    return this._appliquer_surcharge(spec, genere);
  }

  /**
   * Une performance valide un palier si elle est **au moins aussi lourde et
   * au moins aussi volumineuse**.
   *
   * Le volume prime, mais pas seul : exiger en plus `poids >= palier.poids`
   * empeche une longue serie legere de valider un palier lourd. A poids egal,
   * la repartition series/repetitions est libre — c'est ce qui permet a un
   * travail lourd et court de valider un palier plus leger et plus long.
   */
  _valide(palier_teste, poids, series, cible) {
    if (palier_teste === null) return false;
    return (
      poids >= palier_teste.poids &&
      this.volume(series, cible, poids) >=
        this.volume(palier_teste.series, palier_teste.cible, palier_teste.poids)
    );
  }

  /**
   * Niveaux qu'une performance pourrait valider, sans les verifier.
   *
   * Inutile de balayer tout le bareme (il peut etre infini) : dans chaque
   * tranche, un seul niveau est interessant — celui de la meilleure cible
   * tenue.
   */
  _niveaux_candidats(spec, echelle, poids, series, cible) {
    if (poids < echelle[0] || cible <= 0) return [];

    if (spec.cible_max === null) {
      if (cible < spec.cible_min) return [];
      // `Math.floor` explicite : une duree est un reel, et sans cette
      // troncature le niveau lui-meme sortirait en flottant.
      return [Math.floor((cible - spec.cible_min) / spec.pas) + 1];
    }

    const volume_realise = this.volume(series, cible, poids);
    const candidats = [];
    let premier_niveau = 1;

    for (const [series_tranche, poids_tranche, depart, longueur] of
      this._iterer_tranches(spec, echelle)) {
      // Le volume d'entree d'une tranche ne redescend jamais : des qu'il
      // depasse la performance, aucune tranche suivante ne pourra etre
      // validee. C'est aussi ce qui fait terminer la boucle sur un generateur
      // infini.
      if (this.volume(series_tranche, depart, poids_tranche) > volume_realise) break;

      if (poids_tranche <= poids) {
        let atteinte = depart;
        while (
          (longueur === null || atteinte + spec.pas <= spec.cible_max) &&
          this.volume(series_tranche, atteinte + spec.pas, poids_tranche) <=
            volume_realise
        ) {
          atteinte += spec.pas;
        }
        candidats.push(premier_niveau + Math.floor((atteinte - depart) / spec.pas));
      }

      if (longueur === null) break;
      premier_niveau += longueur;
    }

    return candidats;
  }

  /**
   * Le plus haut niveau qu'une performance valide, ou null si aucun.
   *
   * null signifie « hors bareme » — la performance n'atteint meme pas le
   * palier de base — ce qui est distinct du niveau 1.
   */
  niveau_pour(nom, poids, series, cible) {
    const spec = this.specs[nom];
    if (!spec) return null;

    const echelle = this.echelle_exercice(nom);
    const candidats = this._niveaux_candidats(spec, echelle, poids, series, cible);
    // Une surcharge peut placer un palier n'importe ou : on les repasse tous,
    // ils sont peu nombreux.
    for (const cle of Object.keys(spec.surcharges ?? {})) candidats.push(Number(cle));

    const valides = candidats.filter((niveau) =>
      this._valide(this.palier(nom, niveau), poids, series, cible)
    );
    return valides.length ? Math.max(...valides) : null;
  }
}
