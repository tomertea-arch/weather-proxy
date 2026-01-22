# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies including Redis server and client
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    redis-server \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security (best practice for Fargate)
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /data/redis && \
    chown -R appuser:appuser /app /data/redis

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port (Fargate will map this)
EXPOSE 8000

# Health check for Fargate
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use entrypoint script to start Redis (if needed) and the application
# The script will:
# - Start embedded Redis if REDIS_HOST is not provided
# - Start FastAPI with uvicorn with graceful shutdown support
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
