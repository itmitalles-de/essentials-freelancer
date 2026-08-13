#!/usr/bin/env bash
# Restore only into an empty database and empty documents volume.
set -Eeuo pipefail

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${FREELANCER_ENV_FILE:-"$PROJECT_DIR/.env"}
RESTORE_DIR=${1:-}
CONFIRMATION=${2:-}
DATABASE_READY_TIMEOUT_SECONDS=${DATABASE_READY_TIMEOUT_SECONDS:-180}

die() {
  printf 'restore: %s\n' "$*" >&2
  exit 1
}

compose() {
  docker compose --env-file "$ENV_FILE" "$@"
}

[ -n "$RESTORE_DIR" ] || die 'usage: restore-business-data.sh EXPORT_DIR --confirm-empty-target'
[ "$CONFIRMATION" = --confirm-empty-target ] || die 'explicit --confirm-empty-target is required'
[ -d "$RESTORE_DIR" ] || die "not a directory: $RESTORE_DIR"
[ -f "$ENV_FILE" ] || die "missing $ENV_FILE"
for file in business.pg.dump documents.tar.gz SHA256SUMS; do
  [ -f "$RESTORE_DIR/$file" ] || die "missing export file: $file"
done
for command in docker sha256sum; do
  command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

cd "$RESTORE_DIR"
sha256sum --check --quiet SHA256SUMS || die 'export checksum verification failed'
cd "$PROJECT_DIR"
compose config -q

if [ -n "$(compose ps --status running -q backend)" ]; then
  die 'backend is running; stop application traffic before restoring'
fi
compose up -d db >/dev/null
db_container=$(compose ps -q db)
[ -n "$db_container" ] || die 'database container is unavailable'
database_deadline=$((SECONDS + DATABASE_READY_TIMEOUT_SECONDS))
while [ "$SECONDS" -lt "$database_deadline" ]; do
  if [ "$(docker inspect --format '{{.State.Health.Status}}' "$db_container")" = healthy ]; then
    break
  fi
  sleep 2
done
[ "$(docker inspect --format '{{.State.Health.Status}}' "$db_container")" = healthy ] || \
  die "database did not become healthy within ${DATABASE_READY_TIMEOUT_SECONDS}s"

# These commands intentionally expand variables inside their containers.
# shellcheck disable=SC2016
table_count=$(compose exec -T db sh -ec \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema = '\''public'\''"')
[ "$table_count" = 0 ] || die 'target database is not empty; restore refused'

# shellcheck disable=SC2016
if ! compose run --rm --no-deps -T --entrypoint sh backend -ec \
  'mkdir -p /data/invoices; test -z "$(find /data/invoices -mindepth 1 -print -quit)"'; then
  die 'target documents volume is not empty; restore refused'
fi

# shellcheck disable=SC2016
compose exec -T db sh -ec \
  'exec pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges' \
  <"$RESTORE_DIR/business.pg.dump"
compose run --rm --no-deps -T --entrypoint tar backend \
  -xzf - -C /data <"$RESTORE_DIR/documents.tar.gz"

# shellcheck disable=SC2016
compose exec -T db sh -ec \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version"' \
  >/dev/null
printf 'restore: completed; start backend and frontend only after reviewing the restore logs\n'
