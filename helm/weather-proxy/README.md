# Weather Proxy Helm Chart

A Helm chart for deploying the Weather Proxy microservice on Kubernetes.

## Description

This chart deploys a FastAPI-based proxy microservice with Redis caching for weather data. It includes:
- FastAPI application deployment
- Optional Redis cache (can use external Redis)
- Horizontal Pod Autoscaling
- Prometheus metrics endpoint
- Health checks and liveness/readiness probes
- Graceful shutdown handling
- Pod Disruption Budget for high availability

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- PV provisioner support in the underlying infrastructure (if using Redis persistence)

## Installing the Chart

### Quick Start

```bash
# Add your Helm repository (if published)
helm repo add myrepo https://charts.example.com
helm repo update

# Install the chart with default values
helm install weather-proxy myrepo/weather-proxy

# Or install from local directory
helm install weather-proxy ./helm/weather-proxy
```

### Custom Values

```bash
# Install with custom values
helm install weather-proxy ./helm/weather-proxy \
  --set image.repository=your-registry/weather-proxy \
  --set image.tag=1.0.0 \
  --set replicaCount=3

# Install with values file
helm install weather-proxy ./helm/weather-proxy -f custom-values.yaml
```

### Install in specific namespace

```bash
kubectl create namespace weather-proxy
helm install weather-proxy ./helm/weather-proxy --namespace weather-proxy
```

## Uninstalling the Chart

```bash
helm uninstall weather-proxy
```

This removes all the Kubernetes components associated with the chart and deletes the release.

## Configuration

The following table lists the configurable parameters of the Weather Proxy chart and their default values.

### Application Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `2` |
| `image.repository` | Image repository | `your-registry/weather-proxy` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `image.tag` | Image tag | `""` (uses Chart.AppVersion) |

### Service Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port | `80` |
| `service.targetPort` | Container target port | `8000` |

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class name | `""` |
| `ingress.hosts` | Ingress hosts configuration | `[{"host": "weather-proxy.example.com", "paths": [{"path": "/", "pathType": "Prefix"}]}]` |
| `ingress.tls` | Ingress TLS configuration | `[]` |

### Resources

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.limits.cpu` | CPU limit | `500m` |
| `resources.limits.memory` | Memory limit | `512Mi` |
| `resources.requests.cpu` | CPU request | `250m` |
| `resources.requests.memory` | Memory request | `256Mi` |

### Autoscaling

| Parameter | Description | Default |
|-----------|-------------|---------|
| `autoscaling.enabled` | Enable HPA | `false` |
| `autoscaling.minReplicas` | Minimum replicas | `2` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | Target CPU | `80` |
| `autoscaling.targetMemoryUtilizationPercentage` | Target Memory | `80` |

### Redis Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.redis.host` | Redis hostname | `weather-proxy-redis-master` |
| `config.redis.port` | Redis port | `6379` |
| `config.redis.db` | Redis database number | `0` |
| `config.redis.password` | Redis password | `""` |
| `config.redis.external` | Use external Redis | `false` |
| `config.redis.externalHost` | External Redis host | `""` |
| `redis.enabled` | Deploy Redis with chart | `true` |

### Monitoring

| Parameter | Description | Default |
|-----------|-------------|---------|
| `serviceMonitor.enabled` | Create ServiceMonitor for Prometheus Operator | `false` |
| `serviceMonitor.interval` | Scrape interval | `30s` |
| `serviceMonitor.scrapeTimeout` | Scrape timeout | `10s` |

## Examples

### Example 1: Basic Installation

```bash
helm install weather-proxy ./helm/weather-proxy \
  --set image.repository=myregistry/weather-proxy \
  --set image.tag=1.0.0
```

### Example 2: With External Redis

```yaml
# external-redis-values.yaml
redis:
  enabled: false

config:
  redis:
    external: true
    externalHost: redis.example.com
    port: 6379
    password: "my-secret-password"
```

```bash
helm install weather-proxy ./helm/weather-proxy -f external-redis-values.yaml
```

### Example 3: With Ingress and TLS

```yaml
# ingress-values.yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: weather.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: weather-proxy-tls
      hosts:
        - weather.example.com
```

```bash
helm install weather-proxy ./helm/weather-proxy -f ingress-values.yaml
```

### Example 4: With Autoscaling

```yaml
# hpa-values.yaml
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 75

resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

```bash
helm install weather-proxy ./helm/weather-proxy -f hpa-values.yaml
```

### Example 5: With Prometheus ServiceMonitor

```yaml
# monitoring-values.yaml
serviceMonitor:
  enabled: true
  interval: 15s
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

## Upgrading

```bash
# Upgrade with new values
helm upgrade weather-proxy ./helm/weather-proxy \
  --set image.tag=2.0.0 \
  --reuse-values

# Upgrade with new values file
helm upgrade weather-proxy ./helm/weather-proxy -f new-values.yaml
```

## Testing the Deployment

After installation, verify the deployment:

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=weather-proxy

# Check service
kubectl get svc weather-proxy

# Port-forward to access locally
kubectl port-forward svc/weather-proxy 8080:80

# Test endpoints
curl http://localhost:8080/health
curl "http://localhost:8080/weather?city=London"
curl http://localhost:8080/metrics
```

## Health Checks

The chart configures both liveness and readiness probes:

- **Liveness Probe**: `/health` endpoint, checks if app is running
- **Readiness Probe**: `/health` endpoint, checks if app is ready to serve traffic

Default settings:
- Initial delay: 30s (liveness), 10s (readiness)
- Period: 10s (liveness), 5s (readiness)
- Timeout: 5s (liveness), 3s (readiness)

## Graceful Shutdown

The chart configures:
- `terminationGracePeriodSeconds: 30`
- Application handles SIGTERM for graceful shutdown
- Allows in-flight requests to complete before termination

## High Availability

For production deployments, consider:

1. **Multiple Replicas**:
   ```yaml
   replicaCount: 3
   ```

2. **Pod Disruption Budget**:
   ```yaml
   podDisruptionBudget:
     enabled: true
     minAvailable: 1
   ```

3. **Anti-affinity Rules**:
   ```yaml
   affinity:
     podAntiAffinity:
       preferredDuringSchedulingIgnoredDuringExecution:
       - weight: 100
         podAffinityTerm:
           labelSelector:
             matchExpressions:
             - key: app.kubernetes.io/name
               operator: In
               values:
               - weather-proxy
           topologyKey: kubernetes.io/hostname
   ```

## Troubleshooting

### Pods not starting

```bash
# Check pod events
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>

# Check if image can be pulled
kubectl get events --sort-by='.lastTimestamp'
```

### Redis connection issues

```bash
# Check Redis pod status
kubectl get pods -l app.kubernetes.io/name=redis

# Test Redis connectivity from app pod
kubectl exec -it <weather-proxy-pod> -- curl http://localhost:8000/health
```

### Performance issues

```bash
# Check resource usage
kubectl top pods -l app.kubernetes.io/name=weather-proxy

# Check HPA status
kubectl get hpa

# Check metrics
kubectl exec -it <pod-name> -- curl http://localhost:8000/metrics
```

## Security Considerations

The chart implements several security best practices:

1. **Non-root user**: Runs as user 1000
2. **Read-only root filesystem**: Option available
3. **Dropped capabilities**: All capabilities dropped
4. **Service Account**: Dedicated service account created
5. **Security Context**: Pod and container security contexts configured

## Contributing

To modify the chart:

1. Edit templates and values
2. Lint the chart:
   ```bash
   helm lint ./helm/weather-proxy
   ```
3. Test installation:
   ```bash
   helm install --dry-run --debug weather-proxy ./helm/weather-proxy
   ```
4. Package the chart:
   ```bash
   helm package ./helm/weather-proxy
   ```

## Support

For issues and questions:
- GitHub: https://github.com/yourusername/weather-proxy
- Email: team@example.com

## License

[Your License Here]
