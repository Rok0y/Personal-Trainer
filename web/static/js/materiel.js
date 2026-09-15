// Jumeau de core/materiel.py — l'inventaire d'halteres et d'accessoires.
//
// C'est **un inventaire, pas deux echelles**. `paliers.js` raisonne sur une
// gamme « un haltere » et une gamme « une paire », mais ce sont deux *vues*
// d'un meme stock : le profil declare `{poids: quantite}` une fois, et les
// deux s'en derivent (`quantite >= 1`, `quantite >= 2`). C'est ce qui interdit
// de posseder une paire de 12 kg sans posseder l'haltere de 12 kg.
//
// Deux regles a ne pas confondre. Le materiel **restreint** l'echelle mais ne
// la vide jamais : une echelle vide ferait planter tout le moteur, y compris
// l'affichage des records, sur quelqu'un qui n'a coche aucun haltere. La
// question « puis-je faire ce mouvement ? » vit **a part**, dans
// `exercice_realisable`, qui est strict la ou l'echelle est permissive : rien
// ne casse s'il repond non.

/**
 * Un inventaire propre depuis ce que porte la base (objet, chaine, ou pire).
 *
 * `null` veut dire « rien de declare » et rend le materiel par defaut : c'est
 * le cas des profils crees avant cette colonne, et leur bareme ne doit pas
 * bouger. Un inventaire *declare* mais vide, lui, est une reponse valide et
 * reste vide — quelqu'un qui ne coche aucun haltere n'en a pas. Les deux ne
 * veulent pas dire la meme chose.
 */
export function normaliser(tables, brut) {
  const defaut = () => ({
    halteres: { ...tables.materiel_par_defaut.halteres },
    accessoires: [...tables.materiel_par_defaut.accessoires],
  });

  if (brut === null || brut === undefined) return defaut();
  if (typeof brut === "string") {
    try {
      brut = JSON.parse(brut);
    } catch {
      return defaut();
    }
  }
  if (typeof brut !== "object" || Array.isArray(brut)) return defaut();

  const reference = tables.echelles.reference;
  const halteres = {};
  for (const [cle, valeur] of Object.entries(brut.halteres ?? {})) {
    const poids = Number.parseInt(cle, 10);
    const quantite = Number.parseInt(valeur, 10);
    if (Number.isNaN(poids) || Number.isNaN(quantite)) continue;
    // Deux exemplaires au plus : au-dela, c'est la meme paire.
    if (reference.includes(poids) && quantite > 0) {
      halteres[poids] = Math.min(2, quantite);
    }
  }

  const connus = Object.keys(tables.accessoires);
  const accessoires = (brut.accessoires ?? []).filter((cle) => connus.includes(cle));
  return { halteres, accessoires };
}

/**
 * Les charges praticables avec `nb_halteres` halteres identiques.
 *
 * Croissant, **jamais vide** : un stock qui ne couvre pas ce besoin rend la
 * gamme de reference complete. Le bareme reste ainsi calculable pour tout le
 * monde, et c'est `exercice_realisable` — pas une echelle vide — qui dit
 * qu'un mouvement est hors de portee.
 */
export function echelle_disponible(echelles, inventaire, nb_halteres) {
  if (nb_halteres <= 0) return null;
  const reference = echelles.reference;
  // `inventaire` est toujours **normalise** : cote Python, `echelle_disponible`
  // passe par `materiel_du_profil`, qui appelle `normaliser` — il n'y a donc
  // jamais de stock absent, seulement un stock par defaut. Court-circuiter ce
  // filtre quand rien n'est declare rendait la gamme entiere, alors que le
  // materiel par defaut n'a **qu'un exemplaire** au-dela de 10 kg : un
  // exercice a deux halteres s'arretait a 18 au lieu de 10, et tout le bareme
  // se decalait a partir du niveau 34.
  const stock = inventaire.halteres;
  const possedes = reference.filter((poids) => (stock[poids] ?? 0) >= nb_halteres);
  return possedes.length ? possedes : reference;
}

/** Accessoires que cet exercice reclame et que le profil n'a pas coches. */
export function accessoires_manquants(tables, inventaire, nom_exercice) {
  const brut = (tables.materiel[nom_exercice]?.brut ?? "").toLowerCase();
  const possedes = inventaire?.accessoires ?? tables.materiel_par_defaut.accessoires;
  return Object.entries(tables.accessoires)
    .filter(([cle]) => brut.includes(cle) && !possedes.includes(cle))
    .map(([, libelle]) => libelle);
}
