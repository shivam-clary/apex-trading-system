# =============================================================================
# APEX Trading Intelligence System -- Production Dockerfile
# Optimized for speed, caching, and small runtime images
# =============================================================================

############################
# Stage 1 — Build Wheels
############################
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib C library (required by ta-lib Python wheel)
# NOTE: parallel make (-j) causes a race condition in gen_code tool — use single-threaded build
RUN wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib \
    && wget -q -O config.guess "https://git.savannah.gnu.org/cgit/config.git/plain/config.guess" \
    && wget -q -O config.sub "https://git.savannah.gnu.org/cgit/config.git/plain/config.sub" \
    && chmod +x config.guess config.sub \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && cd .. && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Upgrade packaging tools
RUN pip install --upgrade pip setuptools wheel

# Copy dependency file first (for Docker caching)
COPY requirements.txt .

# Build wheels for all dependencies
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


############################
# Stage 2 — Runtime Image
############################
FROM python:3.11-slim AS runtime

LABEL maintainer="sn-sujay"
LABEL description="APEX Multi-Agent AI Trading System"
LABEL version="1.0.0"

WORKDIR /app

# Runtime packages only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nginx \
    supervisor \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy TA-Lib shared libraries from builder (avoids build-essential in runtime)
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
COPY --from=builder /usr/include/ta-lib /usr/include/ta-lib
RUN ldconfig

# Copy built wheels from builder
COPY --from=builder /wheels /wheels

# Install wheels
RUN pip install --no-cache-dir /wheels/*

# Create non-root user
RUN groupadd -g 1000 apex && useradd -m -u 1000 -g apex apex

# Copy application code
COPY trading_system/ ./trading_system/
COPY scripts/ ./scripts/

# nginx config
COPY infrastructure/nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/sites-enabled/default

# supervisor config
COPY infrastructure/supervisord.conf /etc/supervisor/conf.d/apex.conf

# runtime dirs + Streamlit config dir for non-root user
RUN mkdir -p \
        /app/logs \
        /app/data \
        /var/log/apex \
        /run/nginx \
        /home/apex/.streamlit && \
    chown -R apex:apex /app /home/apex/.streamlit

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    DASHBOARD_PORT=8501

EXPOSE 8000 8501 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s \
    CMD curl -fsSL http://localhost:8000/health || exit 1

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/apex.conf"]