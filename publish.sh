#!/usr/bin/env bash
# Creates the PUBLIC GitHub repo for ruslaw-public and pushes it.
#
# NOT run automatically by the agent — the harness's permission classifier blocks agent-initiated
# public-repo creation ("Create Public Surface"). Denis (or anyone with shell access here) runs
# this by hand:
#
#   bash ~/ruslaw_public/publish.sh                 # create + push (first time)
#   bash ~/ruslaw_public/publish.sh --update         # just commit + push to an already-created repo
#
set -euo pipefail
cd "$(dirname "$0")"

REPO_NAME="${REPO_NAME:-ruslaw-public}"
ACCOUNT="vadimpokrov396-ship-it"   # the visible account (karlson1980/powervpsdenis-max are hidden/404)
VISIBILITY="public"

echo "== Checking gh auth =="
gh auth status | grep -q "$ACCOUNT" || { echo "ERROR: $ACCOUNT not in gh auth status"; exit 1; }
ACTIVE=$(gh auth status 2>&1 | grep -B1 "Active account: true" | head -1 | awk '{print $3}')
if [ "$ACTIVE" != "$ACCOUNT" ]; then
  echo "Switching active gh account to $ACCOUNT ..."
  gh auth switch -h github.com -u "$ACCOUNT"
fi

echo "== Safety check: no file over 45MB (GitHub hard-blocks 100MB, warns 50MB) =="
BIG=$(find . -type f -not -path './.git/*' -size +45M || true)
if [ -n "$BIG" ]; then
  echo "REFUSING to publish: these files exceed 45MB and need Git LFS or a GitHub Release instead:"
  echo "$BIG"
  exit 1
fi

echo "== Safety check: no obvious secrets =="
if grep -rIlE "(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{12,}" \
    --exclude-dir=.git --exclude-dir=data . ; then
  echo "REFUSING to publish: possible secret-looking string found above. Review before publishing."
  exit 1
fi

cat > .gitignore <<'EOF'
__pycache__/
*.pyc
.DS_Store
EOF

if [ ! -d .git ]; then
  git init
  git add -A
  git commit -m "Initial commit: ruslaw-fetch tool + dataset (24 codes + federal laws, current redactions from actual.pravo.gov.ru)"
fi

if ! gh repo view "$ACCOUNT/$REPO_NAME" >/dev/null 2>&1; then
  echo "== Creating $ACCOUNT/$REPO_NAME ($VISIBILITY) =="
  gh repo create "$ACCOUNT/$REPO_NAME" --"$VISIBILITY" --source=. --remote=origin \
    --description "Open tool + free dataset: current (amendments-merged) text of all 24 Russian codes + ~49 federal laws, from the official actual.pravo.gov.ru service. MIT tool, public-domain texts." \
    --push
else
  echo "== Repo already exists, pushing update =="
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$ACCOUNT/$REPO_NAME.git"
  git add -A
  git commit -m "Update: $(date +%Y-%m-%d)" || echo "(nothing to commit)"
  git push -u origin HEAD
fi

echo "== Adding topics =="
gh repo edit "$ACCOUNT/$REPO_NAME" --add-topic russian-law --add-topic legal-dataset \
  --add-topic open-data --add-topic pravo-gov-ru --add-topic nlp --add-topic rag || true

echo ""
echo "Done: https://github.com/$ACCOUNT/$REPO_NAME"
