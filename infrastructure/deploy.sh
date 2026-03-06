#!/usr/bin/env bash
# =============================================================================
# APEX Trading Intelligence System -- Production Deployment Script
# Usage:  bash infrastructure/deploy.sh [--skip-pull] [--no-tail]
# =============================================================================
set -euo pipefail

APP_NAME="apex-trading-system"
IMAGE_NAME="apex-trading"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
LOG_TAIL_SECONDS=30
GIT_BRANCH="main"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SKIP_PULL=false
NO_TAIL=false

for arg in "$@"; do
    case $arg in
        --skip-pull) SKIP_PULL=true ;;
        --no-tail)   NO_TAIL=true ;;
        *) echo -e "${RED}Unknown argument: $arg${NC}"; exit 1 ;;
    esac
done

log()     { echo -e "${BLUE}[$(date -u '+%H:%M:%S')]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()    { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }

echo ""
echo "============================================================"
echo "  APEX Trading System -- Deployment"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"
echo ""

log "Running pre-flight checks..."

command -v docker >/dev/null 2>&1 || fail "Docker is not installed or not in PATH."
command -v git    >/dev/null 2>&1 || fail "git is not installed."

if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    fail "Neither 'docker compose' nor 'docker-compose' found."
fi

success "Docker:         $(docker --version)"
success "Docker Compose: $($COMPOSE_CMD version --short 2>/dev/null || echo 'v1')"

[[ -f "$ENV_FILE" ]] || fail ".env file not found. Copy .env.example to .env and fill in credentials."
success ".env file found."

[[ -d "trading_system" ]] || fail "Run this script from the apex-trading-system repo root."
success "Repo root confirmed."

docker info >/dev/null 2>&1 || fail "Docker daemon is not running."
success "Docker daemon is running."
echo ""

if [[ "$SKIP_PULL" == "false" ]]; then
    log "[1/6] Pulling latest code from origin/$GIT_BRANCH..."
    git fetch origin
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse "origin/$GIT_BRANCH")
    if [[ "$LOCAL" == "$REMOTE" ]]; then
        warn "Already up to date ($(git rev-parse --short HEAD))."
    else
        git pull origin "$GIT_BRANCH"
        success "Pulled to $(git rev-parse --short HEAD)."
    fi
else
    warn "[1/6] Skipping git pull (--skip-pull)."
fi

COMMIT_SHA=$(git rev-parse --short HEAD)
echo ""

log "[2/6] Validating .env configuration..."

REQUIRED_KEYS=(
    "DHAN_CLIENT_ID"
    "DHAN_ACCESS_TOKEN"
    "REDIS_HOST"
    "KAFKA_BOOTSTRAP_SERVERS"
)

MISSING=()
for key in "${REQUIRED_KEYS[@]}"; do
    value=$(grep -E "^${key}=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs 2>/dev/null || true)
    if [[ -z "$value" || "$value" == *"your_"* ]]; then
        MISSING+=("$key")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    warn "The following .env keys appear unset or still have placeholder values:"
    for k in "${MISSING[@]}"; do warn "  - $k"; done
    warn "Continuing anyway (paper trading mode should still work)."
else
    success ".env validation passed."
fi
echo ""

log "[3/6] Creating host directories..."
mkdir -p ./logs ./data
success "Directories ready: ./logs ./data"
echo ""

log "[4/6] Building Docker image (tag: $IMAGE_NAME:$COMMIT_SHA)..."
$COMPOSE_CMD -f "$COMPOSE_FILE" build --pull app
docker tag "${IMAGE_NAME}:latest" "${IMAGE_NAME}:${COMMIT_SHA}" 2>/dev/null || true
success "Image built: ${IMAGE_NAME}:latest (${COMMIT_SHA})"
echo ""

log "[5/6] Starting services..."

$COMPOSE_CMD -f "$COMPOSE_FILE" up -d zookeeper redis
log "  Waiting for zookeeper and redis to be healthy (up to 120s)..."
timeout 120 bash -c "until $COMPOSE_CMD -f $COMPOSE_FILE ps | grep -E '(zookeeper|redis).*healthy' | wc -l | grep -q 2; do sleep 3; done" || \
    warn "  Timed out waiting for infra health checks -- continuing anyway."

$COMPOSE_CMD -f "$COMPOSE_FILE" up -d kafka
log "  Waiting for kafka to be healthy (up to 90s)..."
timeout 90 bash -c "until $COMPOSE_CMD -f $COMPOSE_FILE ps | grep kafka | grep -q healthy; do sleep 5; done" || \
    warn "  Kafka health timeout -- continuing."

$COMPOSE_CMD -f "$COMPOSE_FILE" up -d --no-deps --build app

success "All services started."
echo ""

if [[ "$NO_TAIL" == "false" ]]; then
    log "[6/6] Tailing app logs for ${LOG_TAIL_SECONDS}s..."
    echo "  (Press Ctrl+C to stop tailing -- deployment is already complete)"
    echo "  ----------------------------------------------------------------"
    timeout "$LOG_TAIL_SECONDS" $COMPOSE_CMD -f "$COMPOSE_FILE" logs -f app 2>/dev/null || true
    echo "  ----------------------------------------------------------------"
else
    log "[6/6] Skipping log tail (--no-tail)."
fi

echo ""
log "Running final health check..."
sleep 5

HTTP_STATUS=$(curl -o /dev/null -s -w "%{http_code}" --max-time 10 \
    http://localhost:8000/health 2>/dev/null || echo "000")

if [[ "$HTTP_STATUS" == "200" ]]; then
    echo ""
    echo "============================================================"
    success "APEX Trading System deployed successfully!"
    echo "  Commit:    $COMMIT_SHA"
    echo "  API:       http://localhost:8000"
    echo "  Dashboard: http://localhost:8501"
    echo "  Proxy:     http://localhost:80"
    echo "  Health:    http://localhost:8000/health  [HTTP $HTTP_STATUS]"
    echo "  Logs:      $COMPOSE_CMD logs -f app"
    echo "============================================================"
    echo ""
else
    echo ""
    echo "============================================================"
    warn "Deployment complete but health check returned HTTP $HTTP_STATUS."
    warn "The app may still be initialising (90s start period)."
    echo "  Check logs:  $COMPOSE_CMD logs app"
    echo "  Health URL:  http://localhost:8000/health"
    echo "============================================================"
    echo ""
fi
