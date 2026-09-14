# Idées d'amélioration de la détection

Notes ouvertes, rien n'est décidé. Point de départ : le workflow d'un joueur de
tennis qui analyse ses séances (iPhone → Roboflow → étiquetage assisté →
RF-DETR affiné → annotation OpenCV a posteriori). Ce qui suit trie ce qui est
transférable de ce qui ne l'est pas, et pourquoi.

## Ce qui n'est pas transférable, et pourquoi le noter quand même

**Affiner un modèle de détection sur nos propres images serait une régression.**
Lui détecte des *objets* propres à son domaine (balle, raquette) : aucun modèle
pré-entraîné ne les connaît, d'où le dataset annoté. Nous détectons des
*articulations humaines*, problème générique que MediaPipe résout sans une seule
image étiquetée. Le coût de son pipeline est dans l'étiquetage, pas dans
l'architecture — et c'est exactement le coût qu'on n'a pas à payer.

**Sa stabilité apparente vient d'abord du post-traitement, pas du modèle.** Il
annote une vidéo enregistrée : il peut lire l'image N+5 pour décider de
l'image N, lisser une trajectoire, boucher un trou. Notre boucle tourne en
temps réel dans un navigateur, sans connaître l'avenir et avec ~25 ms par image.
Et une boîte englobante décalée de cinq pixels ne se voit pas, là où un genou
estimé à 118° au lieu de 108° ne compte pas la répétition : nous vivons sur une
*frontière de décision*, lui sur un affichage.

À garder en tête avant de conclure « leur détection est meilleure » : ce n'est
pas la même exigence, et une vidéo de démo ne montre pas les prises ratées.

---

## Piste 1 — Lisser les angles dans le temps (le seul vrai emprunt)

Aujourd'hui, le tremblement des landmarks est absorbé par **l'hystérésis** :
l'écart entre le seuil `"debut"` et le seuil `"fin"` (cf. CLAUDE.md, section
détection). C'est une réponse binaire et coûteuse — elle interdit de resserrer
un seuil, et elle ne fait rien pour un mode `maintien`, qui n'a qu'un seuil et
se met donc à clignoter dès qu'on le rapproche de la position parfaite.

Un **filtre passe-bas adaptatif sur les angles eux-mêmes** (type *one euro
filter*, conçu pour ce compromis exact : peu de latence sur un mouvement rapide,
beaucoup de lissage sur une position tenue) traiterait la cause au lieu du
symptôme.

Trois contraintes à respecter si on s'y met :

- **Filtrer en amont des détections, jamais à l'intérieur.** Les fonctions
  `*_detection(corps)` sont pures : c'est ce qui permet au harnais
  `scripts/generer_fixtures.py` + `scripts/comparer_detections.mjs` de les
  rejouer sur 5 000 poses aléatoires. Un état interne les rendrait
  non-rejouables et casserait le jumelage.
- Le filtre a donc sa place **entre le détecteur de pose et l'appel de
  détection**, avec un état par exercice, remis à zéro au début de chaque série.
- Il doit être **jumelé Python/JS** comme le reste, le Python faisant autorité —
  mais le harnais actuel ne le couvrira pas, puisqu'il compare des fonctions
  sans mémoire. Il faudrait un second harnais qui rejoue une *séquence*.

Bénéfice attendu : pouvoir resserrer les seuils de maintien, réduire les
répétitions fantômes, et surtout arrêter de payer la gigue en hystérésis.

## Piste 2 — Enregistrer des séquences de landmarks (pas des vidéos)

C'est l'équivalent de son « vidéo iPhone → dataset », en cent fois moins cher et
sans donnée personnelle : au lieu de filmer, écrire un `.jsonl` d'une ligne par
image (horodatage + 33 landmarks). Quelques centaines de Ko par exercice, aucune
image ne quitte l'appareil, et rien à annoter pour commencer.

Ça débloque plus que tout le reste réuni :

- **rejouer une séance hors caméra**, donc déboguer une détection sans se
  relever et sans refaire dix squats ;
- **un corpus de non-régression réel**, qui manque aujourd'hui : le harnais
  compare Python et JS sur des poses *aléatoires*, il vérifie qu'ils
  s'accordent, jamais qu'ils ont **raison** ;
- de quoi régler un seuil sur des données au lieu d'une intuition.

Où : la démo (`web/static/demo/`) est le bon endroit — les testeurs y passent
déjà, et le `localStorage` y stocke déjà des histogrammes de fluidité. Prévoir
un export explicite, pas une collecte silencieuse.

## Piste 3 — Le compte de vérité, à deux nombres

Un corpus ne vaut que s'il porte la bonne réponse. Le moins cher possible : à la
fin d'un exercice, demander « tu en as fait combien ? » et comparer à ce que
l'app a compté. Deux nombres par série, saisis en trois secondes, et on obtient
un **taux de justesse par exercice et par appareil** — la métrique qui manque
aujourd'hui pour dire si une modification de seuil améliore ou dégrade quoi que
ce soit.

Le QCM de fin d'exercice de la démo est déjà à moitié ce mécanisme ; il récolte
des impressions, pas un chiffre comparable.

## Piste 4 — Une passe d'analyse après la série

C'est son « annotation vidéo avec Python + OpenCV », adapté : une fois la
séquence de landmarks enregistrée (piste 2), on peut la relire **en connaissant
la suite**, ce que le temps réel interdit. On y calcule ce qu'une boucle
image par image ne peut pas :

- recompter les répétitions proprement, donc repérer celles que le direct a
  ratées, et à quel moment ;
- l'**amplitude** réelle de chaque répétition (angle minimal atteint), la
  **vitesse concentrique**, la **symétrie** gauche/droite, la dégradation de la
  forme au fil de la série ;
- de la matière pour un retour de fin de séance, là où le coach vocal ne peut
  dire que l'essentiel pendant l'effort.

Attention à la frontière : le comptage temps réel reste la source de vérité de
la séance enregistrée. Une passe qui corrigerait l'historique après coup rendrait
le compteur affiché menteur.

## Piste 5 — Contraindre le point de vue plutôt que d'y résister

Sa caméra est fixe, en hauteur, cadrant le court : il n'a jamais à se demander
sous quel angle il filme. C'est une leçon qu'on a déjà apprise à nos dépens
(le genou illisible de face, la consigne de distance supprimée, cf. CLAUDE.md) :
**il est plus efficace d'imposer un cadrage que de rendre une détection robuste
à tous les cadrages**. `web/static/js/cadrage.js` va dans ce sens ; le
prolongement naturel serait de vérifier aussi **l'orientation** (de face / de
profil) attendue par l'exercice, et pas seulement que les points sont dans
l'image.

## Piste 6 — Détecter les objets : le seul endroit où son approche s'appliquerait

Si un jour on veut savoir *quelle charge* est réellement soulevée, ou détecter
qu'un haltère est posé, c'est bien un problème de détection d'objet, et donc son
pipeline. Coût : étiqueter des milliers d'images de nos propres haltères. Gain :
supprimer une saisie manuelle. Le rapport est mauvais aujourd'hui — noté pour
mémoire, pas comme candidat.

## Piste 7 — Un classifieur appris, mais pas pour compter

Remplacer les seuils écrits à la main par un modèle entraîné sur des séquences
de landmarks est l'alternative architecturale sérieuse. Le comptage n'est pas
le bon endroit pour l'essayer :

| | seuils écrits (actuel) | classifieur appris |
|---|---|---|
| données nécessaires | aucune | des centaines de répétitions étiquetées, par exercice |
| explicable | « descends plus bas » | « pas une rep », sans raison |
| débogable | banc d'essai `?banc=1` | réentraîner |
| jumelage Python/JS | fonctions pures + harnais de diff | deux runtimes à accorder |

Un coach doit dire *pourquoi*, et un classifieur ne sait pas le dire. L'endroit
où le ML deviendrait rentable, c'est la **notation de qualité d'exécution** —
là où écrire une règle est justement impossible — et ça suppose la piste 2 comme
préalable.

---

## Ordre suggéré

1. **Piste 2** (enregistrement de séquences) — préalable à presque tout le reste,
   et la moins risquée : rien de branché sur le chemin critique.
2. **Piste 3** (compte de vérité) — donne enfin une métrique pour juger.
3. **Piste 1** (filtre temporel) — à faire une fois qu'on sait la mesurer, pas
   avant : sans piste 3, on ne saura pas si le lissage a aidé.
4. **Piste 5** (orientation) — indépendante, petit coût, corrige une vraie cause
   de séance à zéro répétition.
5. Pistes 4, 7, 6 — ensuite, dans cet ordre.
