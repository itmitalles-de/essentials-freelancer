#!/usr/bin/env bash
# Conservative static scan. Prints file names only, never matching content.
set -Eeuo pipefail

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

fail() {
  printf 'secret-scan: %s\n' "$*" >&2
  exit 1
}

tracked_sensitive=$(git ls-files | awk '
  /(^|\/)\.env$/ || /(^|\/)(id_rsa|id_ed25519|credentials\.json|restic-password)$/ ||
  /\.(pem|key|p12|pfx|jks|keystore)$/ { print }
')
[ -z "$tracked_sensitive" ] || {
  printf 'secret-scan: sensitive file names are tracked:\n%s\n' "$tracked_sensitive" >&2
  exit 1
}

patterns='-----BEGIN [A-Z ]*PRIVATE KEY-----|(AKIA|ASIA)[0-9A-Z]{16}|github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-(proj-)?[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|AIza[0-9A-Za-z_-]{30,}|SG\.[0-9A-Za-z_-]{16,}\.[0-9A-Za-z_-]{16,}|sk_live_[0-9A-Za-z]{16,}|smtps?://[^[:space:]/:]+:[^[:space:]@]+@'
matches=$(git grep --untracked --exclude-standard -IlE -e "$patterns" -- . ':!scripts/check-secrets.sh' || true)
[ -z "$matches" ] || {
  printf 'secret-scan: possible credential material found in:\n%s\n' "$matches" >&2
  exit 1
}

history_matches=$(
  for revision in $(git rev-list --all); do
    git grep -IlE -e "$patterns" "$revision" -- . ':!scripts/check-secrets.sh' || true
  done | sort -u
)
[ -z "$history_matches" ] || {
  printf 'secret-scan: possible credential material exists in Git history (commit:path only):\n%s\n' "$history_matches" >&2
  exit 1
}

printf 'secret-scan: tracked, working-tree, and full-history checks passed\n'
