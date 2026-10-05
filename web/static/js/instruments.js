// Instruments de diagnostic : chaque detection de detections.js redecrite en
// **mesures + zones**, pour que la demo puisse montrer ce que la detection
// regarde et pas seulement ce qu'elle conclut.
//
// Une detection rend un jeton et jette l'angle qui l'a produit : pour le curl,
// 35 et 150 degres rendent tous deux "milieu", et personne ne peut savoir
// qu'on est passe *pres* du haut. Un instrument garde la valeur, dit dans
// quelle zone elle tombe et quelle condition manque.
//
// Ce module n'est **jamais sur le chemin du comptage** : la seance compte avec
// detections.js, qui reste la seule autorite. Un instrument en est un miroir,
// et un miroir qui ment serait pire que pas de miroir — d'ou
// scripts/verifier_instruments.mjs, qui rederive le jeton de chaque instrument
// sur les 5 500 poses du harnais des detections et le compare au jeton
// **Python**. Changer un seuil dans detections.js sans le changer ici fait
// echouer ce controle.
//
// La forme est aussi un prototype : « une mesure, des zones ordonnees » est ce
// qu'il faudra pour des seuils plus stricts, pour dire « pas assez haut », et
// pour des mouvements a plus de deux positions.
//
// Regle de derivation, generique : les jetons de `ordre` sont essayes dans cet
// ordre, et un jeton est rendu si **toutes** les mesures qui declarent une zone
// pour lui y sont. Sinon c'est `defaut`. Une mesure qui vaut null ne remplit
// aucune zone. Les comparaisons sont strictes, comme dans les detections.

import { calculer_angle, calculer_distance } from "./outils.js";
import {
  _appui_sur_le_bras, _descente_hanche, _hauteur_sous_epaule, _ecart_lateral,
  _angle_coude_proche, _bras_proche, _buste_vertical, _ecart_rapporte_aux_epaules,
  _hanche_decollee, _visibilite_bras, _genou_depasse_pied,
} from "./detections.js";

const ECHELLE_ANGLE = [0, 180];

// Un angle en un sommet. `sommet` sert a ecrire la valeur sur l'image.
function angle(libelle, a, b, c, zones) {
  return {
    libelle, unite: "°", echelle: ECHELLE_ANGLE, sommet: b, zones,
    valeur: (corps) => calculer_angle(corps[a], corps[b], corps[c]),
  };
}

// La moyenne de deux angles. Meme ordre d'addition que la detection : deux
// operandes commutent exactement en virgule flottante, mais autant ne pas
// avoir a le verifier.
function angle_moyen(libelle, t1, t2, zones) {
  return {
    libelle, unite: "°", echelle: ECHELLE_ANGLE, sommet: t1[1], zones,
    valeur: (corps) =>
      (calculer_angle(corps[t1[0]], corps[t1[1]], corps[t1[2]]) +
        calculer_angle(corps[t2[0]], corps[t2[1]], corps[t2[2]])) / 2,
  };
}

// Une comparaison de hauteurs (`a.y < b.y`) devient une difference signee
// comparee a zero : elle garde la meme verite, et elle dit en plus de combien
// il s'en faut. En coordonnees d'image, y croit vers le bas.
function ecart_vertical(libelle, a, b, zones) {
  return {
    libelle, unite: "", echelle: [-0.4, 0.4], sommet: a, zones,
    valeur: (corps) => corps[a].y - corps[b].y,
  };
}

function distance_moyenne(libelle, p1, p2, echelle, zones) {
  return {
    libelle, unite: "", echelle, sommet: p1[0], zones,
    valeur: (corps) =>
      (calculer_distance(corps[p1[0]], corps[p1[1]]) +
        calculer_distance(corps[p2[0]], corps[p2[1]])) / 2,
  };
}

function curl(cote) {
  const [e, c, p] = cote === "droit"
    ? ["epaule_droite", "coude_droit", "poignet_droit"]
    : ["epaule_gauche", "coude_gauche", "poignet_gauche"];
  return {
    ordre: ["fin", "debut"],
    defaut: "milieu",
    mesures: [angle(`Coude ${cote}`, e, c, p, { fin: ["<", 20], debut: [">", 160] })],
  };
}

function coude_avance(cote) {
  const [h, e, c] = cote === "droit"
    ? ["hanche_droite", "epaule_droite", "coude_droit"]
    : ["hanche_gauche", "epaule_gauche", "coude_gauche"];
  return {
    ordre: ["forme_coude_qui_part_en_avant"],
    defaut: null,
    mesures: [angle(`Coude ${cote} qui avance (angle à l'épaule)`, h, e, c,
      { forme_coude_qui_part_en_avant: [">", 23] })],
  };
}

// Les detections a deux coudes nomment leurs variables a l'envers des
// landmarks (angle_coude_droit lit le cote gauche) ; les libelles suivent ici
// les landmarks, c'est-a-dire ce qu'on voit a l'image.
function deux_coudes(debut, fin, { ordre = ["debut", "fin"], extra = [] } = {}) {
  return {
    ordre,
    defaut: "milieu",
    mesures: [
      angle("Coude gauche", "epaule_gauche", "coude_gauche", "poignet_gauche", { debut, fin }),
      angle("Coude droit", "epaule_droite", "coude_droit", "poignet_droit", { debut, fin }),
      ...extra,
    ],
  };
}

// Le coude lu est celui du bras le plus proche de la camera, qui peut changer
// d'une image a l'autre : le sommet ou ecrire la valeur est donc une fonction.
function coude_proche(zones) {
  return {
    libelle: "Coude le plus proche de la caméra", unite: "°", echelle: ECHELLE_ANGLE, zones,
    sommet: (corps) => (_bras_proche(corps)[1] === corps.coude_gauche ? "coude_gauche" : "coude_droit"),
    valeur: (corps) => _angle_coude_proche(corps),
  };
}

// Sans zone : n'entre dans aucun jeton, sert a verifier au banc d'essai que
// le bon bras est choisi (negatif = epaule gauche plus pres).
function profondeur_epaules() {
  return {
    libelle: "Profondeur épaule G − D (< 0 : gauche plus près)", unite: "", echelle: [-0.6, 0.6],
    sommet: null, zones: {},
    valeur: (corps) => corps.epaule_gauche.z - corps.epaule_droite.z,
  };
}

// Sans zone, comme la profondeur : c'est la visibilite qui choisit le bras,
// et ce cadran dit au banc d'essai sur quoi le choix s'est fait (positif =
// gauche mieux vu). Sous 0,1 en valeur absolue, c'est la profondeur qui
// tranche.
function visibilite_bras() {
  return {
    libelle: "Visibilité bras G − D (> 0 : gauche mieux vu)", unite: "", echelle: [-1, 1],
    sommet: null, zones: {},
    valeur: (corps) =>
      _visibilite_bras(corps.coude_gauche, corps.poignet_gauche) -
      _visibilite_bras(corps.coude_droit, corps.poignet_droit),
  };
}

// Faute du genou avant : dit de combien le genou passe devant la pointe du
// pied, en tibias. null (pied vu de bout) n'entre dans aucune zone.
function genou_avant(cote) {
  const [g, c, t, p] = cote === "droite"
    ? ["genou_droit", "cheville_droite", "talon_droit", "pointe_pied_droite"]
    : ["genou_gauche", "cheville_gauche", "talon_gauche", "pointe_pied_gauche"];
  return {
    ordre: ["forme_genou_avant_trop_avance"],
    defaut: null,
    mesures: [{
      libelle: `Genou ${cote === "droite" ? "droit" : "gauche"} devant la pointe (÷ tibia)`,
      unite: "", echelle: [-0.6, 0.6], sommet: g,
      zones: { forme_genou_avant_trop_avance: [">", 0.05] },
      valeur: (corps) => _genou_depasse_pied(corps[g], corps[c], corps[t], corps[p]),
    }],
  };
}

function fente(cote) {
  const [h, g, c] = cote === "droite"
    ? ["hanche_droite", "genou_droit", "cheville_droite"]
    : ["hanche_gauche", "genou_gauche", "cheville_gauche"];
  return {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [angle(`Genou ${cote === "droite" ? "droit" : "gauche"}`, h, g, c,
      { debut: ["<", 100], fin: [">", 150] })],
  };
}

function gainage_lateral(cote) {
  const g = cote === "gauche";
  const [epaule, hanche, cheville, coude, autre_epaule] = g
    ? ["epaule_gauche", "hanche_gauche", "cheville_gauche", "coude_gauche", "epaule_droite"]
    : ["epaule_droite", "hanche_droite", "cheville_droite", "coude_droit", "epaule_gauche"];
  return {
    ordre: ["maintien"],
    defaut: "repos",
    mesures: [
      angle(`Alignement épaule-hanche-cheville`, epaule, hanche, cheville, { maintien: [">", 155] }),
      ecart_vertical(`Côté ${cote} au sol (épaule plus basse)`, epaule, autre_epaule, { maintien: [">", 0] }),
      ecart_vertical("Hanche au-dessus du coude", hanche, coude, { maintien: ["<", 0] }),
      {
        libelle: "Buste soulevé par l'avant-bras", unite: "", echelle: [-0.2, 0.8],
        sommet: coude, zones: { maintien: [">", 0.25] },
        valeur: (corps) => _appui_sur_le_bras(corps[epaule], corps[coude], corps[hanche]),
      },
      {
        libelle: "Hanche décollée du sol (0 = posée)", unite: "", echelle: [-0.2, 1],
        sommet: hanche, zones: { maintien: [">", 0.3] },
        valeur: (corps) => _hanche_decollee(corps[epaule].y, corps[hanche].y, corps[cheville].y),
      },
    ],
  };
}

function rowing(cote, seuil_buste, seuil_coude) {
  const [e, c, p, h, g] = cote === "gauche"
    ? ["epaule_gauche", "coude_gauche", "poignet_gauche", "hanche_gauche", "genou_gauche"]
    : ["epaule_droite", "coude_droit", "poignet_droit", "hanche_droite", "genou_droit"];
  return {
    ordre: ["fin", "debut"],
    defaut: "milieu",
    mesures: [
      angle(`Coude ${cote === "gauche" ? "gauche" : "droit"}`, e, c, p, { fin: ["<", seuil_coude], debut: [">", 150] }),
      ecart_vertical("Poignet au-dessus de la hanche", p, h, { fin: ["<", 0] }),
      angle("Buste penché (épaule-hanche-genou)", e, h, g, { fin: ["<", seuil_buste] }),
    ],
  };
}

function erreur_buste(cote, seuil) {
  const [e, h, g] = cote === "gauche"
    ? ["epaule_gauche", "hanche_gauche", "genou_gauche"]
    : ["epaule_droite", "hanche_droite", "genou_droit"];
  return {
    ordre: ["forme_buste_pas_assez_penche"],
    defaut: null,
    mesures: [angle("Buste (épaule-hanche-genou)", e, h, g,
      { forme_buste_pas_assez_penche: [">=", seuil] })],
  };
}

export const INSTRUMENTS = {
  curl_biceps_droit_detection: curl("droit"),
  coude_avance_curl_droit: coude_avance("droit"),
  coude_avance_curl_gauche: coude_avance("gauche"),
  curl_biceps_gauche_detection: curl("gauche"),

  elevation_laterale_detection: {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [
      ...["droit", "gauche"].map((cote) => {
        const [p, e, h] = cote === "droit"
          ? ["poignet_droit", "epaule_droite", "hanche_droite"]
          : ["poignet_gauche", "epaule_gauche", "hanche_gauche"];
        return {
          libelle: `Main ${cote === "droit" ? "droite" : "gauche"} sous l'épaule (1 = en bas)`,
          unite: "", echelle: [-0.4, 1.2], sommet: p,
          zones: { debut: [">", 0.6], fin: ["<", 0.15] },
          valeur: (corps) => _hauteur_sous_epaule(corps[p], corps[e], corps[h]),
        };
      }),
      angle("Coude droit (bras tendu)", "epaule_droite", "coude_droit", "poignet_droit", { fin: [">", 140] }),
      angle("Coude gauche (bras tendu)", "epaule_gauche", "coude_gauche", "poignet_gauche", { fin: [">", 140] }),
      ...["droit", "gauche"].map((cote) => {
        const [p, e, autre, h] = cote === "droit"
          ? ["poignet_droit", "epaule_droite", "epaule_gauche", "hanche_droite"]
          : ["poignet_gauche", "epaule_gauche", "epaule_droite", "hanche_gauche"];
        return {
          libelle: `Main ${cote === "droit" ? "droite" : "gauche"} sortie sur le côté`,
          unite: "", echelle: [-0.5, 1.5], sommet: p,
          zones: { fin: [">", 0.3] },
          valeur: (corps) => _ecart_lateral(corps[p], corps[e], corps[autre], corps[h]),
        };
      }),
    ],
  },

  pompe_detection: {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [coude_proche({ debut: ["<", 100], fin: [">", 160] }), visibilite_bras(), profondeur_epaules()],
  },
  developpe_couche_sol_detection: {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [
      coude_proche({ debut: ["<", 100], fin: [">", 160] }),
      {
        libelle: "Buste debout (< 0 = allongé)", unite: "", echelle: [-0.4, 0.4],
        sommet: null, zones: { debut: ["<", 0], fin: ["<", 0] },
        valeur: (corps) => _buste_vertical(corps),
      },
      visibilite_bras(),
      profondeur_epaules(),
    ],
  },
  extension_triceps_au_dessus_de_la_tete_detection: deux_coudes(["<", 90], [">", 140], {
    extra: [
      ecart_vertical("Coude gauche au-dessus de l'épaule", "coude_gauche", "epaule_gauche",
        { debut: ["<", 0], fin: ["<", 0] }),
      ecart_vertical("Coude droit au-dessus de l'épaule", "coude_droit", "epaule_droite",
        { debut: ["<", 0], fin: ["<", 0] }),
      {
        libelle: "Écart des poignets (÷ largeur d'épaules)", unite: "", echelle: [0, 2],
        sommet: "poignet_gauche", zones: { debut: ["<", 0.6], fin: ["<", 0.6] },
        valeur: (corps) => _ecart_rapporte_aux_epaules(corps.poignet_gauche, corps.poignet_droit, corps),
      },
    ],
  }),
  // L'erreur ne parle que coudes leves : l'ecart y vaut donc null quand ils ne
  // le sont pas, ce qui redit la garde de la fonction.
  extension_triceps_erreur_coudes: {
    ordre: ["forme_coudes_trop_ecartes"],
    defaut: null,
    mesures: [{
      libelle: "Écart des coudes (÷ largeur d'épaules)", unite: "", echelle: [0, 2],
      sommet: "coude_gauche", zones: { forme_coudes_trop_ecartes: [">", 1.35] },
      valeur: (corps) =>
        corps.coude_gauche.y < corps.epaule_gauche.y && corps.coude_droit.y < corps.epaule_droite.y
          ? _ecart_rapporte_aux_epaules(corps.coude_gauche, corps.coude_droit, corps)
          : null,
    }],
  },
  developpe_epaule_detection: deux_coudes(["<", 60], [">", 150], {
    extra: [
      ecart_vertical("Poignet gauche au-dessus de l'épaule", "poignet_gauche", "epaule_gauche", { fin: ["<", 0] }),
      ecart_vertical("Poignet droit au-dessus de l'épaule", "poignet_droit", "epaule_droite", { fin: ["<", 0] }),
    ],
  }),

  crunches_detection: {
    ordre: ["fin", "debut"],
    defaut: "milieu",
    mesures: [
      angle("Hanche gauche", "epaule_gauche", "hanche_gauche", "genou_gauche", { fin: ["<", 85], debut: [">", 100] }),
      angle("Hanche droite", "epaule_droite", "hanche_droite", "genou_droit", { fin: ["<", 85], debut: [">", 100] }),
    ],
  },

  detection_gainage: {
    ordre: ["maintien"],
    defaut: "repos",
    mesures: [
      angle_moyen("Hanches (moyenne des deux côtés)",
        ["epaule_gauche", "hanche_gauche", "genou_gauche"],
        ["epaule_droite", "hanche_droite", "genou_droit"],
        { maintien: [">", 135] }),
      ecart_vertical("Hanche au-dessus du coude", "hanche_gauche", "coude_gauche", { maintien: ["<", 0] }),
      {
        libelle: "Épaules soulevées (moyenne des deux bras)", unite: "", echelle: [-0.2, 0.8],
        sommet: "epaule_gauche", zones: { maintien: [">", 0.25] },
        valeur: (corps) =>
          (_appui_sur_le_bras(corps.epaule_gauche, corps.coude_gauche, corps.hanche_gauche) +
            _appui_sur_le_bras(corps.epaule_droite, corps.coude_droit, corps.hanche_droite)) / 2,
      },
      {
        libelle: "Hanches décollées du sol (0 = posées)", unite: "", echelle: [-0.2, 1],
        sommet: "hanche_gauche", zones: { maintien: [">", 0.3] },
        valeur: (corps) => _hanche_decollee(
          (corps.epaule_gauche.y + corps.epaule_droite.y) / 2,
          (corps.hanche_gauche.y + corps.hanche_droite.y) / 2,
          (corps.cheville_gauche.y + corps.cheville_droite.y) / 2
        ),
      },
    ],
  },

  squat_detection: {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [distance_moyenne("Distance coude-genou (moyenne)",
      ["coude_gauche", "genou_gauche"], ["coude_droit", "genou_droit"], [0, 0.4],
      { debut: ["<", 0.05], fin: [">", 0.15] })],
  },

  fente_droite_detection: fente("droite"),
  fente_gauche_detection: fente("gauche"),
  fente_droite_erreur_genou: genou_avant("droite"),
  fente_gauche_erreur_genou: genou_avant("gauche"),

  souleve_de_terre_roumain_detection: {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [distance_moyenne("Distance poignet-cheville (moyenne)",
      ["poignet_gauche", "cheville_gauche"], ["poignet_droit", "cheville_droite"], [0, 0.6],
      { debut: ["<", 0.1], fin: [">", 0.2] })],
  },

  detection_gainage_laterale_gauche: gainage_lateral("gauche"),
  detection_gainage_laterale_droite: gainage_lateral("droit"),

  rowing_unilateral_gauche_detection: rowing("gauche", 160, 90),
  rowing_unilateral_gauche_erreur_buste: erreur_buste("gauche", 160),
  rowing_unilateral_droit_detection: rowing("droit", 160, 90),
  rowing_unilateral_droit_erreur_buste: erreur_buste("droit", 160),
  rowing_penche_detection: rowing("gauche", 165, 70),
  rowing_penche_erreur_buste: erreur_buste("gauche", 165),
  rowing_penche_erreur_genoux: {
    ordre: ["forme_genoux_trop_plies"],
    defaut: null,
    mesures: [angle("Genou gauche", "hanche_gauche", "genou_gauche", "cheville_gauche",
      { forme_genoux_trop_plies: ["<", 155] })],
  },

  oiseau_detection: {
    ordre: ["fin", "debut"],
    defaut: "milieu",
    mesures: [angle_moyen("Bras écartés (moyenne hanche-épaule-coude)",
      ["hanche_gauche", "epaule_gauche", "coude_gauche"],
      ["hanche_droite", "epaule_droite", "coude_droit"],
      { fin: [">", 65], debut: ["<", 30] })],
  },
  oiseau_erreur_coudes: {
    ordre: ["forme_coudes_trop_tendus", "forme_coudes_trop_plies"],
    defaut: null,
    mesures: [angle_moyen("Coudes (moyenne)",
      ["epaule_gauche", "coude_gauche", "poignet_gauche"],
      ["epaule_droite", "coude_droit", "poignet_droit"],
      { forme_coudes_trop_tendus: [">", 170], forme_coudes_trop_plies: ["<", 120] })],
  },

  squat_sur_chaise_detection: {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [{
      libelle: "Descente de la hanche (1 = debout)", unite: "", echelle: [0, 1.2],
      sommet: "hanche_gauche", zones: { debut: ["<", 0.45], fin: [">", 0.75] },
      // Meme calcul que la detection, repli compris : aucune jambe lisible
      // donne null, donc aucune zone, donc "milieu".
      valeur: (corps) => {
        const mesures = [
          _descente_hanche(corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche),
          _descente_hanche(corps.hanche_droite, corps.genou_droit, corps.cheville_droite),
        ].filter((mesure) => mesure !== null);
        if (!mesures.length) return null;
        return mesures.reduce((a, b) => a + b, 0) / mesures.length;
      },
    }],
  },
};

// ----- derivation -----

export function dans_zone(valeur, zone) {
  if (valeur === null || valeur === undefined || !zone) return false;
  const [op, seuil] = zone;
  if (op === "<") return valeur < seuil;
  if (op === ">") return valeur > seuil;
  if (op === "<=") return valeur <= seuil;
  if (op === ">=") return valeur >= seuil;
  return false;
}

export function jeton_des_valeurs(instrument, valeurs) {
  for (const jeton of instrument.ordre) {
    const remplie = instrument.mesures.every(
      (mesure, i) => !mesure.zones[jeton] || dans_zone(valeurs[i], mesure.zones[jeton])
    );
    if (remplie) return jeton;
  }
  return instrument.defaut;
}

export function lire_instrument(instrument, corps) {
  const valeurs = instrument.mesures.map((mesure) => mesure.valeur(corps));
  return { valeurs, jeton: jeton_des_valeurs(instrument, valeurs) };
}

// « Vers la zone » veut dire vers le bas pour une zone `<`, vers le haut pour
// une zone `>` : c'est dans ce sens qu'on retient la meilleure valeur d'une
// tentative.
function vers_le_bas(zone) {
  return zone[0] === "<" || zone[0] === "<=";
}

// ----- affichage -----

export function formater_valeur(mesure, valeur) {
  if (valeur === null || valeur === undefined || Number.isNaN(valeur)) return "—";
  return mesure.unite === "°" ? `${Math.round(valeur)}°` : valeur.toFixed(2);
}

export function formater_zone(mesure, zone) {
  if (!zone) return "";
  const seuil = mesure.unite === "°" ? `${zone[1]}°` : String(zone[1]);
  return `${zone[0]} ${seuil}`;
}

// ----- suivi des tentatives -----

// Part minimale du chemin entre les deux positions qu'une tentative doit avoir
// parcourue pour meriter un commentaire. En dessous, c'est un tremblement
// autour du seuil de depart — le coach qui dirait « pas assez haut » a chaque
// fois parlerait a tort en permanence, et apprendrait vite a ne plus etre
// ecoute. Au-dessus, c'est une vraie demi-repetition : 92 degres sur un curl
// (52 %), 74 sur un rowing ouvert a 90 (95 %).
export const PROGRESSION_SIGNIFICATIVE = 0.3;

// Jusqu'ou une tentative est allee, de 0 (a peine sortie du depart) a 1 (zone
// visee atteinte), sur la meilleure des mesures qui ont une zone de depart et
// une zone visee **opposees** — un seuil ` < ` d'un cote, ` > ` de l'autre. Une
// condition de position partagee par les deux zones (« coudes leves ») ne dit
// rien du chemin parcouru. null quand aucune mesure ne s'y prete.
export function progression(instrument, depart, cible, meilleures) {
  let meilleure = null;
  instrument.mesures.forEach((mesure, i) => {
    const zone_depart = mesure.zones[depart];
    const zone_cible = mesure.zones[cible];
    const v = meilleures[i];
    if (!zone_depart || !zone_cible || v === null || v === undefined || Number.isNaN(v)) return;
    if (vers_le_bas(zone_depart) === vers_le_bas(zone_cible)) return;
    const etendue = zone_depart[1] - zone_cible[1];
    if (etendue === 0) return;
    const part = Math.max(0, Math.min(1, (zone_depart[1] - v) / etendue));
    if (meilleure === null || part > meilleure) meilleure = part;
  });
  return meilleure;
}

function autre(position) {
  return position === "debut" ? "fin" : "debut";
}

function mediane(nombres) {
  const tries = nombres.filter((n) => n !== null && !Number.isNaN(n)).sort((a, b) => a - b);
  if (!tries.length) return null;
  const milieu = Math.floor(tries.length / 2);
  return tries.length % 2 ? tries[milieu] : (tries[milieu - 1] + tries[milieu]) / 2;
}

// Decoupe le mouvement en **demi-cycles** : l'aller part de "debut" et vise
// "fin" (c'est lui qui compte une repetition), le retour part de "fin" et vise
// "debut" (c'est lui qui rearme le compteur). Un demi-cycle s'ouvre quand on
// quitte une extremite et se clot quand on en atteint une :
//
// - aller complet : "fin" atteinte, la repetition compte ;
// - aller interrompu : retour a "debut" sans passer par "fin" — le cas
//   « pas assez haut », qu'aucun jeton ne signale ;
// - retour incomplet : retour a "fin" sans etre repasse par "debut" — le
//   compteur n'est pas rearme, donc la repetition suivante ne comptera pas.
//   C'est la cause la plus sournoise d'une repetition oubliee.
//
// Pendant un demi-cycle, chaque mesure retient sa meilleure valeur *vers la
// zone visee*. Pour un demi-cycle complet, cette valeur continue d'etre suivie
// tant qu'on reste dans la zone atteinte : c'est l'amplitude reelle, celle qui
// dira jusqu'ou un seuil peut etre resserre.
//
// Meme regle que CompteurMouvement pour le premier jeton : il fixe la position
// de depart sans rien compter. Les allers complets coincident donc avec les
// repetitions comptees.
//
// Pur : l'instant est passe a chaque image, rien ne lit l'horloge.
export class SuiviTentatives {
  constructor(instrument, { intervalle_max = 0.5, taille_journal = 200 } = {}) {
    this.instrument = instrument;
    this.maintien = instrument.ordre.includes("maintien");
    this.intervalle_max = intervalle_max;
    this.taille_journal = taille_journal;
    this.position = null;
    this.ouvert = null;
    this.sejour = null;
    this.journal = [];
    this.totaux = {
      aller_complet: 0, aller_interrompu: 0, retour_complet: 0, retour_incomplet: 0,
      // Tentatives trop courtes pour etre des echecs : voir PROGRESSION_SIGNIFICATIVE.
      hesitations: 0,
    };
    this.extremes = instrument.mesures.map(() => ({ min: null, max: null }));
    this.hors_zone = instrument.mesures.map(() => 0);
    this.temps_perdu = 0;
    this.dernier = null;
  }

  // Rend l'entree du journal qui vient de se clore, ou null.
  observer(jeton, valeurs, instant) {
    valeurs.forEach((v, i) => {
      if (v === null || v === undefined || Number.isNaN(v)) return;
      const e = this.extremes[i];
      if (e.min === null || v < e.min) e.min = v;
      if (e.max === null || v > e.max) e.max = v;
    });
    const delta = this.dernier === null ? 0 : Math.min(instant - this.dernier, this.intervalle_max);
    this.dernier = instant;

    if (this.maintien) {
      this._observer_maintien(jeton, valeurs, delta);
      return null;
    }
    return this._observer_repetitions(jeton, valeurs, instant);
  }

  // Un maintien perdu se ventile par mesure : c'est la reponse a « pourquoi
  // le chrono s'arrete ». Plusieurs mesures peuvent manquer a la fois, donc
  // les temps ne s'additionnent pas au temps perdu total.
  _observer_maintien(jeton, valeurs, delta) {
    if (jeton === "maintien") return;
    this.temps_perdu += delta;
    this.instrument.mesures.forEach((mesure, i) => {
      if (mesure.zones.maintien && !dans_zone(valeurs[i], mesure.zones.maintien)) {
        this.hors_zone[i] += delta;
      }
    });
  }

  _observer_repetitions(jeton, valeurs, instant) {
    const extremite = jeton === "debut" || jeton === "fin";

    if (!extremite) {
      if (this.position && !this.ouvert) {
        this.sejour = null;
        this.ouvert = this._ouvrir(this.position, autre(this.position), instant);
      }
      if (this.ouvert) this._retenir(this.ouvert, valeurs);
      return null;
    }

    if (this.sejour && jeton === this.sejour.cible) this._retenir(this.sejour, valeurs);

    if (this.position === null) {
      this.position = jeton;
      return null;
    }

    let entree = null;
    if (this.ouvert) {
      this._retenir(this.ouvert, valeurs);
      entree = this._clore(this.ouvert, jeton === this.ouvert.cible, instant);
      this.ouvert = null;
    } else if (jeton !== this.position) {
      // Saut d'une extremite a l'autre sans image intermediaire : un
      // demi-cycle complet de duree nulle.
      const saut = this._ouvrir(this.position, jeton, instant);
      this._retenir(saut, valeurs);
      entree = this._clore(saut, true, instant);
    }
    this.position = jeton;
    return entree;
  }

  _ouvrir(depart, cible, instant) {
    return {
      type: depart === "debut" ? "aller" : "retour",
      depart,
      cible,
      debut: instant,
      meilleures: this.instrument.mesures.map(() => null),
    };
  }

  _retenir(demi_cycle, valeurs) {
    this.instrument.mesures.forEach((mesure, i) => {
      const zone = mesure.zones[demi_cycle.cible];
      const v = valeurs[i];
      if (!zone || v === null || v === undefined || Number.isNaN(v)) return;
      const actuelle = demi_cycle.meilleures[i];
      if (actuelle === null || (vers_le_bas(zone) ? v < actuelle : v > actuelle)) {
        demi_cycle.meilleures[i] = v;
      }
    });
  }

  _clore(demi_cycle, complet, instant) {
    const bloquantes = complet
      ? []
      : this.instrument.mesures
        .map((mesure, i) => i)
        .filter((i) => {
          const zone = this.instrument.mesures[i].zones[demi_cycle.cible];
          return zone && !dans_zone(demi_cycle.meilleures[i], zone);
        });
    const avance = complet
      ? 1
      : progression(this.instrument, demi_cycle.depart, demi_cycle.cible, demi_cycle.meilleures);
    const entree = {
      type: demi_cycle.type,
      cible: demi_cycle.cible,
      complet,
      duree: instant - demi_cycle.debut,
      meilleures: demi_cycle.meilleures,
      bloquantes,
      progression: avance,
      // Sans mesure pour en juger, on prefere signaler que taire.
      significatif: complet || avance === null || avance >= PROGRESSION_SIGNIFICATIVE,
    };
    if (entree.significatif) {
      const issue = complet ? "complet" : demi_cycle.type === "aller" ? "interrompu" : "incomplet";
      this.totaux[`${demi_cycle.type}_${issue}`] += 1;
    } else {
      this.totaux.hesitations += 1;
    }
    this.journal.push(entree);
    if (this.journal.length > this.taille_journal) this.journal.shift();
    this.sejour = complet ? entree : null;
    return entree;
  }

  // Ce que la demo enregistre a la fin d'un exercice : des nombres, jamais du
  // texte, pour que le rendu puisse changer sans perdre ce qui a ete mesure.
  resume() {
    const mesures = this.instrument.mesures.map((mesure, i) => ({
      libelle: mesure.libelle,
      unite: mesure.unite,
      zones: mesure.zones,
      min: this.extremes[i].min,
      max: this.extremes[i].max,
      hors_zone: this.hors_zone[i],
      // Amplitude mediane des demi-cycles complets, par sens : jusqu'ou on
      // va vraiment quand ca compte.
      amplitude_aller: mediane(this.journal
        .filter((e) => e.complet && e.type === "aller").map((e) => e.meilleures[i])),
      amplitude_retour: mediane(this.journal
        .filter((e) => e.complet && e.type === "retour").map((e) => e.meilleures[i])),
    }));
    const echecs = this.journal
      .filter((e) => !e.complet && e.significatif)
      .slice(-10)
      .map((e) => ({
        type: e.type,
        progression: e.progression,
        bloquantes: e.bloquantes.map((i) => ({ mesure: i, valeur: e.meilleures[i] })),
      }));
    return {
      maintien: this.maintien,
      totaux: { ...this.totaux },
      tempo_aller: mediane(this.journal.filter((e) => e.complet && e.type === "aller").map((e) => e.duree)),
      tempo_retour: mediane(this.journal.filter((e) => e.complet && e.type === "retour").map((e) => e.duree)),
      temps_perdu: this.temps_perdu,
      mesures,
      echecs,
    };
  }
}
