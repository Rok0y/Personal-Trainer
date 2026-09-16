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

## Trois choses a savoir avant de commencer

**Tu peux y aller par lots.** Un fichier absent est un **silence**, jamais une
panne : le coach abrege sa phrase et la seance continue. Rien n'attend que la
liste soit complete, et chaque prise ajoutee fait parler quelque chose de plus.

**Prononce a plat.** Ces phrases sont assemblees bout a bout — « prochain
exercice », « curl biceps droit », « prepare un haltere de », « huit »,
« kilos ». Une intonation descendante de fin de phrase ferait entendre la
couture au milieu de l'annonce. Garde le meme debit et le meme niveau d'une
prise a l'autre, c'est ce qui rend l'assemblage invisible.

**Le nom du fichier est le texte.** Si une formulation ne te plait pas, change
le texte dans `audio/annonces.py` et relance ce script : le nom de fichier
suivra. L'inverse — renommer un fichier — ne changerait rien, le code cherche
le nom que la table produit.

**127 prises restantes.**

## Liaisons

Les mots qui cousent une annonce. Prononces **a plat**, au milieu d'une phrase : une intonation de fin de phrase rendrait la couture audible.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `prochain_exercice.wav` | « Prochain exercice » | **a enregistrer** |
| `prepare_un_haltere_de.wav` | « Prépare un haltère de » | **a enregistrer** |
| `prepare_deux_halteres_de.wav` | « Prépare deux haltères de » | **a enregistrer** |
| `kilos.wav` | « kilos » | **a enregistrer** |
| `kilo.wav` | « kilo » | **a enregistrer** |

## Orientation par rapport a la camera

Cinq prises couvrent les trente-neuf mouvements du catalogue. C'est le meilleur rapport du lot.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `place_toi_face_a_la_camera.wav` | « Place-toi face à la caméra » | **a enregistrer** |
| `place_toi_de_profil.wav` | « Place-toi de profil » | **a enregistrer** |
| `place_toi_de_profil_la_camera_a_ta_gauche.wav` | « Place-toi de profil, la caméra à ta gauche » | **a enregistrer** |
| `place_toi_de_profil_la_camera_a_ta_droite.wav` | « Place-toi de profil, la caméra à ta droite » | **a enregistrer** |
| `allonge_toi_la_camera_sur_le_cote.wav` | « Allonge-toi, la caméra sur le côté » | **a enregistrer** |

## Cadrage

Sept parties du corps et quatre actions, assemblees deux a deux : onze prises couvrent les vingt-huit consignes possibles.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `je_ne_vois_pas_ta_tete.wav` | « Je ne vois pas ta tête » | **a enregistrer** |
| `je_ne_vois_pas_tes_epaules.wav` | « Je ne vois pas tes épaules » | **a enregistrer** |
| `je_ne_vois_pas_tes_coudes.wav` | « Je ne vois pas tes coudes » | **a enregistrer** |
| `je_ne_vois_pas_tes_mains.wav` | « Je ne vois pas tes mains » | **a enregistrer** |
| `je_ne_vois_pas_tes_hanches.wav` | « Je ne vois pas tes hanches » | **a enregistrer** |
| `je_ne_vois_pas_tes_genoux.wav` | « Je ne vois pas tes genoux » | **a enregistrer** |
| `je_ne_vois_pas_tes_pieds.wav` | « Je ne vois pas tes pieds » | **a enregistrer** |
| `recule_tu_ne_tiens_pas_dans_l_image.wav` | « Recule, tu ne tiens pas dans l'image » | **a enregistrer** |
| `baisse_la_camera_ou_incline_la_vers_le_bas.wav` | « Baisse la caméra ou incline-la vers le bas » | **a enregistrer** |
| `monte_la_camera_ou_incline_la_vers_le_haut.wav` | « Monte la caméra ou incline-la vers le haut » | **a enregistrer** |
| `place_toi_au_centre_de_l_image.wav` | « Place-toi au centre de l'image » | **a enregistrer** |

## Installation et gestes

Le guidage du debut de seance, dit camera ouverte pendant qu'on se place.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `pose_ton_appareil_a_hauteur_de_poitrine.wav` | « Pose ton appareil à hauteur de poitrine » | **a enregistrer** |
| `pose_au_sol_il_ne_te_verra_pas_en_entier.wav` | « Posé au sol, il ne te verra pas en entier » | **a enregistrer** |
| `recule_a_deux_ou_trois_metres.wav` | « Recule à deux ou trois mètres » | **a enregistrer** |
| `place_ton_tapis_perpendiculaire_a_la_camera.wav` | « Place ton tapis perpendiculaire à la caméra » | **a enregistrer** |
| `fais_un_pas_a_droite_puis_un_pas_a_gauche.wav` | « Fais un pas à droite, puis un pas à gauche » | **a enregistrer** |
| `puis_un_pas_en_arriere_et_un_pas_en_avant.wav` | « Puis un pas en arrière et un pas en avant » | **a enregistrer** |
| `on_doit_te_voir_en_entier_a_chaque_fois.wav` | « On doit te voir en entier à chaque fois » | **a enregistrer** |
| `parfait_tu_es_bien_cadre.wav` | « Parfait, tu es bien cadré » | **a enregistrer** |
| `garde_l_appareil_bien_droit_pas_incline.wav` | « Garde l'appareil bien droit, pas incliné » | **a enregistrer** |
| `une_fois_pose_ne_le_bouge_plus.wav` | « Une fois posé, ne le bouge plus » | **a enregistrer** |
| `chaque_exercice_te_dira_comment_te_placer.wav` | « Chaque exercice te dira comment te placer » | **a enregistrer** |
| `verifions_que_tu_tiens_dans_l_image.wav` | « Vérifions que tu tiens dans l'image » | **a enregistrer** |
| `croise_les_bras_devant_toi_pour_demarrer.wav` | « Croise les bras devant toi pour démarrer » | **a enregistrer** |
| `leve_les_deux_bras_pour_remettre_a_zero.wav` | « Lève les deux bras pour remettre à zéro » | **a enregistrer** |
| `croise_les_bras_pour_valider_ta_serie.wav` | « Croise les bras pour valider ta série » | **a enregistrer** |
| `en_haut_ou_en_bas_seul_le_croisement_compte.wav` | « En haut ou en bas, seul le croisement compte » | **a enregistrer** |
| `ton_compteur_monte_a_chaque_repetition.wav` | « Ton compteur monte à chaque répétition » | **a enregistrer** |
| `leve_les_deux_bras_et_tiens_la_position.wav` | « Lève les deux bras et tiens la position » | **a enregistrer** |
| `c_est_bien_te_voila_reparti_de_zero.wav` | « C'est bien, te voilà reparti de zéro » | **a enregistrer** |
| `croise_les_bras_et_tiens_la_position.wav` | « Croise les bras et tiens la position » | **a enregistrer** |
| `bravo_tu_sais_tout_piloter_de_loin.wav` | « Bravo, tu sais tout piloter de loin » | **a enregistrer** |

## Accueil d'un nouveau profil

Joue une seule fois dans la vie d'un profil. A enregistrer en dernier parmi les briques.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `bienvenue_je_suis_ton_coach.wav` | « Bienvenue, je suis ton coach » | **a enregistrer** |
| `tu_poses_ton_appareil_et_tu_t_entraines.wav` | « Tu poses ton appareil, et tu t'entraînes » | **a enregistrer** |
| `ma_camera_compte_tes_repetitions.wav` | « Ma caméra compte tes répétitions » | **a enregistrer** |
| `et_je_te_guide_a_la_voix.wav` | « Et je te guide à la voix » | **a enregistrer** |
| `aucune_image_ne_sort_de_ton_appareil.wav` | « Aucune image ne sort de ton appareil » | **a enregistrer** |
| `on_y_va_quand_tu_veux.wav` | « On y va quand tu veux » | **a enregistrer** |

## Noms des exercices

Le nom **est** le texte : il n'y a aucune table a tenir a jour a cote du catalogue, et un exercice ajoute apparait ici tout seul.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `crunches.wav` | « Crunches » | **a enregistrer** |
| `curl_biceps_droit.wav` | « Curl biceps droit » | **a enregistrer** |
| `curl_biceps_gauche.wav` | « Curl biceps gauche » | **a enregistrer** |
| `developpe_couche_alteres.wav` | « Developpé couché altères » | **a enregistrer** |
| `developpe_epaule.wav` | « Développé épaule » | **a enregistrer** |
| `elevations_laterales.wav` | « Elevations latérales » | **a enregistrer** |
| `extension_triceps.wav` | « Extension Triceps » | **a enregistrer** |
| `fente_droite.wav` | « Fente droite » | **a enregistrer** |
| `fente_gauche.wav` | « Fente gauche » | **a enregistrer** |
| `gainage_planche.wav` | « Gainage planche » | **a enregistrer** |
| `gainage_planche_laterale_droite.wav` | « Gainage planche laterale droite » | **a enregistrer** |
| `gainage_planche_laterale_gauche.wav` | « Gainage planche laterale gauche » | **a enregistrer** |
| `gainage_sur_les_genoux.wav` | « Gainage sur les genoux » | **a enregistrer** |
| `oiseau.wav` | « Oiseau » | **a enregistrer** |
| `pompes.wav` | « Pompes » | **a enregistrer** |
| `pompes_inclinees.wav` | « Pompes inclinées » | **a enregistrer** |
| `pompes_sur_les_genoux.wav` | « Pompes sur les genoux » | **a enregistrer** |
| `rowing_penche.wav` | « Rowing penche » | **a enregistrer** |
| `rowing_unilateral_droit.wav` | « Rowing unilateral droit » | **a enregistrer** |
| `rowing_unilateral_gauche.wav` | « Rowing unilateral gauche » | **a enregistrer** |
| `souleve_de_terre_roumain.wav` | « Souleve de terre roumain » | **a enregistrer** |
| `squat.wav` | « Squat » | **a enregistrer** |
| `squat_sur_chaise.wav` | « Squat sur chaise » | **a enregistrer** |

## Noms des echauffements

Meme regle. Ils sont annonces comme les exercices, meme s'ils ne comptent nulle part dans les statistiques.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `abducteurs.wav` | « Abducteurs » | **a enregistrer** |
| `extensions_de_mollets.wav` | « Extensions de mollets » | **a enregistrer** |
| `hanches_en_avant_en_arriere.wav` | « Hanches en avant en arrière » | **a enregistrer** |
| `hip_thrust.wav` | « Hip thrust » | **a enregistrer** |
| `jumping_jacks.wav` | « Jumping jacks » | **a enregistrer** |
| `montees_de_genou.wav` | « Montées de genou » | **a enregistrer** |
| `pompes_lentes.wav` | « Pompes lentes » | **a enregistrer** |
| `rotation_des_chevilles.wav` | « Rotation des chevilles » | **a enregistrer** |
| `rotation_des_coudes.wav` | « Rotation des coudes » | **a enregistrer** |
| `rotation_des_genoux.wav` | « Rotation des genoux » | **a enregistrer** |
| `rotation_des_poignets.wav` | « Rotation des poignets » | **a enregistrer** |
| `rotation_des_epaules.wav` | « Rotation des épaules » | **a enregistrer** |
| `rotation_du_cou.wav` | « Rotation du cou » | **a enregistrer** |
| `squat_de_priere.wav` | « Squat de prière » | **a enregistrer** |
| `squat_lent.wav` | « Squat lent » | **a enregistrer** |
| `elevations_laterales_a_vide.wav` | « Élévations latérales à vide » | **a enregistrer** |

## Nombres de 21 a 60

Les vingt premiers sont deja enregistres — ce sont ceux du comptage des repetitions, reutilises tels quels. Au-dela de soixante, le coach se tait sur le nombre et poursuit sa phrase : c'est un lot a faire en dernier, il ne sert qu'aux charges et aux cibles les plus elevees.

| Fichier | A prononcer | Etat |
| --- | --- | --- |
| `21.wav` | « vingt-et-un » | **a enregistrer** |
| `22.wav` | « vingt-deux » | **a enregistrer** |
| `23.wav` | « vingt-trois » | **a enregistrer** |
| `24.wav` | « vingt-quatre » | **a enregistrer** |
| `25.wav` | « vingt-cinq » | **a enregistrer** |
| `26.wav` | « vingt-six » | **a enregistrer** |
| `27.wav` | « vingt-sept » | **a enregistrer** |
| `28.wav` | « vingt-huit » | **a enregistrer** |
| `29.wav` | « vingt-neuf » | **a enregistrer** |
| `30.wav` | « trente » | **a enregistrer** |
| `31.wav` | « trente-et-un » | **a enregistrer** |
| `32.wav` | « trente-deux » | **a enregistrer** |
| `33.wav` | « trente-trois » | **a enregistrer** |
| `34.wav` | « trente-quatre » | **a enregistrer** |
| `35.wav` | « trente-cinq » | **a enregistrer** |
| `36.wav` | « trente-six » | **a enregistrer** |
| `37.wav` | « trente-sept » | **a enregistrer** |
| `38.wav` | « trente-huit » | **a enregistrer** |
| `39.wav` | « trente-neuf » | **a enregistrer** |
| `40.wav` | « quarante » | **a enregistrer** |
| `41.wav` | « quarante-et-un » | **a enregistrer** |
| `42.wav` | « quarante-deux » | **a enregistrer** |
| `43.wav` | « quarante-trois » | **a enregistrer** |
| `44.wav` | « quarante-quatre » | **a enregistrer** |
| `45.wav` | « quarante-cinq » | **a enregistrer** |
| `46.wav` | « quarante-six » | **a enregistrer** |
| `47.wav` | « quarante-sept » | **a enregistrer** |
| `48.wav` | « quarante-huit » | **a enregistrer** |
| `49.wav` | « quarante-neuf » | **a enregistrer** |
| `50.wav` | « cinquante » | **a enregistrer** |
| `51.wav` | « cinquante-et-un » | **a enregistrer** |
| `52.wav` | « cinquante-deux » | **a enregistrer** |
| `53.wav` | « cinquante-trois » | **a enregistrer** |
| `54.wav` | « cinquante-quatre » | **a enregistrer** |
| `55.wav` | « cinquante-cinq » | **a enregistrer** |
| `56.wav` | « cinquante-six » | **a enregistrer** |
| `57.wav` | « cinquante-sept » | **a enregistrer** |
| `58.wav` | « cinquante-huit » | **a enregistrer** |
| `59.wav` | « cinquante-neuf » | **a enregistrer** |
| `60.wav` | « soixante » | **a enregistrer** |
