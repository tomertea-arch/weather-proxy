# Helm Chart Deployment Guide

## Quick Reference

```bash
# Lint the chart
helm lint ./helm/weather-proxy

# Dry-run installation
helm install weather-proxy ./helm/weather-proxy --dry-run --debug

# Install with default values
helm install weather-proxy ./helm/weather-proxy

# Install in specific namespace
helm install weather-proxy ./helm/weather-proxy -n weather-proxy --create-namespace

# Install with custom values
helm install weather-proxy ./helm/weather-proxy -f custom-values.yaml

# Upgrade release
helm upgrade weather-proxy ./helm/weather-proxy

# Uninstall
helm uninstall weather-proxy
```

## Chart Structure

```
helm/weather-proxy/
├── Chart.yaml                      # Chart metadata
├── values.yaml                     # Default configuration values
├── values-production.yaml          # Production overrides
├── values-staging.yaml             # Staging overrides
├── README.md                       # Detailed chart documentation
├── .helmignore                     # Files to ignore
└── templates/
    ├── NOTES.txt                   # Post-install notes
    ├── _helpers.tpl                # Template helpers
    ├── deployment.yaml             # Deployment resource
    ├── service.yaml                # Service resource
    ├── serviceaccount.yaml         # ServiceAccount resource
    ├── configmap.yaml              # ConfigMap for configuration
    ├── secret.yaml                 # Secret for sensitive data
    ├── ingress.yaml                # Ingress resource (optional)
    ├── hpa.yaml                    # HorizontalPodAutoscaler (optional)
    ├── poddisruptionbudget.yaml    # PodDisruptionBudget (optional)
    └── servicemonitor.yaml         # ServiceMonitor for Prometheus (optional)
```

## Prerequisites

### 1. Install Helm

```bash
# macOS
brew install helm

# Linux
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Windows
choco install kubernetes-helm

# Verify installation
helm version
```

### 2. Kubernetes Cluster Access

```bash
# Verify kubectl access
kubectl cluster-info
kubectl get nodes
```

### 3. Build and Push Docker Image

```bash
# Build the Docker image
docker build -t your-registry/weather-proxy:1.0.0 .

# Push to registry
docker push your-registry/weather-proxy:1.0.0
```

## Installation Methods

### Method 1: Using the Install Script

```bash
# Navigate to helm directory
cd helm

# Basic installation
./install.sh

# Production installation
./install.sh --environment production --image 1.0.0

# Staging installation with dry-run
./install.sh --environment staging --dry-run

# Custom namespace
./install.sh --namespace my-namespace --release my-release
```

### Method 2: Direct Helm Commands

#### Development/Testing

```bash
helm install weather-proxy ./helm/weather-proxy \
  --set image.repository=your-registry/weather-proxy \
  --set image.tag=dev \
  --set redis.enabled=true
```

#### Staging

```bash
helm install weather-proxy ./helm/weather-proxy \
  -f ./helm/weather-proxy/values-staging.yaml \
  --set image.tag=staging \
  --namespace weather-proxy-staging \
  --create-namespace
```

#### Production

```bash
helm install weather-proxy ./helm/weather-proxy \
  -f ./helm/weather-proxy/values-production.yaml \
  --set image.tag=1.0.0 \
  --namespace weather-proxy-prod \
  --create-namespace
```

## Configuration Examples

### Example 1: Minimal Configuration

```yaml
# minimal-values.yaml
replicaCount: 1

image:
  repository: your-registry/weather-proxy
  tag: "1.0.0"

redis:
  enabled: true
  auth:
    enabled: false
```

```bash
helm install weather-proxy ./helm/weather-proxy -f minimal-values.yaml
```

### Example 2: External Redis

```yaml
# external-redis-values.yaml
redis:
  enabled: false

config:
  redis:
    external: true
    externalHost: redis.example.com
    port: 6379
    db: 0
    password: "my-secure-password"
```

```bash
helm install weather-proxy ./helm/weather-proxy -f external-redis-values.yaml
```

### Example 3: With Ingress and SSL

```yaml
# ingress-ssl-values.yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
  hosts:
    - host: weather.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: weather-proxy-tls
      hosts:
        - weather.yourdomain.com
```

```bash
helm install weather-proxy ./helm/weather-proxy -f ingress-ssl-values.yaml
```

### Example 4: High Availability Production

```yaml
# ha-production-values.yaml
replicaCount: 5

image:
  repository: your-registry/weather-proxy
  tag: "1.0.0"

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 30
  targetCPUUtilizationPercentage: 70

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 1000m
    memory: 1Gi

podDisruptionBudget:
  enabled: true
  minAvailable: 3

affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchExpressions:
        - key: app.kubernetes.io/name
          operator: In
          values:
          - weather-proxy
      topologyKey: kubernetes.io/hostname

redis:
  enabled: true
  architecture: replication
  master:
    persistence:
      enabled: true
      size: 10Gi
    resources:
      limits:
        cpu: 1000m
        memory: 1Gi
  replica:
    replicaCount: 2
    persistence:
      enabled: true
      size: 10Gi
```

```bash
helm install weather-proxy ./helm/weather-proxy -f ha-production-values.yaml
```

### Example 5: Monitoring with Prometheus

```yaml
# monitoring-values.yaml
serviceMonitor:
  enabled: true
  interval: 15s
  scrapeTimeout: 10s
  labels:
    release: prometheus

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

```bash
helm install weather-proxy ./helm/weather-proxy -f monitoring-values.yaml
```

## Validation and Testing

### 1. Lint the Chart

```bash
# Lint with default values
helm lint ./helm/weather-proxy

# Lint with specific values file
helm lint ./helm/weather-proxy -f ./helm/weather-proxy/values-production.yaml

# Lint and show warnings
helm lint ./helm/weather-proxy --strict
```

### 2. Dry Run

```bash
# Dry run with debug output
helm install weather-proxy ./helm/weather-proxy --dry-run --debug

# Dry run with production values
helm install weather-proxy ./helm/weather-proxy \
  -f ./helm/weather-proxy/values-production.yaml \
  --dry-run --debug > output.yaml
```

### 3. Template Rendering

```bash
# Render templates and view output
helm template weather-proxy ./helm/weather-proxy

# Render with specific values
helm template weather-proxy ./helm/weather-proxy \
  -f ./helm/weather-proxy/values-production.yaml \
  --set image.tag=1.0.0
```

## Post-Installation Verification

### Check Resources

```bash
# List all releases
helm list

# Get release status
helm status weather-proxy

# Check deployed resources
kubectl get all -l app.kubernetes.io/name=weather-proxy

# Check pods
kubectl get pods -l app.kubernetes.io/name=weather-proxy

# Check services
kubectl get svc -l app.kubernetes.io/name=weather-proxy

# Check ingress (if enabled)
kubectl get ingress
```

### Test Endpoints

```bash
# Port-forward to local machine
kubectl port-forward svc/weather-proxy 8080:80

# In another terminal, test endpoints
curl http://localhost:8080/health
curl "http://localhost:8080/weather?city=London"
curl http://localhost:8080/metrics
```

### View Logs

```bash
# Get logs from all pods
kubectl logs -l app.kubernetes.io/name=weather-proxy --tail=100

# Follow logs
kubectl logs -l app.kubernetes.io/name=weather-proxy -f

# Logs from specific pod
kubectl logs <pod-name>
```

## Upgrading

### Basic Upgrade

```bash
# Upgrade with new image tag
helm upgrade weather-proxy ./helm/weather-proxy \
  --set image.tag=1.1.0 \
  --reuse-values

# Upgrade with new values file
helm upgrade weather-proxy ./helm/weather-proxy \
  -f new-values.yaml
```

### Rolling Back

```bash
# View revision history
helm history weather-proxy

# Rollback to previous version
helm rollback weather-proxy

# Rollback to specific revision
helm rollback weather-proxy 2
```

## Troubleshooting

### Chart Issues

```bash
# Verify chart structure
helm show chart ./helm/weather-proxy

# Show computed values
helm get values weather-proxy

# Show all values (including defaults)
helm get values weather-proxy --all

# Show manifest
helm get manifest weather-proxy
```

### Common Problems

#### 1. Image Pull Errors

```bash
# Check image pull secrets
kubectl get secrets

# Describe pod to see events
kubectl describe pod <pod-name>

# Solution: Add imagePullSecrets
helm upgrade weather-proxy ./helm/weather-proxy \
  --set imagePullSecrets[0].name=my-registry-secret
```

#### 2. Redis Connection Issues

```bash
# Check Redis pods
kubectl get pods -l app.kubernetes.io/name=redis

# Test Redis connectivity
kubectl exec -it <weather-proxy-pod> -- curl http://localhost:8000/health

# Check logs for Redis errors
kubectl logs <weather-proxy-pod> | grep -i redis
```

#### 3. Resource Limits

```bash
# Check pod resource usage
kubectl top pods -l app.kubernetes.io/name=weather-proxy

# Increase resources
helm upgrade weather-proxy ./helm/weather-proxy \
  --set resources.limits.memory=1Gi \
  --reuse-values
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy Helm Chart

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          kubeconfig: ${{ secrets.KUBE_CONFIG }}
      
      - name: Install Helm
        uses: azure/setup-helm@v3
      
      - name: Lint Helm chart
        run: helm lint ./helm/weather-proxy
      
      - name: Deploy to staging
        run: |
          helm upgrade --install weather-proxy ./helm/weather-proxy \
            -f ./helm/weather-proxy/values-staging.yaml \
            --set image.tag=${{ github.sha }} \
            --namespace weather-proxy-staging \
            --create-namespace \
            --wait
      
      - name: Test deployment
        run: |
          kubectl rollout status deployment/weather-proxy -n weather-proxy-staging
          kubectl get pods -n weather-proxy-staging
```

### GitLab CI Example

```yaml
deploy:
  stage: deploy
  image: alpine/helm:latest
  script:
    - helm lint ./helm/weather-proxy
    - helm upgrade --install weather-proxy ./helm/weather-proxy \
        -f ./helm/weather-proxy/values-production.yaml \
        --set image.tag=$CI_COMMIT_TAG \
        --namespace weather-proxy-prod \
        --wait
  only:
    - tags
```

## Packaging and Distribution

### Create Package

```bash
# Package the chart
helm package ./helm/weather-proxy

# This creates: weather-proxy-1.0.0.tgz
```

### Publish to Chart Repository

```bash
# Create index
helm repo index . --url https://charts.example.com

# Upload to repository
# (method depends on your chart repository)
```

### Install from Repository

```bash
# Add repository
helm repo add myrepo https://charts.example.com

# Update repositories
helm repo update

# Install from repository
helm install weather-proxy myrepo/weather-proxy
```

## Best Practices

1. **Version Control**: Always version your values files
2. **Secrets Management**: Use external secrets (Sealed Secrets, External Secrets Operator)
3. **Resource Limits**: Always set resource requests and limits
4. **Health Checks**: Configure appropriate liveness and readiness probes
5. **Pod Disruption Budgets**: Use PDB for critical services
6. **Monitoring**: Enable ServiceMonitor for Prometheus integration
7. **Documentation**: Keep values.yaml well-documented
8. **Testing**: Always dry-run before production deployment
9. **Rollback Plan**: Test rollback procedures
10. **Backup**: Keep backup of values used for each deployment

## Security Considerations

1. **Non-root User**: Application runs as user 1000
2. **Security Contexts**: Pod and container security contexts configured
3. **Secrets**: Redis passwords stored in Kubernetes Secrets
4. **Network Policies**: Consider adding NetworkPolicies
5. **RBAC**: Service account with minimal permissions
6. **Image Scanning**: Scan images before deployment
7. **TLS**: Use TLS for ingress endpoints

## Support and Resources

- Helm Documentation: https://helm.sh/docs/
- Chart Best Practices: https://helm.sh/docs/chart_best_practices/
- Kubernetes Documentation: https://kubernetes.io/docs/

## Contributing

To contribute improvements to the chart:

1. Make changes to templates or values
2. Run `helm lint` to validate
3. Test with `--dry-run --debug`
4. Submit pull request with changes

---

**Chart Version**: 1.0.0  
**App Version**: 1.0.0  
**Last Updated**: 2026-01-22
