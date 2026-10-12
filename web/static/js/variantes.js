// Jouer une variante plus facile a la
// place d'un mouvement, et en revenir.
//
// `node scripts/comparer_variantes.mjs` rejoue des questions figees et compare
// aux reponses figees.
//
// Deux regles a retenir. **Une substitution est une preference du profil**,
// jamais une donnee de seance : les seances sont partagees. Et **elle ne doit jamais atteindre le fichier des seances**
// — `appliquer_au_circuit` ne s'appelle que sur le chemin de jeu (`demarrer()`),
// l'affichage interroge `substitution` sans rien reecrire.
//
// Le bareme est injecte (`Baremes`), comme dans `objectifs.js` : il porte
// l'unite de chaque exercice et `niveau_pour`, et c'est lui qui connait le
// materiel du profil. Les seuils de retour viennent de `reglages.json`
// (`variantes.retour`), via `composer_baremes`.

import { note_valide } from "./calibration.js";

const MODE_ECHAUFFEMENT = "echauffement";

/**
 * La table d'un profil sous une forme toujours exploitable.
 *
 * Aucune migration n'ajoute le champ (`migrer` ne fait qu'en renommer les
 * cles) : un profil anterieur ou importe de l'ancienne base ne l'a pas, et « pas de champ » veut dire « aucune variante »
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
      // `mouvements.json` nomme la fonction de detection ; il suffit ici de
      // savoir si elle existe.
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
  /**
   * `niveaux` est une instance de `Niveaux` : `montees` en tire
   * `niveau_prouve_par`, la lecture d'une ligne d'historique.
   *
   * `departs` est la table `variantes.depart` de `reglages.json` : pour la
   * tete de chaque famille, la note a partir de laquelle on demarre sur
   * chacun de ses mouvements (`selon_la_note`).
   */
  constructor(baremes, seuils_retour = {}, niveaux = null, departs = {}) {
    this.baremes = baremes;
    this.seuils_retour = seuils_retour ?? {};
    this.niveaux = niveaux;
    this.departs = departs ?? {};
  }

  /**
   * Le profil peut-il charger ce mouvement ? Un bareme qui ne le sait pas
   * (une page sans materiel) repond oui : la regle ne s'applique alors pas.
   */
  _chargeable(nom) {
    return this.baremes.chargeable?.(nom) ?? true;
  }

  /**
   * Le mouvement qu'on jouera vraiment a la place de `nom` : lui-meme s'il
   * se charge, sinon la premiere variante plus facile qui se charge et se
   * mesure pareil. null si rien dans la chaine ne convient.
   *
   * **Le materiel n'est jamais ecrit dans la table** : il change (on achete
   * une paire de 8 kg), et la table doit alors redevenir ce qu'elle etait.
   */
  _jouable_avec_le_materiel(nom, original, catalogue) {
    let joue = nom;
    const vus = new Set();
    while (joue && !this._chargeable(joue)) {
      vus.add(joue);
      const facile = catalogue[joue]?.variante_facile ?? null;
      if (!facile || vus.has(facile) || !_jouable(facile, catalogue) || !this._compatibles(original, facile)) {
        return null;
      }
      joue = facile;
    }
    return joue;
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
    let joue = normaliser(variantes)[nom] ?? null;
    if (joue && (!_jouable(joue, catalogue) || !this._compatibles(nom, joue))) joue = null;
    // Le materiel par-dessus la preference : un squat charge sans halteres
    // se joue a vide, que le profil l'ait choisi ou non.
    const possible = this._jouable_avec_le_materiel(joue ?? nom, nom, catalogue);
    if (possible === null || possible === nom) return null;
    return possible;
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
    // Un original que le materiel ne permet pas ne se propose pas : choisir
    // un squat charge sans halteres serait un choix sans effet, et la liste
    // le presenterait comme « la version complete ». L'ecran dit alors
    // simplement ce qui est joue a sa place.
    if (!this._chargeable(original)) return [];
    const noms = [
      original,
      ...chaine(original, catalogue)
        .slice(1)
        .filter((nom) => _jouable(nom, catalogue) && this._compatibles(original, nom)),
    ];
    return noms.length > 1 ? noms : [];
  }

  /**
   * La table apres « pour `original`, je joue `joue` ». Leve sur un refus :
   * point d'entree unique de l'ecriture.
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

  /**
   * La table apres le choix du mouvement de depart de chaque famille **jamais
   * jouee**, selon la note d'athlete.
   *
   * `departs` donne, pour la tete d'une famille, la note a partir de laquelle
   * on demarre sur chacun de ses mouvements : on part du plus dur que la note
   * atteint. Sans note valide, du premier de la table — faute de savoir, on
   * part du bas, comme `niveau_de_depart`.
   *
   * Une famille dont un mouvement a deja ete joue, ou porte un ancrage, n'est
   * plus touchee : c'est alors l'historique qui sait, et les montees et
   * descentes qui decident. **Le choix est ecrit dans la table**, au
   * demarrage de la premiere seance (l'appelant l'enregistre) : relu a chaque
   * lecture, il s'effacerait des la seance suivante, la famille ayant
   * entre-temps ete jouee.
   */
  selon_la_note(variantes, note, seances, ancrages, catalogue) {
    let table = normaliser(variantes);
    const joues = new Set();
    for (const seance of seances ?? []) {
      for (const exercice of seance.exercices ?? []) joues.add(exercice.nom);
    }
    for (const nom of Object.keys(ancrages ?? {})) joues.add(nom);

    for (const [tete, seuils] of Object.entries(this.departs)) {
      if (!(tete in catalogue)) continue;
      const famille = chaine(tete, catalogue);
      if (famille.some((nom) => joues.has(nom))) continue;
      const candidats = Object.entries(seuils ?? {})
        .filter(([nom]) => famille.includes(nom))
        .sort(([, a], [, b]) => a - b);
      if (!candidats.length) continue;
      const atteints = note_valide(note) ? candidats.filter(([, minimum]) => minimum <= note) : [];
      const [depart] = atteints.at(-1) ?? candidats[0];
      try {
        table = this.definir(table, tete, depart, catalogue);
      } catch {
        // Une table de depart qui designe une variante injouable : la famille
        // garde sa preference, `verifier_donnees` le signale a froid.
      }
    }
    return table;
  }

  /**
   * Cette ligne d'historique prouve-t-elle la performance de retour ? Lue sur
   * la seance et jamais sur le record — sinon un retour en
   * arriere remonterait tout seul a la seance suivante.
   */
  retour_prouve_par(ligne, catalogue = {}) {
    const seuil = this.seuils_retour[ligne.nom];
    if (!seuil) return false;
    // Vers une forme chargee, le seuil se lit « avec le premier haltere du
    // profil », traduit a vide par la part du corps (`Baremes`) : il depend
    // donc du materiel. Entre variantes sans charge, il se lit tel quel.
    const dur = catalogue[ligne.nom]?.variante_difficile ?? null;
    const a_vide = dur ? this.baremes.volume_a_vide_pour_charger?.(ligne.nom, dur, seuil[0], seuil[1]) ?? null : null;
    const requis = a_vide !== null
      ? this.baremes.niveau_pour_volume(ligne.nom, a_vide)
      : this.baremes.niveau_pour(ligne.nom, 0, seuil[0], seuil[1]);
    const prouve = this.niveaux.niveau_prouve_par(ligne);
    return requis !== null && requis !== undefined && prouve !== null && prouve >= requis;
  }

  /**
   * La table apres cette seance, et les crans qu'elle a fait monter :
   * `[table, [{original, depuis, vers}]]`. Un cran par seance et par cle ;
   * rien sur une seance abandonnee.
   */
  montees(variantes, seance, catalogue) {
    let table = normaliser(variantes);
    seance = seance ?? {};
    if (seance.statut === "abandoned") return [table, []];
    const faites = [];
    const vues = new Set();
    for (const ligne of seance.exercices ?? []) {
      const cle = original_de(ligne.nom, table);
      if (cle === null || vues.has(cle)) continue;
      const dur = catalogue[ligne.nom]?.variante_difficile ?? null;
      // On ne monte pas vers ce que le materiel ne permet pas : la montee
      // serait aussitot defaite par `substitution`, et l'ecran l'aurait
      // annoncee pour rien.
      if (!dur || !this._chargeable(dur) || !this.retour_prouve_par(ligne, catalogue)) continue;
      try {
        table = this.definir(table, cle, dur, catalogue);
      } catch {
        continue;
      }
      vues.add(cle);
      faites.push({ original: cle, depuis: ligne.nom, vers: dur });
    }
    return [table, faites];
  }

  /**
   * Ce qu'il faut proposer sous chaque ligne d'historique :
   * `{seance_id: {nom: {sens, original, vers}}}`. Plus facile sous un echec
   * au palier 1, sous un echec **au depart** (voir plus bas), ou apres une
   * bascule en seance, et seulement sur la derniere seance ou l'exercice
   * apparait. « Plus dur » n'est plus propose : `montees` le fait d'elle-meme.
   *
   * **Le depart**, c'est un mouvement jamais reussi dont aucune variante plus
   * facile n'est reussie non plus : on y est arrive par la note, pas par une
   * montee. Quelqu'un qui se note 6 et ne tient qu'une pompe part de 4x8 ;
   * sans cette regle, il lui faudrait descendre jusqu'au palier 1, a coups de
   * « trop dur », avant qu'on lui propose les genoux. Apres une **montee**, un
   * echec fait seulement refaire la seance : proposer de redescendre aussitot
   * renvoyait a vide celui qui venait de passer au squat charge, qui remontait
   * a la seance suivante, et ainsi de suite. Un niveau ancre n'est pas compte
   * (la page qui affiche les propositions ne passe pas les ancrages).
   */
  propositions(seances, jugements, variantes, catalogue) {
    variantes = normaliser(variantes);
    const prouves = this.niveaux ? this.niveaux.niveaux_par_exercice(seances) : {};
    const au_depart = (nom) => chaine(nom, catalogue).every((m) => !(m in prouves));
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
          variantes, catalogue, au_depart(nom),
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

  _proposition(nom, lignes, jugement, variantes, catalogue, au_depart = false) {
    if (jugement === null || jugement.reussi) return null;
    const facile = catalogue[nom]?.variante_facile ?? null;
    if (!facile || !(jugement.base === 1 || au_depart || lignes.includes(facile))) return null;
    const cle = this._racine(nom, lignes, variantes, catalogue);
    // « Jouer X a la place de X » n'est pas une proposition : `definir` y
    // verrait une suppression et ne leverait pas. Ca n'arrive que sur un
    // catalogue dont les chaines bouclent.
    if (variantes[cle] === facile || cle === facile) return null;
    try {
      this.definir(variantes, cle, facile, catalogue);
    } catch {
      return null;
    }
    return { sens: "facile", original: cle, vers: facile };
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
