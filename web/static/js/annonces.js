// Jumeau d'`audio/annonces.py` : les briques dont le coach compose ses phrases.
//
// **Aucune valeur n'est ecrite ici.** La table des briques est exportee du
// Python par `scripts/preparer_demo.py` dans `donnees/sons.json`, sous la cle
// `briques` — a cote de `fichiers`, `priorites` et `delais`. Elle y arrive
// **deja resolue** en noms de fichiers : le navigateur n'a jamais besoin du
// texte prononce, seulement du `.wav` qui le porte.
//
// Elle est donc **injectee** en premier argument plutot que lue d'un import,
// exactement comme `moteur.js` recoit son `coach`. Ca garde le module pur —
// donc verifiable sans navigateur — et ca rend visible, au site d'appel, d'ou
// vient la donnee.
//
// Un seul texte transite encore en clair : le **nom de l'exercice**, qui vient
// du catalogue local et qui **est** son propre texte. C'est ce que
// `normaliser_nom` traduit, et c'est la seule fonction de ce fichier qui doive
// rendre exactement la meme chose que son homologue Python sur n'importe
// quelle entree.

/**
 * Le nom de fichier d'un texte : sans accents, sans ponctuation, minuscules.
 * Jumeau strict de `normaliser_nom` dans `audio/annonces.py`.
 *
 * `\p{Mn}` est la categorie Unicode « Nonspacing_Mark », celle-la meme que le
 * Python teste par `unicodedata.category(c) != "Mn"`. Les deux retirent donc
 * exactement les memes signes apres decomposition NFD.
 */
export function normaliser_nom(texte) {
  const sans_accents = String(texte).normalize("NFD").replace(/\p{Mn}/gu, "");
  return sans_accents
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

/**
 * Le `.wav` qui porte ce texte.
 *
 * Aucun cas particulier pour les nombres : `normaliser_nom("12")` rend `"12"`,
 * donc `12.wav` — le fichier deja enregistre pour le comptage des repetitions.
 */
export function fichier(texte) {
  return `${normaliser_nom(texte)}.wav`;
}

//: Au-dela, la partie chiffree est muette. Meme valeur qu'en Python, et meme
//: raison : le bareme se terminant par une tranche ouverte, il n'existe aucun
//: plafond a atteindre, et une annonce sans son nombre reste utile.
export const NOMBRE_MAXIMAL_DIT = 60;

/**
 * Le fichier d'une brique du vocabulaire fixe, ou `null` si elle manque.
 *
 * Elle rend `null` la ou le Python leve : cote navigateur, une table
 * incomplete peut venir d'un `sons.json` plus ancien que le code — un cache
 * qui n'a pas expire —, et une exception y arreterait la boucle d'affichage.
 * `scripts/verifier_annonces.py` est ce qui attrape la vraie faute de frappe,
 * a froid, plutot que la boucle camera a chaud.
 */
export function brique(briques, cle) {
  return (briques ?? {})[cle] ?? null;
}

/** Le nombre, s'il est enregistre. Sinon rien, et la phrase se poursuit. */
export function sequence_nombre(valeur) {
  const entier = Number(valeur);
  if (!Number.isInteger(entier)) return [];
  if (entier < 1 || entier > NOMBRE_MAXIMAL_DIT) return [];
  return [fichier(String(entier))];
}

/**
 * La consigne de cadrage, en deux briques.
 *
 * `partie` peut valoir null : c'est le cas « coupe en haut *et* en bas », ou
 * nommer une partie tromperait puisqu'il en manque des deux cotes. C'est
 * `message_de_cadrage` (`cadrage.js`) qui en decide — ce module ne fait que
 * prononcer.
 */
export function sequence_cadrage(briques, partie, action) {
  const sons = [];
  if (partie) sons.push(brique(briques, `cadrage_manque_${partie}`));
  if (action) sons.push(brique(briques, `cadrage_action_${action}`));
  return sons.filter(Boolean);
}

/** Comment se placer par rapport a la camera, pour ce mouvement-la. */
export function sequence_orientation(briques, orientation) {
  const son = brique(briques, `orientation_${orientation}`);
  return son ? [son] : [];
}

/**
 * L'annonce du prochain exercice : ce qu'il est, et ce qu'il faut sortir.
 *
 * « Prochain exercice. Curl biceps droit. Prepare un haltere de 8 kilos. »
 *
 * **Les series et les repetitions n'y sont volontairement pas** : elles sont
 * deja a l'ecran, et les dire allongeait l'annonce de plusieurs secondes au
 * moment precis ou l'on veut agir plutot qu'ecouter. Le critere retenu : on
 * prononce ce qui demande un **geste** pendant le repos, pas ce qui se lit.
 *
 * `nombre_halteres` est injecte — il vient de `materiel.js` cote navigateur,
 * de `session.seances.nombre_halteres` cote Python. Un et deux ne sont pas
 * interchangeables a l'oreille : on ne sort pas la meme chose du placard, et
 * aucun ecran regarde de trois metres ne donne cette information.
 */
export function sequence_prochain_exercice(briques, etape, nombre_halteres = 0) {
  if (!etape) return [];

  const sons = [brique(briques, "prochain_exercice"), fichier(etape.exercice)];

  const poids = etape.poids || 0;
  if (poids <= 0 || ![1, 2].includes(nombre_halteres)) {
    // Poids du corps, ou materiel non declare : il n'y a rien a preparer, et
    // le silence le dit sans ambiguite. « Zero kilo » n'existe pas.
    return sons.filter(Boolean);
  }

  const amorce = brique(
    briques,
    nombre_halteres === 1 ? "prepare_un_haltere_de" : "prepare_deux_halteres_de"
  );
  const chiffre = sequence_nombre(poids);
  const unite = brique(briques, poids === 1 ? "kilo" : "kilos");

  // La clause entiere ou rien : une amorce suivie d'un blanc — « prepare un
  // haltere de… » — s'entend comme une panne, la ou son absence s'entend comme
  // une annonce breve.
  if (amorce && chiffre.length && unite) {
    sons.push(amorce, ...chiffre, unite);
  }

  return sons.filter(Boolean);
}
