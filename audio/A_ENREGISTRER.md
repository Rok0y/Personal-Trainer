# Ce qu'il reste a enregistrer

> Ce fichier est **genere**. Ne le modifie pas a la main : relance
> `python -m scripts.lister_annonces` apres chaque lot, il se met a jour tout
> seul et recompte ce qui reste.

## Comment enregistrer

1. Enregistre chaque phrase dans un `.wav` portant **exactement** le nom donne
   ci-dessous, et depose-le dans `audio/a_traiter/`.
2. Lance `python audio/nettoyer_sons.py` : il rogne les silences, pose un fondu
   et ecrit le resultat dans `audio/Fichiers/`.
3. Lance `python -m scripts.preparer_demo` pour que l'application les recoive.

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
le texte dans `audio/annonces.py` et relance ce script : le nom de fichier
suivra. L'inverse — renommer un fichier — ne changerait rien, le code cherche
le nom que la table produit.

**20 prises restantes.**

## Amorces d'annonce

Trois facons d'annoncer un mouvement, selon sa place dans la seance. Elles se disent **devant** un nom d'exercice, jamais seules : prononce-les suspendues, sans chute de fin de phrase — « prochain exercice : curl biceps droit ». Trois prises x trente-neuf noms = cent dix-sept annonces, et c'est ce qui justifie que le nom du mouvement reste une prise a part.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `prochain_exercice.wav` | « Prochain exercice » | deja fait |
| `le_premier_exercice_sera.wav` | « Le premier exercice sera » | deja fait |
| `pour_finir.wav` | « Pour finir » | deja fait |

## Orientation par rapport a la camera

Cinq prises couvrent les trente-neuf mouvements du catalogue. C'est le meilleur rapport du lot.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `place_toi_face_a_la_camera.wav` | « Place-toi face à la caméra » | deja fait |
| `place_toi_de_profil.wav` | « Place-toi de profil » | deja fait |
| `place_toi_de_profil_la_camera_a_ta_gauche.wav` | « Place-toi de profil, la caméra à ta gauche » | deja fait |
| `place_toi_de_profil_la_camera_a_ta_droite.wav` | « Place-toi de profil, la caméra à ta droite » | deja fait |
| `allonge_toi_la_camera_sur_le_cote.wav` | « Allonge-toi, la caméra sur le côté » | deja fait |

## Cadrage

Sept parties du corps et quatre actions, assemblees deux a deux : onze prises couvrent les vingt-huit consignes possibles.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `je_ne_vois_pas_ta_tete.wav` | « Je ne vois pas ta tête » | deja fait |
| `je_ne_vois_pas_tes_epaules.wav` | « Je ne vois pas tes épaules » | deja fait |
| `je_ne_vois_pas_tes_coudes.wav` | « Je ne vois pas tes coudes » | deja fait |
| `je_ne_vois_pas_tes_mains.wav` | « Je ne vois pas tes mains » | deja fait |
| `je_ne_vois_pas_tes_hanches.wav` | « Je ne vois pas tes hanches » | deja fait |
| `je_ne_vois_pas_tes_genoux.wav` | « Je ne vois pas tes genoux » | deja fait |
| `je_ne_vois_pas_tes_pieds.wav` | « Je ne vois pas tes pieds » | deja fait |
| `recule_tu_ne_tiens_pas_dans_l_image.wav` | « Recule, tu ne tiens pas dans l'image » | deja fait |
| `baisse_la_camera_ou_incline_la_vers_le_bas.wav` | « Baisse la caméra ou incline-la vers le bas » | deja fait |
| `monte_la_camera_ou_incline_la_vers_le_haut.wav` | « Monte la caméra ou incline-la vers le haut » | deja fait |
| `place_toi_au_centre_de_l_image.wav` | « Place-toi au centre de l'image » | deja fait |

## Installation et gestes

Le guidage du debut de seance, dit camera ouverte pendant qu'on se place.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `pose_ton_appareil_a_hauteur_de_poitrine.wav` | « Pose ton appareil à hauteur de poitrine » | deja fait |
| `pose_au_sol_il_ne_te_verra_pas_en_entier.wav` | « Posé au sol, il ne te verra pas en entier » | deja fait |
| `recule_a_deux_ou_trois_metres.wav` | « Recule à deux ou trois mètres » | deja fait |
| `place_ton_tapis_perpendiculaire_a_la_camera.wav` | « Place ton tapis perpendiculaire à la caméra » | deja fait |
| `fais_un_pas_a_droite_puis_un_pas_a_gauche.wav` | « Fais un pas à droite, puis un pas à gauche » | deja fait |
| `puis_un_pas_en_arriere_et_un_pas_en_avant.wav` | « Puis un pas en arrière et un pas en avant » | deja fait |
| `on_doit_te_voir_en_entier_a_chaque_fois.wav` | « On doit te voir en entier à chaque fois » | deja fait |
| `parfait_tu_es_bien_cadre.wav` | « Parfait, tu es bien cadré » | deja fait |
| `garde_l_appareil_bien_droit_pas_incline.wav` | « Garde l'appareil bien droit, pas incliné » | deja fait |
| `une_fois_pose_ne_le_bouge_plus.wav` | « Une fois posé, ne le bouge plus » | deja fait |
| `chaque_exercice_te_dira_comment_te_placer.wav` | « Chaque exercice te dira comment te placer » | deja fait |
| `verifions_que_tu_tiens_dans_l_image.wav` | « Vérifions que tu tiens dans l'image » | deja fait |
| `croise_les_bras_devant_toi_pour_demarrer.wav` | « Croise les bras devant toi pour démarrer » | deja fait |
| `leve_les_deux_bras_pour_remettre_a_zero.wav` | « Lève les deux bras pour remettre à zéro » | deja fait |
| `croise_les_bras_pour_valider_ta_serie.wav` | « Croise les bras pour valider ta série » | deja fait |
| `en_haut_ou_en_bas_seul_le_croisement_compte.wav` | « En haut ou en bas, seul le croisement compte » | deja fait |
| `ton_compteur_monte_a_chaque_repetition.wav` | « Ton compteur monte à chaque répétition » | deja fait |
| `leve_les_deux_bras_et_tiens_la_position.wav` | « Lève les deux bras et tiens la position » | deja fait |
| `c_est_bien_te_voila_reparti_de_zero.wav` | « C'est bien, te voilà reparti de zéro » | deja fait |
| `croise_les_bras_et_tiens_la_position.wav` | « Croise les bras et tiens la position » | deja fait |
| `bravo_tu_sais_tout_piloter_de_loin.wav` | « Bravo, tu sais tout piloter de loin » | deja fait |

## Accueil d'un nouveau profil

Joue une seule fois dans la vie d'un profil. A enregistrer en dernier parmi les briques.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `bienvenue_je_suis_ton_coach.wav` | « Bienvenue, je suis ton coach » | deja fait |
| `tu_poses_ton_appareil_et_tu_t_entraines.wav` | « Tu poses ton appareil, et tu t'entraînes » | deja fait |
| `ma_camera_compte_tes_repetitions.wav` | « Ma caméra compte tes répétitions » | deja fait |
| `et_je_te_guide_a_la_voix.wav` | « Et je te guide à la voix » | deja fait |
| `aucune_image_ne_sort_de_ton_appareil.wav` | « Aucune image ne sort de ton appareil » | deja fait |
| `on_y_va_quand_tu_veux.wav` | « On y va quand tu veux » | deja fait |

## Noms des exercices

Le nom **est** le texte : aucune table a tenir a jour a cote du catalogue, et un exercice ajoute apparait ici tout seul. Prononce-les **isoles et neutres** : chacun se dit derriere l'une des trois amorces ci-dessus, et se trouve suivi d'une charge ou d'une consigne de placement.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `crunches.wav` | « Crunches » | deja fait |
| `curl_biceps_droit.wav` | « Curl biceps droit » | deja fait |
| `curl_biceps_gauche.wav` | « Curl biceps gauche » | deja fait |
| `developpe_couche_alteres.wav` | « Developpé couché altères » | deja fait |
| `developpe_epaule.wav` | « Développé épaule » | deja fait |
| `elevations_laterales.wav` | « Elevations latérales » | deja fait |
| `extension_triceps.wav` | « Extension Triceps » | deja fait |
| `fente_droite.wav` | « Fente droite » | deja fait |
| `fente_gauche.wav` | « Fente gauche » | deja fait |
| `gainage_planche.wav` | « Gainage planche » | deja fait |
| `gainage_planche_laterale_droite.wav` | « Gainage planche laterale droite » | deja fait |
| `gainage_planche_laterale_gauche.wav` | « Gainage planche laterale gauche » | deja fait |
| `gainage_sur_les_genoux.wav` | « Gainage sur les genoux » | deja fait |
| `oiseau.wav` | « Oiseau » | deja fait |
| `pompes.wav` | « Pompes » | deja fait |
| `pompes_inclinees.wav` | « Pompes inclinées » | deja fait |
| `pompes_sur_les_genoux.wav` | « Pompes sur les genoux » | deja fait |
| `rowing_penche.wav` | « Rowing penche » | deja fait |
| `rowing_unilateral_droit.wav` | « Rowing unilateral droit » | deja fait |
| `rowing_unilateral_gauche.wav` | « Rowing unilateral gauche » | deja fait |
| `souleve_de_terre_roumain.wav` | « Souleve de terre roumain » | deja fait |
| `squat.wav` | « Squat » | deja fait |
| `squat_sur_chaise.wav` | « Squat sur chaise » | deja fait |

## Noms des echauffements

Meme regle. Ils sont annonces comme les exercices, meme s'ils ne comptent nulle part dans les statistiques.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `abducteurs.wav` | « Abducteurs » | deja fait |
| `extensions_de_mollets.wav` | « Extensions de mollets » | deja fait |
| `hanches_en_avant_en_arriere.wav` | « Hanches en avant en arrière » | deja fait |
| `hip_thrust.wav` | « Hip thrust » | deja fait |
| `jumping_jacks.wav` | « Jumping jacks » | deja fait |
| `montees_de_genou.wav` | « Montées de genou » | deja fait |
| `pompes_lentes.wav` | « Pompes lentes » | deja fait |
| `rotation_des_chevilles.wav` | « Rotation des chevilles » | deja fait |
| `rotation_des_coudes.wav` | « Rotation des coudes » | deja fait |
| `rotation_des_genoux.wav` | « Rotation des genoux » | deja fait |
| `rotation_des_poignets.wav` | « Rotation des poignets » | deja fait |
| `rotation_des_epaules.wav` | « Rotation des épaules » | deja fait |
| `rotation_du_cou.wav` | « Rotation du cou » | deja fait |
| `squat_de_priere.wav` | « Squat de prière » | deja fait |
| `squat_lent.wav` | « Squat lent » | deja fait |
| `elevations_laterales_a_vide.wav` | « Élévations latérales à vide » | deja fait |

## Charges — la gamme courante

Ce que le bareme propose avec le materiel suppose : jusqu'a 18 kg a un haltere, 10 kg a la paire. Une phrase entiere par charge : couper avant le nombre tombe au milieu d'un groupe nominal, et ca s'entend — contrairement a la couture entre une amorce et un nom d'exercice, qui tombe sur une pause que la phrase a deja.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `prepare_un_haltere_de_2_kilos.wav` | « Prépare un haltère de 2 kilos » | deja fait |
| `prepare_un_haltere_de_3_kilos.wav` | « Prépare un haltère de 3 kilos » | deja fait |
| `prepare_un_haltere_de_4_kilos.wav` | « Prépare un haltère de 4 kilos » | deja fait |
| `prepare_un_haltere_de_5_kilos.wav` | « Prépare un haltère de 5 kilos » | deja fait |
| `prepare_un_haltere_de_6_kilos.wav` | « Prépare un haltère de 6 kilos » | deja fait |
| `prepare_un_haltere_de_8_kilos.wav` | « Prépare un haltère de 8 kilos » | deja fait |
| `prepare_un_haltere_de_10_kilos.wav` | « Prépare un haltère de 10 kilos » | deja fait |
| `prepare_un_haltere_de_12_kilos.wav` | « Prépare un haltère de 12 kilos » | deja fait |
| `prepare_un_haltere_de_14_kilos.wav` | « Prépare un haltère de 14 kilos » | deja fait |
| `prepare_un_haltere_de_16_kilos.wav` | « Prépare un haltère de 16 kilos » | deja fait |
| `prepare_un_haltere_de_18_kilos.wav` | « Prépare un haltère de 18 kilos » | deja fait |
| `prepare_deux_halteres_de_2_kilos.wav` | « Prépare deux haltères de 2 kilos » | deja fait |
| `prepare_deux_halteres_de_3_kilos.wav` | « Prépare deux haltères de 3 kilos » | deja fait |
| `prepare_deux_halteres_de_4_kilos.wav` | « Prépare deux haltères de 4 kilos » | deja fait |
| `prepare_deux_halteres_de_5_kilos.wav` | « Prépare deux haltères de 5 kilos » | deja fait |
| `prepare_deux_halteres_de_6_kilos.wav` | « Prépare deux haltères de 6 kilos » | deja fait |
| `prepare_deux_halteres_de_8_kilos.wav` | « Prépare deux haltères de 8 kilos » | deja fait |
| `prepare_deux_halteres_de_10_kilos.wav` | « Prépare deux haltères de 10 kilos » | deja fait |

## Charges lourdes — a faire en dernier

Le questionnaire de materiel va jusqu'a 40 kg, donc ces charges existent pour qui les declare. **Coupe ce lot a la hauteur de ton propre placard** : une charge sans prise rend l'annonce breve (« prochain exercice, squat »), jamais muette.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `prepare_un_haltere_de_20_kilos.wav` | « Prépare un haltère de 20 kilos » | **a enregistrer** |
| `prepare_un_haltere_de_22_kilos.wav` | « Prépare un haltère de 22 kilos » | **a enregistrer** |
| `prepare_un_haltere_de_24_kilos.wav` | « Prépare un haltère de 24 kilos » | **a enregistrer** |
| `prepare_un_haltere_de_25_kilos.wav` | « Prépare un haltère de 25 kilos » | **a enregistrer** |
| `prepare_un_haltere_de_28_kilos.wav` | « Prépare un haltère de 28 kilos » | **a enregistrer** |
| `prepare_un_haltere_de_30_kilos.wav` | « Prépare un haltère de 30 kilos » | **a enregistrer** |
| `prepare_un_haltere_de_35_kilos.wav` | « Prépare un haltère de 35 kilos » | **a enregistrer** |
| `prepare_un_haltere_de_40_kilos.wav` | « Prépare un haltère de 40 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_12_kilos.wav` | « Prépare deux haltères de 12 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_14_kilos.wav` | « Prépare deux haltères de 14 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_16_kilos.wav` | « Prépare deux haltères de 16 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_18_kilos.wav` | « Prépare deux haltères de 18 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_20_kilos.wav` | « Prépare deux haltères de 20 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_22_kilos.wav` | « Prépare deux haltères de 22 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_24_kilos.wav` | « Prépare deux haltères de 24 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_25_kilos.wav` | « Prépare deux haltères de 25 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_28_kilos.wav` | « Prépare deux haltères de 28 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_30_kilos.wav` | « Prépare deux haltères de 30 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_35_kilos.wav` | « Prépare deux haltères de 35 kilos » | **a enregistrer** |
| `prepare_deux_halteres_de_40_kilos.wav` | « Prépare deux haltères de 40 kilos » | **a enregistrer** |

## Nombres de 21 a 60

Les vingt premiers sont deja enregistres — ce sont ceux du comptage des repetitions, reutilises tels quels. Ceux-ci servent la meme chose au-dela de vingt repetitions, ce que le bareme atteint sur les mouvements au poids du corps. Les charges, elles, ne passent plus par eux : elles sont devenues des phrases entieres.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `21.wav` | « vingt-et-un » | deja fait |
| `22.wav` | « vingt-deux » | deja fait |
| `23.wav` | « vingt-trois » | deja fait |
| `24.wav` | « vingt-quatre » | deja fait |
| `25.wav` | « vingt-cinq » | deja fait |
| `26.wav` | « vingt-six » | deja fait |
| `27.wav` | « vingt-sept » | deja fait |
| `28.wav` | « vingt-huit » | deja fait |
| `29.wav` | « vingt-neuf » | deja fait |
| `30.wav` | « trente » | deja fait |
| `31.wav` | « trente-et-un » | deja fait |
| `32.wav` | « trente-deux » | deja fait |
| `33.wav` | « trente-trois » | deja fait |
| `34.wav` | « trente-quatre » | deja fait |
| `35.wav` | « trente-cinq » | deja fait |
| `36.wav` | « trente-six » | deja fait |
| `37.wav` | « trente-sept » | deja fait |
| `38.wav` | « trente-huit » | deja fait |
| `39.wav` | « trente-neuf » | deja fait |
| `40.wav` | « quarante » | deja fait |
| `41.wav` | « quarante-et-un » | deja fait |
| `42.wav` | « quarante-deux » | deja fait |
| `43.wav` | « quarante-trois » | deja fait |
| `44.wav` | « quarante-quatre » | deja fait |
| `45.wav` | « quarante-cinq » | deja fait |
| `46.wav` | « quarante-six » | deja fait |
| `47.wav` | « quarante-sept » | deja fait |
| `48.wav` | « quarante-huit » | deja fait |
| `49.wav` | « quarante-neuf » | deja fait |
| `50.wav` | « cinquante » | deja fait |
| `51.wav` | « cinquante-et-un » | deja fait |
| `52.wav` | « cinquante-deux » | deja fait |
| `53.wav` | « cinquante-trois » | deja fait |
| `54.wav` | « cinquante-quatre » | deja fait |
| `55.wav` | « cinquante-cinq » | deja fait |
| `56.wav` | « cinquante-six » | deja fait |
| `57.wav` | « cinquante-sept » | deja fait |
| `58.wav` | « cinquante-huit » | deja fait |
| `59.wav` | « cinquante-neuf » | deja fait |
| `60.wav` | « soixante » | deja fait |
