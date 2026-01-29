# Fix: ECR Repository Not Found Error

## ❌ The Error

```
name unknown: The repository with name 'weather-proxy' does not exist 
in the registry with id '903224468564'
Error: Process completed with exit code 1.
```

## ✅ The Solution

The ECR repository needs to be created **before** GitHub Actions can push images to it.

### Quick Fix (2 minutes)

**Step 1: Create ECR Repository**

```bash
# Run this command in your terminal:
cd scripts
./setup-ecr.sh
```

**OR manually via AWS CLI:**

```bash
aws ecr create-repository \
  --repository-name weather-proxy \
  --region eu-west-1 \
  --image-scanning-configuration scanOnPush=true
```

**OR via AWS Console:**
1. Go to: https://eu-west-1.console.aws.amazon.com/ecr/repositories
2. Click "Create repository"
3. Name: `weather-proxy`
4. Enable "Scan on push"
5. Click "Create repository"

**Step 2: Re-run GitHub Actions**

```bash
# Make a small change and push again
git commit --allow-empty -m "Trigger deployment after ECR setup"
git push origin main
```

**OR manually trigger:**
- GitHub → Actions → Select workflow → "Re-run all jobs"

## 🔍 Why This Happens

GitHub Actions tries to push your Docker image to ECR (Elastic Container Registry), but the repository doesn't exist yet. This is a **one-time setup** that needs to happen before the first deployment.

## ✅ Verification

After running the setup script, verify the repository exists:

```bash
aws ecr describe-repositories \
  --repository-names weather-proxy \
  --region eu-west-1
```

Expected output:
```json
{
    "repositories": [
        {
            "repositoryName": "weather-proxy",
            "repositoryUri": "903224468564.dkr.ecr.eu-west-1.amazonaws.com/weather-proxy",
            "registryId": "903224468564"
        }
    ]
}
```

## 📋 Complete Setup Checklist

To avoid similar issues, make sure you've done these steps:

- [ ] **AWS CLI configured**: `aws configure`
- [ ] **ECR repository created**: `./scripts/setup-ecr.sh`
- [ ] **GitHub secrets set**:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `ELASTICACHE_CLUSTER_ID` (optional initially)

## 🚀 After Fix

Once the ECR repository is created:

1. **GitHub Actions will succeed** and:
   - ✅ Build Docker image
   - ✅ Push to ECR
   - ✅ Deploy to ECS

2. **Monitor progress**:
   - GitHub → Actions tab
   - Watch the workflow run

3. **Verify deployment**:
   ```bash
   # Check image in ECR
   aws ecr describe-images \
     --repository-name weather-proxy \
     --region eu-west-1
   ```

## 💡 Pro Tip

Run the complete prerequisites setup to avoid all issues:

```bash
# One-time setup
cd scripts
./setup-ecr.sh                # Creates ECR repository
./create-elasticache.sh       # Creates ElastiCache (optional)

# Configure GitHub secrets (manual step in GitHub UI)

# Then deploy
git push origin main
```

## 🆘 Still Getting Errors?

### Error: "Access Denied"

**Fix:** Check IAM permissions
```bash
# Your AWS user needs ECR permissions
aws iam attach-user-policy \
  --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess
```

### Error: "Invalid credentials"

**Fix:** Reconfigure AWS CLI
```bash
aws configure
# Enter your AWS Access Key ID and Secret Access Key
```

### Error: "Region not supported"

**Fix:** Make sure you're using eu-west-1
```bash
# Update GitHub workflow or ECR setup
export AWS_REGION=eu-west-1
```

## 📚 Related Documentation

- **Prerequisites Guide**: [PREREQUISITES.md](PREREQUISITES.md)
- **Quick Start**: [QUICK_START_ELASTICACHE.md](QUICK_START_ELASTICACHE.md)
- **Full Setup**: [ELASTICACHE_SETUP.md](ELASTICACHE_SETUP.md)

---

**Summary:** Run `./scripts/setup-ecr.sh` then re-trigger GitHub Actions. That's it! 🎉
