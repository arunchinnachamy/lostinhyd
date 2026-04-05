#!/usr/bin/env bash
# Setup Hyperdrive configuration for the Lost in Hyd admin project.
# Requires: wrangler CLI authenticated (npx wrangler login) or CLOUDFLARE_API_TOKEN set.
#
# Usage: bash scripts/setup-hyperdrive.sh

set -euo pipefail

CONNECTION_STRING="${DATABASE_URL:?Set DATABASE_URL to your PostgreSQL connection string}"

echo "Creating Hyperdrive config 'lostinhyd-db'..."
RESULT=$(npx wrangler hyperdrive create lostinhyd-db --connection-string="$CONNECTION_STRING" 2>&1)
echo "$RESULT"

# Extract the config ID from the output
CONFIG_ID=$(echo "$RESULT" | grep -oP 'id:\s*\K[a-f0-9-]+' || echo "")

if [ -z "$CONFIG_ID" ]; then
  echo ""
  echo "Could not extract config ID. Please update wrangler.toml manually with the Hyperdrive ID."
  exit 1
fi

echo ""
echo "Hyperdrive config created with ID: $CONFIG_ID"
echo ""
echo "Updating wrangler.toml..."

# Uncomment and set the Hyperdrive binding
sed -i "s|# \[\[hyperdrive\]\]|[[hyperdrive]]|" wrangler.toml
sed -i "s|# binding = \"HYPERDRIVE\"|binding = \"HYPERDRIVE\"|" wrangler.toml
sed -i "s|# id = \"<your-hyperdrive-config-id>\"|id = \"$CONFIG_ID\"|" wrangler.toml

echo "Done! wrangler.toml updated with Hyperdrive binding."
echo ""
echo "Next steps:"
echo "  1. Set ADMIN_TOKEN secret: npx wrangler pages secret put ADMIN_TOKEN"
echo "  2. Deploy: npx wrangler pages deploy dist/"
