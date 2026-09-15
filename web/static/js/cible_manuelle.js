// Les quatre fonctions de **cible manuelle**, isolees dans un module sans
// aucune dependance.
//
// Elles vivaient dans `objectifs.js`, d'ou `circuit.js` devrait les importer
// pour resoudre le drapeau a l'export — sauf que `niveaux.js` importe deja
// `circuit.js`, et qu'un import d'`objectifs.js` depuis `circuit.js` fermerait
// le cycle. Le Python contourne le meme cycle par un import differe en corps
// de fonction ; les modules ES n'ont pas cet echappatoire, un cycle y laisse
// une liaison non initialisee et la page meurt au chargement avec un
// `ReferenceError` qui ne nomme aucun des deux fichiers fautifs.
//
// Ces fonctions ne dependent de rien — ni bareme, ni historique, ni profil
// connecte : les sortir ici est donc gratuit, et ce module est desormais une
// **feuille** que n'importe qui peut importer sans y penser. `objectifs.js`
// les re-exporte pour que les appelants existants, harnais compris, ne voient
// aucune difference.
//
// Rappel de la regle qu'elles portent : les seances sont partagees entre
// profils, donc une cible figee a la main appartient a **celui qui l'a figee**,
// pas a la seance.

/**
 * Normalise la valeur stockee en ensemble d'identifiants de profils.
 *
 * Les seances sont partagees entre profils : une cible figee a la main
 * appartient donc a **celui qui l'a figee**, pas a la seance. L'ancien
 * booleen doit continuer a se lire, sans quoi les marques posees avant les
 * profils disparaîtraient silencieusement.
 *
 * Une valeur qu'aucun format connu ne couvre est lue comme « personne » : un
 * faux positif fige une cible que le moteur ne fera plus jamais bouger, et
 * c'est un blocage **silencieux**, alors qu'un faux negatif se voit des le
 * prochain affichage et se corrige d'un clic.
 */
export function profils_cible_manuelle(valeur) {
  if (valeur === null || valeur === undefined || valeur === false) return new Set();
  // `true` date d'avant les profils : la marque appartient au profil 1, celui
  // qui a herite de tout l'historique a la migration.
  if (valeur === true) return new Set([1]);
  if (typeof valeur === "number" && Number.isInteger(valeur)) return new Set([valeur]);
  if (Array.isArray(valeur)) {
    return new Set(valeur.filter((p) => typeof p === "number" && Number.isInteger(p)));
  }
  return new Set();
}

function _valeur_cible_manuelle(bloc) {
  // Les blocs sont soit des dictionnaires (JSON des seances), soit des
  // `BlocExercice` : l'acces est le meme en JavaScript, contrairement au
  // Python qui doit distinguer les deux.
  return bloc.cible_manuelle ?? null;
}

/** Ce bloc est-il fige a la main **pour ce profil** ? */
export function est_cible_manuelle(bloc, utilisateur_id) {
  if (utilisateur_id === null || utilisateur_id === undefined) return false;
  return profils_cible_manuelle(_valeur_cible_manuelle(bloc)).has(Number(utilisateur_id));
}

/**
 * Nouvelle valeur a stocker apres decision pour un seul profil.
 *
 * Rend null quand plus personne ne fige ce bloc, pour que l'appelant retire
 * la cle plutot que d'ecrire une liste vide. Les identifiants des autres
 * profils sont conserves : c'est tout l'objet du format en liste.
 */
export function definir_cible_manuelle(valeur_actuelle, manuelle, utilisateur_id) {
  const profils = profils_cible_manuelle(valeur_actuelle);
  if (utilisateur_id !== null && utilisateur_id !== undefined) {
    if (manuelle) profils.add(Number(utilisateur_id));
    else profils.delete(Number(utilisateur_id));
  }
  const tries = [...profils].sort((a, b) => a - b);
  return tries.length ? tries : null;
}

/**
 * Combine la decision du profil connecte et les marques deja sur le disque.
 *
 * Indispensable parce qu'un enregistrement de seance **reecrit tous les
 * blocs** : le formulaire renvoie ce que le profil connecte voit,
 * c'est-a-dire rien des autres. Sans fusion, la premiere sauvegarde du second
 * profil effacerait les cibles figees du premier — sur des blocs qu'il n'a
 * jamais touches.
 */
export function fusionner_cible_manuelle(valeur_entrante, valeur_stockee, utilisateur_id) {
  const autres = profils_cible_manuelle(valeur_stockee);
  if (utilisateur_id === null || utilisateur_id === undefined) {
    const tries = [...autres].sort((a, b) => a - b);
    return tries.length ? tries : null;
  }
  const profil = Number(utilisateur_id);
  autres.delete(profil);
  if (profils_cible_manuelle(valeur_entrante).has(profil)) autres.add(profil);
  const tries = [...autres].sort((a, b) => a - b);
  return tries.length ? tries : null;
}

/**
 * Une seance jouee jusqu'au bout fait de sa cible figee la reference.
 *
 * Figer une cible est une exception provisoire : le moteur propose autre
 * chose, l'utilisateur impose sa valeur, et le badge orange rend ce
 * decrochage visible. Une fois la seance **terminee** a cette cible,
 * l'exception n'en est plus une — l'historique porte desormais la performance
 * realisee, et c'est d'elle que `ressenti._cible_visee` repartira. Lever la
 * marque ne perd donc pas la valeur : elle rebranche le moteur *sur* elle.
 *
 * Une seance abandonnee ne prouve rien et garde sa marque.
 *
 * A ne pas confondre avec `marquer_cibles_manuelles`, qui *detecte* un ecart
 * au palier propose : appliquee ici, elle effacerait aussi les marques des
 * blocs que la seance n'a pas joues.
 *
 * Rend true si au moins une marque a ete levee.
 */
export function enteriner_cibles_manuelles(blocs, utilisateur_id) {
  let leve = false;
  for (const bloc of blocs) {
    if (!est_cible_manuelle(bloc, utilisateur_id)) continue;
    const valeur = definir_cible_manuelle(
      _valeur_cible_manuelle(bloc), false, utilisateur_id
    );
    if (valeur === null) delete bloc.cible_manuelle;
    else bloc.cible_manuelle = valeur;
    leve = true;
  }
  return leve;
}
