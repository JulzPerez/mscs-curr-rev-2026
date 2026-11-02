#!/usr/bin/env bash
# Pull the latest commit from GitHub and rebuild the production container.
#   ./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"

DATA_DIR="${DATA_DIR:-../mscs-curr-rev-data}"
mkdir -p "$DATA_DIR"
if [ ! -f "$DATA_DIR/form_data.json" ]; then
    cp form_data.json "$DATA_DIR/form_data.json"
    echo "Seeded $DATA_DIR/form_data.json from the repo."
fi

# Back up live data before each deploy (keeps the last 20).
mkdir -p "$DATA_DIR/backups"
cp "$DATA_DIR/form_data.json" "$DATA_DIR/backups/form_data.$(date +%Y%m%d-%H%M%S).json"
ls -1t "$DATA_DIR"/backups/form_data.*.json | tail -n +21 | xargs -r rm --

git pull --ff-only
docker compose up -d --build
docker image prune -f >/dev/null
docker compose ps
