# Kubernetes deployment

Production manifests for the AI Ads Agent platform.

## Layout

| File | Contents |
| --- | --- |
| `namespace.yaml` | `ai-ads-agent` namespace |
| `config.yaml` | ConfigMap + Secret **template** (populate real secrets securely) |
| `data.yaml` | Postgres StatefulSet + Redis (prefer managed services in prod) |
| `backend.yaml` | API Deployment + Service + **HorizontalPodAutoscaler** (CPU/mem) |
| `worker.yaml` | Celery worker Deployment + single beat scheduler |
| `frontend.yaml` | Next.js Deployment + Service |
| `ingress.yaml` | NGINX ingress + TLS (cert-manager), routes `/api`→backend, `/`→frontend |

Images are pulled from GHCR (built by `.github/workflows/docker.yml`):
`ghcr.io/abhi3975/aigoogleads-backend` and `-frontend`.

## Apply

```bash
kubectl apply -f deploy/k8s/namespace.yaml

# Provide real secrets (do NOT commit them) — replaces the template:
kubectl -n ai-ads-agent create secret generic backend-secrets \
  --from-env-file=.env.production --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f deploy/k8s/config.yaml     # ConfigMap (and template secret, if not created above)
kubectl apply -f deploy/k8s/data.yaml
kubectl apply -f deploy/k8s/backend.yaml
kubectl apply -f deploy/k8s/worker.yaml
kubectl apply -f deploy/k8s/frontend.yaml
kubectl apply -f deploy/k8s/ingress.yaml

# Run migrations once (job or one-off):
kubectl -n ai-ads-agent exec deploy/backend -- alembic upgrade head
```

## Notes

- **Secrets**: use a sealed-secrets controller or a cloud secret manager;
  `config.yaml`'s Secret is a placeholder only.
- **Autoscaling**: `backend` scales 3→20 pods on 70% CPU / 80% memory
  (requires metrics-server).
- **Scheduler**: exactly one `beat` replica (`Recreate` strategy) to avoid
  duplicate scheduled jobs.
- **Managed data**: for real workloads point `POSTGRES_HOST`/`REDIS_HOST` at
  managed Postgres/Redis and drop `data.yaml`.
