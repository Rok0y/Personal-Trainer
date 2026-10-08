// Rejoue une suite d'ecritures figee sur la base de l'historique.
//
// La question verifiee : a ecritures identiques, `recuperer_historique`
// rend-il toujours la meme structure ? Cela couvre les jointures, les valeurs
// de repli, l'ordre des seances, le detail des series et le cloisonnement par
// profil — chaque profil est relu apres *chaque* ecriture, donc une seance qui
// deborderait sur l'autre historique se verrait au pas ou elle est ecrite, pas
// trois cents pas plus loin. Un troisieme profil est cree puis supprime, et
// continue d'etre relu : c'est la seule facon de voir une seance, un exercice
// ou un ancrage laisse derriere.
//
// Usage : node scripts/comparer_historique.mjs [--mettre-a-jour]

import {
  base_vide, creer_utilisateur, enregistrer_seance, enregistrer_ressentis,
  enregistrer_ancrage, supprimer_seance, supprimer_utilisateur, recuperer_historique,
  definir_note_athlete,
  definir_variantes,
  recuperer_ancrages, statistiques_exercices, exporter, importer,
} from "../web/static/js/historique.js";
import { normaliser as normaliser_variantes } from "../web/static/js/variantes.js";
import { METTRE_A_JOUR, Releve, lire_lignes } from "./fixtures.mjs";

// Horloge figee : `enregistrer_seance` horodate, et deux executions
// ecriraient sinon des dates differentes.
const DEBUT = new Date(2026, 2, 1, 8, 0);
const PAS_MINUTES = 1;

function horloge_figee() {
  let appels = 0;
  return () => new Date(DEBUT.getTime() + appels++ * PAS_MINUTES * 60_000);
}

function main() {
  const pas = lire_lignes("historique");
  const base = base_vide();
  const maintenant = horloge_figee();
  const releve = new Releve();

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
      } else if (ligne.commande === "supprimer_utilisateur") {
        resultat = supprimer_utilisateur(base, a.utilisateur_id);
      } else if (ligne.commande === "definir_variantes") {
        definir_variantes(base, a.utilisateur_id, a.variantes);
      } else if (ligne.commande === "definir_note_athlete") {
        try {
          definir_note_athlete(base, a.utilisateur_id, a.note);
        } catch {
          resultat = "refus";
        }
      } else {
        throw new Error(`Commande inconnue : ${ligne.commande}`);
      }
    } catch (e) {
      erreur = e.message;
    }

    const ou = `pas ${ligne.pas} — ${ligne.commande}`;
    // Une exception est un comportement releve, au meme titre qu'un resultat.
    releve.verifier(`${ou} / exception`, ligne, "erreur", erreur ?? undefined);
    releve.verifier(`${ou} / valeur de retour`, ligne, "resultat", resultat);

    for (const profil of Object.keys(ligne.historique)) {
      releve.verifier(
        `${ou} / historique du profil ${profil}`,
        ligne.historique, profil,
        recuperer_historique(base, Number(profil))
      );
    }
    for (const profil of Object.keys(ligne.ancrages)) {
      releve.verifier(
        `${ou} / ancrages du profil ${profil}`,
        ligne.ancrages, profil,
        recuperer_ancrages(base, Number(profil))
      );
    }
    for (const profil of Object.keys(ligne.statistiques ?? {})) {
      releve.verifier(
        `${ou} / statistiques du profil ${profil}`,
        ligne.statistiques, profil,
        statistiques_exercices(recuperer_historique(base, Number(profil)))
      );
    }
    for (const profil of Object.keys(ligne.notes ?? {})) {
      const u = base.utilisateurs.find((x) => x.id === Number(profil));
      releve.verifier(
        `${ou} / note du profil ${profil}`,
        ligne.notes, profil,
        u ? [u.note_athlete ?? null, u.note_relevee_apres ?? null, normaliser_variantes(u.variantes)] : null
      );
    }
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

  if (!aller_retour && !METTRE_A_JOUR) process.exitCode = 1;
  releve.conclure({
    fichier: "historique",
    lignes: pas,
    succes: "Aucun ecart : l'historique rend les reponses figees.",
    detail: 3,
  });
}

main();
