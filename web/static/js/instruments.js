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
// sur les poses figees des tests et le compare au jeton que rend la detection
// **actuelle**. Changer un seuil dans detections.js sans le changer ici fait
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
  _hanche_decollee, _visibilite_bras, _genou_depasse_pied, _poignet_devant_epaule,
  _inclinaison_buste, _genou_au_dessus_de_l_autre, _hauteur_poignets,
  _ecart_chevilles, _bras_le_plus_bas, _bras_le_plus_haut, _descente_hanches,
  _toucher_hauteur, _toucher_croisement,
  _pied_le_plus_leve, _genou_le_plus_leve, _genou_le_plus_haut_sous_hanche, _appui_exterieur,
  _main_opposee_au_dessus_de_la_tete, _pied_haut_sous_hanche, _pied_haut_portee, _ecart_avant_arriere,
  _mains_au_genou, _crochet_croisement, _crochet_hauteur, _ecart_a_sa_place, _flexion,
  _ecart_poignets, _hanches_au_dessus_des_genoux,
  FENTE_GENOU_AVANT_MIN, SOULEVE_BAS_MAX, SOULEVE_HAUT_MIN,
  JACK_ECART_JOINT, JACK_ECART_ECARTE, JACK_BRAS_BAS, JACK_BRAS_HAUT, JACK_MAINS_JOINTES,
  POWER_JACK_HANCHES_BAS, POWER_JACK_HANCHES_HAUT,
  STANCE_JACK_TOUCHER, STANCE_JACK_DEBOUT, STANCE_JACK_CROISEMENT, STANCE_JACK_ECARTE,
  COURSE_PIED_LEVE, COURSE_PIEDS_AU_SOL, MONTEE_GENOU_HAUT, MONTEE_GENOUX_BAS,
  TALON_HAUT, TALON_GENOUX_ALIGNES, TALON_PIEDS_AU_SOL,
  HEISMAN_GENOU_LEVE, HEISMAN_APPUI_EXTERIEUR, GENOUX_ALIGNES,
  CLIMBER_GENOU_LEVE, CLIMBER_MAIN_HAUTE,
  KICK_PIED_HAUT, KICK_PORTEE, KICK_PIEDS_AU_SOL,
  CISEAUX_ECARTES, CISEAUX_JOINTS,
  SEUIL_COMPTAGE_POMPE, SOL_DEBOUT_HANCHES, SOL_BUSTE_DEBOUT, SOL_BUSTE_COUCHE, SUICIDE_BRAS_TENDUS,
  POWER_KNEE_GENOU_LEVE, POWER_KNEE_MAINS,
  CROCHET_CROISE, CROCHET_HAUTEUR, GARDE_DE_SON_COTE, GARDE_HAUTE,
  SKI_DE_COTE, SKI_FLECHI, SKI_TENDU,
} from "./detections.js";

const ECHELLE_ANGLE = [0, 180];

// Pourquoi une repetition ne compte pas : une cle de `messages.js` (le
// bandeau) et de `sons.json` (la voix, apres « Ca ne compte pas »), par
// position visee. Un constat de ce qui a manque, pas un ordre. Un petit vocabulaire partage, parce que chaque cle est une
// prise de son : ce qui manque se dit de la meme facon d'un mouvement a
// l'autre. Une mesure sans raison pour une cible laisse la phrase generique
// du demi-cycle (`amplitude_aller_incomplet`, `amplitude_retour_incomplet`).
export const RAISONS = {
  descendre: "raison_descendre",
  monter: "raison_monter",
  tendre: "raison_tendre_bras",
  remonter: "raison_remonter",
  coudes: "raison_coudes_ecartes",
};
// Le mauvais cote d'un mouvement unilateral se dit par la meme voix, mais
// aucune mesure ne le porte : c'est `surveiller_autre_cote` (`moteur.js`) qui
// le voit, en lisant la detection de l'autre cote. `raison_autre_bras`,
// `raison_autre_jambe`, `raison_autre_cote` — par le membre du mouvement.

// La meme mesure, qui sait dire ce qui lui manque.
function avec_raisons(mesure, raisons) {
  return { ...mesure, raisons };
}

// Bas -> haut sur un bras qui pousse : en bas, « tu ne descends pas assez
// bas » ; en haut, « tes bras ne sont pas completement tendus ».
const POUSSEE = { debut: RAISONS.descendre, fin: RAISONS.tendre };
// Bas -> debout sur des jambes : « tu ne descends pas assez bas », « tu ne
// remontes pas completement ».
const FLEXION = { debut: RAISONS.descendre, fin: RAISONS.remonter };

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

// L'inclinaison du buste au-dessus du sol (crunch), ecrite sur la hanche.
function inclinaison_buste(libelle, zones) {
  return {
    libelle, unite: "°", echelle: [-20, 90], sommet: "hanche_gauche", zones,
    valeur: (corps) => _inclinaison_buste(corps),
  };
}

function curl(cote) {
  const [e, c, p] = cote === "droit"
    ? ["epaule_droite", "coude_droit", "poignet_droit"]
    : ["epaule_gauche", "coude_gauche", "poignet_gauche"];
  return {
    ordre: ["fin", "debut"],
    defaut: "milieu",
    mesures: [avec_raisons(angle(`Coude ${cote}`, e, c, p, { fin: ["<", 20], debut: [">", 160] }),
      { fin: RAISONS.monter })],
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
function deux_coudes(debut, fin, { ordre = ["debut", "fin"], extra = [], raisons = undefined } = {}) {
  return {
    ordre,
    defaut: "milieu",
    mesures: [
      avec_raisons(angle("Coude gauche", "epaule_gauche", "coude_gauche", "poignet_gauche", { debut, fin }), raisons),
      avec_raisons(angle("Coude droit", "epaule_droite", "coude_droit", "poignet_droit", { debut, fin }), raisons),
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
  const droite = cote === "droite";
  const [h, g, c, autre] = droite
    ? ["hanche_droite", "genou_droit", "cheville_droite", "genou_gauche"]
    : ["hanche_gauche", "genou_gauche", "cheville_gauche", "genou_droit"];
  return {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [
      avec_raisons(angle(`Genou ${droite ? "droit" : "gauche"}`, h, g, c,
        { debut: ["<", 100], fin: [">", 150] }), FLEXION),
      // La jambe mesuree est devant : une condition du bas seulement, sans
      // raison — l'autre cote (`surveiller_autre_cote`) dit l'erreur de pied.
      {
        libelle: `Genou ${droite ? "droit" : "gauche"} au-dessus de l'autre (÷ tibia)`,
        unite: "", echelle: [-1.2, 1.2], sommet: g,
        zones: { debut: [">", FENTE_GENOU_AVANT_MIN] },
        valeur: (corps) => _genou_au_dessus_de_l_autre(corps[g], corps[c], corps[autre]),
      },
    ],
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
      avec_raisons(angle(`Coude ${cote === "gauche" ? "gauche" : "droit"}`, e, c, p,
        { fin: ["<", seuil_coude], debut: [">", 150] }), { fin: RAISONS.monter }),
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
          raisons: { fin: RAISONS.monter },
          valeur: (corps) => _hauteur_sous_epaule(corps[p], corps[e], corps[h]),
        };
      }),
      avec_raisons(angle("Coude droit (bras tendu)", "epaule_droite", "coude_droit", "poignet_droit", { fin: [">", 140] }),
        { fin: RAISONS.tendre }),
      avec_raisons(angle("Coude gauche (bras tendu)", "epaule_gauche", "coude_gauche", "poignet_gauche", { fin: [">", 140] }),
        { fin: RAISONS.tendre }),
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
    mesures: [
      avec_raisons(coude_proche({ debut: ["<", 120], fin: [">", 160] }), POUSSEE),
      {
        libelle: "Buste debout (< 0 = allongé)", unite: "", echelle: [-0.4, 0.4],
        sommet: null, zones: { debut: ["<", 0], fin: ["<", 0] },
        valeur: (corps) => _buste_vertical(corps),
      },
      visibilite_bras(),
      profondeur_epaules(),
    ],
  },
  // Les deux bornes de hauteur sont deux mesures : une zone ne porte qu'une
  // comparaison. Toutes trois partagees par "debut" et "fin", comme la
  // condition de position de la detection.
  pompe_mur_detection: {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [
      avec_raisons(coude_proche({ debut: ["<", 120], fin: [">", 160] }), POUSSEE),
      {
        libelle: "Buste debout (> 0 = debout)", unite: "", echelle: [-0.4, 0.4],
        sommet: null, zones: { debut: [">", 0], fin: [">", 0] },
        valeur: (corps) => _buste_vertical(corps),
      },
      {
        libelle: "Mains pas trop basses (sous l'épaule, en bustes)", unite: "",
        echelle: [-0.6, 1], sommet: null, zones: { debut: ["<", 0.5], fin: ["<", 0.5] },
        valeur: (corps) => _poignet_devant_epaule(corps)[0],
      },
      {
        libelle: "Mains pas trop hautes", unite: "",
        echelle: [-0.6, 1], sommet: null, zones: { debut: [">", -0.35], fin: [">", -0.35] },
        valeur: (corps) => _poignet_devant_epaule(corps)[0],
      },
      {
        libelle: "Mains devant l'épaule (en bustes)", unite: "",
        echelle: [0, 1.2], sommet: null, zones: { debut: [">", 0.2], fin: [">", 0.2] },
        valeur: (corps) => _poignet_devant_epaule(corps)[1],
      },
      visibilite_bras(),
    ],
  },
  pompe_profondeur: {
    ordre: ["profond"],
    defaut: null,
    mesures: [coude_proche({ profond: ["<", 108] })],
  },
  developpe_couche_sol_detection: {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [
      avec_raisons(coude_proche({ debut: ["<", 100], fin: [">", 160] }), POUSSEE),
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
    raisons: POUSSEE,
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
      {
        libelle: "Écart des coudes (÷ largeur d'épaules)", unite: "", echelle: [0, 2.5],
        sommet: "coude_gauche", zones: { debut: ["<", 1.6], fin: ["<", 1.6] },
        // Une condition de forme : on fait le mouvement, coudes ouverts.
        raisons: { debut: RAISONS.coudes, fin: RAISONS.coudes },
        valeur: (corps) => _ecart_rapporte_aux_epaules(corps.coude_gauche, corps.coude_droit, corps),
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
      sommet: "coude_gauche", zones: { forme_coudes_trop_ecartes: [">", 1.3] },
      valeur: (corps) =>
        corps.coude_gauche.y < corps.epaule_gauche.y && corps.coude_droit.y < corps.epaule_droite.y
          ? _ecart_rapporte_aux_epaules(corps.coude_gauche, corps.coude_droit, corps)
          : null,
    }],
  },
  developpe_epaule_detection: deux_coudes(["<", 60], [">", 150], {
    raisons: POUSSEE,
    extra: [
      ecart_vertical("Poignet gauche au-dessus de l'épaule", "poignet_gauche", "epaule_gauche", { fin: ["<", 0] }),
      ecart_vertical("Poignet droit au-dessus de l'épaule", "poignet_droit", "epaule_droite", { fin: ["<", 0] }),
    ],
  }),

  // Deux mesures pour une seule valeur : une zone ne porte qu'une
  // comparaison, et `fin` est une fourchette.
  crunches_detection: {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [
      avec_raisons(inclinaison_buste("Buste décollé (degrés au-dessus du sol)", { debut: ["<", 10], fin: [">", 20] }),
        { fin: RAISONS.monter }),
      inclinaison_buste("Buste pas redressé (assis au-delà)", { fin: ["<", 60] }),
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
    mesures: [avec_raisons(distance_moyenne("Distance coude-genou (moyenne)",
      ["coude_gauche", "genou_gauche"], ["coude_droit", "genou_droit"], [0, 0.4],
      { debut: ["<", 0.05], fin: [">", 0.15] }), FLEXION)],
  },

  fente_droite_detection: fente("droite"),
  fente_gauche_detection: fente("gauche"),
  fente_droite_erreur_genou: genou_avant("droite"),
  fente_gauche_erreur_genou: genou_avant("gauche"),

  souleve_de_terre_roumain_detection: {
    ordre: ["debut", "fin"],
    defaut: "milieu",
    mesures: [avec_raisons({
      libelle: "Poignets au-dessus des chevilles (÷ tibia)",
      unite: "", echelle: [0, 2.2], sommet: "poignet_gauche",
      zones: { debut: ["<", SOULEVE_BAS_MAX], fin: [">", SOULEVE_HAUT_MIN] },
      valeur: (corps) => _hauteur_poignets(corps),
    }, FLEXION)],
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
    mesures: [avec_raisons(angle_moyen("Bras écartés (moyenne hanche-épaule-coude)",
      ["hanche_gauche", "epaule_gauche", "coude_gauche"],
      ["hanche_droite", "epaule_droite", "coude_droit"],
      { fin: [">", 65], debut: ["<", 30] }), { fin: RAISONS.monter })],
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

// ----- sauts (seance cardio) -----

// Le buste debout, condition de position des sauts : allonge ou plie en deux,
// rien n'est ni debut ni fin.
function buste_debout(jetons) {
  return {
    libelle: "Buste debout (> 0)", unite: "", echelle: [-0.3, 0.3], sommet: "epaule_gauche",
    zones: Object.fromEntries(jetons.map((jeton) => [jeton, [">", 0]])),
    valeur: (corps) => _buste_vertical(corps),
  };
}

function ecart_des_chevilles(zones) {
  return {
    libelle: "Écart des chevilles (÷ épaules)", unite: "", echelle: [0, 2.5],
    sommet: "cheville_gauche", zones, valeur: (corps) => _ecart_chevilles(corps),
  };
}

// Le poignet le plus bas des deux, sous son epaule : negatif, les deux mains
// sont en haut.
function bras_en_haut() {
  return avec_raisons({
    libelle: "Main la plus basse, sous l'épaule (÷ buste)", unite: "", echelle: [-1, 1.2],
    sommet: "poignet_gauche", zones: { fin: ["<", JACK_BRAS_HAUT] },
    valeur: (corps) => _bras_le_plus_bas(corps),
  }, { fin: RAISONS.monter });
}

INSTRUMENTS.jumping_jacks_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_debout(["fin", "debut"]),
    ecart_des_chevilles({ fin: [">", JACK_ECART_ECARTE], debut: ["<", JACK_ECART_JOINT] }),
    bras_en_haut(),
    {
      libelle: "Écart des poignets (÷ épaules)", unite: "", echelle: [0, 3],
      sommet: "poignet_gauche", zones: { fin: ["<", JACK_MAINS_JOINTES] },
      valeur: (corps) => _ecart_poignets(corps),
    },
    {
      libelle: "Main la plus haute, sous l'épaule (÷ buste)", unite: "", echelle: [-1, 1.2],
      sommet: "poignet_droit", zones: { debut: [">", JACK_BRAS_BAS] },
      valeur: (corps) => _bras_le_plus_haut(corps),
    },
  ],
};

INSTRUMENTS.power_jacks_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_debout(["fin", "debut"]),
    avec_raisons({
      libelle: "Hanches, par rapport à debout (repère)", unite: "", echelle: [0, 1.2],
      sommet: "hanche_gauche",
      zones: { fin: [">", POWER_JACK_HANCHES_HAUT], debut: ["<", POWER_JACK_HANCHES_BAS] },
      valeur: (corps, repere) => _flexion(corps, repere),
    }, FLEXION),
    ecart_des_chevilles({ debut: [">", JACK_ECART_ECARTE] }),
    bras_en_haut(),
  ],
};

INSTRUMENTS.stance_jacks_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    avec_raisons({
      libelle: "Main au-dessus du pied opposé (÷ tibia)", unite: "", echelle: [0, 2.2],
      sommet: "poignet_gauche",
      zones: { fin: ["<", STANCE_JACK_TOUCHER], debut: [">", STANCE_JACK_DEBOUT] },
      valeur: (corps) => _toucher_hauteur(corps),
    }, { fin: RAISONS.descendre, debut: RAISONS.remonter }),
    {
      libelle: "Main passée de l'autre côté (÷ épaules)", unite: "", echelle: [-0.6, 0.6],
      sommet: "poignet_droit", zones: { fin: [">", STANCE_JACK_CROISEMENT] },
      valeur: (corps) => _toucher_croisement(corps),
    },
    ecart_des_chevilles({ fin: [">", STANCE_JACK_ECARTE], debut: ["<", JACK_ECART_JOINT] }),
  ],
};

// ----- jambes alternees (seance cardio) -----
//
// Chaque cote compte : chaque mesure garde le cote le plus avance, et
// `debut` est la position neutre (pieds au sol, genoux au meme niveau).

// Une mesure sans unite, ecrite sur un point.
function mesure(libelle, sommet, echelle, zones, valeur) {
  return { libelle, unite: "", echelle, sommet, zones, valeur };
}

const pied_leve = (zones) => mesure("Pied le plus levé, au-dessus de l'autre (÷ tibia)",
  "cheville_gauche", [-0.2, 2], zones, (corps) => _pied_le_plus_leve(corps));
const genou_leve = (zones) => mesure("Genou le plus levé, au-dessus de l'autre (÷ tibia)",
  "genou_gauche", [-0.2, 1.5], zones, (corps) => _genou_le_plus_leve(corps));

INSTRUMENTS.course_sur_place_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_debout(["fin", "debut"]),
    pied_leve({ fin: [">", COURSE_PIED_LEVE], debut: ["<", COURSE_PIEDS_AU_SOL] }),
  ],
};

INSTRUMENTS.montees_de_genou_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_debout(["fin", "debut"]),
    avec_raisons(mesure("Genou le plus haut, sous sa hanche (÷ tibia)", "genou_gauche", [-0.5, 1.5],
      { fin: ["<", MONTEE_GENOU_HAUT], debut: [">", MONTEE_GENOUX_BAS] },
      (corps) => _genou_le_plus_haut_sous_hanche(corps)), { fin: RAISONS.monter }),
  ],
};

INSTRUMENTS.talons_fesses_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_debout(["fin", "debut"]),
    avec_raisons(pied_leve({ fin: [">", TALON_HAUT], debut: ["<", TALON_PIEDS_AU_SOL] }),
      { fin: RAISONS.monter }),
    genou_leve({ fin: ["<", TALON_GENOUX_ALIGNES] }),
  ],
};

INSTRUMENTS.heisman_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_debout(["fin", "debut"]),
    avec_raisons(genou_leve({ fin: [">", HEISMAN_GENOU_LEVE], debut: ["<", GENOUX_ALIGNES] }),
      { fin: RAISONS.monter }),
    mesure("Pied d'appui hors de la hanche (÷ épaules)", "cheville_droite", [-0.5, 1],
      { fin: [">", HEISMAN_APPUI_EXTERIEUR] }, (corps) => _appui_exterieur(corps)),
  ],
};

INSTRUMENTS.mountain_climber_debout_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_debout(["fin", "debut"]),
    avec_raisons(genou_leve({ fin: [">", CLIMBER_GENOU_LEVE], debut: ["<", GENOUX_ALIGNES] }),
      { fin: RAISONS.monter }),
    mesure("Main opposée au-dessus de la tête (÷ buste)", "poignet_gauche", [-1.5, 1],
      { fin: [">", CLIMBER_MAIN_HAUTE] }, (corps) => _main_opposee_au_dessus_de_la_tete(corps)),
  ],
};

INSTRUMENTS.switch_kicks_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_debout(["fin", "debut"]),
    avec_raisons(mesure("Pied le plus haut, sous sa hanche (÷ tibia)", "cheville_gauche", [-0.5, 2.5],
      { fin: ["<", KICK_PIED_HAUT], debut: [">", KICK_PIEDS_AU_SOL] },
      (corps) => _pied_haut_sous_hanche(corps)), { fin: RAISONS.monter }),
    mesure("Portée du pied depuis la hanche (÷ tibia)", "cheville_droite", [0, 2.5],
      { fin: [">", KICK_PORTEE] }, (corps) => _pied_haut_portee(corps)),
  ],
};

INSTRUMENTS.scissor_runs_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_debout(["fin", "debut"]),
    mesure("Écart avant-arrière des chevilles (÷ tibia)", "cheville_gauche", [0, 2.5],
      { fin: [">", CISEAUX_ECARTES], debut: ["<", CISEAUX_JOINTS] },
      (corps) => _ecart_avant_arriere(corps)),
  ],
};

// ----- au sol (seance cardio) -----

// Le buste : couche pour `debut`, debout pour `fin` — le chemin du sol a
// debout.
function buste_du_sol_a_debout() {
  return inclinaison_buste("Inclinaison du buste",
    { debut: ["<", SOL_BUSTE_COUCHE], fin: [">", SOL_BUSTE_DEBOUT] });
}

function hanches_debout() {
  return avec_raisons(mesure("Hanches au-dessus des genoux (÷ tibia, moyenne)", "hanche_gauche", [-0.5, 1.5],
    { fin: [">", SOL_DEBOUT_HANCHES] }, (corps) => _hanches_au_dessus_des_genoux(corps)), { fin: RAISONS.remonter });
}

INSTRUMENTS.burpee_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_du_sol_a_debout(),
    hanches_debout(),
    avec_raisons(coude_proche({ debut: ["<", SEUIL_COMPTAGE_POMPE] }), { debut: RAISONS.descendre }),
  ],
};

INSTRUMENTS.suicide_jumps_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_du_sol_a_debout(),
    hanches_debout(),
    avec_raisons(coude_proche({ debut: [">", SUICIDE_BRAS_TENDUS] }), { debut: RAISONS.tendre }),
  ],
};

// ----- power knees (seance cardio) -----

function power_knee(cote) {
  const [g, c, autre] = cote === "droit"
    ? ["genou_droit", "cheville_droite", "genou_gauche"]
    : ["genou_gauche", "cheville_gauche", "genou_droit"];
  return {
    ordre: ["fin", "debut"],
    defaut: "milieu",
    mesures: [
      buste_debout(["fin", "debut"]),
      avec_raisons(mesure(`Genou ${cote} au-dessus de l'autre (÷ tibia)`, g, [-0.5, 1.5],
        { fin: [">", POWER_KNEE_GENOU_LEVE], debut: ["<", GENOUX_ALIGNES] },
        (corps) => _genou_au_dessus_de_l_autre(corps[g], corps[c], corps[autre])), { fin: RAISONS.monter }),
      mesure("Main la plus loin du genou (÷ tibia)", "poignet_gauche", [0, 3],
        { fin: ["<", POWER_KNEE_MAINS] }, (corps) => _mains_au_genou(corps[g], corps[c], corps)),
      mesure("Main la plus basse, sous l'épaule (÷ buste)", "poignet_droit", [-1, 1.2],
        { debut: ["<", JACK_BRAS_HAUT] }, (corps) => _bras_le_plus_bas(corps)),
    ],
  };
}

INSTRUMENTS.power_knees_droit_detection = power_knee("droit");
INSTRUMENTS.power_knees_gauche_detection = power_knee("gauche");

// ----- crochets (seance cardio) -----

INSTRUMENTS.crochets_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_debout(["fin", "debut"]),
    mesure("Poing passé de l'autre côté (÷ épaules)", "poignet_droit", [-1, 1.5],
      { fin: [">", CROCHET_CROISE], debut: ["<", GARDE_DE_SON_COTE] }, (corps) => _crochet_croisement(corps)),
    avec_raisons(mesure("Ce poing, loin de la hauteur d'épaule (÷ buste)", "poignet_gauche", [0, 1.5],
      { fin: ["<", CROCHET_HAUTEUR] }, (corps) => _crochet_hauteur(corps)), { fin: RAISONS.monter }),
    mesure("Garde : poing le plus bas, sous l'épaule (÷ buste)", "epaule_gauche", [-1, 1.2],
      { debut: ["<", GARDE_HAUTE] }, (corps) => _bras_le_plus_bas(corps)),
  ],
};

// ----- ski (seance cardio) -----

INSTRUMENTS.ski_detection = {
  ordre: ["fin", "debut"],
  defaut: "milieu",
  mesures: [
    buste_debout(["fin", "debut"]),
    avec_raisons(mesure("Hanches, par rapport à debout (repère)", "hanche_gauche", [0, 1.2],
      { fin: ["<", SKI_FLECHI], debut: [">", SKI_TENDU] }, (corps, repere) => _flexion(corps, repere)),
      { fin: RAISONS.descendre }),
    mesure("Pieds loin de la place de départ (÷ épaules)", "cheville_gauche", [0, 2],
      { fin: [">", SKI_DE_COTE] }, (corps, repere) => _ecart_a_sa_place(corps, repere)),
  ],
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

// `repere` : celui de la mise en place, pour une detection qui en lit un
// (`REPERES`, detections.js) ; les autres mesures l'ignorent.
export function lire_instrument(instrument, corps, repere = null) {
  const valeurs = instrument.mesures.map((mesure) => mesure.valeur(corps, repere));
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

/**
 * Le role d'une mesure dans un demi-cycle `depart` -> `cible`, lu sur ses
 * zones, ou null si elle n'en a pas pour la cible :
 *
 * - "chemin" : zones de depart et de cible opposees (l'angle du coude d'une
 *   pompe). C'est sur elles que se mesure la progression ;
 * - "position" : la meme zone des deux cotes, sans raison (« buste
 *   allonge »). Hors d'elle, on n'est pas en train de faire le mouvement ;
 * - "forme" : la meme zone des deux cotes, **avec** une raison (l'ecart des
 *   coudes du triceps). On fait le mouvement, mais mal ;
 * - "cible" : une zone pour la seule cible (« poignets au-dessus des
 *   epaules » en haut d'un developpe), une condition d'arrivee.
 */
export function role_mesure(mesure, depart, cible) {
  const zone_cible = mesure.zones[cible];
  if (!zone_cible) return null;
  const zone_depart = mesure.zones[depart];
  if (!zone_depart) return "cible";
  if (vers_le_bas(zone_depart) !== vers_le_bas(zone_cible)) return "chemin";
  return mesure.raisons?.[cible] ? "forme" : "position";
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
// de depart sans rien compter, et seul le jeton `depart` le peut quand le
// mouvement en declare un. Les allers complets coincident donc avec les
// repetitions comptees.
//
// **Une tentative ne progresse qu'en position** : une image ou une condition
// de position manque (debout pendant une pompe) ne retient rien. Sans cela,
// marcher entre deux series en pliant les bras ferait dire « descends plus
// bas ». Et **une tentative qui echoue dit pourquoi** (`raison`) : la forme
// d'abord — le chemin est alle au bout pendant qu'une condition de forme
// manquait, *a la meme image* (les meilleures valeurs, mesure par mesure, ne
// le verraient pas : l'ecart minimal des coudes vient du haut du mouvement,
// ou ils sont serres) —, puis la premiere mesure bloquante qui porte une
// raison, puis la phrase generique du demi-cycle.
//
// Pur : l'instant est passe a chaque image, rien ne lit l'horloge.
export class SuiviTentatives {
  constructor(instrument, { intervalle_max = 0.5, taille_journal = 200, depart = null } = {}) {
    this.instrument = instrument;
    this.depart = depart;
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
      if (this.depart === null || jeton === this.depart) this.position = jeton;
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
    const roles = this.instrument.mesures.map((mesure) => role_mesure(mesure, depart, cible));
    return {
      type: depart === "debut" ? "aller" : "retour",
      depart,
      cible,
      debut: instant,
      meilleures: this.instrument.mesures.map(() => null),
      roles,
      a_un_chemin: roles.includes("chemin"),
      en_position_vu: false,
      // La premiere mesure de forme qui manquait quand tout le reste etait
      // arrive : la raison d'un refus de forme.
      forme_manquee: null,
    };
  }

  // `demi_cycle` est aussi le sejour d'un demi-cycle complet (l'entree du
  // journal, sans roles) : on y suit l'amplitude reelle, sans condition.
  _retenir(demi_cycle, valeurs) {
    const { roles, cible } = demi_cycle;
    const dedans = (i) => dans_zone(valeurs[i], this.instrument.mesures[i].zones[cible]);
    const indices = (roles ?? []).map((_, i) => i);
    if (indices.some((i) => roles[i] === "position" && !dedans(i))) return;
    if (roles) demi_cycle.en_position_vu = true;
    if (roles && demi_cycle.forme_manquee === null) {
      const arrive = indices.every((i) => !["chemin", "cible"].includes(roles[i]) || dedans(i));
      const manquee = indices.find((i) => roles[i] === "forme" && !dedans(i));
      if (arrive && manquee !== undefined) demi_cycle.forme_manquee = manquee;
    }
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
    // Jamais en position : rien n'a ete tente. Une mesure de chemin existait
    // pour en juger, elle n'a simplement rien vu.
    const avance = complet
      ? 1
      : demi_cycle.a_un_chemin && !demi_cycle.en_position_vu
        ? 0
        : progression(this.instrument, demi_cycle.depart, demi_cycle.cible, demi_cycle.meilleures);
    const entree = {
      type: demi_cycle.type,
      cible: demi_cycle.cible,
      complet,
      duree: instant - demi_cycle.debut,
      meilleures: demi_cycle.meilleures,
      bloquantes,
      raison: complet ? null : this._raison(demi_cycle, bloquantes),
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

  // La cle de message qui dit pourquoi un demi-cycle n'a pas abouti. Les
  // mesures de chemin passent avant les conditions d'arrivee : « descends plus
  // bas » dit le geste, « mains au-dessus des epaules » n'en est qu'un detail.
  _raison(demi_cycle, bloquantes) {
    const raison_de = (i) => this.instrument.mesures[i].raisons?.[demi_cycle.cible] ?? null;
    if (demi_cycle.forme_manquee !== null) return raison_de(demi_cycle.forme_manquee);
    const ordre = ["chemin", "cible"];
    const triees = [...bloquantes].sort(
      (a, b) => ordre.indexOf(demi_cycle.roles[a]) - ordre.indexOf(demi_cycle.roles[b])
    );
    for (const i of triees) if (raison_de(i)) return raison_de(i);
    return `amplitude_${demi_cycle.type}_incomplet`;
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
