# AWS Fargate Deployment Guide

This guide walks you through deploying the Weather Proxy microservice to AWS Fargate.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Quick Start (5 Steps)](#quick-start-5-steps)
- [Detailed Deployment](#detailed-deployment)
- [Environment Variables](#environment-variables)
- [Monitoring & Scaling](#monitoring--scaling)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)
- [Cost Optimization](#cost-optimization)

---

## Prerequisites

### Required

- ✅ **AWS Account** with permissions for ECS, ECR, VPC, and IAM
- ✅ **AWS CLI v2** installed and configured
- ✅ **Docker image** pushed to a registry (Docker Hub or ECR)

### Optional

- **Terraform/CloudFormation** for Infrastructure as Code
- **Redis ElastiCache** for production (or use embedded Redis)

---

## Architecture Overview

```
Internet
    ↓
Application Load Balancer (ALB)
    ↓
AWS Fargate (ECS)
├─ Container 1: weather-proxy:latest
├─ Container 2: weather-proxy:latest
└─ Container N: weather-proxy:latest
    ↓
AWS ElastiCache (Redis) [Optional]
    ↓
Open-Meteo API (External)
```

**Components:**
- **ECS Cluster**: Manages Fargate tasks
- **Task Definition**: Defines container configuration
- **Service**: Ensures desired number of tasks running
- **ALB**: Load balancer for traffic distribution
- **Security Groups**: Network access control

---

## Quick Start (5 Steps)

### Step 1: Install AWS CLI

```bash
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
```

### Step 2: Configure AWS Credentials

```bash
aws configure
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region: us-east-1
# Default output format: json
```

### Step 3: Push Docker Image to ECR (Recommended)

```bash
# Create ECR repository
aws ecr create-repository \
    --repository-name weather-proxy \
    --region us-east-1

# Get login credentials
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin \
    YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag your image
docker tag weather-proxy:latest \
    YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/weather-proxy:latest

# Push to ECR
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/weather-proxy:latest
```

### Step 4: Deploy Using AWS Console (Easiest)

1. **Go to ECS Console**: https://console.aws.amazon.com/ecs/
2. **Click "Get Started"** or "Create Cluster"
3. **Select "Networking only" (Fargate)**
4. **Follow the wizard** - it will create:
   - ECS Cluster
   - Task Definition
   - Service
   - Load Balancer
   - Security Groups

### Step 5: Access Your Application

```bash
# Get the Load Balancer DNS
aws elbv2 describe-load-balancers \
    --query "LoadBalancers[0].DNSName" \
    --output text

# Test it
curl http://YOUR-ALB-DNS/health
curl http://YOUR-ALB-DNS/weather?city=London
```

---

## Detailed Deployment

### Option 1: AWS CLI Deployment

#### 1. Create ECS Cluster

```bash
aws ecs create-cluster \
    --cluster-name weather-proxy-cluster \
    --region us-east-1
```

#### 2. Create Task Execution Role

```bash
# Create trust policy
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document file://trust-policy.json

# Attach policy
aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

#### 3. Create Task Definition

```bash
cat > task-definition.json <<EOF
{
  "family": "weather-proxy",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "weather-proxy",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/weather-proxy:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/weather-proxy",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Register task definition
aws ecs register-task-definition \
    --cli-input-json file://task-definition.json
```

#### 4. Create CloudWatch Log Group

```bash
aws logs create-log-group \
    --log-group-name /ecs/weather-proxy \
    --region us-east-1
```

#### 5. Get Default VPC and Subnets

```bash
# Get VPC ID
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query "Vpcs[0].VpcId" \
    --output text)

# Get Subnet IDs
SUBNET_IDS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "Subnets[*].SubnetId" \
    --output text | tr '\t' ',')

echo "VPC: $VPC_ID"
echo "Subnets: $SUBNET_IDS"
```

#### 6. Create Security Group

```bash
# Create security group
SG_ID=$(aws ec2 create-security-group \
    --group-name weather-proxy-sg \
    --description "Security group for Weather Proxy" \
    --vpc-id $VPC_ID \
    --output text)

# Allow inbound HTTP on port 8000
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0

# Allow outbound (all)
aws ec2 authorize-security-group-egress \
    --group-id $SG_ID \
    --protocol -1 \
    --cidr 0.0.0.0/0

echo "Security Group: $SG_ID"
```

#### 7. Create ECS Service

```bash
aws ecs create-service \
    --cluster weather-proxy-cluster \
    --service-name weather-proxy-service \
    --task-definition weather-proxy \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
    --region us-east-1
```

#### 8. Get Public IP and Test

```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
    --cluster weather-proxy-cluster \
    --service-name weather-proxy-service \
    --query "taskArns[0]" \
    --output text)

# Get network interface
ENI_ID=$(aws ecs describe-tasks \
    --cluster weather-proxy-cluster \
    --tasks $TASK_ARN \
    --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" \
    --output text)

# Get public IP
PUBLIC_IP=$(aws ec2 describe-network-interfaces \
    --network-interface-ids $ENI_ID \
    --query "NetworkInterfaces[0].Association.PublicIp" \
    --output text)

echo "Public IP: $PUBLIC_IP"

# Test
curl http://$PUBLIC_IP:8000/health
curl http://$PUBLIC_IP:8000/weather?city=London
```

---

### Option 2: Using Application Load Balancer (Production)

#### 1. Create Target Group

```bash
TG_ARN=$(aws elbv2 create-target-group \
    --name weather-proxy-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text)
```

#### 2. Create Application Load Balancer

```bash
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name weather-proxy-alb \
    --subnets $(echo $SUBNET_IDS | tr ',' ' ') \
    --security-groups $SG_ID \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4 \
    --query "LoadBalancers[0].LoadBalancerArn" \
    --output text)
```

#### 3. Create Listener

```bash
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

#### 4. Update Security Group for ALB

```bash
# Allow HTTP on port 80
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0
```

#### 5. Create Service with Load Balancer

```bash
aws ecs create-service \
    --cluster weather-proxy-cluster \
    --service-name weather-proxy-service-alb \
    --task-definition weather-proxy \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
    --load-balancers targetGroupArn=$TG_ARN,containerName=weather-proxy,containerPort=8000 \
    --health-check-grace-period-seconds 60
```

#### 6. Get ALB DNS

```bash
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --query "LoadBalancers[0].DNSName" \
    --output text)

echo "Load Balancer URL: http://$ALB_DNS"

# Test
curl http://$ALB_DNS/health
curl http://$ALB_DNS/weather?city=Tokyo
```

---

## Environment Variables

### Configure Environment Variables in Task Definition

```json
{
  "environment": [
    {
      "name": "LOG_LEVEL",
      "value": "INFO"
    },
    {
      "name": "REDIS_HOST",
      "value": "your-redis.cache.amazonaws.com"
    },
    {
      "name": "REDIS_PORT",
      "value": "6379"
    },
    {
      "name": "REDIS_PASSWORD",
      "value": "your-password"
    }
  ]
}
```

### Using AWS Secrets Manager (Recommended for Sensitive Data)

```bash
# Store secret
aws secretsmanager create-secret \
    --name weather-proxy/redis-password \
    --secret-string "your-secure-password"

# Update task definition to use secrets
{
  "secrets": [
    {
      "name": "REDIS_PASSWORD",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:weather-proxy/redis-password"
    }
  ]
}
```

---

## Monitoring & Scaling

### Auto Scaling

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/weather-proxy-cluster/weather-proxy-service-alb \
    --min-capacity 2 \
    --max-capacity 10

# Create scaling policy (CPU-based)
aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/weather-proxy-cluster/weather-proxy-service-alb \
    --policy-name cpu-scaling-policy \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
        "TargetValue": 70.0,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
        },
        "ScaleInCooldown": 300,
        "ScaleOutCooldown": 60
    }'
```

### CloudWatch Alarms

```bash
# CPU Utilization Alarm
aws cloudwatch put-metric-alarm \
    --alarm-name weather-proxy-high-cpu \
    --alarm-description "Alert when CPU exceeds 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=ClusterName,Value=weather-proxy-cluster Name=ServiceName,Value=weather-proxy-service-alb

# Memory Utilization Alarm
aws cloudwatch put-metric-alarm \
    --alarm-name weather-proxy-high-memory \
    --alarm-description "Alert when memory exceeds 80%" \
    --metric-name MemoryUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=ClusterName,Value=weather-proxy-cluster Name=ServiceName,Value=weather-proxy-service-alb
```

---

## CI/CD Integration

### Add AWS Deployment to GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS Fargate

on:
  push:
    branches: [ main ]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: weather-proxy
  ECS_CLUSTER: weather-proxy-cluster
  ECS_SERVICE: weather-proxy-service-alb
  CONTAINER_NAME: weather-proxy

jobs:
  deploy:
    name: Deploy to Fargate
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v2
    
    - name: Build, tag, and push image to Amazon ECR
      id: build-image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
        echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT
    
    - name: Download task definition
      run: |
        aws ecs describe-task-definition \
          --task-definition weather-proxy \
          --query taskDefinition > task-definition.json
    
    - name: Fill in the new image ID in the Amazon ECS task definition
      id: task-def
      uses: aws-actions/amazon-ecs-render-task-definition@v1
      with:
        task-definition: task-definition.json
        container-name: ${{ env.CONTAINER_NAME }}
        image: ${{ steps.build-image.outputs.image }}
    
    - name: Deploy Amazon ECS task definition
      uses: aws-actions/amazon-ecs-deploy-task-definition@v1
      with:
        task-definition: ${{ steps.task-def.outputs.task-definition }}
        service: ${{ env.ECS_SERVICE }}
        cluster: ${{ env.ECS_CLUSTER }}
        wait-for-service-stability: true
```

### Required GitHub Secrets

Add to: `Settings` → `Secrets and variables` → `Actions`

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

---

## Troubleshooting

### Tasks Not Starting

```bash
# Check service events
aws ecs describe-services \
    --cluster weather-proxy-cluster \
    --services weather-proxy-service-alb \
    --query "services[0].events[0:5]"

# Check task stopped reason
aws ecs describe-tasks \
    --cluster weather-proxy-cluster \
    --tasks TASK_ARN \
    --query "tasks[0].stoppedReason"
```

### View Container Logs

```bash
# Using AWS CLI
aws logs tail /ecs/weather-proxy --follow

# Or use CloudWatch Console
# https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Fecs$252Fweather-proxy
```

### Health Check Failing

```bash
# Check container logs
aws logs filter-log-events \
    --log-group-name /ecs/weather-proxy \
    --filter-pattern "ERROR" \
    --start-time $(date -u -d '5 minutes ago' +%s)000

# SSH into task (if enabled)
aws ecs execute-command \
    --cluster weather-proxy-cluster \
    --task TASK_ARN \
    --container weather-proxy \
    --interactive \
    --command "/bin/bash"
```

### Service Won't Scale

```bash
# Check service desired vs running count
aws ecs describe-services \
    --cluster weather-proxy-cluster \
    --services weather-proxy-service-alb \
    --query "services[0].[desiredCount,runningCount]"

# Check capacity provider
aws ecs describe-clusters \
    --clusters weather-proxy-cluster \
    --include STATISTICS
```

---

## Cost Optimization

### Estimated Monthly Costs

| Resource | Configuration | Cost/Month |
|----------|--------------|------------|
| Fargate (2 tasks) | 0.25 vCPU, 0.5 GB | ~$15 |
| Application Load Balancer | Standard | ~$23 |
| Data Transfer | 100 GB | ~$9 |
| CloudWatch Logs | 10 GB | ~$5 |
| **Total** | | **~$52/month** |

### Cost Saving Tips

1. **Use Fargate Spot** (up to 70% savings):
   ```bash
   --capacity-provider-strategy capacityProvider=FARGATE_SPOT,weight=1
   ```

2. **Right-size resources**:
   - Start with 0.25 vCPU / 0.5 GB
   - Monitor and adjust based on actual usage

3. **Use embedded Redis** for development:
   - No ElastiCache costs
   - Built into the container

4. **Enable container insights selectively**:
   - Only in production
   - Incurs additional CloudWatch costs

5. **Set up auto-scaling**:
   - Scale down during off-peak hours
   - Use scheduled scaling for predictable patterns

---

## Production Checklist

- [ ] Use Application Load Balancer
- [ ] Enable auto-scaling (min: 2, max: 10)
- [ ] Configure CloudWatch alarms
- [ ] Use AWS Secrets Manager for credentials
- [ ] Enable container insights
- [ ] Set up ElastiCache Redis cluster
- [ ] Configure custom domain with Route 53
- [ ] Enable HTTPS with ACM certificate
- [ ] Set up VPC with private subnets
- [ ] Enable VPC Flow Logs
- [ ] Configure backup strategy
- [ ] Set up monitoring dashboard
- [ ] Document runbooks
- [ ] Test disaster recovery

---

## Additional Resources

- [AWS Fargate Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [ECS Task Definitions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html)
- [Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)
- [ECS Auto Scaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html)
- [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)

---

**Need help?** Check the [Troubleshooting](#troubleshooting) section or review CloudWatch logs!
