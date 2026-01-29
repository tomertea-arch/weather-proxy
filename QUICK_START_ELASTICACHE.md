# 🚀 Quick Start: Deploy with ElastiCache

Deploy Weather Proxy to AWS ECS with ElastiCache Redis in **under 15 minutes**.

## Prerequisites

- ✅ AWS Account with appropriate permissions
- ✅ AWS CLI configured (`aws configure`)
- ✅ GitHub repository for the project
- ✅ Existing VPC with private subnets (or use default VPC)

## Step 1: Create ElastiCache Cluster (10 minutes)

```bash
cd scripts
./create-elasticache.sh
```

This creates:
- ElastiCache Redis 7.0 cluster (`cache.t3.medium`)
- TLS encryption enabled
- Auth token stored in Secrets Manager
- Automated backups configured

**Output:**
```
✅ ElastiCache Redis cluster created successfully!

Connection Details:
  Endpoint: weather-proxy-redis.abc123.0001.euw1.cache.amazonaws.com
  Port: 6379
  Cluster ID: weather-proxy-redis
```

## Step 2: Configure GitHub Secrets (2 minutes)

Go to: **GitHub → Settings → Secrets and variables → Actions**

Add these secrets:

| Secret | Value |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `ELASTICACHE_CLUSTER_ID` | `weather-proxy-redis` |

## Step 3: Deploy via GitHub Actions (3 minutes)

```bash
# Commit and push
git add .
git commit -m "Add ElastiCache support"
git push origin main

# GitHub Actions will automatically:
# 1. Run tests
# 2. Build Docker image
# 3. Push to ECR
# 4. Get ElastiCache endpoint
# 5. Update ECS task definition
# 6. Deploy to ECS with 6 containers
```

**Monitor deployment:**
```
GitHub → Actions → "Deploy to ECS with ElastiCache"
```

## Step 4: Verify Deployment

```bash
# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names weather-proxy-alb \
  --region eu-west-1 \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

# Test health endpoint
curl "http://$ALB_DNS/health"

# Should show:
# {
#   "status": "healthy",
#   "redis": {
#     "status": "connected",
#     "host": "weather-proxy-redis.abc123.0001.euw1.cache.amazonaws.com"
#   }
# }

# Test weather API (cache miss)
curl "http://$ALB_DNS/weather?city=London"
# "cached": false

# Test again (cache hit)
curl "http://$ALB_DNS/weather?city=London"
# "cached": true  ✅
```

## That's It! 🎉

Your Weather Proxy is now running with:
- ✅ 6 ECS Fargate containers
- ✅ ElastiCache Redis for shared caching
- ✅ TLS encryption
- ✅ Automated backups
- ✅ Production-ready configuration

## Architecture

```
Internet → ALB → 6 ECS Tasks → ElastiCache Redis
```

## Costs

**Estimated monthly costs:**
- 6x Fargate tasks (0.5 vCPU, 1GB): ~$60/month
- ElastiCache (cache.t3.medium): ~$40/month
- ALB: ~$20/month
- Data transfer: ~$10/month
- **Total: ~$130/month**

## Local Development

For local development, use Docker Compose with containerized Redis:

```bash
# Start local services
docker-compose up -d

# Application connects to local Redis (no ElastiCache)
```

## Next Steps

- [ ] Set up custom domain with Route53
- [ ] Configure SSL/TLS with ACM
- [ ] Enable auto-scaling (3-12 tasks based on CPU)
- [ ] Set up CloudWatch alarms
- [ ] Configure CI/CD for staging environment

## Troubleshooting

### Can't connect to ElastiCache

```bash
# Check security group rules
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=*redis-sg*" \
  --region eu-west-1

# Verify ECS tasks can reach ElastiCache
aws ecs execute-command \
  --cluster weather-proxy-cluster-eu-west \
  --task <task-id> \
  --container weather-proxy \
  --interactive \
  --command "/bin/sh"

# Inside container:
nc -zv <elasticache-endpoint> 6379
```

### GitHub Actions fails

```bash
# Check that secrets are set
GitHub → Settings → Secrets → Actions

# Verify AWS credentials work
aws sts get-caller-identity
```

## Full Documentation

- **Complete Setup**: [ELASTICACHE_SETUP.md](ELASTICACHE_SETUP.md)
- **Request Tracing**: [REQUEST_TRACING.md](REQUEST_TRACING.md)
- **Main README**: [README.md](README.md)

---

**Need help?** Open an issue on GitHub or check the logs:
```bash
# View ECS service logs
aws logs tail /ecs/weather-proxy --follow --region eu-west-1
```
