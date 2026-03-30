#!/usr/bin/env bash
# =============================================================
# MCP Agent DAG Platform — Environment Setup
# =============================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="/opt/mcp-platform/venv"
ENV_FILE="${PROJECT_DIR}/.env"
DOCKER_DIR="${PROJECT_DIR}/infra/docker"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[MCP]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()  { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# docker compose wrapper: all relative paths resolve from PROJECT_DIR
dc() { docker compose --project-directory "${PROJECT_DIR}" "$@"; }

cd "${PROJECT_DIR}"

# ─── 1. Prerequisites ──────────────────────────────────────────
log "Checking prerequisites..."
command -v python3.12 >/dev/null 2>&1 || die "Python 3.12 not found."
command -v docker      >/dev/null 2>&1 || die "Docker not found."
docker compose version >/dev/null 2>&1 || die "Docker Compose plugin not found."
log "Prerequisites OK (Python $(python3.12 --version), $(docker --version))"

# ─── 2. Docker network ─────────────────────────────────────────
log "Creating Docker network mcp_network..."
if docker network inspect mcp_network >/dev/null 2>&1; then
  warn "Network mcp_network already exists — skipping."
else
  docker network create --driver bridge mcp_network
  log "Network mcp_network created."
fi

# ─── 3. Generate .env ──────────────────────────────────────────
if [[ -f "${ENV_FILE}" ]]; then
  warn ".env already exists — skipping key generation."
else
  log "Generating .env with Fernet and secret keys..."
  FERNET_KEY=$(python3.12 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())")
  SECRET_KEY=$(python3.12 -c "import secrets; print(secrets.token_hex(32))")

  cat > "${ENV_FILE}" <<EOF
# MCP Agent DAG Platform — Environment Variables
# Generated on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# !! Change all passwords before exposing to any network !!

# Airflow
AIRFLOW_FERNET_KEY=${FERNET_KEY}
AIRFLOW_SECRET_KEY=${SECRET_KEY}

# PostgreSQL — Airflow metadata (port 5432)
POSTGRES_AIRFLOW_USER=admin
POSTGRES_AIRFLOW_PASSWORD=admin
POSTGRES_AIRFLOW_DB=airflow

# PostgreSQL — Serving layer (port 5433)
POSTGRES_SERVING_USER=admin
POSTGRES_SERVING_PASSWORD=admin
POSTGRES_SERVING_DB=serving

# Redis (port 6379)
REDIS_PASSWORD=admin

# Databricks (fill in after connecting)
DATABRICKS_HOST=
DATABRICKS_TOKEN=
DATABRICKS_HTTP_PATH=
EOF
  log ".env created."
fi

# ─── 4. Python venv ────────────────────────────────────────────
log "Setting up Python venv at ${VENV_DIR}..."
if [[ -d "${VENV_DIR}" ]]; then
  warn "venv already exists at ${VENV_DIR} — skipping creation."
else
  [[ -d "$(dirname "${VENV_DIR}")" ]] || \
    die "/opt/mcp-platform not found. Run: sudo mkdir -p /opt/mcp-platform && sudo chown $(id -u):$(id -g) /opt/mcp-platform"
  python3.12 -m venv "${VENV_DIR}"
  log "venv created."
fi

log "Installing Python dependencies..."
"${VENV_DIR}/bin/pip" install --upgrade pip --quiet
"${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/requirements.txt" --quiet
log "Python dependencies installed."

# ─── 5. Start PostgreSQL ───────────────────────────────────────
log "Starting PostgreSQL (airflow + serving)..."
dc -f "${DOCKER_DIR}/docker-compose.postgres.yml" --env-file "${ENV_FILE}" up -d
log "Waiting for PostgreSQL to be healthy..."
for i in {1..30}; do
  if docker exec postgres-airflow pg_isready -U admin -d airflow -q 2>/dev/null && \
     docker exec postgres-serving pg_isready -U admin -d serving -q 2>/dev/null; then
    log "PostgreSQL is ready."; break
  fi
  [[ $i -eq 30 ]] && die "PostgreSQL did not become healthy in time."
  sleep 2
done

# ─── 6. Start Redis ────────────────────────────────────────────
log "Starting Redis..."
dc -f "${DOCKER_DIR}/docker-compose.redis.yml" --env-file "${ENV_FILE}" up -d
for i in {1..20}; do
  docker exec redis redis-cli -a admin ping 2>/dev/null | grep -q PONG && { log "Redis is ready."; break; }
  [[ $i -eq 20 ]] && die "Redis did not become healthy in time."
  sleep 2
done

# ─── 7. Start Airflow ──────────────────────────────────────────
log "Initializing Airflow (db migrate + admin user)..."
docker rm -f airflow-init 2>/dev/null || true
dc -f "${DOCKER_DIR}/docker-compose.airflow.yml" --env-file "${ENV_FILE}" up airflow-init
log "Starting Airflow services..."
dc -f "${DOCKER_DIR}/docker-compose.airflow.yml" --env-file "${ENV_FILE}" up -d \
  airflow-webserver airflow-scheduler airflow-worker airflow-flower
log "Airflow services started."

# ─── 8. Start Spark ────────────────────────────────────────────
log "Starting Spark Standalone (master + worker)..."
dc -f "${DOCKER_DIR}/docker-compose.spark.yml" --env-file "${ENV_FILE}" up -d
log "Spark services started."

# ─── 9. Summary ────────────────────────────────────────────────
echo ""
echo "============================================================"
echo -e "${GREEN}  MCP Agent DAG Platform — Stack ready!${NC}"
echo "============================================================"
echo ""
echo "  Service             URL / Connection"
echo "  ─────────────────── ────────────────────────────────────"
echo "  Airflow UI          http://localhost:8080  (admin / admin)"
echo "  Celery Flower       http://localhost:5555"
echo "  Spark Master UI     http://localhost:8081"
echo "  dbt docs            http://localhost:8001  (run: dbt docs serve)"
echo ""
echo "  PostgreSQL Airflow  localhost:5432  (admin / admin)"
echo "  PostgreSQL Serving  localhost:5433  (admin / admin)"
echo "  Redis               localhost:6379  (password: admin)"
echo ""
echo "  Python venv         ${VENV_DIR}"
echo "  Activate:           source ${VENV_DIR}/bin/activate"
echo ""
echo -e "${YELLOW}  IMPORTANT: Change all passwords before connecting to any network!${NC}"
echo "============================================================"
