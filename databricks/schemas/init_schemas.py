"""
init_schemas.py — Inicializa o catálogo football_prediction e todas as tabelas Delta Lake.

Executa os 4 arquivos DDL em ordem usando o Databricks SQL Connector.

Uso:
    source /opt/mcp-platform/venv/bin/activate
    python databricks/schemas/init_schemas.py

    # Ou apenas um arquivo:
    python databricks/schemas/init_schemas.py --file 02_bronze_ddl.sql
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from databricks import sql
from dotenv import load_dotenv

# Carrega .env da raiz do projeto
_ROOT = Path(__file__).parent.parent.parent
load_dotenv(_ROOT / ".env")

_SCHEMAS_DIR = Path(__file__).parent
_DDL_FILES = [
    "01_create_catalog.sql",
    "02_bronze_ddl.sql",
    "03_silver_ddl.sql",
    "04_gold_ddl.sql",
]


def _get_connection():
    host = os.environ["DATABRICKS_HOST"].replace("https://", "")
    token = os.environ["DATABRICKS_TOKEN"]
    http_path = os.environ["DATABRICKS_HTTP_PATH"]

    return sql.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token,
    )


def _split_statements(sql_text: str) -> list[str]:
    """
    Divide o arquivo SQL em statements individuais.
    Remove comentários de linha (--) e blocos vazios.
    """
    # Remove blocos de comentário de linha para não confundir o split
    lines = []
    for line in sql_text.splitlines():
        stripped = line.split("--")[0].rstrip()
        lines.append(stripped)

    full_text = "\n".join(lines)

    # Split por ; e filtrar vazios
    statements = [s.strip() for s in full_text.split(";")]
    return [s for s in statements if s and not s.isspace()]


def run_file(cursor, filepath: Path) -> int:
    """Executa todos os statements de um arquivo SQL. Retorna quantidade executada."""
    sql_text = filepath.read_text(encoding="utf-8")
    statements = _split_statements(sql_text)

    executed = 0
    for stmt in statements:
        try:
            print(f"  → {stmt[:80].replace(chr(10), ' ')}...")
            cursor.execute(stmt)
            executed += 1
        except Exception as exc:
            print(f"  ✗ ERRO: {exc}")
            raise

    return executed


def main(files: list[str] | None = None) -> None:
    targets = files or _DDL_FILES

    print(f"\n{'='*60}")
    print("  Databricks Schema Initializer — football_prediction")
    print(f"  Host: {os.environ.get('DATABRICKS_HOST', '?')}")
    print(f"{'='*60}\n")

    try:
        conn = _get_connection()
    except KeyError as e:
        print(f"ERRO: variável de ambiente {e} não definida no .env")
        sys.exit(1)

    total = 0
    with conn.cursor() as cursor:
        for fname in targets:
            fpath = _SCHEMAS_DIR / fname
            if not fpath.exists():
                print(f"[SKIP] {fname} — arquivo não encontrado")
                continue

            print(f"\n[{fname}]")
            try:
                n = run_file(cursor, fpath)
                total += n
                print(f"  ✓ {n} statements executados")
            except Exception as exc:
                print(f"\nFalha em {fname}: {exc}")
                conn.close()
                sys.exit(1)

    conn.close()
    print(f"\n{'='*60}")
    print(f"  Concluído — {total} statements executados com sucesso.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicializa schemas Delta Lake no Databricks")
    parser.add_argument(
        "--file",
        type=str,
        help="Executar apenas este arquivo (ex: 02_bronze_ddl.sql)",
    )
    args = parser.parse_args()

    main(files=[args.file] if args.file else None)
