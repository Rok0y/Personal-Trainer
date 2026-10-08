// Les tables du coach se tiennent-elles ?
//
// **Une table de cles qui ne leve pas se verifie de l'exterieur.** `coach()`
// sort en silence sur une cle inconnue — une exception dans la boucle d'images
// gelerait l'ecran. La contrepartie est qu'une cle mal orthographiee, une table
// oubliee ou un fichier jamais enregistre ne se signalent **nulle part** :
// l'application se contente de ne rien dire, ce que personne ne remarque. Le
// projet en a eu la preuve : `repos_20.wav` etait sur le disque depuis
// toujours, et la cle `repos_20` n'etait declaree nulle part — le seuil des
// vingt secondes de repos etait muet sans que rien ne l'ait jamais dit.
//
// Les questions, posees a froid plutot qu'en seance :
//
//  1. toute cle de `priorites` existe-t-elle dans `fichiers` ?
//  2. chaque brique et chaque fragment portent-ils le fichier que leur texte
//     produit (`briques[k] == fichier(textes[k])`) ? Les deux sont ecrits a la
//     main dans `sons.json`, ils peuvent donc diverger ;
//  3. toute phrase enregistree produit-elle un nom de fichier **unique** ?
//  4. les noms restent-ils lisibles, c'est-a-dire les phrases courtes ?
//  5. les orientations declarees sur les mouvements sont-elles au vocabulaire ?
//  6. les amorces que `Circuit` rend le sont-elles aussi ?
//  7. les changements d'echauffement ont-ils une cle et un instant valides ?
//  8. la charge cousue par fichiers (`fichier_assemble`, ce que fait
//     l'application) mene-t-elle au meme fichier que son texte ?
//
// Les sons manquants ne sont **pas** un probleme : un fichier absent est un
// silence, jamais une panne. Ils se comptent, ils ne font pas echouer.
//
//     node scripts/verifier_annonces.mjs

import { existsSync } from "node:fs";
import { join } from "node:path";

import {
  AMORCES_EXERCICE,
  NOMBRE_MAXIMAL_DIT,
  fichier_assemble,
} from "../web/static/js/annonces.js";
import { AMORCES_PAR_POSITION } from "../web/static/js/circuit.js";
import { SONS, charger, fichier, phrases_enregistrees, texte_charge } from "./vocabulaire.mjs";

function main() {
  const donnees = charger();
  const { sons, mouvements, echelles } = donnees;
  const problemes = [];

  // 1.
  for (const cle of Object.keys(sons.priorites)) {
    if (!(cle in sons.fichiers)) {
      problemes.push(`cle « ${cle} » : une priorite lui est donnee, mais aucun fichier — elle est demandee et ne produit rien`);
    }
  }

  // 2.
  for (const [table, textes] of [["textes", sons.textes], ["fragments", sons.fragments]]) {
    for (const [cle, texte] of Object.entries(textes)) {
      if (sons.briques[cle] !== fichier(texte)) {
        problemes.push(`${table} « ${cle} » : briques doit valoir ${fichier(texte)}, pas ${sons.briques[cle] ?? "rien"}`);
      }
    }
  }
  for (const cle of Object.keys(sons.briques)) {
    if (!(cle in sons.textes) && !(cle in sons.fragments)) {
      problemes.push(`brique « ${cle} » : aucun texte dans textes ni fragments`);
    }
  }

  // 3. et 4.
  const phrases = phrases_enregistrees(donnees);
  const par_fichier = {};
  for (const [origine, texte] of Object.entries(phrases)) {
    const nom = fichier(texte);
    (par_fichier[nom] ??= []).push(origine);
    if (nom.length > sons.longueur_maximale_nom) {
      problemes.push(
        `« ${origine} » : ${nom.length} caracteres de nom de fichier (plafond ` +
          `${sons.longueur_maximale_nom}). La phrase est trop longue pour une brique, decoupe-la — « ${texte} »`
      );
    }
  }
  for (const [nom, origines] of Object.entries(par_fichier)) {
    if (origines.length > 1) {
      problemes.push(`collision sur « ${nom} » : ${origines.sort().join(", ")} produisent le meme nom, l'un sera prononce a la place de l'autre`);
    }
  }

  // 5., 7.
  for (const m of Object.values(mouvements)) {
    if (m.orientation != null && !sons.orientations.includes(m.orientation)) {
      problemes.push(`« ${m.nom} » : orientation « ${m.orientation} » hors vocabulaire (${sons.orientations.join(", ")})`);
    }
    for (const [fraction, quoi] of m.changements ?? []) {
      if (!(`changement_${quoi}` in sons.fichiers)) {
        problemes.push(`« ${m.nom} » : changement « ${quoi} » hors vocabulaire`);
      }
      if (!(fraction > 0 && fraction < 1)) {
        problemes.push(`« ${m.nom} » : changement a ${fraction}, hors de ]0, 1[`);
      }
    }
  }
  for (const [cle, texte] of Object.entries(sons.textes)) {
    if (cle.startsWith("changement_") && JSON.stringify(sons.fichiers[cle]) !== JSON.stringify([fichier(texte)])) {
      problemes.push(`cle « ${cle} » : fichiers doit jouer ${fichier(texte)}, le fichier de sa brique`);
    }
  }

  // 6.
  for (const amorce of Object.values(AMORCES_PAR_POSITION)) {
    if (!AMORCES_EXERCICE.includes(amorce)) {
      problemes.push(`amorce « ${amorce} » : rendue par Circuit.amorce_annonce mais hors du vocabulaire (${AMORCES_EXERCICE.join(", ")})`);
    }
  }

  // 8.
  for (const halteres of [1, 2]) {
    for (const poids of echelles.reference) {
      const texte = texte_charge(sons.fragments, halteres, poids);
      if (!texte) continue;
      const cousu = fichier_assemble(
        sons.briques[halteres === 1 ? "prepare_un_haltere_de" : "prepare_deux_halteres_de"],
        fichier(String(poids)),
        sons.briques[poids === 1 ? "kilo" : "kilos"]
      );
      if (cousu !== fichier(texte)) {
        problemes.push(`charge ${halteres}x${poids} kg : l'application coud ${cousu}, le texte donne ${fichier(texte)}`);
      }
    }
  }

  if (problemes.length) {
    console.log(`${problemes.length} problemes :\n`);
    for (const p of problemes) console.log(`  - ${p}`);
  }

  const attendus = new Set();
  for (const variantes of Object.values(sons.fichiers)) for (const f of variantes) attendus.add(f);
  for (const texte of Object.values(phrases)) attendus.add(fichier(texte));
  for (let n = 1; n <= NOMBRE_MAXIMAL_DIT; n++) attendus.add(fichier(String(n)));
  const manquants = [...attendus].filter((f) => !existsSync(join(SONS, f)));
  console.log(
    `\n${attendus.size - manquants.length} / ${attendus.size} sons enregistres. ` +
      `${manquants.length} restent a faire — voir audio/A_ENREGISTRER.md`
  );

  if (problemes.length) {
    process.exitCode = 1;
    return;
  }
  console.log("Les tables du coach se tiennent.");
}

main();
