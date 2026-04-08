# Lost in Hyd

> A weekly newsletter exploring local happenings and hidden gems in Hyderabad, India

## Project Structure

```
lostinhyd/
├── docker-compose.yml    # Docker orchestration for all services
├── nginx/                # NGINX reverse proxy
│   ├── nginx.conf        # Route configuration
│   └── Dockerfile
├── website/              # Astro SSR website (PostgreSQL)
│   ├── src/
│   │   ├── lib/db.js     # PostgreSQL queries
│   │   ├── pages/        # Server-rendered pages
│   │   └── components/   # Astro components
│   └── Dockerfile
├── admin/                # React Admin + Express API
│   ├── src/
│   │   ├── server.js     # Express API server
│   │   ├── db.js         # Database connection
│   │   ├── lib/          # CRUD helpers, errors
│   │   └── ...           # React Admin frontend
│   └── Dockerfile
├── crawler/              # Python event crawlers
│   ├── sources/          # Per-site crawlers
│   ├── core/             # Base crawler, HTTP client
│   └── Dockerfile
├── migrations/           # PostgreSQL schema migrations
└── DEPLOYMENT.md         # Docker deployment guide
```

## Quick Start (Docker)

### 1. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with your DATABASE_URL and ADMIN_TOKEN
```

### 2. Start All Services

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f

# Check health
curl http://localhost/nginx-health
curl http://localhost/health
curl http://localhost/admin/health
```

### 3. Access the Services

- **Website**: http://localhost/
- **Admin Panel**: http://localhost/admin/

### 4. Run the Crawler

```bash
# Crawl all sources
docker compose --profile crawler run --rm crawler

# Crawl specific source
docker compose --profile crawler run --rm crawler python -m crawler.cli crawl --source bookmyshow
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## Development

### Website (Astro)

```bash
cd website
npm install
npm run dev        # Local development
```

### Admin (Express API + React)

```bash
cd admin
npm install

# Terminal 1: Run API server
npm run server   # Express API on port 3001

# Terminal 2: Run React dev server
npm run dev      # Vite dev server (proxies /api to Express)
```

### Crawlers

```bash
cd crawler
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run crawls
python -m crawler.cli crawl
python -m crawler.cli clean
```

## Architecture

```
Cloudflare (SSL termination)
    |
    v
NGINX (port 80/443)
    |---> Website (Astro SSR, port 3000)
    |---> Admin (Express + React, port 3001)
    
PostgreSQL (OVH Managed)
    ^
    |
Crawler (on-demand Docker runs)
```

- **Website**: Astro SSR with PostgreSQL (no caching layer)
- **Admin**: Express API serving React Admin SPA
- **Crawler**: Python scripts running on-demand
- **Database**: OVH Managed PostgreSQL (shared by all services)

## Environment Variables

```bash
# Required for all services
DATABASE_URL="postgresql://user:pass@host:port/lostinhyd?sslmode=require"

# Admin panel authentication
ADMIN_TOKEN="your-secure-random-token"

# Optional: Browserless for JS-heavy sites
BROWSERLESS_TOKEN=""
```

## Previous Architecture

This project was previously deployed on Cloudflare Pages with D1 database. The migration to Docker was completed to:
- Consolidate all services locally for easier monitoring and debugging
- Use PostgreSQL as the single source of truth (eliminating D1 sync issues)
- Enable the local Hermes agent to manage deployment and operations
