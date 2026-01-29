#!/bin/bash

###############################################################################
# Setup AWS ECR Repository for Weather Proxy
# Run this BEFORE pushing to GitHub
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
ECR_REPO_NAME="weather-proxy"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         AWS ECR Repository Setup Script                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install it first."
    exit 1
fi

# Check credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured"
    print_info "Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_success "AWS Account: $ACCOUNT_ID"
print_success "Region: $AWS_REGION"
echo ""

# Check if repository exists
print_info "Checking if ECR repository exists..."
if aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" &>/dev/null; then
    print_warning "ECR repository '$ECR_REPO_NAME' already exists"
    ECR_URI=$(aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" --query 'repositories[0].repositoryUri' --output text)
    print_success "Repository URI: $ECR_URI"
else
    print_info "Creating ECR repository..."
    ECR_URI=$(aws ecr create-repository \
        --repository-name "$ECR_REPO_NAME" \
        --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 \
        --tags "Key=Application,Value=weather-proxy" "Key=ManagedBy,Value=github-actions" \
        --query 'repository.repositoryUri' \
        --output text)
    print_success "ECR repository created: $ECR_URI"
fi

echo ""
print_info "Setting lifecycle policy (keep last 10 images)..."
aws ecr put-lifecycle-policy \
    --repository-name "$ECR_REPO_NAME" \
    --region "$AWS_REGION" \
    --lifecycle-policy-text '{
        "rules": [
            {
                "rulePriority": 1,
                "description": "Keep last 10 images",
                "selection": {
                    "tagStatus": "any",
                    "countType": "imageCountMoreThan",
                    "countNumber": 10
                },
                "action": {
                    "type": "expire"
                }
            }
        ]
    }' &>/dev/null

print_success "Lifecycle policy set (keeps last 10 images)"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   Setup Complete! 🎉                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
print_success "ECR Repository Details:"
echo "  Name: $ECR_REPO_NAME"
echo "  URI: $ECR_URI"
echo "  Region: $AWS_REGION"
echo "  Account: $ACCOUNT_ID"
echo ""
print_info "📋 Next Steps:"
echo ""
echo "1. Configure GitHub Secrets:"
echo "   GitHub → Settings → Secrets → Actions"
echo ""
echo "   Add these secrets:"
echo "   • AWS_ACCESS_KEY_ID"
echo "   • AWS_SECRET_ACCESS_KEY"
echo "   • ELASTICACHE_CLUSTER_ID (after creating ElastiCache)"
echo ""
echo "2. (Optional) Test local Docker build and push:"
echo "   aws ecr get-login-password --region $AWS_REGION | \\"
echo "     docker login --username AWS --password-stdin $ECR_URI"
echo "   docker build -t $ECR_REPO_NAME:test ."
echo "   docker tag $ECR_REPO_NAME:test $ECR_URI:test"
echo "   docker push $ECR_URI:test"
echo ""
echo "3. Push to GitHub to trigger deployment:"
echo "   git push origin main"
echo ""
print_success "You can now run GitHub Actions workflows!"
echo ""
