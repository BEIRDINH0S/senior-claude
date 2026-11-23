# Déployer les dashboards en GitOps avec le sidecar Grafana

La méthode la plus simple : le sidecar `k8s-sidecar` est **déjà inclus** dans le chart Helm Grafana (et donc dans kube-prometheus-stack). Il surveille les ConfigMaps qui portent un label donné et écrit leur contenu dans le dossier de provisioning de Grafana. Ni opérateur, ni CRD.

## 1. Activer le sidecar (values du chart)

Avec kube-prometheus-stack, ces valeurs vont sous la clé `grafana:`.

```yaml
sidecar:
  dashboards:
    enabled: true
    label: grafana_dashboard
    labelValue: "1"
    searchNamespace: ALL            # ou une liste de namespaces
    folderAnnotation: grafana_folder
    provider:
      foldersFromFilesStructure: true
      allowUiUpdates: false         # une modification passe par Git
```

Vérifiez ces noms dans le `values.yaml` de **votre** version du chart : ils changent parfois.

## 2. Le repo : un fichier JSON par dashboard

```
gitops/
└── apps/observability/dashboards/
    ├── kustomization.yaml
    ├── rdv/
    │   └── rdv-overview.json          ← niveau 1, le vôtre
    └── composants/
        ├── cloudnative-pg.json        ← communautaire, versionné ici
        └── kubernetes-pods.json
```

```yaml
# kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: monitoring

generatorOptions:
  disableNameSuffixHash: true       # nom stable : pas de ConfigMap orpheline à chaque modification
  labels:
    grafana_dashboard: "1"

configMapGenerator:
  - name: dashboard-rdv-overview
    files: [rdv/rdv-overview.json]
    options:
      annotations:
        grafana_folder: "rdv"
  - name: dashboard-cloudnative-pg
    files: [composants/cloudnative-pg.json]
    options:
      annotations:
        grafana_folder: "Composants"
```

**Une ConfigMap par dashboard** : la limite d'une ConfigMap est de 1 Mio. Avec un dashboard par ConfigMap, on ne l'atteint pratiquement jamais.

## 3. ArgoCD : Server-Side Apply

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: dashboards
spec:
  syncPolicy:
    automated: { prune: true, selfHeal: true }
    syncOptions:
      - ServerSideApply=true
```

Sans cette option, ArgoCD applique en client-side et recopie tout le manifest dans l'annotation `kubectl.kubernetes.io/last-applied-configuration`, limitée à **262 144 octets**. Un dashboard un peu riche dépasse cette limite, et le sync échoue avec `metadata.annotations: Too long`. C'est cette limite qu'on prend souvent pour « la limite des ConfigMaps ».

## 4. Le cycle de modification

1. Prototyper dans l'interface Grafana, sur une copie ou sur une instance de dev.
2. **Exporter** le JSON (Partager → Exporter, sans cocher « exporter pour un partage externe », pour garder les références `${datasource}`).
3. Remplacer le fichier dans le repo, lancer le linter, ouvrir une MR.
4. ArgoCD synchronise, et le sidecar recharge le dashboard (en quelques secondes, ou au prochain cycle de rechargement).

Avec `allowUiUpdates: false`, Grafana refuse d'enregistrer une modification faite dans l'interface sur un dashboard provisionné. C'est voulu : Git reste la source de vérité.

## 5. Dashboards v2 (onglets) et provisioning

Le sidecar écrit des fichiers et Grafana les lit avec son provisioning par fichier. Pour un dashboard au **schéma v2** (onglets, layouts dynamiques), le fichier doit être au format **ressource Kubernetes** :
```json
{
  "apiVersion": "dashboard.grafana.app/v2beta1",
  "kind": "Dashboard",
  "metadata": { "name": "rdv-overview" },
  "spec": { "title": "rdv : vue d'ensemble", "elements": { }, "layout": { } }
}
```
- L'`apiVersion` exacte dépend de la version de Grafana (`v2alpha1`, `v2beta1`, `v2`…). **Exportez un dashboard v2 depuis votre instance** et reprenez ce qu'elle produit.
- Selon les versions, la doc Grafana présente le schéma v2 comme preview ou expérimental, avec des feature toggles (`dashboardNewLayouts` / dynamic dashboards, `kubernetesDashboards`). Sur une version récente, ils sont activés par défaut.
- Un dashboard v1 reste valide : Grafana le migre à l'affichage. Les onglets demandent le v2.

## 6. Dashboards communautaires

Téléchargez le JSON à une version précise (release du projet, ou ID grafana.com) et commitez-le. Ne vous contentez pas d'un import manuel ni d'un téléchargement à chaque démarrage : vous savez ainsi exactement ce qui tourne, et une mise à jour passe par une MR.

Pensez à remplacer leur source de données en dur par la variable `${datasource}` si le dashboard n'en a pas.
