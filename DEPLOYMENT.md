# Docker Deployment Guide

This guide covers deploying Lost in Hyd locally using Docker Compose.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- PostgreSQL database (OVH managed or local)
- Environment variables configured

## Quick Start

### 1. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual values
nano .env
```

Required variables:
- `DATABASE_URL` - PostgreSQL connection string
- `ADMIN_TOKEN` - Secure random token for admin access
- `SITE_URL` - Your domain (e.g., https://lostinhyd.com)

### 2. Build and Start Services

```bash
# Build all Docker images
docker compose build

# Start services in detached mode
docker compose up -d

# View logs
docker compose logs -f
```

### 3. Verify Health

```bash
# Check all services are healthy
curl http://localhost/nginx-health
curl http://localhost/health  # Website health
curl http://localhost/admin/health  # Admin health
```

### 4. Access the Services

With NGINX reverse proxy:
- **Website**: http://localhost/
- **Admin Panel**: http://localhost/admin/

Direct access (if needed):
- **Website**: http://localhost:3000
- **Admin API**: http://localhost:3001

## Running the Crawler

The crawler doesn't auto-start. Run it manually:

```bash
# Run a full crawl of all sources
docker compose --profile crawler run --rm crawler python -m crawler.cli crawl

# Crawl a specific source
docker compose --profile crawler run --rm crawler python -m crawler.cli crawl --source bookmyshow

# Clean and deduplicate data
docker compose --profile crawler run --rm crawler python -m crawler.cli clean
```

## Managing Services

```bash
# Stop all services
docker compose down

# Restart a specific service
docker compose restart website

# View logs for specific service
docker compose logs -f website

# Rebuild after code changes
docker compose build --no-cache website
docker compose up -d website

# Shell into a container
docker compose exec website sh
docker compose exec admin sh
```

## Cloudflare Proxy Setup

To use Cloudflare for SSL termination:

1. Point your domain to your server's IP
2. In Cloudflare DNS, set the record to "Proxied" (orange cloud)
3. Set SSL/TLS mode to "Full (strict)" or "Full"
4. No additional configuration needed - NGINX handles the rest

## Troubleshooting

### Database Connection Issues

```bash
# Test database connectivity from container
docker compose exec website node -e "
const { Pool } = require('pg');
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
pool.query('SELECT 1').then(() => console.log('OK')).catch(e => console.error(e));
"
```

### Port Already in Use

```bash
# Find process using port 80
sudo lsof -i :80

# Kill it or change docker-compose.yml ports to use a different port
```

### Container Won't Start

```bash
# Check container logs
docker compose logs website
docker compose logs admin
docker compose logs nginx

# Check for build errors
docker compose build --no-cache
```

## Architecture

```
Cloudflare (SSL)
    |
    v
NGINX (port 80) ----> Website (Astro SSR, port 3000)
                \
                 ----> Admin (Express + React, port 3001)
                /
PostgreSQL (OVH Managed)
```

All services share a single Docker network and communicate internally.

## Production Considerations

1. **Security**: Change default ADMIN_TOKEN to a strong random value
2. **Backups**: Database is managed by OVH - verify backup settings
3. **Monitoring**: Health check endpoints at `/health` for each service
4. **Updates**: Rebuild containers after code changes: `docker compose up -d --build`

## Development Mode

For local development with hot reload:

```bash
# Website
cd website && npm install && npm run dev

# Admin (API)
cd admin && npm install && npm run server

# Admin (SPA)
cd admin && npm install && npm run dev
```

Note: In development, the Vite dev server proxies `/api` requests to the Express server.
