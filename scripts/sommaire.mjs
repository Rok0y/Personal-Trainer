// Le sommaire du site : une page qui mene a toutes les autres.
//
// Il est **genere**, jamais tenu a la main : le script parcourt toutes les
// pages `.html` du site, lit leur `<title>` et leur
// `<meta name="description">`, et les range par dossier. Une page ajoutee
// apparait donc d'elle-meme au deploiement suivant — c'est tout l'interet d'une
// liste qu'on ne peut pas oublier de mettre a jour.
//
// Deux usages :
//
//     node scripts/sommaire.mjs                  verifie (joue par tester.mjs)
//     node scripts/sommaire.mjs <site> [commit]  ecrit <site>/sommaire.html
//                                                et <site>/index.html
//
// Le sommaire a **sa propre adresse**, `sommaire.html`, en plus de la racine.
// La racine a longtemps ete une redirection vers la demo, et un navigateur qui
// l'a gardee en cache y renvoie encore : une adresse neuve n'a jamais ete mise
// en cache, donc elle montre toujours la bonne page. C'est celle a mettre en
// favori.
//
// La verification echoue sur une page sans titre ou sans description : c'est
// ce qui garantit que chaque carte du sommaire dit ce qu'on trouve derriere.
// L'ecriture est faite par la CI, sur la copie `_site` publiee ; en local,
// `node scripts/sommaire.mjs web/static` ecrit ces deux fichiers, que Git
// ignore.

import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ICI = dirname(fileURLToPath(import.meta.url));

//: Les fichiers que le script ecrit lui-meme : ils ne sont pas des pages du
//: sommaire.
const FICHIERS_DU_SOMMAIRE = ["index.html", "sommaire.html"];

//: Le nom et l'ordre des sections connues. Un dossier absent d'ici apparait
//: quand meme, sous son propre nom et apres celles-ci : la table ne fait que
//: mieux presenter, elle ne filtre rien.
const SECTIONS = [
  ["app", "L'application"],
  ["demo", "Banc d'essai"],
  ["dev", "Outils de réglage"],
];

/** Toutes les pages `.html` sous `racine`, sauf le sommaire lui-meme. */
function pages(racine) {
  const trouvees = [];
  const parcourir = (dossier) => {
    for (const entree of readdirSync(dossier, { withFileTypes: true })) {
      const chemin = join(dossier, entree.name);
      if (entree.isDirectory()) parcourir(chemin);
      else if (entree.name.endsWith(".html")) trouvees.push(chemin);
    }
  };
  parcourir(racine);
  return trouvees
    .map((chemin) => relative(racine, chemin).split(sep).join("/"))
    .filter((chemin) => !FICHIERS_DU_SOMMAIRE.includes(chemin))
    .sort();
}

function decoder(texte) {
  return texte
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

function echapper(texte) {
  return texte.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/** Titre, description et adresse d'une page. */
function decrire(racine, chemin) {
  const source = readFileSync(join(racine, chemin), "utf-8");
  const titre = source.match(/<title>([^<]*)<\/title>/i)?.[1].trim() ?? "";
  const description = source.match(/<meta\s+name="description"\s+content="([^"]*)"/i)?.[1].trim() ?? "";
  // Un `index.html` se designe par son dossier : c'est l'adresse qu'on partage.
  const adresse = chemin.endsWith("/index.html") ? chemin.slice(0, -"index.html".length) : chemin;
  const dossier = chemin.includes("/") ? chemin.split("/")[0] : "";
  return { chemin, adresse, dossier, titre: decoder(titre), description: decoder(description) };
}

function sections(fiches) {
  const par_dossier = new Map();
  for (const fiche of fiches) {
    if (!par_dossier.has(fiche.dossier)) par_dossier.set(fiche.dossier, []);
    par_dossier.get(fiche.dossier).push(fiche);
  }
  const connues = SECTIONS.filter(([d]) => par_dossier.has(d));
  const autres = [...par_dossier.keys()]
    .filter((d) => !SECTIONS.some(([connu]) => connu === d))
    .sort()
    .map((d) => [d, d || "Racine"]);
  return [...connues, ...autres].map(([d, nom]) => ({ nom, fiches: par_dossier.get(d) }));
}

function rendre(fiches, commit) {
  const date = new Date().toISOString().slice(0, 16).replace("T", " ");
  const version = commit ? ` · version ${echapper(commit.slice(0, 7))}` : "";
  const blocs = sections(fiches)
    .map(({ nom, fiches: liste }) => `
  <section>
    <h2>${echapper(nom)}</h2>
    <div class="cartes">${liste
      .map((f) => `
      <a class="carte" href="${echapper(f.adresse)}">
        <strong>${echapper(f.titre || f.chemin)}</strong>
        <span>${echapper(f.description)}</span>
        <code>${echapper(f.adresse)}</code>
      </a>`)
      .join("")}
    </div>
  </section>`)
    .join("");
  return `<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0a0d13">
<title>Coach — sommaire</title>
<meta name="description" content="Toutes les pages du site.">
<!-- Genere par scripts/sommaire.mjs : ne pas modifier a la main. -->
<script type="module" src="js/version.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="palette.css">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: "Space Grotesk", system-ui, sans-serif;
    padding: max(24px, env(safe-area-inset-top)) 16px 48px;
  }
  main { max-width: 760px; margin: 0 auto; }
  h1 { font-family: "Bebas Neue", sans-serif; font-weight: 400; font-size: 2.6rem; letter-spacing: 0.04em; margin: 0; }
  .sous-titre { color: var(--muted); margin: 4px 0 28px; font-size: 0.9rem; }
  h2 { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); margin: 28px 0 10px; }
  .cartes { display: grid; gap: 10px; }
  .carte {
    display: grid;
    gap: 6px;
    padding: 16px 18px;
    border-radius: 14px;
    background: var(--glass-strong);
    border: 1px solid var(--border);
    color: inherit;
    text-decoration: none;
  }
  .carte:hover, .carte:focus-visible { border-color: var(--orange); outline: none; }
  .carte strong { font-size: 1.1rem; }
  .carte span { color: var(--muted); line-height: 1.45; }
  .carte code { color: var(--teal); font-size: 0.8rem; }
</style>
</head>
<body>
<main>
  <h1>Coach</h1>
  <p class="sous-titre">Toutes les pages du site, générées au déploiement${version} · ${date} UTC</p>${blocs}
</main>
</body>
</html>
`;
}

function main() {
  const [cible, commit] = process.argv.slice(2);
  const racine = cible ?? join(ICI, "..", "web", "static");
  const fiches = pages(racine).map((chemin) => decrire(racine, chemin));

  const incompletes = fiches.filter((f) => !f.titre || !f.description);
  for (const f of incompletes) {
    console.log(`${f.chemin} : ${!f.titre ? "aucun <title>" : "aucune <meta name=\"description\">"} — sa carte dans le sommaire ne dirait rien`);
  }

  if (!cible) {
    console.log(`${fiches.length} pages au sommaire : ${fiches.map((f) => f.adresse).join(", ")}`);
    if (incompletes.length) process.exitCode = 1;
    return;
  }
  const page = rendre(fiches, commit);
  for (const fichier of FICHIERS_DU_SOMMAIRE) writeFileSync(join(racine, fichier), page);
  console.log(`Sommaire ecrit : ${fiches.length} pages.`);
}

main();
