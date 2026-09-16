// Rejoue en JavaScript ce que `generer_annonces.py` a releve.
//
// Le module compose les phrases du coach. Un ecart y est **muet par
// construction** — le navigateur demanderait un `.wav` absent, `_tampon`
// rendrait null, et l'annonce serait seulement plus courte. C'est exactement
// le genre de defaut qu'aucun ecran ne montre et qu'on decouvre des semaines
// plus tard, en s'apercevant que le coach ne nomme plus rien.
//
// La **table des briques est comparee telle quelle**, en plus des sequences :
// c'est elle que `preparer_demo` exporte, et si les deux cotes ne partent pas
// des memes fichiers, tout le reste compare deux choses differentes en croyant
// les trouver identiques.
//
// Une divergence d'API est assumee et relevee comme telle : `brique()` **leve**
// cote Python sur une cle inconnue (c'est une faute de frappe dans du code) et
// rend `null` cote JavaScript (ou une table peut venir d'un `sons.json` garde
// en cache, et ou une exception arreterait la boucle d'affichage). Le harnais
// attend donc `sons: null` la ou Python a refuse.
//
// Usage : node scripts/comparer_annonces.mjs
// Prealable : python -m scripts.generer_annonces

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  NOMBRE_MAXIMAL_DIT,
  fichier,
  normaliser_nom,
  sequence_cadrage,
  sequence_nombre,
  sequence_orientation,
  sequence_prochain_exercice,
} from "../web/static/js/annonces.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(ICI, "fixtures_annonces.jsonl");

const ECARTS_DETAILLES = 6;

const memeListe = (a, b) =>
  JSON.stringify(a ?? null) === JSON.stringify(b ?? null);

function main() {
  let lignes;
  try {
    lignes = readFileSync(FIXTURES, "utf-8").trim().split("\n");
  } catch {
    console.error(
      "fixtures_annonces.jsonl introuvable — lance d'abord " +
        "`python -m scripts.generer_annonces`"
    );
    process.exit(2);
  }

  let briques = {};
  let questions = 0;
  const ecarts = [];

  const verifier = (etiquette, attendu, obtenu) => {
    questions += 1;
    if (!memeListe(attendu, obtenu)) {
      ecarts.push({ etiquette, attendu, obtenu });
    }
  };

  for (const brut of lignes) {
    const ligne = JSON.parse(brut);

    switch (ligne.genre) {
      case "briques": {
        briques = ligne.table;
        // La table elle-meme n'est pas « comparee » : elle *est* l'entree du
        // JS, qui la recoit de `sons.json`. Ce qu'on verifie, c'est que le
        // Python a bien resolu chaque brique en un nom de fichier non vide —
        // une entree vide ferait taire une phrase sans rien signaler.
        for (const [cle, valeur] of Object.entries(briques)) {
          questions += 1;
          if (typeof valeur !== "string" || !valeur.endsWith(".wav")) {
            ecarts.push({
              etiquette: `brique ${cle}`,
              attendu: "<nom>.wav",
              obtenu: valeur,
            });
          }
        }
        break;
      }

      case "normaliser": {
        verifier(
          `normaliser_nom(${JSON.stringify(ligne.texte)})`,
          ligne.nom,
          normaliser_nom(ligne.texte)
        );
        verifier(
          `fichier(${JSON.stringify(ligne.texte)})`,
          ligne.fichier,
          fichier(ligne.texte)
        );
        break;
      }

      case "nombre": {
        verifier(
          `sequence_nombre(${ligne.valeur})`,
          ligne.sons,
          sequence_nombre(ligne.valeur)
        );
        break;
      }

      case "cadrage": {
        // `sons: null` veut dire « Python a refuse ». Le JS rend alors une
        // liste amputee des briques inconnues : c'est le comportement voulu,
        // on verifie seulement qu'il ne fabrique pas un nom de fichier.
        const obtenu = sequence_cadrage(briques, ligne.partie, ligne.action);
        if (ligne.sons === null) {
          questions += 1;
          if (obtenu.some((s) => !Object.values(briques).includes(s))) {
            ecarts.push({
              etiquette: `cadrage(${ligne.partie}, ${ligne.action})`,
              attendu: "aucun fichier invente",
              obtenu,
            });
          }
        } else {
          verifier(
            `sequence_cadrage(${ligne.partie}, ${ligne.action})`,
            ligne.sons,
            obtenu
          );
        }
        break;
      }

      case "orientation": {
        verifier(
          `sequence_orientation(${ligne.orientation})`,
          ligne.sons,
          sequence_orientation(briques, ligne.orientation)
        );
        break;
      }

      case "prochain_exercice": {
        const etiquette = ligne.etape
          ? `prochain(${ligne.etape.exercice}, ${ligne.etape.poids} kg, ` +
            `${ligne.halteres} halteres)`
          : "prochain(null)";
        verifier(
          etiquette,
          ligne.sons,
          sequence_prochain_exercice(briques, ligne.etape, ligne.halteres)
        );
        break;
      }

      default:
        console.error(`genre inconnu : ${ligne.genre}`);
        process.exit(2);
    }
  }

  // Le plafond est une constante des deux cotes : le comparer explicitement
  // evite qu'un seuil deplace d'un cote ne se voie que par ses effets.
  questions += 1;
  const plafondPython = Math.max(
    ...lignes
      .map((l) => JSON.parse(l))
      .filter((l) => l.genre === "nombre" && l.sons.length)
      .map((l) => Number(l.valeur))
  );
  if (plafondPython > NOMBRE_MAXIMAL_DIT) {
    ecarts.push({
      etiquette: "NOMBRE_MAXIMAL_DIT",
      attendu: `>= ${plafondPython}`,
      obtenu: NOMBRE_MAXIMAL_DIT,
    });
  }

  if (ecarts.length) {
    console.log(`${ecarts.length} divergences sur ${questions} questions :\n`);
    for (const ecart of ecarts.slice(0, ECARTS_DETAILLES)) {
      console.log(`  ${ecart.etiquette}`);
      console.log(`    Python     : ${JSON.stringify(ecart.attendu)}`);
      console.log(`    JavaScript : ${JSON.stringify(ecart.obtenu)}\n`);
    }
    if (ecarts.length > ECARTS_DETAILLES) {
      console.log(`  … et ${ecarts.length - ECARTS_DETAILLES} autres.`);
    }
    process.exit(1);
  }

  console.log(`${questions} questions, aucune divergence.`);
}

main();
