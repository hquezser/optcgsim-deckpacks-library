# Idée future : site bibliothèque de deckpacks

Notes de session (2026-08-02/03) — pas un engagement de roadmap, juste une trace de la
réflexion pour ne pas la perdre. À réévaluer avant toute implémentation.

## Pitch initial

Site public listant des « decklist packs » (alimenté par le scraping de ce dépôt),
monétisé par publicité + mini-abonnement pour la retirer, interconnecté avec
`optcgsim-studio` pour l'import via compte membre. Question ouverte de départ : comment
distinguer un deck « original » d'une copie côté deckbuilders communautaires — via un
système de réputation ?

## Modèle économique

- **Publicité seule** : peu réaliste comme moteur principal — marché OPTCG niche, RPM
  display trop faible pour un revenu significatif sans trafic massif.
- **Abonnement anti-pub** : ne fonctionne bien que s'il débloque une vraie fonctionnalité
  (pas juste l'absence de pub) — ex. sync multi-device des decks perso, historique de
  versions, stats de perf par archétype, accès anticipé aux nouveaux packs scrapés.
- **Piste plus prometteuse pour ce marché** : affiliation vers des boutiques de singles
  (TCGplayer OP, Cardmarket…) — « acheter les cartes manquantes du deck ». Sert un vrai
  besoin, monétise probablement mieux qu'une bannière seule.
- Recommandation : pub légère + affiliation comme revenu de base, abonnement qui vend de
  la fonctionnalité réelle.

## Architecture technique

**Découverte clé** : `optcgsim-studio` a déjà une commande `studio sync --url --token`
entièrement câblée (`studio/cli.py: cmd_sync`, `studio/storage/remote.py: RestRemote`,
schéma `studio/db/schema.sql`), qui **anticipe explicitement Supabase/PostgREST** comme
backend (`profiles`/`decks`/`cosmetic_packs`, LWW par `updated_at`, RLS `user_id =
auth.uid()`). Ce n'est pas du code mort — testé (`tests/test_storage_sync.py`,
`tests/test_cli.py`), juste jamais pointé vers un vrai serveur.

Conséquence : le site bibliothèque et le sync privé du studio peuvent partager le **même
backend Supabase**. Un deck synchronisé depuis le studio pourrait être « publié » vers la
bibliothèque publique en ajoutant une colonne `visibility` (private/unlisted/public) à la
table `decks` déjà existante — pas de nouvelle table à inventer pour ce lien.

Stack envisagée :

- **Backend + DB + Auth : Supabase** (Postgres managé, Auth OAuth Discord, RLS, Storage).
  Réplique le schéma `studio/db/schema.sql` avec RLS.
- **Frontend : Next.js (App Router)**, repo séparé (ex. `optcgsim-library`). Cohérent avec
  le pattern déjà utilisé dans `optcgsim-haki-public` (FastAPI + Next.js prébuildé) et
  esquissé dans `optcgsim-studio/frontend` (`core/` logique pure + `adapters/` plateforme +
  `components/` bêtes).
- **Hébergement** : Vercel (Next.js, tier gratuit) + Supabase (tier gratuit au lancement) —
  zéro serveur à opérer.
- **Ingestion** : le scraper Python de ce dépôt reste tel quel ; ajouter une étape qui
  upsert les `deckpack.json` scrapés dans les tables Supabase (`supabase-py` ou REST
  direct), déclenchée en GitHub Action après un scraping planifié (le scraping est
  aujourd'hui lancé à la main, pas encore automatisé).
- **Paiement** : Stripe Checkout + Customer Portal, webhook Next.js qui met à jour
  `profiles.is_premium` dans Supabase (masque les pubs + débloque le premium).

**Point non trivial identifié** : `RestRemote` prend un token statique en argument CLI, or
l'auth Supabase standard émet des JWT utilisateur à courte durée de vie (~1h), sans
refresh dans `RestRemote` actuel. Pour un `studio sync --token ...` configuré une fois,
il faudra soit une clé API personnelle longue durée (table `api_keys` + petite Edge
Function qui la traduit en accès PostgREST), soit accepter une régénération périodique
(mauvaise UX). À trancher à l'implémentation, pas un bloqueur.

**Trois niveaux d'intégration studio**, du moins au plus coûteux :

1. **Niveau 0 (zéro code studio)** : chaque pack du site est exposé à une URL stable au
   format `deckpack.json` → `studio decks import-pack <url>` fonctionne déjà tel quel.
2. **Niveau 1 (confort)** : bouton « Ouvrir dans Studio » via un schéma d'URI personnalisé
   (`optcgsim-studio://import?url=...`) — nécessite d'enregistrer un handler de protocole
   à l'installation (spécifique par OS : `.desktop` Linux, registre Windows, Info.plist
   macOS). Effort modéré, pas encore fait.
3. **Niveau 2 (sync de compte)** : déjà quasi prêt côté studio (`studio sync`) — il
   manque seulement un backend Supabase déployé avec le bon schéma + RLS, et la question
   du token longue durée ci-dessus.

## Réputation / anti-plagiat

Une decklist n'est pas vraiment « copiable » au sens propriété intellectuelle — 60 cartes
+ 1 leader dans un méta donné convergent naturellement entre joueurs indépendants.
Chercher à prouver l'originalité est un combat perdu d'avance ; les sites équivalents
(Moxfield, Archidekt côté Magic) misent sur la **provenance transparente** plutôt que la
preuve d'antériorité :

- **Decks de tournoi** (déjà le cas du scraper actuel) : la réputation vient du résultat
  vérifiable (placement + joueur + tournoi) — rien à inventer, déjà la meilleure preuve
  possible.
- **Decks communautaires (« rogue »)** : horodatage de publication immuable + historique
  de versions façon git, champ explicite « inspiré de / netdecké depuis X » pour
  normaliser la ré-utilisation plutôt que la cacher, badges de compte vérifié (lié à un
  profil Limitless/Discord connu).
- **Détection de similarité automatique** : à la soumission, calculer un score de
  similarité avec les decks existants et proposer de lier comme variante plutôt que
  bloquer — transforme une accusation potentielle en traçabilité assumée.
- Signaux sociaux en complément : votes, followers, compteur d'imports.

## Prochaines étapes possibles (non engagées)

- Schéma de données exact des tables publiques de la bibliothèque + règles RLS.
- Flux détaillé « publier mon deck depuis le studio vers la bibliothèque ».
- Mécanisme d'API key longue durée pour `studio sync` (cf. point non trivial ci-dessus).
- Automatiser le scraping (aujourd'hui lancé à la main) avant de brancher une ingestion
  continue vers un backend hébergé.
