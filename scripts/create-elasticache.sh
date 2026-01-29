#!/bin/bash

###############################################################################
# Create AWS ElastiCache Redis Cluster
# This script creates a production-ready ElastiCache cluster for Weather Proxy
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ $1${NC}"; }

# Configuration
AWS_REGION="${AWS_REGION:-eu-west-1}"
CLUSTER_ID="${CLUSTER_ID:-weather-proxy-redis}"
NODE_TYPE="${NODE_TYPE:-cache.t3.medium}"
ENGINE_VERSION="${ENGINE_VERSION:-7.0}"
SUBNET_GROUP_NAME="${SUBNET_GROUP_NAME:-weather-proxy-redis-subnet-group}"
SECURITY_GROUP_NAME="${SECURITY_GROUP_NAME:-weather-proxy-redis-sg}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      AWS ElastiCache Redis Cluster Creation Script           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

print_info "Configuration:"
echo "  Region: $AWS_REGION"
echo "  Cluster ID: $CLUSTER_ID"
echo "  Node Type: $NODE_TYPE"
echo "  Engine Version: $ENGINE_VERSION"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install it first."
    exit 1
fi

# Check credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_success "AWS Account: $ACCOUNT_ID"
echo ""

# Get VPC ID
print_info "Getting VPC information..."
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=tag:Name,Values=weather-proxy-vpc" \
    --region $AWS_REGION \
    --query 'Vpcs[0].VpcId' \
    --output text 2>/dev/null || echo "None")

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    print_warning "VPC not found. Please create VPC first or specify VPC_ID"
    read -p "Enter VPC ID: " VPC_ID
fi

print_success "Using VPC: $VPC_ID"

# Get Private Subnets
print_info "Getting private subnets..."
SUBNET_1=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=*private-1*" \
    --region $AWS_REGION \
    --query 'Subnets[0].SubnetId' \
    --output text 2>/dev/null || echo "None")

SUBNET_2=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=*private-2*" \
    --region $AWS_REGION \
    --query 'Subnets[0].SubnetId' \
    --output text 2>/dev/null || echo "None")

if [ "$SUBNET_1" == "None" ] || [ "$SUBNET_2" == "None" ]; then
    print_warning "Private subnets not found automatically"
    read -p "Enter Subnet 1 ID: " SUBNET_1
    read -p "Enter Subnet 2 ID: " SUBNET_2
fi

print_success "Using subnets: $SUBNET_1, $SUBNET_2"
echo ""

# Create Subnet Group
print_info "Creating ElastiCache subnet group..."
if aws elasticache describe-cache-subnet-groups \
    --cache-subnet-group-name $SUBNET_GROUP_NAME \
    --region $AWS_REGION &>/dev/null; then
    print_warning "Subnet group already exists"
else
    aws elasticache create-cache-subnet-group \
        --cache-subnet-group-name $SUBNET_GROUP_NAME \
        --cache-subnet-group-description "Subnet group for Weather Proxy Redis" \
        --subnet-ids $SUBNET_1 $SUBNET_2 \
        --region $AWS_REGION \
        --tags "Key=Name,Value=weather-proxy-redis-subnet-group" "Key=Application,Value=weather-proxy"
    print_success "Subnet group created"
fi

# Create Security Group
print_info "Creating security group..."
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --region $AWS_REGION \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "None")

if [ "$SG_ID" != "None" ] && [ -n "$SG_ID" ]; then
    print_warning "Security group already exists: $SG_ID"
else
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP_NAME \
        --description "Security group for Weather Proxy ElastiCache Redis" \
        --vpc-id $VPC_ID \
        --region $AWS_REGION \
        --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$SECURITY_GROUP_NAME}]" \
        --query 'GroupId' \
        --output text)
    print_success "Security group created: $SG_ID"
    
    # Get ECS tasks security group
    ECS_SG=$(aws ec2 describe-security-groups \
        --filters "Name=tag:Name,Values=*ecs-sg*" "Name=vpc-id,Values=$VPC_ID" \
        --region $AWS_REGION \
        --query 'SecurityGroups[0].GroupId' \
        --output text 2>/dev/null || echo "None")
    
    if [ "$ECS_SG" != "None" ]; then
        # Allow access from ECS tasks
        aws ec2 authorize-security-group-ingress \
            --group-id $SG_ID \
            --protocol tcp \
            --port 6379 \
            --source-group $ECS_SG \
            --region $AWS_REGION
        print_success "Allowed access from ECS tasks"
    else
        print_warning "ECS security group not found. You'll need to manually configure ingress rules."
    fi
fi

# Generate secure password
print_info "Generating secure password..."
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

# Store password in Secrets Manager
print_info "Storing password in AWS Secrets Manager..."
SECRET_ARN=$(aws secretsmanager create-secret \
    --name "weather-proxy/elasticache-password" \
    --description "ElastiCache Redis password for Weather Proxy" \
    --secret-string "$REDIS_PASSWORD" \
    --region $AWS_REGION \
    --tags "Key=Application,Value=weather-proxy" \
    --query 'ARN' \
    --output text 2>/dev/null || \
    aws secretsmanager describe-secret \
    --secret-id "weather-proxy/elasticache-password" \
    --region $AWS_REGION \
    --query 'ARN' \
    --output text)

print_success "Password stored in Secrets Manager: $SECRET_ARN"

# Create ElastiCache cluster
echo ""
print_info "Creating ElastiCache Redis cluster..."
print_warning "This will take 5-10 minutes..."
echo ""

if aws elasticache describe-cache-clusters \
    --cache-cluster-id $CLUSTER_ID \
    --region $AWS_REGION &>/dev/null; then
    print_warning "Cluster already exists: $CLUSTER_ID"
else
    aws elasticache create-cache-cluster \
        --cache-cluster-id $CLUSTER_ID \
        --cache-node-type $NODE_TYPE \
        --engine redis \
        --engine-version $ENGINE_VERSION \
        --num-cache-nodes 1 \
        --cache-subnet-group-name $SUBNET_GROUP_NAME \
        --security-group-ids $SG_ID \
        --auth-token "$REDIS_PASSWORD" \
        --transit-encryption-enabled \
        --at-rest-encryption-enabled \
        --region $AWS_REGION \
        --tags "Key=Name,Value=weather-proxy-redis" "Key=Application,Value=weather-proxy" "Key=Environment,Value=production" \
        --snapshot-retention-limit 7 \
        --snapshot-window "03:00-05:00" \
        --preferred-maintenance-window "sun:05:00-sun:07:00"
    
    print_success "Cluster creation initiated"
fi

# Wait for cluster to be available
print_info "Waiting for cluster to become available..."
aws elasticache wait cache-cluster-available \
    --cache-cluster-id $CLUSTER_ID \
    --region $AWS_REGION

print_success "Cluster is now available!"
echo ""

# Get cluster endpoint
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters \
    --cache-cluster-id $CLUSTER_ID \
    --show-cache-node-info \
    --region $AWS_REGION \
    --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
    --output text)

REDIS_PORT=$(aws elasticache describe-cache-clusters \
    --cache-cluster-id $CLUSTER_ID \
    --show-cache-node-info \
    --region $AWS_REGION \
    --query 'CacheClusters[0].CacheNodes[0].Endpoint.Port' \
    --output text)

# Summary
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   Creation Complete! 🎉                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
print_success "ElastiCache Redis cluster created successfully!"
echo ""
echo "📊 Cluster Details:"
echo "  Cluster ID: $CLUSTER_ID"
echo "  Node Type: $NODE_TYPE"
echo "  Engine Version: Redis $ENGINE_VERSION"
echo "  Region: $AWS_REGION"
echo ""
echo "🔌 Connection Details:"
echo "  Endpoint: $REDIS_ENDPOINT"
echo "  Port: $REDIS_PORT"
echo "  Password: (stored in Secrets Manager)"
echo "  Secret ARN: $SECRET_ARN"
echo ""
echo "🔐 Security:"
echo "  Transit Encryption: Enabled (TLS)"
echo "  At-Rest Encryption: Enabled"
echo "  Auth Token: Enabled"
echo "  Security Group: $SG_ID"
echo ""
echo "💰 Cost Estimate:"
echo "  ~\$40-50/month for cache.t3.medium in eu-west-1"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Update ECS Task Definition:"
echo "   aws ecs describe-task-definition --task-definition weather-proxy \\\"
echo "     --query 'taskDefinition' > task-def.json"
echo ""
echo "2. Update environment variables in task-def.json:"
echo "   REDIS_HOST: $REDIS_ENDPOINT"
echo "   REDIS_PORT: $REDIS_PORT"
echo "   REDIS_PASSWORD: (reference Secret ARN)"
echo ""
echo "3. Add to GitHub Secrets:"
echo "   ELASTICACHE_CLUSTER_ID: $CLUSTER_ID"
echo ""
echo "4. Test connection:"
echo "   redis-cli -h $REDIS_ENDPOINT -p $REDIS_PORT --tls -a <password>"
echo ""
echo "🔗 AWS Console:"
echo "https://$AWS_REGION.console.aws.amazon.com/elasticache/home?region=$AWS_REGION#/redis/$CLUSTER_ID"
echo ""

# Save to file
cat > elasticache-config.txt << EOF
# ElastiCache Configuration
REDIS_HOST=$REDIS_ENDPOINT
REDIS_PORT=$REDIS_PORT
REDIS_DB=0
REDIS_PASSWORD=<stored-in-secrets-manager>

# Secrets Manager
SECRET_ARN=$SECRET_ARN

# Cluster Details
CLUSTER_ID=$CLUSTER_ID
REGION=$AWS_REGION
SECURITY_GROUP=$SG_ID

# GitHub Secret (add this to repository secrets)
ELASTICACHE_CLUSTER_ID=$CLUSTER_ID
EOF

print_success "Configuration saved to: elasticache-config.txt"
echo ""
print_warning "⚠️  IMPORTANT: Add ELASTICACHE_CLUSTER_ID to GitHub repository secrets!"
