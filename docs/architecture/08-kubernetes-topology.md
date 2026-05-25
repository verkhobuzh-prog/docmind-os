# Kubernetes Topology — Doc-Hub (Production)

## Cluster layout

```mermaid
flowchart TB
    subgraph Internet
        CF[Cloudflare CDN/WAF]
    end

    subgraph K8s["EKS / GKE — dochub-prod"]
        subgraph ingress_ns["namespace: ingress"]
            IG[Ingress NGINX / Gateway API]
        end

        subgraph app_ns["namespace: dochub-app"]
            API[Deployment: api<br/>HPA 3-20]
            WEB[Deployment: web<br/>HPA 2-10]
            ROUTER[Deployment: llm-router<br/>HPA 2-8]
        end

        subgraph worker_ns["namespace: dochub-workers"]
            W1[Deployment: ingestion-worker]
            W2[Deployment: embedding-worker]
            TEMP[Temporal frontend/matching]
        end

        subgraph data_ns["namespace: dochub-data"]
            REDIS[Redis Sentinel / Elasticache endpoint]
        end
    end

    subgraph External
        SB[(Supabase PostgreSQL)]
        S3[(S3 / R2)]
        NATS[NATS JetStream]
        OTEL[OTel Collector]
    end

    CF --> IG
    IG --> API
    IG --> WEB
    API --> SB
    API --> REDIS
    API --> NATS
    W1 --> S3
    W1 --> SB
    W1 --> TEMP
    API --> OTEL
```

---

## Helm chart structure

```
infra/helm/dochub/
├── Chart.yaml
├── values.yaml
├── values-staging.yaml
├── values-prod.yaml
└── templates/
    ├── deployment-api.yaml
    ├── deployment-web.yaml
    ├── deployment-workers.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── hpa.yaml
    ├── configmap.yaml
    ├── secret.yaml          # External Secrets Operator
    ├── pdb.yaml
    └── networkpolicy.yaml
```

---

## Resource sizing (prod baseline)

| Workload | Replicas | CPU | Memory |
|----------|----------|-----|--------|
| api | 3–20 (HPA) | 500m–2 | 1–4Gi |
| web | 2–10 | 250m–1 | 512Mi–2Gi |
| ingestion-worker | 2–50 (KEDA) | 1–4 | 2–8Gi |
| llm-router | 2–8 | 500m–2 | 1–2Gi |

**KEDA triggers:** NATS queue depth, Temporal task backlog.

---

## GitOps (ArgoCD)

```
apps/
├── dochub-api      → infra/helm/dochub (path: api)
├── dochub-web      → infra/helm/dochub (path: web)
└── dochub-workers  → infra/helm/dochub (path: workers)
```

Secrets: AWS Secrets Manager → External Secrets → K8s Secret.

---

## Network policies

- `api` → Supabase IP allowlist + Redis + NATS only
- `workers` → S3 + Supabase + LLM APIs (egress proxy optional)
- `web` → CDN only, no direct DB
