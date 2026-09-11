// Rejoue en JavaScript les ecritures relevees par `generer_historique.py`.
//
// La question verifiee : a ecritures identiques, `recuperer_historique` rend-il
// la meme structure des deux cotes ? Cela couvre les jointures, les valeurs de
// repli, l'ordre des seances, le detail des series et le cloisonnement par
// profil — les deux profils sont relus apres *chaque* ecriture, donc une
// seance qui deborderait sur l'autre historique se verrait au pas ou elle est
// ecrite, pas trois cents pas plus loin.
//
// Usage : node scripts/comparer_historique.mjs
// Prealable : python -m scripts.generer_historique

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  base_vide, creer_utilisateur, enregistrer_seance, enregistrer_ressentis,
  enregistrer_ancrage, supprimer_seance, recuperer_historique,
  recuperer_ancrages, exporter, importer,
} from "../web/static/js/historique.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(ICI, "fixtures_historique.jsonl");

// Meme horloge figee que cote Python : `enregistrer_seance` horodate, et deux
// executions ecriraient sinon des dates differentes.
const DEBUT = new Date(2026, 2, 1, 8, 0);
const PAS_MINUTES = 1;

function horloge_figee() {
  let appels = 0;
  return () => new Date(DEBUT.getTime() + appels++ * PAS_MINUTES * 60_000);
}

const ECARTS_DETAILLES = 3;

function main() {
  const pas = readFileSync(FIXTURES, "utf-8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));

  const base = base_vide();
  const maintenant = horloge_figee();
  const echecs = [];
  let valeurs = 0;

  for (const ligne of pas) {
    const a = ligne.arguments;
    let resultat = null;
    let erreur = null;
    try {
      if (ligne.commande === "creer_utilisateur") {
        creer_utilisateur(base, a.nom, maintenant);
      } else if (ligne.commande === "enregistrer_seance") {
        resultat = enregistrer_seance(base, { ...a, maintenant });
      } else if (ligne.commande === "enregistrer_ressentis") {
        resultat = enregistrer_ressentis(base, a.seance_id, a.ressentis);
      } else if (ligne.commande === "enregistrer_ancrage") {
        enregistrer_ancrage(base, a.nom_exercice, a.niveau, {
          raison: a.raison, utilisateur_id: a.utilisateur_id, maintenant,
        });
      } else if (ligne.commande === "supprimer_seance") {
        supprimer_seance(base, a.seance_id, a.utilisateur_id);
      } else {
        throw new Error(`Commande inconnue : ${ligne.commande}`);
      }
    } catch (e) {
      erreur = e.message;
    }

    const ecarts = [];
    if (erreur) ecarts.push({ champ: "(exception)", attendu: "aucune", obtenu: erreur });
    if (JSON.stringify(ligne.resultat) !== JSON.stringify(resultat)) {
      ecarts.push({
        champ: "(valeur de retour)",
        attendu: JSON.stringify(ligne.resultat),
        obtenu: JSON.stringify(resultat),
      });
    }

    for (const [profil, attendu] of Object.entries(ligne.historique)) {
      const obtenu = recuperer_historique(base, Number(profil));
      valeurs += JSON.stringify(attendu).length;
      if (JSON.stringify(attendu) !== JSON.stringify(obtenu)) {
        ecarts.push({
          champ: `historique du profil ${profil}`,
          attendu: JSON.stringify(attendu).slice(0, 260),
          obtenu: JSON.stringify(obtenu).slice(0, 260),
        });
      }
    }
    for (const [profil, attendu] of Object.entries(ligne.ancrages)) {
      const obtenu = recuperer_ancrages(base, Number(profil));
      if (JSON.stringify(attendu) !== JSON.stringify(obtenu)) {
        ecarts.push({
          champ: `ancrages du profil ${profil}`,
          attendu: JSON.stringify(attendu).slice(0, 260),
          obtenu: JSON.stringify(obtenu).slice(0, 260),
        });
      }
    }

    if (ecarts.length) echecs.push({ ligne, ecarts });
  }

  const seances = base.seances.length;
  const series = base.series_realisees.length;
  console.log(
    `${pas.length} ecritures rejouees, ${seances} seances et ${series} series en base`
  );

  // L'aller-retour par le fichier d'export doit rendre la base identique :
  // c'est la seule verification qui compte pour une sauvegarde, et elle ne
  // coute qu'une comparaison.
  const relue = importer(exporter(base));
  const aller_retour =
    JSON.stringify(recuperer_historique(base, 1)) ===
      JSON.stringify(recuperer_historique(relue, 1)) &&
    JSON.stringify(recuperer_historique(base, 2)) ===
      JSON.stringify(recuperer_historique(relue, 2));
  console.log(`export puis import : ${aller_retour ? "base identique" : "BASE ALTEREE"}`);

  if (!echecs.length && aller_retour) {
    console.log("\nAucun ecart : le portage de l'historique est fidele.");
    return;
  }

  console.log(`\n${echecs.length} ecritures divergent. Les ${ECARTS_DETAILLES} premieres :\n`);
  for (const { ligne, ecarts } of echecs.slice(0, ECARTS_DETAILLES)) {
    console.log(`  pas ${ligne.pas} — ${ligne.commande}`);
    for (const e of ecarts) {
      console.log(`    ${e.champ}`);
      console.log(`      python = ${e.attendu}`);
      console.log(`      js     = ${e.obtenu}`);
    }
    console.log();
  }
  process.exitCode = 1;
}

main();
