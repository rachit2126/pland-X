# Multi-stage Dockerfile for Standalone MPP Import & Export Parser Service
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and buffer outputs
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install OpenJDK 21 JRE Headless for MPXJ/JPype
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jre-headless \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME (compatible across architectures)
ENV JAVA_HOME=/usr/lib/jvm/default-java

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY pyproject.toml setup.py ./
COPY mpp_parser ./mpp_parser
COPY fixtures ./fixtures

# Install application in editable mode
RUN pip install --no-cache-dir -e .

# Create non-root app user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["python3", "-m", "uvicorn", "mpp_parser.api:app", "--host", "0.0.0.0", "--port", "8000"]
