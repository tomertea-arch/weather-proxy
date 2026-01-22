# CI/CD Pipeline Documentation

## Overview

This project uses **GitHub Actions** for continuous integration and deployment. The pipeline automatically runs on every push and pull request to ensure code quality, test coverage, and successful Docker builds.

## Pipeline Stages

### 1. **Linting** 🔍

Runs multiple code quality checks:

- **flake8**: Python syntax errors and code style
- **black**: Code formatting verification
- **pylint**: Static code analysis

**Trigger**: On every push and PR
**Duration**: ~1-2 minutes

#### Running Locally

```bash
# Install linting tools
pip install flake8 black pylint

# Run flake8
flake8 . --exclude=venv,.venv,__pycache__,.git

# Run black (check only)
black --check --exclude='venv|.venv|__pycache__|.git' .

# Run black (auto-format)
black --exclude='venv|.venv|__pycache__|.git' .

# Run pylint
pylint main.py test_main.py test_integration.py
```

---

### 2. **Testing** 🧪

Runs comprehensive test suite with multiple Python versions:

- **Python Versions**: 3.10, 3.11
- **Redis Service**: Automatically provisioned for integration tests
- **Coverage**: Generates code coverage reports
- **Tests**:
  - Unit tests (`test_main.py`)
  - Integration tests (`test_integration.py`)

**Trigger**: After successful linting
**Duration**: ~3-5 minutes per Python version

#### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run unit tests with coverage
pytest test_main.py -v --cov=main --cov-report=term --cov-report=html

# Run integration tests
pytest test_integration.py -v

# Run all tests
pytest -v --cov=main --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

### 3. **Docker Build** 🐳

Builds and tests the Docker image:

- **Build**: Creates optimized Docker image
- **Cache**: Uses GitHub Actions cache for faster builds
- **Test**: Verifies container starts and health endpoint responds
- **Artifact**: Uploads image for downstream jobs

**Trigger**: After successful tests
**Duration**: ~2-4 minutes

#### Running Locally

```bash
# Build Docker image
docker build -t weather-proxy:local .

# Run container
docker run -d --name weather-proxy-test -p 8000:8000 weather-proxy:local

# Test health endpoint
curl http://localhost:8000/health

# Check logs
docker logs weather-proxy-test

# Stop and remove
docker stop weather-proxy-test
docker rm weather-proxy-test
```

---

### 4. **Docker Push** 📦

Pushes Docker image to registries (only on main branch):

- **Docker Hub**: `username/weather-proxy`
- **GitHub Container Registry**: `ghcr.io/username/weather-proxy`
- **Tags**:
  - `latest` (main branch only)
  - `<branch-name>-<sha>` (e.g., `main-abc1234`)
  - Semantic versions (if tagged)

**Trigger**: On push to `main` branch only
**Duration**: ~3-5 minutes
**Requirements**: 
- `DOCKERHUB_USERNAME` secret
- `DOCKERHUB_TOKEN` secret

#### Multi-Architecture Support

The pipeline builds for both:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM, Apple Silicon)

---

### 5. **Security Scan** 🔒

Scans Docker image for vulnerabilities:

- **Tool**: Trivy vulnerability scanner
- **Severity**: Checks for CRITICAL, HIGH, MEDIUM issues
- **Output**: 
  - SARIF format (uploaded to GitHub Security tab)
  - Table format (visible in logs)

**Trigger**: After Docker build
**Duration**: ~2-3 minutes

#### Running Locally

```bash
# Install Trivy
# macOS
brew install trivy

# Linux
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy

# Scan Docker image
trivy image weather-proxy:local

# Scan with specific severity
trivy image --severity CRITICAL,HIGH weather-proxy:local
```

---

## CI Workflow File

Location: `.github/workflows/ci.yml`

### Jobs Overview

```
lint → test → docker-build → [docker-push, security-scan]
                              (main branch only)
                                     ↓
                              deploy-fargate
                              (main branch only)
```

### Triggers

- **Push**: `main`, `develop` branches
- **Pull Request**: Targeting `main`, `develop` branches
- **AWS Deployment**: Only on `main` branch pushes

---

## Required Secrets

Configure these in GitHub Settings → Secrets and variables → Actions:

| Secret | Description | Required For |
|--------|-------------|--------------|
| `DOCKERHUB_USERNAME` | Docker Hub username | Docker push |
| `DOCKERHUB_TOKEN` | Docker Hub access token | Docker push |
| `AWS_ACCESS_KEY_ID` | AWS access key ID | AWS Fargate deployment |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | AWS Fargate deployment |
| `GITHUB_TOKEN` | Auto-provided by GitHub | GHCR push |

### Setting up Docker Hub Token

1. Go to [Docker Hub](https://hub.docker.com/)
2. Account Settings → Security → New Access Token
3. Copy token and add to GitHub Secrets as `DOCKERHUB_TOKEN`
4. Add your Docker Hub username as `DOCKERHUB_USERNAME`

### Setting up AWS Credentials

1. Create IAM user with programmatic access
2. Attach policies:
   - `AmazonEC2ContainerRegistryPowerUser`
   - `AmazonECS_FullAccess`
   - `AmazonElasticLoadBalancingReadOnly`
3. Copy Access Key ID → Add as `AWS_ACCESS_KEY_ID` secret
4. Copy Secret Access Key → Add as `AWS_SECRET_ACCESS_KEY` secret

---

## Status Badges

Add to README.md:

```markdown
![CI Pipeline](https://github.com/username/weather-proxy/actions/workflows/ci.yml/badge.svg)
```

---

## Performance Optimization

The pipeline uses several optimizations:

1. **Pip Caching**: Python dependencies are cached between runs
2. **Docker Layer Caching**: Uses GitHub Actions cache for faster builds
3. **Parallel Jobs**: Test matrix runs Python 3.10 and 3.11 in parallel
4. **Artifact Reuse**: Docker image is built once and reused across jobs

**Typical Full Pipeline Duration**: 8-12 minutes

---

## Troubleshooting

### Linting Failures

**Issue**: Black formatting errors
```bash
# Auto-fix locally
black --exclude='venv|.venv|__pycache__|.git' .
git add .
git commit -m "Apply black formatting"
```

**Issue**: Flake8 errors
- Check the error message and fix the specific line
- Most common: line too long, unused imports, undefined variables

---

### Test Failures

**Issue**: Redis connection errors in tests
```bash
# Ensure Redis is running locally
docker run -d -p 6379:6379 redis:7-alpine

# Or use embedded Redis
unset REDIS_HOST
pytest
```

**Issue**: Async mocking issues
- These are known issues in `test_weather_fresh_data_no_cache` and `test_weather_cache_read_error`
- Integration tests pass and cover the same functionality

---

### Docker Build Failures

**Issue**: Build context too large
```bash
# Check .dockerignore includes:
echo "venv/" >> .dockerignore
echo ".venv/" >> .dockerignore
echo "*.log" >> .dockerignore
echo "__pycache__/" >> .dockerignore
```

**Issue**: Container health check fails
```bash
# Check logs
docker logs <container-id>

# Verify Redis is starting (if using embedded)
docker exec <container-id> redis-cli ping

# Check application logs
docker exec <container-id> cat /app/weather-proxy.log
```

---

### Docker Push Failures

**Issue**: Authentication failed
- Verify `DOCKERHUB_USERNAME` matches your Docker Hub username exactly
- Regenerate `DOCKERHUB_TOKEN` and update GitHub secret
- Ensure token has write permissions

**Issue**: Multi-architecture build timeout
- This is usually temporary
- Re-run the job or reduce platforms to just `linux/amd64`

---

## Local CI Simulation

Run the entire CI pipeline locally using `act`:

```bash
# Install act
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash  # Linux

# Run all jobs
act

# Run specific job
act -j test

# Run with secrets
act -s DOCKERHUB_USERNAME=myusername -s DOCKERHUB_TOKEN=mytoken
```

---

### 6. **AWS Fargate Deployment** ☁️

Automatically deploys to AWS Fargate on successful builds:

- **ECR Push**: Builds and pushes image to Amazon ECR
- **Task Definition Update**: Updates ECS task definition with new image
- **Service Deployment**: Deploys to Fargate with zero-downtime
- **Status Check**: Verifies deployment and reports load balancer URL

**Trigger**: On push to `main` branch only (after docker-push succeeds)
**Duration**: ~5-8 minutes
**Requirements**:
- `AWS_ACCESS_KEY_ID` secret
- `AWS_SECRET_ACCESS_KEY` secret
- Existing ECS cluster and service (see AWS_FARGATE_DEPLOYMENT.md)

#### Running Deployment Manually

```bash
# Configure AWS CLI
aws configure

# Build and push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker build -t weather-proxy:latest .
docker tag weather-proxy:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/weather-proxy:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/weather-proxy:latest

# Update ECS service
aws ecs update-service \
  --cluster weather-proxy-cluster \
  --service weather-proxy-service-alb \
  --force-new-deployment
```

---

## Future Enhancements

Potential improvements to the CI/CD pipeline:

1. **Environment-Specific Deployments**
   - Deploy to staging environment on PR
   - Deploy to production on release tags
   - Blue-green deployment strategy

2. **Advanced Testing**
   - Performance/load testing with Locust or K6
   - End-to-end tests with real external APIs (staging only)
   - Mutation testing with `mutmut`

3. **Code Quality Gates**
   - Minimum code coverage threshold (e.g., 80%)
   - Complexity analysis with `radon`
   - Dependency vulnerability scanning with `safety`

4. **Monitoring Integration**
   - Post-deployment smoke tests
   - Automatic rollback on health check failures
   - Slack/Discord notifications

5. **Release Automation**
   - Semantic versioning with conventional commits
   - Automatic changelog generation
   - GitHub Releases with release notes

---

## Best Practices

1. **Always run tests locally before pushing**
   ```bash
   pytest -v && docker build -t weather-proxy:test .
   ```

2. **Keep CI fast** - Target < 10 minutes total runtime

3. **Fix broken builds immediately** - Don't push more changes on top

4. **Use feature branches** - Don't push directly to main

5. **Keep secrets secure** - Never commit tokens or passwords

6. **Monitor CI costs** - GitHub Actions minutes are limited on free tier

7. **Update dependencies regularly** - Run `pip list --outdated` monthly

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Pytest Documentation](https://docs.pytest.org/)
- [Trivy Vulnerability Scanner](https://github.com/aquasecurity/trivy)
