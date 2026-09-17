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
//
// **Divergence de chemin assumee, et c'est la seule du module.** Une phrase
// s'enregistre d'un souffle plutot qu'en briques cousues a la lecture : la
// charge (« prepare un haltere de 8 kilos »), parce que son decoupage tombait
// au milieu d'un groupe nominal et s'entendait. Le Python en compose le
// **texte**, puis le traduit en nom de fichier — « le nom du fichier est le
// texte ». Ici, il n'y a pas de texte : on assemble les **noms**
// (`fichier_assemble`). Les deux chemins doivent rendre le meme fichier, et
// c'est `comparer_annonces.mjs` qui le prouve, pas un commentaire qui
// l'affirmerait.
//
// L'amorce et le nom du mouvement, eux, restent **deux prises** : trois
// amorces se recombinent avec trente-neuf mouvements, et la couture tombe sur
// la pause d'un deux-points.

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

//: Les facons d'annoncer un mouvement, selon sa place dans la seance. Meme
//: vocabulaire ferme qu'en Python, et c'est l'appelant qui choisit.
export const AMORCES_EXERCICE = [
  "prochain_exercice",
  "premier_exercice",
  "dernier_exercice",
];

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

/**
 * L'entier qu'on sait prononcer, ou `null`. Point d'entree unique du plafond.
 *
 * `Number.isInteger` refuse 17,5 — un haltere declarable qui n'a aucune prise.
 * Le Python faisait `int(17.5)`, donc annoncait « 17 kilos » : c'est ce cote-ci
 * qui avait raison, et la divergence est passee inapercue tant que le harnais
 * ne tirait que des entiers.
 */
export function nombre_dit(valeur) {
  const entier = Number(valeur);
  if (!Number.isInteger(entier)) return null;
  if (entier < 1 || entier > NOMBRE_MAXIMAL_DIT) return null;
  return entier;
}

/**
 * Le nombre seul, s'il est enregistre. Sinon rien.
 *
 * Sans appelant de production des deux cotes — les charges sont devenues des
 * phrases entieres —, conservee comme forme « sequence » du nombre.
 */
export function sequence_nombre(valeur) {
  const entier = nombre_dit(valeur);
  return entier === null ? [] : [fichier(String(entier))];
}

/**
 * Le `.wav` d'une phrase enregistree d'un souffle, a partir des noms de ses
 * morceaux : `prochain_exercice.wav` + `curl_biceps_droit.wav` donne
 * `prochain_exercice_curl_biceps_droit.wav`.
 *
 * C'est le pendant, cote navigateur, de la composition de texte que fait le
 * Python. L'invariant qui autorise les deux chemins : `normaliser_nom`
 * reduit toute suite de separateurs a un `_` unique et ne change plus rien a
 * un nom deja normalise, donc coudre les noms revient a coudre les textes.
 *
 * Deux refus, qui ne disent pas la meme chose. Un morceau **absent** (`null`,
 * table `briques` plus ancienne que le code) rend `null` : on ne fabrique pas
 * un nom a partir d'un trou. Un morceau **vide** (`.wav` seul, cas d'un nom
 * d'exercice vide) est simplement saute, parce que c'est ce que fait la
 * normalisation du texte cote Python.
 */
export function fichier_assemble(...fichiers) {
  if (fichiers.some((morceau) => !morceau)) return null;

  const noms = fichiers
    .map((morceau) => String(morceau).replace(/\.wav$/, ""))
    .filter(Boolean);

  return noms.length ? `${noms.join("_")}.wav` : null;
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
 *
 * `amorce` est une cle d'`AMORCES_EXERCICE`, choisie par l'appelant selon la
 * position du mouvement dans la seance : « le premier exercice sera » a
 * l'entree, « pour finir » sur le dernier, « prochain exercice » ailleurs.
 */
export function sequence_prochain_exercice(
  briques,
  etape,
  nombre_halteres = 0,
  amorce = "prochain_exercice"
) {
  if (!etape) return [];

  // L'amorce et le nom du mouvement sont deux prises, parce qu'elles se
  // recombinent. La charge, elle, est une phrase entiere.
  const sons = [brique(briques, amorce), fichier(etape.exercice)];

  const poids = nombre_dit(etape.poids);

  // Poids du corps, ou materiel non declare : il n'y a rien a preparer, et le
  // silence le dit sans ambiguite. « Zero kilo » n'existe pas.
  if (poids !== null && [1, 2].includes(nombre_halteres)) {
    // La clause entiere ou rien : `fichier_assemble` rend null des qu'un
    // morceau manque, plutot qu'une amorce suivie d'un blanc — qui s'entend
    // comme une panne, la ou son absence s'entend comme une annonce breve.
    const charge = fichier_assemble(
      brique(
        briques,
        nombre_halteres === 1
          ? "prepare_un_haltere_de"
          : "prepare_deux_halteres_de"
      ),
      fichier(String(poids)),
      brique(briques, poids === 1 ? "kilo" : "kilos")
    );

    if (charge) sons.push(charge);
  }

  return sons.filter(Boolean);
}
