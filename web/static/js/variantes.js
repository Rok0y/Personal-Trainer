// Jumeau de progression/variantes.py — jouer une variante plus facile a la
// place d'un mouvement, et en revenir.
//
// Meme convention que le reste du portage : noms du Python, en snake_case, et
// le Python fait autorite. `python -m scripts.generer_variantes` ecrit l'oracle,
// `node scripts/comparer_variantes.mjs` le rejoue ici et diffe.
//
// Les deux regles a retenir sont celles du module Python. **Une substitution
// est une preference du profil**, jamais une donnee de seance : les seances
// sont partagees. Et **elle ne doit jamais atteindre le fichier des seances**
// — `appliquer_au_circuit` ne s'appelle que sur le chemin de jeu (`demarrer()`),
// l'affichage interroge `substitution` sans rien reecrire.
//
// Le bareme est injecte (`Baremes`), comme dans `objectifs.js` : il porte
// l'unite de chaque exercice et `niveau_pour`, et c'est lui qui connait le
// materiel du profil. Les seuils de retour viennent de `baremes.json`
// (`variantes.retour`), exportes tels quels de `reglages.json`.

const MODE_ECHAUFFEMENT = "echauffement";

/**
 * La table d'un profil sous une forme toujours exploitable.
 *
 * Il n'existe aucune migration cote JavaScript : un profil anterieur ou venu
 * de SQLite n'a pas le champ, et « pas de champ » veut dire « aucune variante »
 * — meme rattrapage que `tutos_vus`.
 */
export function normaliser(variantes) {
  if (!variantes || typeof variantes !== "object" || Array.isArray(variantes)) {
    return {};
  }
  const propres = {};
  for (const [original, joue] of Object.entries(variantes)) {
    if (original && joue && original !== joue) propres[String(original)] = String(joue);
  }
  return propres;
}

/** Le catalogue de ce module, depuis les fiches de `mouvements.json`. */
export function catalogue_depuis(mouvements) {
  const catalogue = {};
  for (const [nom, fiche] of Object.entries(mouvements)) {
    catalogue[nom] = {
      variante_facile: fiche.variante_facile ?? null,
      variante_difficile: fiche.variante_difficile ?? null,
      // `mouvements.json` nomme la fonction de detection ; la fiche Python
      // dit seulement si elle existe. C'est cette seconde forme qu'on garde.
      analyse_la_pose: fiche.analyse_la_pose ?? Boolean(fiche.detection),
    };
  }
  return catalogue;
}

/** L'original puis ses variantes de plus en plus faciles. */
export function chaine(original, catalogue) {
  const noms = [original];
  let suivant = catalogue[original]?.variante_facile ?? null;
  while (suivant && !noms.includes(suivant) && suivant in catalogue) {
    noms.push(suivant);
    suivant = catalogue[suivant]?.variante_facile ?? null;
  }
  return noms;
}

/** Le mouvement que `nom_joue` remplace pour ce profil, ou null. */
export function original_de(nom_joue, variantes) {
  for (const [original, joue] of Object.entries(normaliser(variantes))) {
    if (joue === nom_joue) return original;
  }
  return null;
}

function _jouable(nom, catalogue) {
  return Boolean(catalogue[nom]?.analyse_la_pose);
}

export class Variantes {
  constructor(baremes, seuils_retour = {}) {
    this.baremes = baremes;
    this.seuils_retour = seuils_retour ?? {};
  }

  /** Une variante doit se mesurer dans la meme unite que l'original. */
  _compatibles(original, joue) {
    if (
      this.baremes.est_suivi_par_le_moteur(original) &&
      this.baremes.est_suivi_par_le_moteur(joue)
    ) {
      return this.baremes.unite(original) === this.baremes.unite(joue);
    }
    return true;
  }

  /** Le mouvement a jouer a la place de `nom` dans un bloc, ou null. */
  substitution(nom, mode, variantes, catalogue) {
    if (mode === MODE_ECHAUFFEMENT) return null;
    const joue = normaliser(variantes)[nom];
    if (!joue || !_jouable(joue, catalogue) || !this._compatibles(nom, joue)) {
      return null;
    }
    return joue;
  }

  /**
   * Remplace, dans une seance **qu'on va jouer**, les mouvements substitues.
   *
   * A appeler **avant** `objectifs.appliquer_a_circuit`, pour que l'objectif
   * soit celui de la variante. Jamais sur des blocs destines au stockage.
   */
  appliquer_au_circuit(circuit, variantes, catalogue, exercice_pour) {
    const remplaces = {};
    for (const bloc of circuit.exercices) {
      const joue = this.substitution(bloc.exercice.nom, bloc.mode, variantes, catalogue);
      if (joue === null) continue;
      remplaces[bloc.exercice.nom] = joue;
      bloc.remplace = bloc.exercice.nom;
      bloc.exercice = exercice_pour(joue);
      bloc.cible_manuelle = null;
    }
    for (const bloc of circuit.exercices) {
      if (bloc.entrelace_avec && bloc.entrelace_avec in remplaces) {
        bloc.entrelace_avec = remplaces[bloc.entrelace_avec];
      }
    }
    return circuit;
  }

  /**
   * Les mouvements entre lesquels choisir pour un bloc, avant de le jouer :
   * l'original, puis chaque variante que `definir` accepterait. Vide quand il
   * n'y a rien a choisir.
   */
  versions(original, mode, catalogue) {
    if (mode === MODE_ECHAUFFEMENT || !(original in catalogue)) return [];
    const noms = [
      original,
      ...chaine(original, catalogue)
        .slice(1)
        .filter((nom) => _jouable(nom, catalogue) && this._compatibles(original, nom)),
    ];
    return noms.length > 1 ? noms : [];
  }

  /**
   * La table apres « pour `original`, je joue `joue` ». Leve sur un refus,
   * comme le Python : point d'entree unique de l'ecriture.
   */
  definir(variantes, original, joue, catalogue) {
    const nouvelles = normaliser(variantes);
    if (joue === null || joue === undefined || joue === original) {
      delete nouvelles[original];
      return nouvelles;
    }
    if (!chaine(original, catalogue).slice(1).includes(joue)) {
      throw new Error(`${joue} n'est pas une variante de ${original}`);
    }
    if (!_jouable(joue, catalogue) || !this._compatibles(original, joue)) {
      throw new Error(`${joue} ne peut pas remplacer ${original}`);
    }
    nouvelles[original] = joue;
    return nouvelles;
  }

  /** La variante a-t-elle prouve sa performance de retour ? */
  retour_atteint(nom_joue, niveaux) {
    const seuil = this.seuils_retour[nom_joue];
    if (!seuil) return false;
    const requis = this.baremes.niveau_pour(nom_joue, 0, seuil[0], seuil[1]);
    const acquis = niveaux[nom_joue]?.niveau ?? null;
    return requis !== null && requis !== undefined && acquis !== null && acquis >= requis;
  }

  /**
   * Ce qu'il faut proposer sous chaque ligne d'historique :
   * `{seance_id: {nom: {sens, original, vers}}}`. Memes regles que le Python
   * — plus facile sous un echec au palier 1 ou apres une bascule en seance,
   * plus dur sous une variante qui a prouve son retour, et seulement sur la
   * derniere seance ou l'exercice apparait.
   */
  propositions(seances, jugements, variantes, catalogue, niveaux) {
    variantes = normaliser(variantes);
    const vues = new Set();
    const resultat = {};
    for (const seance of seances) {
      const identifiant = seance.id ?? null;
      const lignes = (seance.exercices ?? []).map((exercice) => exercice.nom);
      const par_cle = new Map();
      for (const nom of lignes) {
        if (vues.has(nom)) continue;
        const proposition = this._proposition(
          nom, lignes, jugements[identifiant]?.[nom] ?? null,
          variantes, catalogue, niveaux,
        );
        // La derniere ligne d'une meme cle l'emporte, sans changer de place :
        // un `Map` garde l'ordre de la premiere insertion, comme un `dict`.
        if (proposition !== null) par_cle.set(proposition.original, [nom, proposition]);
      }
      for (const nom of lignes) vues.add(nom);
      if (par_cle.size) {
        resultat[identifiant] = Object.fromEntries([...par_cle.values()]);
      }
    }
    return resultat;
  }

  _racine(nom, lignes, variantes, catalogue) {
    const original = original_de(nom, variantes);
    if (original !== null) return original;
    for (const autre of lignes) {
      if (autre !== nom && catalogue[autre]?.variante_facile === nom) {
        return this._racine(autre, lignes.filter((l) => l !== nom), variantes, catalogue);
      }
    }
    return nom;
  }

  _proposition(nom, lignes, jugement, variantes, catalogue, niveaux) {
    const fiche = catalogue[nom] ?? {};
    const cle = this._racine(nom, lignes, variantes, catalogue);

    if (jugement !== null && !jugement.reussi) {
      const facile = fiche.variante_facile ?? null;
      const bascule = facile !== null && lignes.includes(facile);
      if (facile && (jugement.base === 1 || bascule)) {
        if (variantes[cle] !== facile) {
          try {
            this.definir(variantes, cle, facile, catalogue);
          } catch {
            return null;
          }
          return { sens: "facile", original: cle, vers: facile };
        }
      }
      return null;
    }

    if (variantes[cle] === nom && this.retour_atteint(nom, niveaux)) {
      const dur = fiche.variante_difficile ?? null;
      if (dur) return { sens: "difficile", original: cle, vers: dur };
    }
    return null;
  }
}

/**
 * Ce qu'un programme dit d'une exigence jouee sous une variante : `{nom,
 * niveau}` ou null. L'avancement de l'exigence n'en est pas modifie.
 */
export function via_variante(nom, variantes, niveaux) {
  const joue = normaliser(variantes)[nom];
  if (!joue) return null;
  return { nom: joue, niveau: niveaux[joue]?.niveau ?? null };
}
