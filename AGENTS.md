# Lost in Hyd — Agent Notes

## Architecture

Three services behind NGINX, all sharing a single OVH Managed PostgreSQL:

- **website/** — Astro SSR (`@astrojs/node` standalone), plain JS, port 3000
- **admin/** — Express API + React Admin SPA, TypeScript, port 3001
- **crawler/** — Python async crawlers (BookMyShow etc.), on-demand Docker runs
- **nginx/** — Reverse proxy routing `/` → website, `/admin` → admin

## Database (critical)

- All tables live in the **`lostinhyd`** schema, NOT `public`. Every connection must run `SET search_path TO lostinhyd, public` first. The `withDb()` helper in both `admin/src/db.js` and `website/src/lib/db.js` handles this.
- OVH PostgreSQL uses self-signed certs. Connection code strips `sslmode=` from the URL and sets `ssl: { rejectUnauthorized: false }`. Do not "fix" the SSL config.
- Schema name `lostinhyd`, database name `toolradar` (on OVH).
- Migrations are numbered SQL files in `migrations/`, applied via `migrations/migrate.sh` (requires `psql`).

## Commands

### Website (Astro)
```bash
cd website && npm install
npm run dev          # dev server on :3000
npm run build        # astro build
```
No test framework configured.

### Admin (Express + React)
```bash
cd admin && npm install
npm run server       # Express API on :3001 (terminal 1)
npm run dev          # Vite dev server, proxies /api → :3001 (terminal 2)
npm run build        # tsc -b && vite build
npm test             # vitest run
npm run test:watch   # vitest watch
```

### Crawler (Python)
```bash
cd crawler && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m crawler.cli crawl                    # all sources
python -m crawler.cli crawl --source bookmyshow # single source
python -m crawler.cli clean                    # deduplicate
```
Or via Docker: `docker compose --profile crawler run --rm crawler python -m crawler.cli crawl`

### Docker (full stack)
```bash
cp .env.example .env   # set DATABASE_URL, ADMIN_TOKEN
docker compose up -d
docker compose --profile crawler run --rm crawler python -m crawler.cli crawl
```

## Testing

Tests exist only in `admin/tests/`. They hit a **real PostgreSQL database** (not mocked). `DATABASE_URL` must be set and point to a database with the `lostinhyd` schema applied. The test setup (`tests/setup.ts`) seeds and cleans data per test using real SQL inserts/deletes.

## Environment Variables

| Variable | Used by | Required |
|---|---|---|
| `DATABASE_URL` | all services | yes |
| `ADMIN_TOKEN` | admin | yes |
| `SITE_URL` | website, admin | no (defaults to `http://localhost`) |
| `BROWSERLESS_TOKEN` | crawler | no (for JS-heavy sites) |

## Key Gotchas

- Node >= 20 required (website `package.json` engines field).
- Admin Vite dev server proxies `/api` to Express on :3001 — both must run during development.
- Crawler Docker service uses `profiles: [crawler]` and will NOT start with `docker compose up`. Use `--profile crawler`.
- Event slugs are unique; test seeds append timestamps to avoid collisions.
- No CI/CD workflows configured (no `.github/workflows/`).
- `VERSION` file follows custom format (currently `0.1.0.0`).
