# APEX Trading System - Production Dockerfile
FROM python:3.11-slim

LABEL maintainer="sn-sujay" \
      description="APEX Multi-Agent AI Trading System"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    supervisor \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 apex

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY trading_system/ ./trading_system/
COPY infrastructure/supervisord.conf /etc/supervisor/conf.d/apex.conf
COPY infrastructure/nginx.conf /etc/nginx/sites-available/apex
RUN ln -sf /etc/nginx/sites-available/apex /etc/nginx/sites-enabled/apex && \
    rm -f /etc/nginx/sites-enabled/default

# Create required directories
RUN mkdir -p /var/log/apex /app/data && \
    chown -R apex:apex /var/log/apex /app/data

# Expose ports
EXPOSE 8000 8501 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

USER apex

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/apex.conf"]
