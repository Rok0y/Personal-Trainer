// Rejoue la composition des annonces du coach et compare aux reponses figees.
//
// Un ecart y est **muet par construction** — le navigateur demanderait un
// `.wav` absent, `_tampon` rendrait null, et l'annonce serait seulement plus
// courte. C'est exactement le genre de defaut qu'aucun ecran ne montre et
// qu'on decouvre des semaines plus tard, en s'apercevant que le coach ne
// nomme plus rien.
//
// La table des briques voyage avec les questions : c'est l'entree du code,
// qui la recoit de `sons.json`. L'**amorce** est jouee sur chaque etape, les
// trois du vocabulaire plus une inconnue : c'est le seul endroit du module ou
// le choix de l'appelant entre dans le calcul. Une amorce ou une partie de
// cadrage inconnue (`sons: null`) ne doit fabriquer aucun nom de fichier —
// c'est un invariant, verifie a part, qu'aucune mise a jour ne fait taire.
//
// Usage : node scripts/comparer_annonces.mjs [--mettre-a-jour]

import {
  NOMBRE_MAXIMAL_DIT,
  fichier,
  nombre_dit,
  normaliser_nom,
  sequence_cadrage,
  sequence_nombre,
  sequence_orientation,
  sequence_prochain_exercice,
} from "../web/static/js/annonces.js";
import { Releve, lire_lignes } from "./fixtures.mjs";

function main() {
  const lignes = lire_lignes("annonces");
  const releve = new Releve();
  const invariant = (etiquette, attendu, obtenu) => {
    releve.comparaisons += 1;
    releve.echecs.push({ ou: etiquette, attendu, rendu: JSON.stringify(obtenu) });
  };
  let briques = {};

  for (const ligne of lignes) {

    switch (ligne.genre) {
      case "briques": {
        briques = ligne.table;
        // La table elle-meme n'est pas « comparee » : elle *est* l'entree du
        // code. On verifie seulement que chaque brique est un nom de fichier
        // non vide — une entree vide ferait taire une phrase sans rien dire.
        for (const [cle, valeur] of Object.entries(briques)) {
          if (typeof valeur !== "string" || !valeur.endsWith(".wav")) {
            invariant(`brique ${cle}`, "<nom>.wav", valeur);
          }
        }
        break;
      }

      case "normaliser": {
        releve.verifier(
          `normaliser_nom(${JSON.stringify(ligne.texte)})`,
          ligne, "nom",
          normaliser_nom(ligne.texte) ?? null
        );
        releve.verifier(
          `fichier(${JSON.stringify(ligne.texte)})`,
          ligne, "fichier",
          fichier(ligne.texte) ?? null
        );
        break;
      }

      case "nombre": {
        // Le gardien du plafond avant la sequence qui s'en sert : un
        // demi-kilo doit se taire, sans quoi on annoncerait « 17 kilos » pour
        // un haltere de 17,5.
        releve.verifier(
          `nombre_dit(${ligne.valeur})`,
          ligne, "dit",
          nombre_dit(ligne.valeur) ?? null
        );
        releve.verifier(
          `sequence_nombre(${ligne.valeur})`,
          ligne, "sons",
          sequence_nombre(ligne.valeur) ?? null
        );
        break;
      }

      case "cadrage": {
        // `sons: null` veut dire « partie ou action inconnue ». Le code rend
        // alors une liste amputee des briques inconnues : c'est voulu, on
        // verifie seulement qu'il ne fabrique pas un nom de fichier.
        const obtenu = sequence_cadrage(briques, ligne.partie, ligne.action);
        if (ligne.sons === null) {
          if (obtenu.some((s) => !Object.values(briques).includes(s))) {
            invariant(`cadrage(${ligne.partie}, ${ligne.action})`, "aucun fichier invente", obtenu);
          }
        } else {
          releve.verifier(
            `sequence_cadrage(${ligne.partie}, ${ligne.action})`,
            ligne, "sons",
            obtenu ?? null
          );
        }
        break;
      }

      case "orientation": {
        releve.verifier(
          `sequence_orientation(${ligne.orientation})`,
          ligne, "sons",
          sequence_orientation(briques, ligne.orientation) ?? null
        );
        break;
      }

      case "prochain_exercice": {
        const etiquette = ligne.etape
          ? `${ligne.amorce}(${ligne.etape.exercice}, ` +
            `${ligne.etape.poids} kg, ${ligne.halteres} halteres)`
          : "prochain(null)";
        const obtenu = sequence_prochain_exercice(
          briques,
          ligne.etape,
          ligne.halteres,
          ligne.amorce
        );
        // `sons: null` veut dire « amorce inconnue ». Le code rend alors une
        // liste amputee de la brique inconnue : c'est voulu, on verifie
        // seulement qu'il n'a pas fabrique un nom de fichier a partir d'une
        // cle qui n'est pas dans la table.
        if (ligne.sons === null) {
          if (obtenu.includes(`${ligne.amorce}.wav`)) {
            invariant(etiquette, "aucun fichier invente", obtenu);
          }
        } else {
          releve.verifier(etiquette, ligne, "sons", obtenu ?? null);
        }
        break;
      }

      default:
        console.error(`genre inconnu : ${ligne.genre}`);
        process.exit(2);
    }
  }

  // Le plafond se compare explicitement : un seuil deplace ne se verrait
  // sinon que par ses effets.
  const plafond_fige = Math.max(
    ...lignes
      .filter((l) => l.genre === "nombre" && l.sons.length)
      .map((l) => Number(l.valeur))
  );
  if (plafond_fige > NOMBRE_MAXIMAL_DIT) {
    invariant("NOMBRE_MAXIMAL_DIT", `>= ${plafond_fige}`, NOMBRE_MAXIMAL_DIT);
  }

  console.log(`${releve.comparaisons} questions`);
  releve.conclure({
    fichier: "annonces",
    lignes,
    succes: "Aucun ecart : les annonces rendent les reponses figees.",
    detail: 6,
  });
}

main();
