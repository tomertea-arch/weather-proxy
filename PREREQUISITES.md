# Prerequisites for Deployment

Complete checklist of prerequisites before deploying Weather Proxy to AWS.

## ✅ Required Steps (Before GitHub Actions)

### 1. AWS CLI Installed and Configured

```bash
# Check if AWS CLI is installed
aws --version

# If not installed:
# Linux/macOS
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS CLI
aws configure
# Enter:
#   AWS Access Key ID: YOUR_ACCESS_KEY
#   AWS Secret Access Key: YOUR_SECRET_KEY
#   Default region name: eu-west-1
#   Default output format: json

# Verify
aws sts get-caller-identity
```

### 2. Create ECR Repository

**Run this script BEFORE pushing to GitHub:**

```bash
cd scripts
./setup-ecr.sh
```

This creates:
- ✅ ECR repository named `weather-proxy`
- ✅ Image scanning enabled
- ✅ Encryption enabled (AES256)
- ✅ Lifecycle policy (keeps last 10 images)

**Output:**
```
✓ ECR repository created: 903224468564.dkr.ecr.eu-west-1.amazonaws.com/weather-proxy
```

### 3. Configure GitHub Secrets

Go to: **GitHub → Settings → Secrets and variables → Actions → New repository secret**

Add these **3 secrets**:

| Secret Name | Value | Where to Get |
|-------------|-------|--------------|
| `AWS_ACCESS_KEY_ID` | Your AWS access key | IAM Console → Users → Security credentials |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key | IAM Console → Users → Security credentials |
| `ELASTICACHE_CLUSTER_ID` | `weather-proxy-redis` | After running `create-elasticache.sh` |

**How to create AWS access keys:**
```bash
# Via CLI (creates for current user)
aws iam create-access-key --user-name YOUR_USERNAME

# Via Console:
# AWS Console → IAM → Users → YOUR_USER → Security credentials → Create access key
```

### 4. (Optional) Create ElastiCache Cluster

**Note:** This can be done after first deployment if you want to use embedded Redis initially.

```bash
cd scripts
./create-elasticache.sh
```

Then add the cluster ID to GitHub secrets:
- `ELASTICACHE_CLUSTER_ID` = `weather-proxy-redis`

## 🔍 Verification Checklist

Before pushing to GitHub, verify:

- [ ] AWS CLI installed: `aws --version`
- [ ] AWS credentials configured: `aws sts get-caller-identity`
- [ ] ECR repository exists: `aws ecr describe-repositories --repository-names weather-proxy --region eu-west-1`
- [ ] GitHub secrets configured (at least AWS credentials)
- [ ] (Optional) ElastiCache cluster created

## 🚨 Common Issues

### Issue: "aws: command not found"

**Solution:** Install AWS CLI (see step 1 above)

### Issue: "Unable to locate credentials"

**Solution:**
```bash
aws configure
# Enter your AWS credentials
```

### Issue: "Repository does not exist in the registry"

**Solution:** Run the ECR setup script:
```bash
cd scripts
./setup-ecr.sh
```

### Issue: "Access Denied"

**Solution:** Verify your IAM user has these permissions:
- `AmazonEC2ContainerRegistryFullAccess`
- `AmazonECS_FullAccess`
- `ElastiCacheFullAccess` (if using ElastiCache)

## 📋 IAM Permissions Required

Your AWS user needs these permissions for deployment:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:*",
        "ecs:*",
        "elasticache:*",
        "ec2:*",
        "elasticloadbalancing:*",
        "iam:PassRole",
        "logs:*",
        "secretsmanager:*"
      ],
      "Resource": "*"
    }
  ]
}
```

**Recommended:** Use AWS managed policies:
- `AmazonEC2ContainerRegistryFullAccess`
- `AmazonECS_FullAccess`
- `AmazonElastiCacheFullAccess`

## 🎯 Quick Setup (All Prerequisites)

Run these commands in order:

```bash
# 1. Configure AWS CLI
aws configure

# 2. Create ECR repository
cd scripts
./setup-ecr.sh

# 3. (Optional) Create ElastiCache
./create-elasticache.sh

# 4. Configure GitHub secrets (manually in GitHub UI)
# AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY
# ELASTICACHE_CLUSTER_ID (if using ElastiCache)

# 5. Now you can push to GitHub!
cd ..
git push origin main
```

## ✅ Post-Setup Verification

After setup, verify everything is ready:

```bash
# Check ECR repository
aws ecr describe-repositories \
  --repository-names weather-proxy \
  --region eu-west-1

# Check ElastiCache (if created)
aws elasticache describe-cache-clusters \
  --cache-cluster-id weather-proxy-redis \
  --region eu-west-1

# Verify GitHub can access AWS (after adding secrets)
# Push a commit and check GitHub Actions tab
```

## 🚀 Ready to Deploy

Once all prerequisites are complete:

1. Commit your code: `git add . && git commit -m "Deploy to AWS"`
2. Push to GitHub: `git push origin main`
3. Watch GitHub Actions: GitHub → Actions tab
4. Monitor deployment progress

## 📚 Related Documentation

- **Quick Start**: [QUICK_START_ELASTICACHE.md](QUICK_START_ELASTICACHE.md)
- **Full Setup**: [ELASTICACHE_SETUP.md](ELASTICACHE_SETUP.md)
- **Deployment Summary**: [DEPLOYMENT_SUMMARY.txt](DEPLOYMENT_SUMMARY.txt)

---

**Need help?** If you're stuck, check:
1. AWS CLI is configured: `aws sts get-caller-identity`
2. ECR repository exists: `aws ecr describe-repositories --repository-names weather-proxy --region eu-west-1`
3. GitHub secrets are set: GitHub → Settings → Secrets
