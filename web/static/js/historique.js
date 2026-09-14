// Jumeau de historique/database.py — l'historique des seances.
//
// Ce n'est pas un portage de SQL : c'est un portage de *ce que le SQL
// produit*. La base y est un objet JavaScript ordinaire, et toutes les
// fonctions de ce module sont pures au sens ou elles ne touchent ni au disque
// ni au reseau : elles recoivent la base, la lisent ou la modifient, et
// rendent exactement les memes structures que leurs jumelles Python.
//
// Trois raisons a ce decoupage, et la troisieme est la plus importante.
// (1) L'historique d'une personne tient largement en memoire — quelques
// centaines de seances —, et le Python recalcule deja tout a la lecture
// plutot que de le stocker. (2) L'export/import devient trivial : l'objet
// *est* le fichier. (3) Surtout, ca rend le portage **verifiable** : un
// harnais peut ecrire les memes seances des deux cotes et diffuser les
// resultats, ce qu'il ne pourrait pas faire si la logique etait melee a
// IndexedDB, qui n'existe pas dans Node.
//
// La persistance vit a cote, dans `stockage.js`, et ne fait que charger et
// sauver cet objet.

/** La version du format, ecrite dans chaque export. */
export const VERSION_BASE = 1;

/**
 * Une base vide.
 *
 * Les cinq collections reprennent les cinq tables SQLite, y compris leurs
 * cles etrangeres : `exercices` porte `seance_id`, `series_realisees` porte
 * `exercice_id`. Aplatir la hierarchie serait plus commode a lire mais
 * rendrait le portage de `progression/` — etape suivante — infidele, puisque
 * tout son calcul part de ces jointures.
 *
 * `utilisateur_id` ne figure que sur les deux tables *racines* (`seances` et
 * `corrections_niveaux`) ; `exercices` et `series_realisees` en heritent par
 * leur cle etrangere et ne doivent pas le dupliquer.
 */
export function base_vide() {
  return {
    version: VERSION_BASE,
    // Les identifiants sont attribues par un compteur par collection, comme
    // AUTOINCREMENT : strictement croissants, jamais reutilises apres une
    // suppression. `progression/` s'appuie sur cette croissance pour dater
    // les ancrages, la date stockee etant en JJ/MM/AAAA — format dans lequel
    // une comparaison de chaines est fausse (31/08 > 02/09).
    prochains_id: { utilisateurs: 1, seances: 1, exercices: 1, series_realisees: 1, corrections_niveaux: 1 },
    utilisateurs: [],
    seances: [],
    exercices: [],
    series_realisees: [],
    corrections_niveaux: [],
    // **Pas une table SQLite** : les seances editees sur cet appareil. Cote
    // Python elles vivent dans `seances_personnalisees.json`, que seul le
    // poste fixe sait ecrire ; un site statique n'a pas de disque a modifier,
    // donc l'appareil les garde avec le reste de sa base.
    //
    // Un objet et non un tableau, parce que c'est la forme du fichier qu'il
    // remplace : un nom de seance vers sa liste de blocs.
    seances_locales: {},
  };
}

function _prochain_id(base, collection) {
  const id = base.prochains_id[collection];
  base.prochains_id[collection] = id + 1;
  return id;
}

/**
 * Horodatage au format du Python : "JJ/MM/AAAA HH:MM".
 *
 * Une fonction et non `new Date()` en dur, pour la meme raison que
 * `Circuit.maintenant` : une verification doit pouvoir figer le temps.
 */
export function horodatage(maintenant = () => new Date()) {
  const d = maintenant();
  const deux = (n) => String(n).padStart(2, "0");
  return `${deux(d.getDate())}/${deux(d.getMonth() + 1)}/${d.getFullYear()} ${deux(d.getHours())}:${deux(d.getMinutes())}`;
}

// ==========================================
// PROFILS
// ==========================================

export function lister_utilisateurs(base) {
  return base.utilisateurs
    .map((u) => ({ ...u }))
    .sort((a, b) => a.nom.localeCompare(b.nom, "fr"));
}

export function creer_utilisateur(base, nom, maintenant) {
  const propre = (nom ?? "").trim();
  if (!propre) throw new Error("Nom requis");
  if (base.utilisateurs.some((u) => u.nom.toLowerCase() === propre.toLowerCase())) {
    throw new Error("Ce nom existe déjà");
  }
  const utilisateur = {
    id: _prochain_id(base, "utilisateurs"),
    nom: propre,
    cree_le: horodatage(maintenant),
    // `creer_utilisateur` pose explicitement 0 : le defaut a 1 de la
    // migration SQL existe pour les profils *deja la*, pas pour un nouveau
    // venu, qui doit passer par le questionnaire de materiel.
    onboarding_termine: 0,
    seance_initiale: null,
    programme_choisi: null,
    materiel: null,
  };
  base.utilisateurs.push(utilisateur);
  return { ...utilisateur };
}

// ==========================================
// SEANCES
// ==========================================

/**
 * Ecrit une seance complete et rend son identifiant.
 *
 * Le retour est indispensable a l'ecran de fin, qui doit pouvoir annoter les
 * lignes qui viennent d'etre creees (`enregistrer_ressentis`).
 */
export function enregistrer_seance(
  base,
  { duree, exercices, statut = "finished", nom_seance = null, utilisateur_id, maintenant }
) {
  const seance_id = _prochain_id(base, "seances");
  base.seances.push({
    id: seance_id,
    date: horodatage(maintenant),
    duree,
    statut,
    nom_seance,
    utilisateur_id,
  });

  for (const exercice of exercices) {
    const exercice_id = _prochain_id(base, "exercices");
    base.exercices.push({
      id: exercice_id,
      seance_id,
      nom: exercice.nom,
      series: exercice.series,
      repetitions: exercice.repetitions,
      poids: exercice.poids ?? 0,
      mode: exercice.mode ?? null,
      duree: exercice.duree ?? 0,
      commentaire: exercice.commentaire ?? "",
      // Les cibles retombent sur le realise quand elles ne sont pas fournies,
      // exactement comme cote Python : une seance jouee sans objectif ne doit
      // pas se relire comme un echec.
      series_cibles: exercice.series_cibles ?? exercice.series,
      repetitions_cibles: exercice.repetitions_cibles ?? 0,
      duree_cible: exercice.duree_cible ?? exercice.duree ?? 0,
      entrelace_avec: exercice.entrelace_avec ?? null,
      repos_entre_series: exercice.repos_entre_series ?? 0,
      repos_apres: exercice.repos_apres ?? 0,
      ressenti: null,
    });

    for (const serie of exercice.series_detaillees ?? []) {
      base.series_realisees.push({
        id: _prochain_id(base, "series_realisees"),
        exercice_id,
        numero: serie.serie ?? serie.numero,
        repetitions: serie.repetitions ?? 0,
        poids: serie.poids ?? 0,
        duree: serie.duree ?? 0,
        // Stocke en 0/1 comme en SQLite, relu en booleen : c'est la forme
        // qu'un export doit conserver pour rester relisable par le Python.
        completee: serie.completee ? 1 : 0,
      });
    }
  }

  return seance_id;
}

function _series_de(base, exercice_id) {
  return base.series_realisees
    .filter((s) => s.exercice_id === exercice_id)
    .map((s) => ({
      serie: s.numero,
      repetitions: s.repetitions,
      poids: s.poids,
      duree: s.duree,
      completee: Boolean(s.completee),
    }));
}

/**
 * Tout l'historique d'un profil, **le plus recent en tete**.
 *
 * L'ordre compte : `progression.niveaux.montees_de_niveau` rejoue le meme
 * historique dans l'ordre inverse, et s'appuie sur celui-ci pour le faire.
 */
export function recuperer_historique(base, utilisateur_id) {
  return base.seances
    .filter((s) => s.utilisateur_id === utilisateur_id)
    .sort((a, b) => b.id - a.id)
    .map((seance) => ({
      id: seance.id,
      date: seance.date,
      duree: seance.duree,
      statut: seance.statut || "finished",
      nom: seance.nom_seance,
      exercices: base.exercices
        .filter((e) => e.seance_id === seance.id)
        .map((exercice) => ({
          nom: exercice.nom,
          series: exercice.series,
          repetitions: exercice.repetitions,
          poids: exercice.poids || 0,
          mode: exercice.mode || "repetitions",
          duree: exercice.duree || 0,
          commentaire: exercice.commentaire || "",
          series_cibles: exercice.series_cibles || exercice.series,
          repetitions_cibles: exercice.repetitions_cibles || 0,
          duree_cible: exercice.duree_cible || 0,
          entrelace_avec: exercice.entrelace_avec,
          repos_entre_series: exercice.repos_entre_series || 0,
          repos_apres: exercice.repos_apres || 0,
          ressenti: exercice.ressenti || "",
          series_detaillees: _series_de(base, exercice.id),
        })),
    }));
}

/**
 * Annote d'un ressenti les exercices d'une seance deja ecrite.
 *
 * Une mise a jour et non une insertion : la seance est enregistree par la
 * boucle image des la phase terminale, donc **avant** que l'utilisateur n'ait
 * vu l'ecran de fin. La saisie arrive toujours apres coup.
 */
export function enregistrer_ressentis(base, seance_id, ressentis, echelle) {
  let modifies = 0;
  for (const [nom, valeur] of Object.entries(ressentis ?? {})) {
    if (valeur && echelle && !echelle.includes(valeur)) {
      throw new Error(`Ressenti inconnu : ${valeur}`);
    }
    for (const exercice of base.exercices) {
      if (exercice.seance_id === seance_id && exercice.nom === nom) {
        exercice.ressenti = valeur || null;
        modifies += 1;
      }
    }
  }
  return modifies;
}

/**
 * Supprime une seance et tout ce qui en depend.
 *
 * Le filtre par profil transforme « la seance d'un autre » en « seance
 * introuvable » : l'identifiant vient de l'interface, il ne doit pas suffire a
 * atteindre l'historique de quelqu'un d'autre. D'ou une **exception** et non
 * un `false` : un refus silencieux passerait pour une suppression reussie.
 */
export function supprimer_seance(base, seance_id, utilisateur_id) {
  const seance = base.seances.find(
    (s) => s.id === seance_id && s.utilisateur_id === utilisateur_id
  );
  if (seance === undefined) throw new Error(`Séance ${seance_id} introuvable`);

  const ids = new Set(
    base.exercices.filter((e) => e.seance_id === seance_id).map((e) => e.id)
  );
  base.series_realisees = base.series_realisees.filter((s) => !ids.has(s.exercice_id));
  base.exercices = base.exercices.filter((e) => e.seance_id !== seance_id);
  base.seances = base.seances.filter((s) => s.id !== seance_id);
}

// ==========================================
// ANCRAGES DE NIVEAU
// ==========================================

/**
 * Le journal des recalages de niveau : on ajoute, on n'ecrase jamais.
 *
 * Le repere chronologique est `apres_seance_id` et **pas la date** : les dates
 * sont en JJ/MM/AAAA, format dans lequel une comparaison de chaines est
 * fausse, alors que les identifiants sont strictement croissants.
 */
export function enregistrer_ancrage(
  base, nom_exercice, niveau, { raison = "", utilisateur_id, maintenant } = {}
) {
  // Le repere chronologique est calcule, jamais fourni : c'est la derniere
  // seance **de ce profil**, une seance faite par quelqu'un d'autre
  // entre-temps rendant l'ancrage posterieur a des seances qu'il n'a pas
  // vocation a effacer.
  const apres_seance_id = base.seances
    .filter((s) => s.utilisateur_id === utilisateur_id)
    .reduce((maximum, s) => Math.max(maximum, s.id), 0);

  const ancrage = {
    id: _prochain_id(base, "corrections_niveaux"),
    nom_exercice,
    niveau: Math.trunc(niveau),
    date: horodatage(maintenant),
    apres_seance_id,
    raison,
    utilisateur_id,
  };
  base.corrections_niveaux.push(ancrage);
  return ancrage.id;
}

/** Le **dernier** ancrage de chaque exercice — seul celui-la compte. */
export function recuperer_ancrages(base, utilisateur_id) {
  const derniers = {};
  for (const a of base.corrections_niveaux) {
    if (a.utilisateur_id !== utilisateur_id) continue;
    const precedent = derniers[a.nom_exercice];
    if (precedent === undefined || a.id > precedent.id) derniers[a.nom_exercice] = a;
  }
  const table = {};
  for (const [nom, a] of Object.entries(derniers)) {
    table[nom] = {
      niveau: a.niveau,
      date: a.date,
      apres_seance_id: a.apres_seance_id || 0,
      raison: a.raison || "",
      // L'identifiant fait partie du releve cote Python : c'est lui que
      // `supprimer_ancrage` prend en argument depuis l'ecran des records.
      id: a.id,
    };
  }
  return table;
}

/** Le journal complet d'un exercice, du plus recent au plus ancien. */
export function recuperer_historique_ancrages(base, nom_exercice, utilisateur_id) {
  return base.corrections_niveaux
    .filter((a) => a.nom_exercice === nom_exercice && a.utilisateur_id === utilisateur_id)
    .sort((a, b) => b.id - a.id)
    .map((a) => ({
      id: a.id,
      niveau: a.niveau,
      date: a.date,
      apres_seance_id: a.apres_seance_id || 0,
      raison: a.raison || "",
    }));
}

export function supprimer_ancrage(base, ancrage_id) {
  const avant = base.corrections_niveaux.length;
  base.corrections_niveaux = base.corrections_niveaux.filter((a) => a.id !== ancrage_id);
  return base.corrections_niveaux.length < avant;
}

export function supprimer_ancrages(base, nom_exercice, utilisateur_id) {
  const avant = base.corrections_niveaux.length;
  base.corrections_niveaux = base.corrections_niveaux.filter(
    (a) => !(a.nom_exercice === nom_exercice && a.utilisateur_id === utilisateur_id)
  );
  return avant - base.corrections_niveaux.length;
}

// ==========================================
// EXPORT / IMPORT
// ==========================================

/**
 * La base, prete a etre ecrite dans un fichier.
 *
 * Ce n'est pas un raffinement : le stockage d'un navigateur iOS n'est pas un
 * disque dur, et un historique d'entrainement ne se parie pas sur la
 * bienveillance de Safari. C'est aussi le transfert d'un appareil a l'autre
 * tant qu'aucun serveur n'existe.
 */
// ==========================================
// SEANCES EDITEES SUR L'APPAREIL
// ==========================================

/**
 * Enregistre une seance editee ici.
 *
 * Elle **masque** desormais celle du fichier exporte, exactement comme
 * `seances_personnalisees.json` masque le catalogue Python. La difference est
 * qu'on ne peut pas renvoyer le resultat au fichier : un site statique n'a
 * pas de serveur a qui ecrire. C'est le prix assume de pouvoir modifier une
 * seance depuis l'appareil, et l'ecran doit le rendre visible plutot que de
 * laisser croire que la modification remontera.
 */
export function enregistrer_seance_locale(base, nom, blocs) {
  base.seances_locales = { ...(base.seances_locales ?? {}), [nom]: blocs };
  return nom;
}

/** Rend une seance au fichier : la version deployee redevient la bonne. */
export function oublier_seance_locale(base, nom) {
  if (!base.seances_locales) return false;
  const existait = nom in base.seances_locales;
  delete base.seances_locales[nom];
  return existait;
}

/** Cette seance a-t-elle ete modifiee sur cet appareil ? */
export function est_seance_locale(base, nom) {
  return Boolean(base.seances_locales && nom in base.seances_locales);
}

export function exporter(base) {
  return JSON.stringify({ ...base, exporte_le: horodatage() }, null, 1);
}

/**
 * Relit un export, en refusant ce qu'on ne sait pas relire.
 *
 * Le refus est volontairement bruyant : importer a moitie une sauvegarde,
 * c'est perdre le reste sans que personne ne s'en apercoive avant des
 * semaines.
 */
export function importer(texte) {
  let contenu;
  try {
    contenu = JSON.parse(texte);
  } catch {
    throw new Error("Ce fichier n'est pas une sauvegarde valide.");
  }
  if (contenu.version !== VERSION_BASE) {
    throw new Error(
      `Sauvegarde en version ${contenu.version ?? "inconnue"}, ` +
        `cette application lit la version ${VERSION_BASE}.`
    );
  }
  const base = base_vide();
  for (const collection of [
    "utilisateurs", "seances", "exercices", "series_realisees", "corrections_niveaux",
  ]) {
    if (!Array.isArray(contenu[collection])) {
      throw new Error(`Sauvegarde incomplète : « ${collection} » manque.`);
    }
    base[collection] = contenu[collection];
  }

  // **Une collection ajoutee apres coup est optionnelle**, et c'est une regle
  // et non une tolerance : l'exiger rendrait illisible *toutes* les
  // sauvegardes deja faites, c'est-a-dire precisement celles qu'on voudra
  // relire le jour ou l'appareil aura ete efface. Le refus bruyant vaut pour
  // ce qu'on ne sait pas lire, pas pour ce qui n'existait pas encore.
  if (contenu.seances_locales && typeof contenu.seances_locales === "object") {
    base.seances_locales = contenu.seances_locales;
  }
  // Les compteurs sont recalcules plutot que relus : un export bricole a la
  // main, ou tronque, redonnerait sinon des identifiants deja pris.
  for (const collection of Object.keys(base.prochains_id)) {
    const maximum = base[collection].reduce((m, ligne) => Math.max(m, ligne.id ?? 0), 0);
    base.prochains_id[collection] = maximum + 1;
  }
  return base;
}

/**
 * Records et progression de chaque exercice — jumeau de `statistiques_exercices`.
 *
 * Calcule uniquement sur les seances **terminees** et les series **menees au
 * bout** : une serie interrompue ne prouve rien, et une seance abandonnee non
 * plus. C'est la meme regle que partout ailleurs, et c'est pour ca que les
 * chiffres d'ici et ceux d'un niveau ne se contredisent jamais.
 *
 * `pb` — le record qui compte pour cet exercice — depend de ce qu'il mesure :
 * la duree pour un maintien, le volume des qu'il y a de la charge, les
 * repetitions au poids du corps. Un record de volume serait en effet
 * structurellement nul sur des pompes.
 *
 * `progression` garde une entree par seance, dans l'ordre ou l'historique les
 * rend — le plus recent en tete. C'est a l'affichage d'inverser.
 */
export function statistiques_exercices(seances) {
  const statistiques = {};

  for (const seance of seances) {
    if (seance.statut === "abandoned") continue;

    for (const exercice of seance.exercices ?? []) {
      const series = (exercice.series_detaillees ?? []).filter((s) => s.completee);
      if (!series.length) continue;

      const nom = exercice.nom;
      const poids = Math.max(...series.map((s) => s.poids || 0));
      const repetitions = series.reduce((total, s) => total + (s.repetitions || 0), 0);
      const volume = series.reduce(
        (total, s) => total + (s.poids || 0) * (s.repetitions || 0),
        0
      );
      const duree = series.reduce((total, s) => total + (s.duree || 0), 0);

      const entree = (statistiques[nom] ??= {
        nom,
        mode: exercice.mode ?? "repetitions",
        seances: 0,
        series: 0,
        repetitions: 0,
        volume: 0,
        duree: 0,
        meilleure_charge: { valeur: 0, seance_id: null, date: null },
        meilleures_repetitions: { valeur: 0, seance_id: null, date: null },
        meilleur_volume: { valeur: 0, seance_id: null, date: null },
        meilleure_duree: { valeur: 0, seance_id: null, date: null },
        progression: [],
      });

      entree.seances += 1;
      entree.series += series.length;
      entree.repetitions += repetitions;
      entree.volume += volume;
      entree.duree += duree;
      entree.progression.push({
        seance_id: seance.id,
        date: seance.date,
        repetitions,
        volume,
        duree,
      });

      for (const [cle, valeur] of [
        ["meilleure_charge", poids],
        ["meilleures_repetitions", repetitions],
        ["meilleur_volume", volume],
        ["meilleure_duree", duree],
      ]) {
        if (valeur > entree[cle].valeur) {
          entree[cle] = { valeur, seance_id: seance.id, date: seance.date };
        }
      }

      if (["maintien", "chrono"].includes(exercice.mode)) entree.pb = entree.meilleure_duree;
      else if (poids > 0) entree.pb = entree.meilleur_volume;
      else entree.pb = entree.meilleures_repetitions;
    }
  }

  return statistiques;
}
