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
//: Bornes d'un poids saisi a la main, jumelles de `core/materiel.py`. Larges
//: a dessein : il ne s'agit pas de juger ce que quelqu'un souleve, seulement
//: d'ecarter une faute de frappe qui ferait sortir le bareme de tout sens.
const POIDS_MIN_DECLARABLE = 1;
const POIDS_MAX_DECLARABLE = 60;

/**
 * Un poids d'haltere utilisable, ou null.
 *
 * Remplace le `reference.includes(poids)` d'avant, qui confondait « ce que le
 * questionnaire propose » et « ce qui est acceptable » : quelqu'un possedant
 * des halteres de 20 kg ne pouvait ni les cocher ni les faire accepter, et son
 * inventaire etait silencieusement ampute au chargement.
 *
 * Arrondi au demi-kilo, qui est le pas reel du materiel. Et **`parseFloat` et
 * non `parseInt`** : ce dernier tronquait « 17.5 » en 17, c'est-a-dire qu'il
 * inventait un haltere que personne ne possede.
 */
export function poids_declarable(valeur) {
  const brut = Number.parseFloat(valeur);
  if (Number.isNaN(brut)) return null;
  const poids = Math.round(brut * 2) / 2;
  if (poids < POIDS_MIN_DECLARABLE || poids > POIDS_MAX_DECLARABLE) return null;
  return poids;
}

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

  const halteres = {};
  for (const [cle, valeur] of Object.entries(brut.halteres ?? {})) {
    const poids = poids_declarable(cle);
    const quantite = Number.parseInt(valeur, 10);
    if (poids === null || Number.isNaN(quantite)) continue;
    // Deux exemplaires au plus : au-dela, c'est la meme paire.
    if (quantite > 0) halteres[poids] = Math.min(2, quantite);
  }

  const connus = Object.keys(tables.accessoires);
  const accessoires = (brut.accessoires ?? []).filter((cle) => connus.includes(cle));
  return { halteres, accessoires };
}

/**
 * Les charges praticables avec `nb_halteres` halteres identiques.
 *
 * Croissant, **et il peut etre vide** : un stock qui ne couvre pas ce besoin ne
 * rend plus la gamme supposee. La reponse honnete a « avec quoi peut-il charger
 * ce mouvement ? » est parfois « rien », et `normaliser` distingue deja un
 * inventaire non declare d'un inventaire declare vide — effacer la distinction
 * ici la perdait la ou elle compte.
 *
 * Mesure cote Python : avec le repli, qui coche « aucun haltere » recevait quand
 * meme l'echelle supposee, donc `charge_de_test` prenait son milieu — 8 kg au
 * squat. Le test se jouait forcement a vide, et l'ancrage creditait 15 squats au
 * poids du corps du niveau 36 au lieu de 8.
 *
 * Le garde « le bareme reste calculable » a demenage dans
 * `Baremes.echelle_exercice` (paliers.js), seul endroit qui sache si l'exercice
 * a un cran au poids du corps sur lequel se rabattre.
 */
export function echelle_disponible(echelles, inventaire, nb_halteres) {
  if (nb_halteres <= 0) return null;
  // `inventaire` est toujours **normalise** : cote Python, `echelle_disponible`
  // passe par `materiel_du_profil`, qui appelle `normaliser` — il n'y a donc
  // jamais de stock absent, seulement un stock par defaut. Court-circuiter ce
  // filtre quand rien n'est declare rendait la gamme entiere, alors que le
  // materiel par defaut n'a **qu'un exemplaire** au-dela de 10 kg : un
  // exercice a deux halteres s'arretait a 18 au lieu de 10, et tout le bareme
  // se decalait a partir du niveau 34.
  //
  // On parcourt le **stock declare** et non la gamme du questionnaire : depuis
  // qu'un poids se saisit a la main, un haltere de 17,5 kg peut exister sans
  // figurer dans `reference`, et le filtrer par la gamme le ferait disparaitre
  // du bareme sans rien dire.
  const stock = inventaire.halteres;
  const possedes = Object.entries(stock)
    .filter(([, nombre]) => nombre >= nb_halteres)
    .map(([poids]) => Number(poids))
    .sort((a, b) => a - b);
  return possedes;
}

/** Accessoires que cet exercice reclame et que le profil n'a pas coches. */
export function accessoires_manquants(tables, inventaire, nom_exercice) {
  const brut = (tables.materiel[nom_exercice]?.brut ?? "").toLowerCase();
  const possedes = inventaire?.accessoires ?? tables.materiel_par_defaut.accessoires;
  return Object.entries(tables.accessoires)
    .filter(([cle]) => brut.includes(cle) && !possedes.includes(cle))
    .map(([, libelle]) => libelle);
}
