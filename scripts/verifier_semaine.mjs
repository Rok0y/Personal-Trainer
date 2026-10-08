// La semaine d'un programme suit-elle le jour de debut et l'ordre choisis ?
//
// Les reponses figees de `comparer_programmes` rejouent des historiques tires
// au hasard, tous lus avec le reglage par defaut (lundi, ordre du fichier) :
// elles ne visitent ni un autre jour de debut, ni un ordre choisi, ni une
// semaine vide entre deux pleines, ni le passage a l'heure d'hiver. Ces cas
// sont ecrits ici a la main, avec leur reponse attendue.
//
//     node scripts/verifier_semaine.mjs

import {
  deplacer_seance,
  jour_debut_retenu,
  ordre_des_seances,
  semaine_du_programme,
} from "../web/static/js/programmes.js";

const PROGRAMME = {
  exigences: [
    { seance: "A", exercice: "x" },
    { seance: "B", exercice: "x" },
    { seance: "C", exercice: "x" },
  ],
  seances: { A: "sa", B: "sb", C: "sc" },
};
const CATALOGUE = { sa: [], sb: [], sc: [] };

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

// Les identifiants suivent l'ordre d'ecriture, donc l'ordre chronologique.
function historique(...lignes) {
  return lignes.map(([nom, date, statut = "finished"], i) => ({ id: i + 1, nom, date, statut }));
}
const semaine = (seances, maintenant, reglage = {}, tours = 1) =>
  semaine_du_programme(PROGRAMME, seances, CATALOGUE, tours, maintenant, reglage);
const libelles = (s) => s.cases.map((c) => c.libelle);

// Lundi 05/10/2026, mercredi 07/10, vendredi 09/10.
const LMV = historique(
  ["sa", "05/10/2026 18:00"],
  ["sb", "07/10/2026 18:00"],
  ["sc", "09/10/2026 18:00"],
);

// --- Jour de debut
{
  const s = semaine(LMV, "10/10/2026 12:00");
  egal("lundi par defaut : semaine reussie", [s.jour_debut, s.faites, s.reussie], [1, 3, true]);
  egal("lundi : bornes de la semaine", [s.debut, s.fin, s.suivante],
    ["05/10/2026 00:00", "11/10/2026 23:59", "12/10/2026 00:00"]);
  egal("lundi : serie", s.serie, 1);
}
{
  // Debut le mercredi : le lundi tombe dans la semaine du mercredi 30/09.
  const s = semaine(LMV, "10/10/2026 12:00", { jour_debut: 3 });
  egal("mercredi : semaine courante", [s.debut, s.faites, s.reussie], ["07/10/2026 00:00", 2, false]);
  egal("mercredi : semaine passee", s.recents,
    [{ debut: "30/09/2026 00:00", faites: 1, total: 3, reussi: false }]);
  egal("mercredi : serie", s.serie, 0);
}
{
  // 0 h pile : le dimanche 23:59 reste dans la semaine, le lundi 00:00 en ouvre une.
  const s = semaine(historique(["sa", "11/10/2026 23:59"], ["sb", "12/10/2026 00:00"]), "12/10/2026 08:00");
  egal("lundi 0 h ouvre la semaine", [s.debut, s.faites, s.recents.length], ["12/10/2026 00:00", 1, 1]);
}
{
  // Passage a l'heure d'hiver le dimanche 25/10/2026 : la semaine du 19/10
  // garde ses sept jours d'horloge murale.
  const s = semaine(historique(["sa", "25/10/2026 23:30"], ["sb", "26/10/2026 00:10"]), "26/10/2026 09:00");
  egal("heure d'hiver : debut", s.debut, "26/10/2026 00:00");
  egal("heure d'hiver : semaine passee", s.recents.map((r) => [r.debut, r.faites]), [["19/10/2026 00:00", 1]]);
}
egal("jour_debut_retenu", [null, undefined, "", "3", 7, -1, 2.5, 0, 6].map(jour_debut_retenu),
  [1, 1, 1, 1, 1, 1, 1, 0, 6]);

// --- Ordre
egal("ordre du fichier par defaut", ordre_des_seances(PROGRAMME, undefined), ["A", "B", "C"]);
egal("ordre choisi recale", ordre_des_seances(PROGRAMME, ["C", "Z", "A", "C"]), ["C", "A", "B"]);
egal("deplacer au milieu", deplacer_seance(["A", "B", "C"], "B", -1), ["B", "A", "C"]);
egal("deplacer en tete : rien", deplacer_seance(["A", "B", "C"], "A", -1), ["A", "B", "C"]);
egal("deplacer en queue : rien", deplacer_seance(["A", "B", "C"], "C", 1), ["A", "B", "C"]);
egal("deplacer un inconnu : rien", deplacer_seance(["A", "B", "C"], "Z", 1), ["A", "B", "C"]);
{
  const vide = semaine([], "08/10/2026 12:00", { ordre: ["C", "A"] });
  egal("ordre : cases", libelles(vide), ["C", "A", "B"]);
  egal("ordre : proposee", vide.prochaine.libelle, "C");
  const deux_tours = semaine([], "08/10/2026 12:00", { ordre: ["C", "A"] }, 2);
  egal("ordre : deux tours", libelles(deux_tours), ["C", "A", "B", "C", "A", "B"]);
  const apres_c = semaine(historique(["sc", "06/10/2026 10:00"]), "08/10/2026 12:00", { ordre: ["C", "A"] });
  egal("ordre : apres C, A", apres_c.prochaine.libelle, "A");
  // L'ordre range les cases, il ne conditionne pas leur remplissage.
  const desordre = semaine(LMV, "10/10/2026 12:00", { ordre: ["C", "B", "A"] });
  egal("ordre : le desordre ne coute rien", desordre.reussie, true);
}

// --- Remplissage et serie
{
  const s = semaine(historique(
    ["sa", "05/10/2026 10:00"],
    ["sa", "06/10/2026 10:00"],
    ["sb", "07/10/2026 10:00", "abandoned"],
    ["inconnue", "07/10/2026 11:00"],
  ), "08/10/2026 12:00");
  egal("surnumeraire, abandonnee, hors programme", [s.faites, s.cases.map((c) => c.faite)], [1, [true, false, false]]);
}
{
  // Pleine, vide, pleine : la semaine vide casse la serie et se compte 0/3.
  const seances = historique(
    ["sa", "21/09/2026 10:00"], ["sb", "23/09/2026 10:00"], ["sc", "25/09/2026 10:00"],
    ["sa", "05/10/2026 10:00"], ["sb", "07/10/2026 10:00"], ["sc", "09/10/2026 10:00"],
  );
  const s = semaine(seances, "10/10/2026 12:00");
  egal("semaine vide comptee", s.recents.map((r) => [r.debut.slice(0, 5), r.faites, r.reussi]),
    [["21/09", 3, true], ["28/09", 0, false]]);
  egal("semaine vide : serie", s.serie, 1);
  // La semaine d'apres, encore vide, ne casse rien.
  const suivante = semaine(seances, "13/10/2026 12:00");
  egal("semaine en cours vide : serie", [suivante.faites, suivante.serie], [0, 1]);
}
{
  const seances = historique(
    ["sa", "28/09/2026 10:00"], ["sb", "29/09/2026 10:00"], ["sc", "30/09/2026 10:00"],
    ["sa", "05/10/2026 10:00"], ["sb", "06/10/2026 10:00"],
  );
  egal("deux semaines d'affilee", semaine(seances, "08/10/2026 12:00").serie, 1);
  egal("deux semaines d'affilee, la seconde finie",
    semaine([...seances, { id: 6, nom: "sc", date: "08/10/2026 10:00", statut: "finished" }], "08/10/2026 12:00").serie, 2);
}

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : la semaine suit le jour de debut et l'ordre choisis.`);
}
