---
name: ops-doc-check
description: >
  Vérifie qu'une doc d'exploitation docs/ respecte le standard ops-doc et colle à la réalité du repo :
  fichiers et sections obligatoires, liens cassés, secrets en clair, chaque alerte Prometheus avec son
  runbook_url et son runbook, variables et secrets des manifests présents dans config.md, dates de revue
  périmées, puis cohérence fine (noms de ressources dans les commandes, valeurs du dimensionnement,
  cases cochées de la checklist). Rapport classé en erreurs, avertissements et infos. À utiliser pour
  « vérifie la doc », « la doc est-elle à jour », « audit de conformité de la doc ops », en relecture
  d'une MR qui touche les manifests, les alertes ou docs/, ou en CI.
---

# ops-doc-check : conformité et cohérence

On vérifie si la doc **respecte le standard** et **dit vrai par rapport au repo**. La qualité rédactionnelle (est-ce qu'on s'en sort à 3 h du matin ?) relève de **ops-doc-review**. Ici, on s'en tient à ce qui se constate.

Le standard de référence est `../ops-doc/references/standard.md` (à partir du dossier de ce skill).

## 1. La passe mécanique : le script

```bash
python3 <dossier de ce skill>/../ops-doc/scripts/check_docs.py <repo> [--docs DIR] [--manifests DIR ...]
```
- `--manifests` : à utiliser quand les alertes ou les manifests vivent dans un autre repo ou un autre dossier. Sinon, tout le repo est analysé, sauf `docs/`.
- `--json` si tu veux traiter le résultat.
- Code de sortie 1 s'il y a des erreurs : le script peut servir tel quel de job de CI.

Les règles et leurs codes sont listés dans le standard, section 6. L'extraction depuis les manifests se fait par heuristique : avant de rapporter un `CONFIG-VAR` ou un `RUNBOOK-ORPHELIN`, vérifie que ce n'est pas un faux positif (variable injectée par un chart tiers, alerte définie dans un autre repo).

## 2. La passe de cohérence : ce que le script ne voit pas

Lis la doc et confronte-la aux manifests. Pour chaque point, ne rapporte que ce que tu as **vérifié**, avec la preuve (fichier:ligne des deux côtés).

| Vérification | Comment |
|---|---|
| **Les noms dans les commandes existent** | Namespaces, deployments, labels (`-l app.kubernetes.io/name=…`), nom du cluster CNPG, de l'Application ArgoCD, des PVC : chaque nom utilisé dans un bloc `bash` d'un runbook ou d'une procédure doit exister dans les manifests |
| **L'en-tête des runbooks colle à l'alerte** | L'expression, la sévérité et le `for` affichés correspondent à la PrometheusRule |
| **Le dimensionnement colle aux manifests** | Les colonnes requests/limits = les `resources` réelles ; les réplicas, les tailles de PVC et les paramètres Postgres = le `Cluster` CNPG |
| **Les composants et les dépendances sont complets** | Chaque workload du repo apparaît dans `README.md` > Composants ; aucun composant listé n'a disparu |
| **Les URLs** | Les hosts des Ingress correspondent aux URLs de `README.md` > Liens |
| **Les flux réseau** | Le tableau de `architecture.md` correspond aux NetworkPolicies |
| **Les sauvegardes** | Planning, rétention, bucket et `serverName` décrits = `ScheduledBackup`, `ObjectStore` ou `Cluster` |
| **La checklist ne ment pas** | Chaque case cochée qui se vérifie dans le repo (PDB, NetworkPolicy, probes, securityContext, tags d'image immuables, `runbook_url`…) est réellement vraie. Une case cochée fausse est une erreur |
| **Les chiffres sont cohérents entre fichiers** | RPO/RTO identiques dans `README.md` et `reprise.md` ; `max_connections` ≥ réplicas × taille du pool de connexions de l'app |
| **Les procédures citées existent** | Un runbook qui renvoie vers une procédure : elle existe (le script vérifie les liens, mais pas les mentions sans lien) |

Si `kubectl` est disponible et que l'utilisateur l'accepte, tu peux confronter aussi au cluster **en lecture seule** : c'est utile pour repérer une dérive entre Git et la réalité (« drift »). Signale-la sans rien corriger sur le cluster.

## 3. Le rapport

```markdown
# Conformité ops-doc : <repo> (<date>)

**Verdict** : CONFORME | NON CONFORME (N erreurs, N avertissements)

## Erreurs
- `CODE` fichier:ligne : constat. **Correction** : action précise.

## Avertissements
- …

## Cohérence doc / repo
- fichier:ligne (doc) ↔ fichier:ligne (repo) : écart constaté. **Correction** : …

## À compléter
- N marqueurs TODO(ops-doc) dans : fichiers…
```

Les erreurs du script et celles de la passe de cohérence vont ensemble, en tête, triées par impact pour l'astreinte : une alerte sans runbook ou une commande fausse avant une date périmée.

Ne corrige rien sans qu'on te le demande : le rapport sert à décider. Si l'utilisateur demande de corriger, fais-le, puis relance le script pour montrer qu'il est vert. Quand l'écart vient du repo (une alerte sans `runbook_url`), la correction va dans le repo, pas dans la doc.
