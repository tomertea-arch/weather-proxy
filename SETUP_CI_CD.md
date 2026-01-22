# Setting Up CI/CD with GitHub Actions

## 🎯 Overview

When you push code to GitHub, the CI/CD pipeline will **automatically**:
1. Lint your code
2. Run all tests
3. Build Docker image
4. Push to Docker Hub & GitHub Container Registry (on main branch)
5. Scan for security vulnerabilities
6. Deploy to AWS Fargate (on main branch)

## 📋 Prerequisites

- GitHub repository created
- Git configured locally
- Docker Hub account (for pushing images)
- AWS account with ECS/Fargate setup (for deployment, optional)

---

## 🚀 Step 1: Commit and Push the CI/CD Configuration

The CI/CD configuration is already created. Now commit and push it:

```bash
cd /home/admin/tomer/weather-proxy

# Verify staged files
git status

# Commit the CI/CD configuration
git commit -m "Add CI/CD pipeline with GitHub Actions

- Add GitHub Actions workflow for automated testing and building
- Implement linting with flake8, black, and pylint
- Add test suite execution with coverage reporting
- Configure Docker multi-stage build and security scanning
- Add automated Docker push to Docker Hub and GHCR
- Include comprehensive CI/CD documentation"

# Push to GitHub
git push origin main
```

**That's it!** The CI/CD pipeline will automatically start running.

---

## 🔐 Step 2: Configure Secrets

For the pipeline to **push Docker images** and **deploy to AWS**, you need to add secrets to GitHub.

### 2.1 Create Docker Hub Access Token

1. Go to [Docker Hub](https://hub.docker.com/)
2. Click your profile → **Account Settings**
3. Go to **Security** → **New Access Token**
4. Name: `github-actions-weather-proxy`
5. Permissions: **Read, Write, Delete**
6. Click **Generate** and **copy the token**

### 2.2 Create AWS IAM User (Optional - for AWS deployment)

1. Go to [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Click **Users** → **Create user**
3. Username: `github-actions-weather-proxy`
4. Select **Programmatic access**
5. Attach the following policies:
   - `AmazonEC2ContainerRegistryPowerUser`
   - `AmazonECS_FullAccess`
   - `AmazonElasticLoadBalancingReadOnly`
6. Click **Create user** and **copy the credentials**

### 2.3 Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**

Add these secrets:

| Name | Value | Required For | Example |
|------|-------|--------------|---------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username | Docker push | `tomertea` |
| `DOCKERHUB_TOKEN` | The access token you generated | Docker push | `dckr_pat_abc123...` |
| `AWS_ACCESS_KEY_ID` | AWS IAM user access key | AWS deployment | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM user secret key | AWS deployment | `wJalrXUtnFEMI/...` |

**Screenshot locations:**
- GitHub: `https://github.com/YOUR_USERNAME/weather-proxy/settings/secrets/actions`

**Note:** AWS secrets are only required if you want automatic deployment to AWS Fargate. See [AWS_FARGATE_DEPLOYMENT.md](AWS_FARGATE_DEPLOYMENT.md) for infrastructure setup.

---

## ☁️ Step 3: Set Up AWS Fargate Infrastructure (Optional)

If you want automatic deployment to AWS Fargate, you need to set up the infrastructure first.

### 3.1 Prerequisites

Before the CI/CD can deploy to AWS, you must manually create:
- ECS Cluster: `weather-proxy-cluster`
- ECS Service: `weather-proxy-service-alb`
- ECR Repository: `weather-proxy`
- Task Definition: `weather-proxy`
- Application Load Balancer (recommended)

### 3.2 Quick Setup Using AWS CLI

```bash
# Set your AWS region
export AWS_REGION=us-east-1

# Create ECR repository
aws ecr create-repository \
    --repository-name weather-proxy \
    --region $AWS_REGION

# Create ECS cluster
aws ecs create-cluster \
    --cluster-name weather-proxy-cluster \
    --region $AWS_REGION

# Follow the detailed guide for complete setup
```

### 3.3 Complete Setup Guide

For detailed infrastructure setup, see:
- **[AWS_FARGATE_DEPLOYMENT.md](AWS_FARGATE_DEPLOYMENT.md)** - Complete deployment guide
  - Step-by-step AWS infrastructure setup
  - Task definitions
  - Load balancer configuration
  - Monitoring and scaling

**Important:** The CI/CD pipeline expects these resources to exist:
- ECR repository: `weather-proxy`
- ECS cluster: `weather-proxy-cluster`
- ECS service: `weather-proxy-service-alb`
- Task definition: `weather-proxy`

You can customize these names by editing the `env` section in `.github/workflows/ci.yml`:

```yaml
env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: weather-proxy
  ECS_CLUSTER: weather-proxy-cluster
  ECS_SERVICE: weather-proxy-service-alb
  CONTAINER_NAME: weather-proxy
```

### 3.4 Verify Infrastructure

Before enabling CI/CD deployment, verify your infrastructure:

```bash
# Check ECR repository exists
aws ecr describe-repositories --repository-names weather-proxy

# Check ECS cluster exists
aws ecs describe-clusters --clusters weather-proxy-cluster

# Check ECS service exists
aws ecs describe-services \
  --cluster weather-proxy-cluster \
  --services weather-proxy-service-alb

# Check task definition exists
aws ecs describe-task-definition --task-definition weather-proxy
```

All commands should return details without errors.

---

## 👀 Step 4: View the Pipeline Running

### From GitHub Web Interface

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. You'll see your workflow running (or completed)

**Example URL:**
```
https://github.com/YOUR_USERNAME/weather-proxy/actions
```

### Pipeline Stages Visualization

```
┌─────────┐
│  Lint   │  (1-2 min)
└────┬────┘
     │
┌────▼────┐
│  Test   │  (3-5 min) - Runs in parallel for Python 3.10 & 3.11
└────┬────┘
     │
┌────▼────────┐
│ Docker Build│  (2-4 min)
└────┬────────┘
     │
     ├──────────┬──────────────┐
     │          │              │
┌────▼─────┐ ┌─▼───────────┐  │
│Security  │ │Docker Push  │  │ (Only on main branch)
│  Scan    │ │(Main only)  │  │
└──────────┘ └──────┬──────┘  │
                    │
                ┌───▼────────────┐
                │ Deploy Fargate │ (Only on main branch)
                │  (AWS ECS)     │
                └────────────────┘
```

**Total Time: ~13-20 minutes (including AWS deployment)**

---

## 🎬 Step 5: Verify Docker Image Was Built

### Check GitHub Actions Logs

1. Go to **Actions** tab
2. Click on the latest workflow run
3. Expand **Docker Build** job
4. Look for: ✅ "Build Docker image" step

### Check Docker Hub (if secrets configured)

1. Go to [Docker Hub](https://hub.docker.com/)
2. Navigate to **Repositories**
3. Find `weather-proxy` repository
4. You should see tags like:
   - `latest`
   - `main-abc1234` (branch-commit)

### Check GitHub Container Registry

1. Go to your GitHub profile
2. Click **Packages**
3. Find `weather-proxy`
4. View available tags

**Direct URL:**
```
https://github.com/YOUR_USERNAME?tab=packages
```

---

## 🔄 How It Works: Triggers

The CI/CD pipeline runs automatically when:

### ✅ Push Events
```bash
# Push to main branch → Full pipeline + Docker push
git push origin main

# Push to develop branch → Full pipeline (no push)
git push origin develop

# Push to feature branch → No pipeline (unless configured)
git push origin feature/my-feature
```

### ✅ Pull Request Events
```bash
# Create PR to main/develop → Full pipeline runs
gh pr create --base main --head feature/my-feature

# Every commit to PR → Pipeline re-runs
git push origin feature/my-feature
```

### 🛑 What Does NOT Trigger
- Pushes to other branches (unless you modify the workflow)
- Local commits (not pushed)
- Manual file changes on GitHub (will trigger on save)

---

## ☁️ Step 6: Verify AWS Deployment (Optional)

If you configured AWS secrets and infrastructure, verify the deployment:

### From GitHub Actions

1. Go to **Actions** tab
2. Click on the latest workflow run (main branch)
3. Expand **Deploy to AWS Fargate** job
4. Look for: ✅ "Deploy Amazon ECS task definition"
5. Check deployment status and Load Balancer URL

### From AWS Console

1. Go to [ECS Console](https://console.aws.amazon.com/ecs/)
2. Click your cluster: `weather-proxy-cluster`
3. Click service: `weather-proxy-service-alb`
4. Verify:
   - **Desired count** = **Running count**
   - **Health status**: Healthy
   - Latest deployment is **PRIMARY**

### Test the Deployed Application

```bash
# Get Load Balancer DNS from AWS
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?contains(LoadBalancerName, 'weather-proxy')].DNSName" \
  --output text)

echo "Application URL: http://$ALB_DNS"

# Test health endpoint
curl http://$ALB_DNS/health

# Test weather endpoint
curl "http://$ALB_DNS/weather?city=London"
```

### View Deployment Logs

```bash
# View ECS service events
aws ecs describe-services \
  --cluster weather-proxy-cluster \
  --services weather-proxy-service-alb \
  --query "services[0].events[0:5]"

# View container logs
aws logs tail /ecs/weather-proxy --follow
```

---

## 📊 Step 7: Add Status Badge to README

Show the world your builds are passing! Add this to your README.md:

```markdown
![CI Pipeline](https://github.com/YOUR_USERNAME/weather-proxy/actions/workflows/ci.yml/badge.svg)
```

Replace `YOUR_USERNAME` with your GitHub username.

**Example:**
```markdown
![CI Pipeline](https://github.com/tomertea-arch/weather-proxy/actions/workflows/ci.yml/badge.svg)
```

It will show:
- ✅ **Green badge** when passing
- ❌ **Red badge** when failing
- 🟡 **Yellow badge** when running

---

## 🐛 Troubleshooting

### Pipeline Not Starting

**Problem:** Pushed code but no Actions workflow running

**Solutions:**
1. Check the **Actions** tab is enabled:
   - Go to: `Settings` → `Actions` → `General`
   - Enable "Allow all actions and reusable workflows"
   
2. Verify file path is correct:
   ```bash
   ls -la .github/workflows/ci.yml
   # Should exist
   ```

3. Check YAML syntax:
   ```bash
   # Install yamllint
   pip install yamllint
   
   # Validate workflow file
   yamllint .github/workflows/ci.yml
   ```

---

### Docker Push Failing

**Problem:** Pipeline fails at "Docker Push" stage

**Solutions:**

1. **Check secrets are configured:**
   - Go to: `Settings` → `Secrets and variables` → `Actions`
   - Verify both `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` exist

2. **Token permissions:**
   - Regenerate token with `Read, Write, Delete` permissions
   - Update `DOCKERHUB_TOKEN` secret

3. **Username mismatch:**
   - Ensure `DOCKERHUB_USERNAME` exactly matches your Docker Hub username (case-sensitive)

4. **Repository doesn't exist:**
   - Go to Docker Hub and create `weather-proxy` repository manually
   - Or: Enable "Auto-create repository" in Docker Hub settings

---

### Tests Failing in CI but Passing Locally

**Problem:** Tests pass on your machine but fail in GitHub Actions

**Solutions:**

1. **Redis not available:**
   - The workflow already includes Redis service
   - Check service health in logs

2. **Environment differences:**
   ```bash
   # Test with same Python version as CI
   python3.11 -m pytest -v
   
   # Test with fresh environment
   python3 -m venv test_env
   source test_env/bin/activate
   pip install -r requirements.txt
   pytest -v
   ```

3. **Async issues:**
   - Some tests have known async mocking issues
   - These are pre-existing and acknowledged

---

### AWS Deployment Failing

**Problem:** "Deploy to AWS Fargate" job fails

**Solutions:**

1. **Check AWS credentials:**
   - Go to: `Settings` → `Secrets and variables` → `Actions`
   - Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` exist
   - Test credentials locally:
     ```bash
     aws sts get-caller-identity
     ```

2. **Infrastructure doesn't exist:**
   - Error: `ServiceNotFoundException` or `ClusterNotFoundException`
   - Solution: Follow [AWS_FARGATE_DEPLOYMENT.md](AWS_FARGATE_DEPLOYMENT.md) to create infrastructure
   - Required resources:
     - ECR repository: `weather-proxy`
     - ECS cluster: `weather-proxy-cluster`
     - ECS service: `weather-proxy-service-alb`

3. **IAM permissions insufficient:**
   - Error: `AccessDeniedException`
   - Solution: Attach required policies to IAM user:
     - `AmazonEC2ContainerRegistryPowerUser`
     - `AmazonECS_FullAccess`
     - `AmazonElasticLoadBalancingReadOnly`

4. **Task definition issues:**
   - Error: Task definition download fails
   - Solution: Ensure task definition `weather-proxy` exists:
     ```bash
     aws ecs describe-task-definition --task-definition weather-proxy
     ```

5. **Service update timeout:**
   - Error: Deployment takes too long
   - Check ECS service events for issues:
     ```bash
     aws ecs describe-services \
       --cluster weather-proxy-cluster \
       --services weather-proxy-service-alb
     ```
   - Common causes:
     - Health checks failing
     - Insufficient resources
     - Security group misconfiguration

6. **Skip AWS deployment temporarily:**
   - If you want to disable AWS deployment while fixing issues
   - Comment out the `deploy-fargate` job in `.github/workflows/ci.yml`
   - Or remove AWS secrets to prevent the job from running

---

### Build Too Slow

**Problem:** Pipeline takes too long

**Current optimizations:**
- ✅ Pip dependency caching
- ✅ Docker layer caching
- ✅ Parallel test matrix

**Additional optimizations:**

1. **Skip security scan on PRs:**
   ```yaml
   security-scan:
     if: github.event_name == 'push' && github.ref == 'refs/heads/main'
   ```

2. **Reduce test matrix:**
   ```yaml
   strategy:
     matrix:
       python-version: ['3.11']  # Only test latest
   ```

3. **Disable multi-arch builds for PRs:**
   ```yaml
   platforms: ${{ github.event_name == 'push' && 'linux/amd64,linux/arm64' || 'linux/amd64' }}
   ```

---

## 🎓 Understanding the Workflow

### What Happens When You Push?

```bash
# 1. You push code
git push origin main

# 2. GitHub detects .github/workflows/ci.yml

# 3. GitHub Actions starts a runner (Ubuntu VM)

# 4. Runner executes workflow:
#    - Checks out your code
#    - Sets up Python 3.10 & 3.11
#    - Installs dependencies
#    - Runs linters (flake8, black, pylint)
#    - Runs tests with Redis
#    - Builds Docker image
#    - Pushes to registries (if main branch)
#    - Scans for vulnerabilities

# 5. You get notification (email/GitHub)

# 6. Badge updates (✅ or ❌)
```

### Where Does It Run?

- **GitHub-hosted runners**: Ubuntu Linux VM
- **Free tier**: 2,000 minutes/month for private repos
- **Public repos**: Unlimited minutes

### What Can It Access?

- ✅ Your repository code
- ✅ GitHub secrets (DOCKERHUB_TOKEN, etc.)
- ✅ Internet (for pip, Docker Hub, etc.)
- ✅ Docker daemon
- ❌ Your local machine

---

## 🔒 Security Best Practices

### ✅ DO:
- Use access tokens, not passwords
- Store credentials in GitHub Secrets
- Limit token permissions
- Rotate tokens regularly (every 90 days)
- Enable branch protection rules

### ❌ DON'T:
- Commit tokens/passwords to git
- Use personal passwords as secrets
- Give tokens unnecessary permissions
- Share tokens in logs or comments

---

## 📝 Next Steps

1. **Commit and push the CI/CD configuration** (Step 1)
2. **Watch the Actions tab** to see it run
3. **Add Docker Hub secrets** (Step 2) for automated pushing
4. **Add status badge** to README (Step 5)
5. **Set up branch protection** (Settings → Branches → Add rule)
   - Require status checks to pass before merging
   - Require pull request reviews

---

## 🎉 Success Checklist

After setup, you should have:

- [ ] CI/CD configuration pushed to GitHub
- [ ] Actions tab shows successful workflow run
- [ ] All jobs completed: Lint, Test, Docker Build, Docker Push, Security Scan
- [ ] Docker image visible in Docker Hub or GHCR
- [ ] Status badge added to README
- [ ] Team can see build status
- [ ] (Optional) AWS Fargate deployment successful
- [ ] (Optional) Application accessible via AWS Load Balancer

---

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/marketplace/actions/build-and-push-docker-images)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [CI_CD.md](CI_CD.md) - Comprehensive CI/CD guide

---

## 💡 Pro Tips

1. **Use `act` for local testing:**
   ```bash
   brew install act  # macOS
   act -j test  # Run test job locally
   ```

2. **Re-run failed jobs:**
   - Go to Actions → Click workflow → "Re-run failed jobs"

3. **Cancel redundant runs:**
   - Add to workflow:
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```

4. **Debug with SSH:**
   - Use [action-tmate](https://github.com/mxschmitt/action-tmate) for interactive debugging

---

**Questions?** Check [CI_CD.md](CI_CD.md) for more details!
