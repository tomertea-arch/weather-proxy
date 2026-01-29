# AWS ElastiCache Setup Guide

Complete guide for deploying Weather Proxy with AWS ElastiCache Redis.

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      AWS eu-west-1                          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Application Load Balancer (Public)          │    │
│  └──────┬──────┬──────┬──────┬──────┬──────┬─────────┘    │
│         │      │      │      │      │      │               │
│    ┌────▼┐  ┌─▼──┐ ┌─▼──┐ ┌─▼──┐ ┌─▼──┐ ┌─▼──┐          │
│    │Task1│  │Task2│ │Task3│ │Task4│ │Task5│ │Task6│         │
│    │:8000│  │:8000│ │:8000│ │:8000│ │:8000│ │:8000│         │
│    └──┬──┘  └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘ └──┬─┘          │
│       │        │      │      │      │      │              │
│       └────────┴──────┴──────┴──────┴──────┘              │
│                        │                                   │
│              ┌─────────▼──────────┐                       │
│              │ ElastiCache Redis  │                       │
│              │   (Managed)        │                       │
│              │ cache.t3.medium    │                       │
│              │ - TLS Encrypted    │                       │
│              │ - Auth Enabled     │                       │
│              │ - Multi-AZ         │                       │
│              └────────────────────┘                       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Setup (3 Steps)

### Step 1: Create ElastiCache Cluster

```bash
# Run the automated script
cd scripts
./create-elasticache.sh

# Or manually via AWS CLI (see below)
```

**What it creates:**
- ✅ ElastiCache Redis 7.0 cluster
- ✅ Subnet group in private subnets
- ✅ Security group with ECS access
- ✅ TLS/SSL encryption enabled
- ✅ At-rest encryption enabled
- ✅ Auth token generated and stored in Secrets Manager
- ✅ Automated backups configured

**Time**: ~10 minutes

### Step 2: Configure GitHub Secrets

Go to: `GitHub Repository → Settings → Secrets and variables → Actions`

Add these secrets:

| Secret Name | Value | Where to Find |
|-------------|-------|---------------|
| `AWS_ACCESS_KEY_ID` | Your AWS access key | IAM Console |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key | IAM Console |
| `ELASTICACHE_CLUSTER_ID` | `weather-proxy-redis` | ElastiCache Console |

### Step 3: Deploy via GitHub Actions

```bash
# Push to main branch
git add .
git commit -m "Add ElastiCache support"
git push origin main

# Or trigger manually
# GitHub → Actions → "Deploy to ECS with ElastiCache" → Run workflow
```

## 📋 Manual ElastiCache Creation

If you prefer to create manually via AWS Console or CLI:

### Via AWS Console

1. **Go to ElastiCache Console**
   ```
   https://eu-west-1.console.aws.amazon.com/elasticache/home?region=eu-west-1
   ```

2. **Click "Create"**
   - Design: Cluster cache
   - Cluster mode: Disabled
   - Engine: Redis
   - Version: 7.0
   
3. **Configure Cluster**
   - Name: `weather-proxy-redis`
   - Node type: `cache.t3.medium`
   - Number of replicas: 0 (or 1-5 for HA)
   
4. **Configure Advanced Settings**
   - Subnet group: Select private subnets
   - Security groups: Allow port 6379 from ECS tasks
   - Encryption in-transit: Enabled (TLS)
   - Encryption at-rest: Enabled
   - Auth token: Generate and save
   
5. **Backup Settings**
   - Automatic backups: Enabled
   - Backup retention: 7 days
   - Backup window: 03:00-05:00 UTC

### Via AWS CLI

```bash
# Create subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name weather-proxy-redis-subnet-group \
  --cache-subnet-group-description "Subnet group for Weather Proxy" \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --region eu-west-1

# Generate auth token
AUTH_TOKEN=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

# Create cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id weather-proxy-redis \
  --cache-node-type cache.t3.medium \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --cache-subnet-group-name weather-proxy-redis-subnet-group \
  --security-group-ids sg-xxxxx \
  --auth-token "$AUTH_TOKEN" \
  --transit-encryption-enabled \
  --at-rest-encryption-enabled \
  --snapshot-retention-limit 7 \
  --region eu-west-1

# Wait for creation
aws elasticache wait cache-cluster-available \
  --cache-cluster-id weather-proxy-redis \
  --region eu-west-1

# Get endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id weather-proxy-redis \
  --show-cache-node-info \
  --region eu-west-1 \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
  --output text
```

## 🔧 Local Development vs AWS Production

### Local Development (Docker Compose)

```bash
# Uses containerized Redis
docker-compose up -d

# Application connects to local Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=  # No password locally
```

### AWS Production (ElastiCache)

```bash
# Application connects to ElastiCache
REDIS_HOST=weather-proxy-redis.abc123.0001.euw1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_PASSWORD=<from-secrets-manager>  # Auth token required
```

## 📝 Update ECS Task Definition

### Option 1: Via GitHub CI/CD (Automatic)

The GitHub Actions workflow automatically:
1. Retrieves ElastiCache endpoint
2. Updates task definition
3. Deploys to ECS

### Option 2: Manual Update

```bash
# Get current task definition
aws ecs describe-task-definition \
  --task-definition weather-proxy \
  --region eu-west-1 > task-def.json

# Edit task-def.json to add ElastiCache endpoint:
{
  "environment": [
    {
      "name": "REDIS_HOST",
      "value": "weather-proxy-redis.abc123.0001.euw1.cache.amazonaws.com"
    },
    {
      "name": "REDIS_PORT",
      "value": "6379"
    }
  ],
  "secrets": [
    {
      "name": "REDIS_PASSWORD",
      "valueFrom": "arn:aws:secretsmanager:eu-west-1:xxx:secret:weather-proxy/elasticache-password"
    }
  ]
}

# Register new task definition
aws ecs register-task-definition \
  --cli-input-json file://task-def.json \
  --region eu-west-1

# Update service
aws ecs update-service \
  --cluster weather-proxy-cluster-eu-west \
  --service weather-proxy-service \
  --task-definition weather-proxy:NEW_REVISION \
  --force-new-deployment \
  --region eu-west-1
```

## 🧪 Testing ElastiCache Connection

### From ECS Task

```bash
# SSH into running ECS task
aws ecs execute-command \
  --cluster weather-proxy-cluster-eu-west \
  --task <task-id> \
  --container weather-proxy \
  --interactive \
  --command "/bin/sh" \
  --region eu-west-1

# Inside container, test connection
redis-cli -h <elasticache-endpoint> -p 6379 --tls -a <password> ping
# Should return: PONG
```

### From Local Machine (via Bastion)

```bash
# Create EC2 bastion in same VPC
# SSH to bastion
ssh -i key.pem ec2-user@bastion-ip

# Install redis-cli
sudo yum install -y redis

# Test connection
redis-cli -h weather-proxy-redis.abc123.0001.euw1.cache.amazonaws.com \
  -p 6379 \
  --tls \
  -a <password> \
  ping
```

### Test via Application

```bash
# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names weather-proxy-alb \
  --region eu-west-1 \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

# Test weather API (first call - cache miss)
curl "http://$ALB_DNS/weather?city=London"
# Response: "cached": false

# Test again (should hit cache)
curl "http://$ALB_DNS/weather?city=London"
# Response: "cached": true

# Check health endpoint for Redis status
curl "http://$ALB_DNS/health" | jq '.redis'
```

## 🔐 Security Configuration

### Network Security

```
Security Group Rules:
┌─────────────────────────────────────────┐
│ ElastiCache Security Group              │
├─────────────────────────────────────────┤
│ Inbound:                                 │
│  - Port 6379 from ECS Tasks SG only     │
│                                          │
│ Outbound:                                │
│  - All traffic                           │
└─────────────────────────────────────────┘
```

### Encryption

- ✅ **In-Transit**: TLS 1.2+ required
- ✅ **At-Rest**: AES-256 encryption
- ✅ **Auth Token**: 32-character secure token

### Access Control

```bash
# IAM Policy for ECS Tasks
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:eu-west-1:*:secret:weather-proxy/elasticache-password*"
    }
  ]
}
```

## 💰 Cost Optimization

### Current Configuration

| Resource | Type | Monthly Cost |
|----------|------|--------------|
| ElastiCache | cache.t3.medium | ~$40 |
| Data Transfer | < 1GB | ~$1 |
| **Total** | | **~$41/month** |

### Cost Reduction Options

1. **Use Smaller Instance**
   ```bash
   # cache.t3.micro (~$12/month)
   # Suitable for < 1000 req/hour
   ```

2. **Reserved Instances**
   ```bash
   # Save 30-40% with 1-year commitment
   ```

3. **Adjust Backup Retention**
   ```bash
   # Reduce from 7 to 1 day
   # Saves ~$2/month
   ```

## 📊 Monitoring

### CloudWatch Metrics

```bash
# CPU Utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name CPUUtilization \
  --dimensions Name=CacheClusterId,Value=weather-proxy-redis \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region eu-west-1

# Memory Usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name DatabaseMemoryUsagePercentage \
  --dimensions Name=CacheClusterId,Value=weather-proxy-redis \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region eu-west-1
```

### Key Metrics to Watch

| Metric | Threshold | Action |
|--------|-----------|--------|
| CPU Utilization | > 70% | Scale up node type |
| Memory Usage | > 80% | Increase maxmemory or node type |
| Cache Hit Rate | < 80% | Review TTL settings |
| Connections | > 1000 | Check for connection leaks |
| Evictions | > 100/min | Increase memory |

### Create CloudWatch Alarms

```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name weather-proxy-redis-high-cpu \
  --alarm-description "Alert when Redis CPU is high" \
  --metric-name CPUUtilization \
  --namespace AWS/ElastiCache \
  --statistic Average \
  --period 300 \
  --threshold 70 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=CacheClusterId,Value=weather-proxy-redis \
  --region eu-west-1

# High memory alarm
aws cloudwatch put-metric-alarm \
  --alarm-name weather-proxy-redis-high-memory \
  --alarm-description "Alert when Redis memory is high" \
  --metric-name DatabaseMemoryUsagePercentage \
  --namespace AWS/ElastiCache \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=CacheClusterId,Value=weather-proxy-redis \
  --region eu-west-1
```

## 🔄 Backup and Recovery

### Automated Backups

Already configured:
- Daily backups at 03:00-05:00 UTC
- 7-day retention
- Stored in S3

### Manual Backup

```bash
# Create manual snapshot
aws elasticache create-snapshot \
  --cache-cluster-id weather-proxy-redis \
  --snapshot-name weather-proxy-manual-$(date +%Y%m%d) \
  --region eu-west-1

# List snapshots
aws elasticache describe-snapshots \
  --cache-cluster-id weather-proxy-redis \
  --region eu-west-1
```

### Restore from Backup

```bash
# Restore to new cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id weather-proxy-redis-restored \
  --snapshot-name weather-proxy-manual-20260129 \
  --cache-node-type cache.t3.medium \
  --region eu-west-1
```

## 🚨 Troubleshooting

### Cannot Connect to ElastiCache

**Problem**: Connection timeouts

**Solutions**:
```bash
# 1. Check security group rules
aws ec2 describe-security-groups \
  --group-ids sg-xxxxx \
  --region eu-west-1

# 2. Verify ECS tasks are in correct subnets
aws ecs describe-tasks \
  --cluster weather-proxy-cluster-eu-west \
  --tasks <task-arn> \
  --region eu-west-1

# 3. Test from ECS task
aws ecs execute-command \
  --cluster weather-proxy-cluster-eu-west \
  --task <task-id> \
  --container weather-proxy \
  --interactive \
  --command "/bin/sh" \
  --region eu-west-1

# Inside container:
nc -zv <elasticache-endpoint> 6379
```

### Authentication Failures

**Problem**: NOAUTH or WRONGPASS errors

**Solutions**:
```bash
# 1. Verify password in Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id weather-proxy/elasticache-password \
  --region eu-west-1

# 2. Check ECS task has permission to read secret
aws iam get-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-name SecretsManagerPolicy

# 3. Update task definition with correct secret ARN
```

### High Memory Usage

**Problem**: Memory usage > 90%

**Solutions**:
```bash
# 1. Check eviction rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name Evictions \
  --dimensions Name=CacheClusterId,Value=weather-proxy-redis \
  --region eu-west-1

# 2. Connect and check memory
redis-cli -h <endpoint> -p 6379 --tls -a <password> INFO memory

# 3. Clear cache if needed
redis-cli -h <endpoint> -p 6379 --tls -a <password> FLUSHALL

# 4. Scale up node type
aws elasticache modify-cache-cluster \
  --cache-cluster-id weather-proxy-redis \
  --cache-node-type cache.t3.large \
  --apply-immediately \
  --region eu-west-1
```

## ✅ Deployment Checklist

- [ ] ElastiCache cluster created
- [ ] Security group configured (port 6379 from ECS)
- [ ] Auth token stored in Secrets Manager
- [ ] ECS task execution role has Secrets Manager permission
- [ ] ECS task definition updated with ElastiCache endpoint
- [ ] GitHub secrets configured (ELASTICACHE_CLUSTER_ID)
- [ ] Deployed via GitHub Actions
- [ ] Health check shows Redis connected
- [ ] Cache hit/miss working correctly
- [ ] CloudWatch alarms configured
- [ ] Backups enabled and tested

## 📚 Additional Resources

- [ElastiCache Best Practices](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/BestPractices.html)
- [ElastiCache Pricing](https://aws.amazon.com/elasticache/pricing/)
- [Redis Commands](https://redis.io/commands)
- [GitHub Actions AWS Docs](https://github.com/aws-actions)

---

**Need Help?** Check the application health endpoint:
```bash
curl http://your-alb-dns/health | jq '.redis'
```
