#!/usr/bin/env bash
# Conservative static scan. Prints file names only, never matching content.
set -Eeuo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

fail() {
  printf 'secret-scan: %s\n' "$*" >&2
  exit 1
}

tracked_sensitive=$(git ls-files | awk '
  /(^|\/)\.env$/ || /\.(pem|key|p12|pfx)$/ { print }
')
[ -z "$tracked_sensitive" ] || {
  printf 'secret-scan: sensitive file names are tracked:\n%s\n' "$tracked_sensitive" >&2
  exit 1
}

patterns='-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}'
matches=$(git grep --untracked --exclude-standard -IlE -e "$patterns" -- . ':!scripts/check-secrets.sh' || true)
[ -z "$matches" ] || {
  printf 'secret-scan: possible credential material found in:\n%s\n' "$matches" >&2
  exit 1
}

printf 'secret-scan: no known credential patterns found\n'
