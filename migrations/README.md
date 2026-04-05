# Database Migrations

Numbered SQL migration files for the Lost in Hyd database.

## Running migrations

Migrations are run manually against the PostgreSQL database in order:

```bash
# Set your database connection
export DATABASE_URL="postgresql://user:pass@host:5432/lostinhyd"

# Run a specific migration
psql $DATABASE_URL -f migrations/001_initial_schema.sql

# Run all migrations in order
for f in migrations/*.sql; do
  echo "Running $f..."
  psql $DATABASE_URL -f "$f"
done
```

## Conventions

- Files are numbered sequentially: 001_, 002_, etc.
- Each migration should be idempotent (use IF NOT EXISTS, IF NOT EXISTS, etc.)
- Never modify an existing migration file after it has been applied to production
- Add a comment at the top describing what the migration does
