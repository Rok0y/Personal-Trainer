// Ecrit `audio/A_ENREGISTRER.md` : ce qu'il reste a dire au micro.
//
// **Le document est derive, jamais tenu a la main.** C'est toute sa valeur :
// le nom du fichier y est celui que l'application reclamera, et le texte celui
// que le nom traduit, parce que les deux sortent des memes donnees. Deux
// listes qu'on doit garder d'accord finissent toujours par diverger — celle-ci
// ne le peut pas.
//
// Il vaut aussi **etat d'avancement** : chaque ligne dit si la prise existe
// deja dans `web/static/sons/`. On le relance apres chaque lot plutot que de
// cocher a la main.
//
// L'ordre des familles n'est pas decoratif, il est economique : les premieres
// debloquent le plus de phrases par prise. Trois amorces multipliees par
// trente-neuf noms de mouvements font cent dix-sept annonces, cinq prises
// d'orientation servent tout le catalogue ; en bout de liste viennent les lots
// **un pour un** — une prise par charge, un nombre par nombre — qu'on peut
// arreter en route sans rien casser.
//
//     node scripts/lister_annonces.mjs

import { existsSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

import { NOMBRE_MAXIMAL_DIT } from "../web/static/js/annonces.js";
import { RACINE, SONS, charger, fichier, texte_charge } from "./vocabulaire.mjs";

const SORTIE = join(RACINE, "audio", "A_ENREGISTRER.md");

// Les familles, dans l'ordre ou on gagne a les enregistrer. La cle est le
// prefixe des cles de `sons.json` → `textes` ; les familles suivantes viennent
// du catalogue, des gammes d'halteres et des nombres.
//
// Les `fragments` n'y figurent pas, et c'est tout l'objet du decoupage : ces
// morceaux ne s'enregistrent jamais seuls, ils sont deja dans les phrases
// assemblees plus bas.
const FAMILLES = [
  [
    ["prochain_exercice", "premier_exercice", "dernier_exercice"],
    "Amorces d'annonce",
    "Trois facons d'annoncer un mouvement, selon sa place dans la seance. " +
      "Elles se disent **devant** un nom d'exercice, jamais seules : " +
      "prononce-les suspendues, sans chute de fin de phrase — « prochain " +
      "exercice : curl biceps droit ». Trois prises x trente-neuf noms = " +
      "cent dix-sept annonces, et c'est ce qui justifie que le nom du " +
      "mouvement reste une prise a part.",
  ],
  [
    ["orientation_"],
    "Orientation par rapport a la camera",
    "Cinq prises couvrent les trente-neuf mouvements du catalogue. C'est " +
      "le meilleur rapport du lot.",
  ],
  [
    ["cadrage_"],
    "Cadrage",
    "Sept parties du corps et quatre actions, assemblees deux a deux : " +
      "onze prises couvrent les vingt-huit consignes possibles.",
  ],
  [
    ["installation_", "geste_"],
    "Installation et gestes",
    "Le guidage du debut de seance, dit camera ouverte pendant qu'on se " +
      "place.",
  ],
  [
    ["changement_"],
    "Changements en cours d'echauffement",
    "Dits au milieu d'une rotation, a quelqu'un qui ne regarde plus " +
      "l'ecran. Un ordre bref, qui arrive seul.",
  ],
  [
    ["bienvenue"],
    "Accueil d'un nouveau profil",
    "Joue une seule fois dans la vie d'un profil. A enregistrer en " +
      "dernier parmi les briques.",
  ],
];

/**
 * « vingt-et-un » pour 21. Sert au document, jamais au code : le fichier
 * s'appelle `21.wav`, mais on n'enregistre pas un chiffre, on enregistre un
 * mot.
 */
function nombre_en_lettres(n) {
  const unites = [
    "", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit",
    "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze",
    "seize", "dix-sept", "dix-huit", "dix-neuf",
  ];
  const dizaines = { 20: "vingt", 30: "trente", 40: "quarante", 50: "cinquante", 60: "soixante" };
  if (n < 20) return unites[n];
  const dizaine = Math.floor(n / 10) * 10;
  const unite = n % 10;
  if (unite === 0) return dizaines[dizaine];
  if (unite === 1) return `${dizaines[dizaine]}-et-un`;
  return `${dizaines[dizaine]}-${unites[unite]}`;
}

const etat = (nom) => (existsSync(join(SONS, nom)) ? "deja fait" : "**a enregistrer**");

function tableau(lignes) {
  return ["| Fichier | A prononcer | Etat |", "| --- | --- | --- |", ...lignes].join("\n");
}

/** Une ligne par (fichier, texte), et le compte de ce qui reste a faire. */
function lignes_de(paires, prononce = (texte) => texte) {
  let restants = 0;
  const lignes = paires.map(([nom, texte]) => {
    const e = etat(nom);
    if (e.startsWith("**")) restants += 1;
    return `| \`${nom}\` | « ${prononce(texte)} » | ${e} |`;
  });
  return [lignes, restants];
}

const EN_TETE = `# Ce qu'il reste a enregistrer

> Ce fichier est **genere**. Ne le modifie pas a la main : relance
> \`node scripts/lister_annonces.mjs\` apres chaque lot, il se met a jour tout
> seul et recompte ce qui reste.

## Comment enregistrer

1. Enregistre chaque phrase dans un \`.wav\` portant **exactement** le nom donne
   ci-dessous, et depose-le dans \`audio/a_traiter/\`.
2. Lance \`python audio/nettoyer_sons.py\` : il rogne les silences, pose un fondu
   et ecrit le resultat dans \`web/static/sons/\`, ou l'application le lit.
3. Relance ce script pour recompter, et pousse.

## Quatre choses a savoir avant de commencer

**Tu peux y aller par lots.** Un fichier absent est un **silence**, jamais une
panne : le coach abrege sa phrase et la seance continue. Rien n'attend que la
liste soit complete, et chaque prise ajoutee fait parler quelque chose de plus.

**Les prises s'enchainent, et chaque famille se prononce en consequence.**
Une annonce de changement d'exercice en joue quatre a la suite : « Prochain
exercice » · « Curl biceps droit » · « Prepare un haltere de 8 kilos » ·
« Place-toi de profil ». Les **amorces** et les **noms de mouvements** se
disent donc suspendus, sans chute de fin de phrase — un nom d'exercice est
annonce comme un titre. Les autres familles sont des phrases completes, dites
d'un ton normal.

**Le meme debit et le meme niveau d'une prise a l'autre**, dans tous les cas :
c'est ce qui rend l'enchainement naturel, bien plus que l'intonation de
chacune.

**Une charge ne se decoupe pas**, en revanche : « prepare un haltere de 8
kilos » est une seule prise, parce que couper avant le nombre tombe au milieu
d'un groupe nominal — la ou la voix ne s'arrete jamais — et s'entend comme un
saccadement.

**Le nom du fichier est le texte.** Si une formulation ne te plait pas, change
le texte dans \`web/static/donnees/sons.json\` (\`textes\`) puis le nom dans
\`briques\` — \`node scripts/verifier_annonces.mjs\` dit lequel il attend. Renommer
un fichier seul ne changerait rien : l'application cherche le nom de la table.
`;

function main() {
  const { sons, mouvements, echelles } = charger();
  const sections = [];
  let total = 0;
  const ajouter = (titre, note, [lignes, restants]) => {
    total += restants;
    if (lignes.length) sections.push(`## ${titre}\n\n${note}\n\n${tableau(lignes)}`);
  };

  for (const [prefixes, titre, note] of FAMILLES) {
    const paires = Object.entries(sons.textes)
      .filter(([cle]) => prefixes.some((p) => cle.startsWith(p)))
      .map(([, texte]) => [fichier(texte), texte]);
    ajouter(titre, note, lignes_de(paires));
  }

  const noms = (echauffement) =>
    Object.values(mouvements)
      .filter((m) => Boolean(m.est_echauffement) === echauffement)
      .map((m) => m.nom)
      .sort()
      .map((nom) => [fichier(nom), nom]);
  ajouter(
    "Noms des exercices",
    "Le nom **est** le texte : aucune table a tenir a jour a cote du " +
      "catalogue, et un exercice ajoute apparait ici tout seul. " +
      "Prononce-les **isoles et neutres** : chacun se dit derriere l'une " +
      "des trois amorces ci-dessus, et se trouve suivi d'une charge ou " +
      "d'une consigne de placement.",
    lignes_de(noms(false))
  );
  ajouter(
    "Noms des echauffements",
    "Meme regle. Ils sont annonces comme les exercices, meme s'ils ne " +
      "comptent nulle part dans les statistiques.",
    lignes_de(noms(true))
  );

  // Deux echelles et non une : au-dela de 10 kg le materiel suppose n'a qu'un
  // exemplaire de chaque haltere, donc un mouvement bilateral s'arrete la.
  const max_un = Math.max(...echelles.un_haltere);
  const max_deux = Math.max(...echelles.deux_halteres);
  const charges = (couples) =>
    couples
      .map(([h, p]) => texte_charge(sons.fragments, h, p))
      .filter(Boolean)
      .map((texte) => [fichier(texte), texte]);
  ajouter(
    "Charges — la gamme courante",
    "Ce que le bareme propose avec le materiel suppose : jusqu'a " +
      `${max_un} kg a un haltere, ${max_deux} kg a la paire. Une phrase entiere ` +
      "par charge : couper avant le nombre tombe au milieu d'un " +
      "groupe nominal, et ca s'entend — contrairement a la couture " +
      "entre une amorce et un nom d'exercice, qui tombe sur une pause " +
      "que la phrase a deja.",
    lignes_de(charges([
      ...echelles.un_haltere.map((p) => [1, p]),
      ...echelles.deux_halteres.map((p) => [2, p]),
    ]))
  );
  ajouter(
    "Charges lourdes — a faire en dernier",
    "Le questionnaire de materiel va jusqu'a 40 kg, donc ces charges " +
      "existent pour qui les declare. **Coupe ce lot a la hauteur de " +
      "ton propre placard** : une charge sans prise rend l'annonce " +
      "breve (« prochain exercice, squat »), jamais muette.",
    lignes_de(charges([
      ...echelles.reference.filter((p) => p > max_un).map((p) => [1, p]),
      ...echelles.reference.filter((p) => p > max_deux).map((p) => [2, p]),
    ]))
  );

  const nombres = [];
  for (let n = 21; n <= NOMBRE_MAXIMAL_DIT; n++) nombres.push([fichier(String(n)), n]);
  const [lignes, restants] = lignes_de(nombres, nombre_en_lettres);
  total += restants;
  sections.push(
    "## Nombres de 21 a 60\n\n" +
      "Les vingt premiers sont deja enregistres — ce sont ceux du comptage " +
      "des repetitions, reutilises tels quels. Ceux-ci servent la meme chose " +
      "au-dela de vingt repetitions, ce que le bareme atteint sur les " +
      "mouvements au poids du corps. Les charges, elles, ne passent plus par " +
      "eux : elles sont devenues des phrases entieres.\n\n" +
      tableau(lignes)
  );

  writeFileSync(SORTIE, `${EN_TETE}\n**${total} prises restantes.**\n\n${sections.join("\n\n")}\n`);
  console.log(`${relative(RACINE, SORTIE)} ecrit — ${total} prises restantes.`);
}

main();
