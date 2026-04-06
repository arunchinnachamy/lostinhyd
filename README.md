# Lost in Hyd

> A weekly newsletter exploring local happenings and hidden gems in Hyderabad, India

## Project Structure

```
lostinhyd/
├── website/              # Astro SSR website on Cloudflare Pages (D1 + caching)
│   ├── src/
│   │   ├── lib/db.js     # D1 database queries with cache layer
│   │   ├── middleware/    # Cache-Control headers per route
│   │   ├── pages/        # Server-rendered pages
│   │   └── components/   # Astro components
│   └── wrangler.toml     # Cloudflare Pages config
├── admin/                # React Admin SPA on Cloudflare Pages
│   ├── functions/api/    # Cloudflare Pages Functions (REST API)
│   ├── functions/lib/    # Shared CRUD, DB connection, error handling
│   ├── src/              # React Admin frontend
│   ├── tests/            # Vitest integration tests
│   └── wrangler.toml     # Cloudflare Pages config
├── crawler/              # Python event crawlers
│   ├── sources/          # Per-site crawlers (BookMyShow, Meetup, etc.)
│   ├── core/             # Base crawler, HTTP client, data store
│   ├── cleaning/         # Data cleaning and deduplication
│   └── runner.py         # Main runner script
├── migrations/           # PostgreSQL schema migrations
├── utils/                # Shared Python utilities
│   └── db.py             # Database connection helper
├── editions/             # Legacy newsletter archive
├── templates/            # Email/Newsletter templates
└── assets/               # Images, logos, etc.
```

## Quick Start

### Website (Astro + Cloudflare)

```bash
cd website
npm install
npm run dev        # Local development
npm run build      # Production build
```

### Admin Panel (React Admin + Cloudflare)

```bash
cd admin
npm install
npm run dev        # Local development (needs DATABASE_URL in .dev.vars)
npm test           # Run integration tests (needs DATABASE_URL)
npm run build      # Production build
```

### Event Crawlers

```bash
# Set up database first
# (You'll provide credentials, then we'll connect)

# Run specific crawler
python -m crawler.runner --source insider

# Run all crawlers
python -m crawler.runner --all

# List available crawlers
python -m crawler.runner --list
```

## Deployment

### Cloudflare Pages (Website)

1. Push to GitHub
2. Connect to Cloudflare Pages
3. Build command: `cd website && npm run build`
4. Output directory: `website/dist`

Or use GitHub Actions (configured in `.github/workflows/deploy.yml`).

### Cloudflare Pages (Admin)

1. Push to GitHub
2. Connect to Cloudflare Pages (project: `lostinhyd-admin`)
3. Build command: `cd admin && npm run build`
4. Output directory: `admin/dist`
5. Set secrets: `ADMIN_TOKEN`, `DATABASE_URL`
6. Optional: Set up Hyperdrive with `bash admin/scripts/setup-hyperdrive.sh`

### Environment Variables

```bash
# Required for crawlers and admin
export DATABASE_URL="postgresql://user:pass@host:port/lostinhyd"

# Admin panel
export ADMIN_TOKEN="your-admin-bearer-token"
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

Content is © Lost in Hyd. All rights reserved.
Code is MIT licensed.
