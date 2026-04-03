# Lost in Hyd

> A weekly newsletter exploring local happenings and hidden gems in Hyderabad, India

## Project Structure

```
lostinhyd/
├── website/              # Astro-based SEO website for Cloudflare Pages
│   ├── src/
│   │   ├── content/      # Newsletter, events, places content
│   │   ├── pages/        # Website pages
│   │   └── layouts/      # Page layouts
│   └── dist/             # Build output (auto-generated)
├── crawler/              # Event aggregation crawlers
│   ├── base.py           # Base crawler classes
│   ├── sources.py        # Website-specific crawlers
│   └── runner.py         # Main runner script
├── utils/                # Utilities
│   ├── db.py             # Database models & connection
│   └── schema.sql        # PostgreSQL schema
├── editions/             # Legacy newsletter archive
├── newsletters/          # Draft newsletter content
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

Or use GitHub Actions (already configured in `.github/workflows/deploy.yml`)

### Environment Variables

For crawlers, you'll need:
```bash
export DATABASE_URL="postgresql://user:pass@host:port/lostinhyd"
```

Optional:
```bash
export MEETUP_API_KEY="your_key_here"  # For Meetup crawler
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

Content is © Lost in Hyd. All rights reserved.
Code is MIT licensed.
