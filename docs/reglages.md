# Ce que veut dire chaque réglage de `reglages.json`

Les valeurs vivent dans `web/static/donnees/reglages.json`, pour être réglables depuis
`dev/baremes.html` — y compris sur la tablette, là où on les juge. Leur **raison** vit ici :
JSON ne prend pas de commentaires, et ces réglages en demandent.

**Modifier un nombre sans avoir lu la note correspondante est la façon la plus simple de
casser le barème en silence.** Un barème ne se juge pas sur ses paramètres mais sur les
paliers qu'il sort : régler sur `dev/baremes.html`, qui recalcule tout sous les yeux.

## Le barème d'un exercice (`specs`)

Un palier est un triplet (poids, séries, cible) et un *niveau* en est l'index, à partir de 1.
**L'invariant est le volume** (séries × cible × poids), qui ne redescend jamais d'un palier au
suivant : après une hausse de poids, la cible repart de la plus petite valeur qui tient le
volume déjà atteint, jamais de `cible_min`. L'ordre des bascules est cible → poids → séries.
Une fois l'haltère le plus lourd et le plafond de séries atteints, les répétitions montent sans
plafond (la *tranche ouverte*) : aucun objectif n'est jamais hors d'atteinte.

**`cible_min` : le bas du barème appartient au débutant.** C'est le premier palier proposé à
quelqu'un dont l'historique ne prouve rien. Le fixer au niveau d'un pratiquant confirmé laisse
un débutant « hors barème », c'est-à-dire sans objectif du tout. Sur les mouvements au poids du
corps, il est délibérément très bas (1 répétition aux pompes).
- En baisser un est sans danger tant qu'on ne touche **ni `series` ni `poids_min`** : la
  première tranche s'allonge par le bas et tous les paliers supérieurs se décalent d'une
  *constante*, sans changer de contenu.
- Toucher `series` ou `poids_min` fait au contraire recalculer le départ de chaque tranche, et
  rebat tout le barème.
- Les numéros de niveau changent, les performances non : c'est attendu.

**`cible_max`** fixe le volume de fin de tranche, donc l'entrée de la suivante. C'est le
réglage par lequel on ajuste un barème à un programme : le baisser fait entrer les séries en
jeu plus tôt. Tant qu'il reste haut, le barème épuise les répétitions avant d'ajouter une série.

Piège du baisser : les séances déjà enregistrées portent des cibles qui peuvent dépasser le
nouveau plafond. Le ressenti ne sait alors plus les traduire en niveau, et l'objectif proposé
retombe sous le niveau acquis. C'est transitoire : la première séance jouée sur le nouveau
barème rétablit un repère valide.

**`poids_min`** : un curl ne commence pas à 2 kg pour quelqu'un qui en a fait. Mais le
descendre est justement ce qui ouvre le barème aux débutants.

- Penser aussi à la **première borne de ligue** de l'exercice. Elle vaut souvent le volume de
  l'ancien palier 1 : laissée en place, elle prive de ligue précisément le débutant qu'on vient
  d'ouvrir.

**Un barème ne mélange jamais le poids du corps et les haltères.** Le squat et les fentes allaient
autrefois de l'un aux autres dans un seul barème (`poids_min` à 0, plus un `premiere_charge`
pour sauter les haltères trop légers) ; ce sont désormais deux mouvements chacun (« Squat » à
vide, « Squat chargé »), reliés par les variantes. Un seul barème ne savait pas comparer
« 4x15 à vide » et « 4x13 à 2 kg » : c'étaient deux mesures.
- Le `poids_min` d'une forme chargée (5 kg) garde la leçon de l'ancien barème : un squat à 2 ou
  3 kg par main ne se distingue pas du poids du corps — testé, 4x13 à 2 kg était *plus facile*
  que 4x15 sans rien. En dessous, on reste sur la forme à vide.

**`charge_corps`** : ce que pèse le corps dans le volume d'un mouvement chargé où le corps
reste la charge principale (squat chargé, fentes chargées), en kg « par haltère ».
- Sans lui, le poids du corps compterait pour 1 kg, et deux haltères de 2 kg *doubleraient* le
  volume d'un squat. Le barème passait ainsi de 4x15 au poids du corps à 4x8 à 2 kg en appelant
  ça une progression.
- Le volume vaut `séries × cible × (poids + charge_corps)`.
- **15 est un compromis et non une mesure** : à 30-35, plus proche de la physique, chaque cran
  d'haltère se jouerait à la cible maximale et les répétitions ne bougeraient plus.
- C'est lui qui fait qu'un cran d'haltère ne coûte que quelques répétitions : sans lui, passer
  de 5 à 6 kg ferait perdre un cinquième des répétitions, comme sur un curl.
- C'est aussi lui qui traduit une performance à vide en volume chargé, pour le seuil de passage
  à la forme chargée et pour le palier d'entrée (voir *Le retour des variantes*). Le monter rend
  l'haltère moins coûteux par rapport au corps : le passage à la charge se fait plus tôt et
  entre avec plus de répétitions.
- Le toucher rebat tout le barème de l'exercice et change l'échelle de ses volumes. Ses bornes
  de ligue, en volume absolu, sont à recaler avec.

**`poids_max`** : le plafond de charge n'est pas celui du matériel. Sans lui, le barème
proposait un curl unilatéral à 18 kg, et une exigence de programme s'y calait.

**`series` / `series_max`** : au-delà de six séries dures, chaque série supplémentaire coûte
du temps et de la fatigue pour un rendement qui s'effondre. La progression relève alors d'une
variante plus dure. `series_max_par_defaut` s'applique aux specs qui ne le précisent pas.

**`surcharges`** : une surcharge **corrige** un palier existant, elle n'en insère ni n'en
supprime jamais. Sinon, tous les niveaux au-dessus se décaleraient et l'historique déjà
interprété changerait de sens.

Réglages par famille de mouvement, qui expliquent les écarts entre exercices :
- **poids du corps** (pompes, squat, crunches) : sans axe de charge, la fourchette
  de répétitions est allongée, sinon le barème est épuisé en une poignée de paliers ;
- **variantes assistées** (pompes inclinées, sur les genoux, contre le mur) : départ plus bas
  *en effort*. Elles existent pour que quelqu'un qui ne fait pas une pompe ait quand même une
  progression ;
- **isolation légère** (élévations latérales, oiseau) : beaucoup de répétitions, jamais très
  lourd ;
- **lourd et court** (extension triceps) : fourchette basse des deux côtés ;
- **jambes** : elles encaissent plus de répétitions, et les haltères y sont vite le facteur
  limitant ;
- **gainage** : plafonné par série, puis c'est le nombre de séries qui prend le relais.

## Les ligues (`ligues`)

La ligue d'un exercice vient du **volume** du palier atteint, pas du numéro de niveau. Le
niveau dit la position sur le barème, la ligue dit l'effort produit.

**`seuils_par_exercice`** : les dix-huit bornes, posées à la main exercice par exercice, en
**volume absolu**.
- C'est la seule unité qui permette de placer un cran là où il veut dire quelque chose.
- Une table relative unique donnait un Or III sensé au curl (4x14 à 12 kg) et 324 répétitions
  aux pompes. Passer de 2 à 12 kg multiplie le volume par six sans changer une répétition,
  alors qu'au poids du corps le seul levier *est* la répétition.
- **Une borne se juge sur la performance qu'elle exige**, que `dev/baremes.html` montre à côté
  d'elle, jamais sur son nombre.
- Sur un barème court (pompes et variantes), la cadence et le point d'arrivée ne peuvent pas
  être bons en même temps : les durcir rouvre le problème des 324 répétitions.

**`seuils_volume`** : la table relative de repli (volume rapporté au palier 1). Elle donne des
ligues à un exercice ajouté qui n'a pas encore de bornes propres. Ce repli n'est pas
décoratif. Mais il masque aussi un branchement oublié : devant deux vues qui ne s'accordent
pas, vérifier qu'elles lisent bien les bornes propres.

**`ligues` / `divisions`** : les noms. Une ligue se traverse par sa division III et se quitte
par sa division I.

## L'XP et le niveau général (`xp`)

**`paliers_xp`** : XP rapportée par **chaque** niveau d'une tranche, sous la forme (niveau à
partir duquel la tranche s'applique, XP par niveau). La table est croissante, parce qu'un
niveau gagné haut sur le barème coûte bien plus d'entraînement qu'un niveau gagné en bas.

**`base_niveau_general` / `increment_niveau_general`** : le coût du niveau général 1 → 2,
puis l'incrément de chaque niveau suivant. Le cumul est quadratique.
- La ligue générale avance d'**un cran par niveau général** : c'est ce coût qui porte
  l'exigence, pas un second réglage.
- À 200 + 100x(n-1), tout le catalogue au niveau 30 suffisait pour Maître I.
- À 500 + 600x(n-1), Maître I demande le catalogue entier autour du niveau 50.

## La note d'athlète (`note_athlete`)

Chacun se donne une note de 1 à 10, qui fixe le départ de tout exercice jamais fait. Elle ne
pose jamais de niveau.

**`rangs`** : un rang de ligue par note. Le départ est le premier palier qui atteint la borne
de ce rang. Les bornes ayant été posées pour vouloir dire la même chose partout, un 5 demande
le même effort aux pompes et au curl. Un départ trop dur se juge sur cette ligne, pas sur
`cible_min` seul.

**`part_exercices` / `exercices_min` / `marge`** : la note monte toute seule.
- La note mesurée est la plus haute note dont `part_exercices` des exercices récents (au moins
  `exercices_min`) atteignent le départ.
- Elle n'est retenue qu'à partir de `marge` crans au-dessus de la note déclarée.
- **0,66 et non 0,667** : à 0,667, quatre exercices sur six donnaient 4,002 et ne comptaient
  pas.

## Le retour des variantes (`variantes.retour`)

Pour chaque variante assistée, la **performance** (séries, cible) qu'une séance menée à son
terme doit prouver pour monter d'un cran vers le mouvement complet. C'est une performance,
jamais un numéro de niveau : le barème la traduit.
- **Vers une forme chargée** (squat, fentes), le seuil dit ce qu'on doit pouvoir tenir **avec
  le premier haltère du profil** : `"Squat": [4, 15]` veut dire « l'équivalent de 4x15 avec ton
  plus petit haltère utilisable ». Traduit à vide par `charge_corps`, il demande 4x15 x (5 + 15)
  / 15 = 80 répétitions à vide au total avec des 5 kg, 100 avec des 10 kg : on reste plus longtemps à
  vide quand le premier haltère est lourd.
- On y entre au palier de **même volume** que le niveau acquis à vide (même traduction), jamais
  au palier 1 : 4x3 à 5 kg après 4x15 à vide reculait de plusieurs séances. Entre variantes sans
  charge (pompes, gainage), on entre au palier 1.
- On ne monte jamais vers une forme que le matériel ne permet pas de charger.

## Le départ des variantes (`variantes.depart`)

Pour la **tête** de chaque chaîne de variantes (le mouvement complet, celui que les séances
écrivent), la note d'athlète à partir de laquelle on **démarre** sur chacun de ses mouvements :
`{"Pompes contre le mur": 1, "Pompes inclinées": 2, "Pompes sur les genoux": 3, "Pompes": 4}`.
- On part du plus dur que la note atteint ; sans note, du premier de la table.
- Ne s'applique qu'à une famille **jamais jouée** : ensuite, ce sont les montées et les
  descentes qui décident.
- Un mouvement absent de la table n'est jamais un départ : il ne s'atteint que par un échec.
- La note choisit le mouvement, puis le palier dans ce mouvement (par ses bornes de ligue,
  comme pour tout exercice jamais fait) : régler les deux ensemble, sur
  `dev/progression.html`, qui montre la courbe de départ note par note et matériel par
  matériel.
- `verifier_donnees` exige qu'un mouvement plus dur demande une note plus haute.
