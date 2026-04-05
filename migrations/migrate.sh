#!/usr/bin/env bash
# Run all pending migrations against the database.
# Usage: ./migrations/migrate.sh [DATABASE_URL]

set -euo pipefail

DB_URL="${1:-${DATABASE_URL:-}}"
if [ -z "$DB_URL" ]; then
  echo "Usage: $0 <database_url>"
  echo "  or set DATABASE_URL environment variable"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for migration in "$SCRIPT_DIR"/*.sql; do
  echo "Applying $(basename "$migration")..."
  psql "$DB_URL" -f "$migration"
done

echo "All migrations applied."
