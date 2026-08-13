#!/usr/bin/env bash
# Export PostgreSQL plus all generated PDFs, logos, and expense receipts.
set -Eeuo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${FREELANCER_ENV_FILE:-"$PROJECT_DIR/.env"}
EXPORT_ROOT=${1:-"$PROJECT_DIR/backups"}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FINAL_DIR="$EXPORT_ROOT/$STAMP"
WORK_DIR=
BACKEND_WAS_RUNNING=false
DB_WAS_RUNNING=false
DB_STARTED=false

die() {
  printf 'export: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  local status=$?
  if [ "$BACKEND_WAS_RUNNING" = true ]; then
    if ! compose -f "$PROJECT_DIR/docker-compose.yml" up -d backend >/dev/null; then
      printf 'export: WARNING: backend could not be restarted\n' >&2
      status=1
    fi
  elif [ "$DB_STARTED" = true ]; then
    compose -f "$PROJECT_DIR/docker-compose.yml" stop db >/dev/null || status=1
  fi
  if [ -n "$WORK_DIR" ] && [ -d "$WORK_DIR" ] && [ "$status" -ne 0 ]; then
    rm -rf -- "$WORK_DIR"
  fi
  exit "$status"
}
trap cleanup EXIT INT TERM

compose() {
  docker compose --env-file "$ENV_FILE" "$@"
}

for command in docker flock git mktemp sha256sum tar; do
  command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done
[ -f "$ENV_FILE" ] || die "missing $ENV_FILE"
case "$EXPORT_ROOT" in
  /|'') die 'refusing unsafe export root' ;;
esac

cd "$PROJECT_DIR"
compose config -q
umask 077
mkdir -p "$EXPORT_ROOT"
exec 9>"$EXPORT_ROOT/.export.lock"
flock -n 9 || die 'another export is already running'
[ ! -e "$FINAL_DIR" ] || die "export already exists: $FINAL_DIR"
WORK_DIR=$(mktemp -d "$EXPORT_ROOT/.${STAMP}.incomplete.XXXXXX")

if [ -n "$(compose ps --status running -q backend)" ]; then
  BACKEND_WAS_RUNNING=true
fi
if [ -n "$(compose ps --status running -q db)" ]; then
  DB_WAS_RUNNING=true
fi
if [ "$DB_WAS_RUNNING" = false ]; then
  compose up -d db >/dev/null
  DB_STARTED=true
fi

db_container=$(compose ps -q db)
[ -n "$db_container" ] || die 'database container is unavailable'
for attempt in $(seq 1 30); do
  if [ "$(docker inspect --format '{{.State.Health.Status}}' "$db_container")" = healthy ]; then
    break
  fi
  [ "$attempt" -lt 30 ] || die 'database did not become healthy'
  sleep 2
done

if [ "$BACKEND_WAS_RUNNING" = true ]; then
  compose stop --timeout 30 backend >/dev/null
fi

compose exec -T db sh -ec \
  'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
  >"$WORK_DIR/business.pg.dump"
compose run --rm --no-deps -T --entrypoint tar backend \
  -czf - -C /data invoices >"$WORK_DIR/documents.tar.gz"

cp docker-compose.yml "$WORK_DIR/docker-compose.yml"
cp .env.example "$WORK_DIR/env.example"
repository_commit=$(git rev-parse HEAD 2>/dev/null || printf 'unknown')
database_version=$(compose exec -T db postgres --version | tr -d '\r')
{
  printf 'created_utc=%s\n' "$STAMP"
  printf 'repository_commit=%s\n' "$repository_commit"
  printf 'database_version=%s\n' "$database_version"
  printf 'contains=PostgreSQL custom-format dump and /data/invoices archive\n'
  printf 'secrets_included=no\n'
} >"$WORK_DIR/MANIFEST.txt"

compose exec -T db pg_restore --list <"$WORK_DIR/business.pg.dump" >/dev/null
tar -tzf "$WORK_DIR/documents.tar.gz" >/dev/null
(
  cd "$WORK_DIR"
  sha256sum business.pg.dump documents.tar.gz docker-compose.yml env.example MANIFEST.txt >SHA256SUMS
  sha256sum --check --quiet SHA256SUMS
)

if [ "$BACKEND_WAS_RUNNING" = true ]; then
  compose up -d backend >/dev/null
  BACKEND_WAS_RUNNING=false
elif [ "$DB_STARTED" = true ]; then
  compose stop db >/dev/null
  DB_STARTED=false
fi

mv -- "$WORK_DIR" "$FINAL_DIR"
WORK_DIR=
printf 'export: created %s\n' "$FINAL_DIR"
