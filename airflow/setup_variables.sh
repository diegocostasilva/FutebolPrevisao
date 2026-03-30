#!/usr/bin/env bash
# =============================================================================
# setup_variables.sh — cria Airflow Variables necessárias para a DAG
#
# Execute DENTRO do container airflow-webserver ou airflow-scheduler:
#   docker exec -it airflow-webserver bash airflow/setup_variables.sh
#
# Ou pelo host (com o stack rodando):
#   docker exec -i airflow-webserver bash < airflow/setup_variables.sh
# =============================================================================

set -euo pipefail

# ── Carrega .env se existir ───────────────────────────────────────────────────
ENV_FILE="/opt/airflow/project/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a; source "$ENV_FILE"; set +a
  echo "[INFO] .env carregado de $ENV_FILE"
fi

# ── Variáveis obrigatórias (credenciais) ──────────────────────────────────────
# Lê das env vars do shell ou falha com mensagem clara
: "${DATABRICKS_HOST:?Variável DATABRICKS_HOST não definida}"
: "${DATABRICKS_TOKEN:?Variável DATABRICKS_TOKEN não definida}"
: "${API_FOOTBALL_KEY:?Variável API_FOOTBALL_KEY não definida}"

airflow variables set DATABRICKS_HOST    "$DATABRICKS_HOST"
airflow variables set DATABRICKS_TOKEN   "$DATABRICKS_TOKEN"
airflow variables set API_FOOTBALL_KEY   "$API_FOOTBALL_KEY"

echo "[OK] Credenciais Databricks e API-Football configuradas."

# ── Variáveis opcionais (com defaults) ────────────────────────────────────────
airflow variables set ENVIRONMENT        "${ENVIRONMENT:-dev}"
airflow variables set LEAGUE_IDS         "${LEAGUE_IDS:-71}"
airflow variables set SEASON             "${SEASON:-2025}"
airflow variables set DATABRICKS_CLUSTER_ID "${DATABRICKS_CLUSTER_ID:-}"

echo "[OK] Variáveis de runtime configuradas."
echo ""
echo "Variáveis definidas:"
airflow variables list
