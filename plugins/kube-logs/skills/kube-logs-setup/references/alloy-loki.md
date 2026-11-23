# Alloy et Loki : la configuration côté plateforme

> Ces exemples suivent la documentation officielle (sources en fin de fichier). Vérifiez les noms d'options pour votre version d'Alloy et de Loki : ils évoluent.

## Alloy : collecter les pods, parser le JSON, labels sobres

### Variante A : par l'API Kubernetes (`loki.source.kubernetes`)
Ni DaemonSet, ni accès au système de fichiers du nœud, ni privilèges. En contrepartie, plus de charge sur le kubelet et le réseau. Adapté à un petit cluster.

```alloy
discovery.kubernetes "pods" {
  role = "pod"
}

discovery.relabel "pods" {
  targets = discovery.kubernetes.pods.targets

  rule {
    source_labels = ["__meta_kubernetes_namespace"]
    target_label  = "namespace"
  }
  rule {
    source_labels = ["__meta_kubernetes_pod_label_app_kubernetes_io_name"]
    target_label  = "app"
  }
  rule {
    source_labels = ["__meta_kubernetes_pod_container_name"]
    target_label  = "container"
  }
  // Le nom du pod est utile, mais il change à chaque déploiement : il ira en
  // structured metadata (voir loki.process), pas en label.
  rule {
    source_labels = ["__meta_kubernetes_pod_name"]
    target_label  = "pod"
  }
}

loki.source.kubernetes "pods" {
  targets    = discovery.relabel.pods.output
  forward_to = [loki.process.app.receiver]
}
```

### Variante B : par les fichiers du nœud (`loki.source.file`)
DaemonSet avec `/var/log/pods` monté en lecture seule, et `stage.cri` pour retirer le préfixe CRI. La charge est minimale. C'est l'exemple de référence de la doc Alloy (« Collect Kubernetes logs »).

## Le traitement : `loki.process`

```alloy
loki.process "app" {
  // 1. Parser le JSON de l'app (sans effet sur une ligne qui n'est pas du JSON)
  stage.json {
    expressions = {
      level    = "",
      req_id   = "",
      trace_id = "",
    }
  }

  // 2. Un seul label tiré du contenu : le niveau (5 valeurs)
  stage.labels {
    values = { level = "" }
  }

  // 3. Les champs à forte cardinalité : en structured metadata, pas en labels
  stage.structured_metadata {
    values = {
      pod      = "",
      req_id   = "",
      trace_id = "",
    }
  }

  forward_to = [loki.write.default.receiver]
}

loki.write "default" {
  endpoint {
    url = "http://loki-gateway.monitoring.svc.cluster.local/loki/api/v1/push"
  }
}
```

- **Ne promouvez pas en label** `user_id`, `order_id`, `route`, l'URL ou l'IP : ils restent dans le JSON et se filtrent à la requête (`| json | order_id="42"`).
- `pod` passe d'un label (posé par la relabellisation) aux structured metadata : la doc précise qu'un label ajouté aux structured metadata est retiré de la liste des labels.
- Mettre `level` en label est un choix : cela accélère les filtres « que les erreurs ». Sans lui, `| json | level="error"` fonctionne aussi, simplement plus lentement à gros volume.

## Loki : rétention (désactivée par défaut)

Sans ces réglages, **Loki garde les logs pour toujours**.

```yaml
compactor:
  working_directory: /var/loki/compactor
  retention_enabled: true
  delete_request_store: s3
  retention_delete_delay: 2h

limits_config:
  retention_period: 744h          # 31 jours
  # Rétention par flux, si besoin :
  # retention_stream:
  #   - selector: '{namespace="staging"}'
  #     priority: 1
  #     period: 168h
```

- `retention_enabled` doit être dans le bloc **`compactor`** : `limits_config` seul ne suffit pas.
- Le compactor tourne en **instance unique**, avec des fichiers de marquage durables (un volume persistant, ou un préfixe dans l'objet storage selon la version).
- La rétention n'est pas rétroactive.
- Une règle de **cycle de vie S3**, si vous en mettez une, doit être plus longue que `retention_period`.
- Avec le chart Helm officiel de Loki, ces blocs se placent sous `loki:` dans `values.yaml` (`loki.compactor`, `loki.limits_config`).

## Loki : recording rules pour les dashboards sur logs

Pour un panneau qui recalcule un taux depuis les logs à chaque rafraîchissement, le ruler de Loki peut précalculer la requête et l'écrire dans Prometheus :

```yaml
groups:
  - name: rdv-api-logs
    interval: 1m
    rules:
      - record: rdv_api:log_errors:rate5m
        expr: sum by (namespace, app) (rate({app="rdv-api"} | json | level="error" [5m]))
```
Le ruler doit être configuré avec un `remote_write` vers Prometheus, et Prometheus doit accepter l'écriture distante (`--web.enable-remote-write-receiver`). Surveillez `loki_prometheus_rule_group_iterations_missed_total` : une valeur non nulle signale des évaluations manquées.

Si la mesure est importante, la vraie solution reste une métrique exposée par l'app (`prom-client`).

## Sources
- https://grafana.com/docs/alloy/latest/collect/logs-in-kubernetes/
- https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.kubernetes/
- https://grafana.com/docs/alloy/latest/reference/components/loki/loki.process/
- https://grafana.com/docs/loki/latest/get-started/labels/structured-metadata/
- https://grafana.com/docs/loki/latest/operations/storage/retention/
- https://grafana.com/docs/loki/latest/operations/recording-rules/
