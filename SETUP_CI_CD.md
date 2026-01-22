# Setting Up CI/CD with GitHub Actions

## 🎯 Overview

When you push code to GitHub, the CI/CD pipeline will **automatically**:
1. Lint your code
2. Run all tests
3. Build Docker image
4. Push to Docker Hub & GitHub Container Registry (on main branch)
5. Scan for security vulnerabilities

## 📋 Prerequisites

- GitHub repository created
- Git configured locally
- Docker Hub account (for pushing images)

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

## 🔐 Step 2: Configure Docker Hub Secrets (Optional but Recommended)

For the pipeline to **push Docker images**, you need to add secrets to GitHub.

### 2.1 Create Docker Hub Access Token

1. Go to [Docker Hub](https://hub.docker.com/)
2. Click your profile → **Account Settings**
3. Go to **Security** → **New Access Token**
4. Name: `github-actions-weather-proxy`
5. Permissions: **Read, Write, Delete**
6. Click **Generate** and **copy the token**

### 2.2 Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**

Add these two secrets:

| Name | Value | Example |
|------|-------|---------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username | `tomertea` |
| `DOCKERHUB_TOKEN` | The access token you generated | `dckr_pat_abc123...` |

**Screenshot locations:**
- GitHub: `https://github.com/YOUR_USERNAME/weather-proxy/settings/secrets/actions`

---

## 👀 Step 3: View the Pipeline Running

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
└──────────┘ └─────────────┘  │
```

**Total Time: ~8-12 minutes**

---

## 🎬 Step 4: Verify Docker Image Was Built

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

## 📊 Step 5: Add Status Badge to README

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
- [ ] All 5 jobs completed: Lint, Test, Docker Build, Docker Push, Security Scan
- [ ] Docker image visible in Docker Hub or GHCR
- [ ] Status badge added to README
- [ ] Team can see build status

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
