#!/usr/bin/env bash
# Publish docs/wiki/*.md to the GitHub Wiki of vanowarna/altotech-task-1.
#
# PREREQUISITE (one-time): the wiki repo only exists after you create the first page.
#   Go to https://github.com/vanowarna/altotech-task-1/wiki -> "Create the first page" -> Save.
#
# Then run from the repo root:
#   ./scripts/publish-wiki.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WIKI_URL="https://github.com/vanowarna/altotech-task-1.wiki.git"
TMP="$(mktemp -d)"

echo "Cloning wiki..."
git clone "$WIKI_URL" "$TMP"

echo "Copying pages..."
cp "$ROOT"/docs/wiki/*.md "$TMP"/

cd "$TMP"
git add .
git commit -m "Update wiki: architecture, sequence diagrams, ADRs, Brick design, running, API" || {
  echo "Nothing to commit (already up to date)."; exit 0; }
git push
echo "Wiki published: https://github.com/vanowarna/altotech-task-1/wiki"
