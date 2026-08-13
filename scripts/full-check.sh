#!/usr/bin/env bash
# Fully disposable automated acceptance using synthetic data and local simulators.
set -Eeuo pipefail

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
RUNTIME_DIR=$(mktemp -d "${TMPDIR:-/tmp}/essentials-freelancer-full-check.XXXXXX")
RUN_ID=$(python3 -c 'import secrets; print(secrets.token_hex(4))')
SOURCE_PROJECT="freelancer-fc-source-$RUN_ID"
TARGET_PROJECT="freelancer-fc-target-$RUN_ID"
PROXY_NETWORK="freelancer-fc-proxy-$RUN_ID"
SOURCE_ENV="$RUNTIME_DIR/source.env"
TARGET_ENV="$RUNTIME_DIR/target.env"
BACKUP_CONFIG="$RUNTIME_DIR/restic.env"
RESTIC_PASSWORD_FILE="$RUNTIME_DIR/restic-password"
RESTIC_REPOSITORY="$RUNTIME_DIR/restic-repository"
REVISION=$(git -C "$PROJECT_DIR" rev-parse HEAD)
ADMIN_USERNAME='admin'
ADMIN_PASSWORD=$(python3 -c 'import secrets; print("synthetic-" + secrets.token_hex(24))')
JWT_SECRET=$(python3 -c 'import secrets; print("synthetic-" + secrets.token_hex(32))')
SOURCE_DB_PASSWORD=$(python3 -c 'import secrets; print("synthetic-" + secrets.token_hex(24))')
TARGET_DB_PASSWORD=$(python3 -c 'import secrets; print("synthetic-" + secrets.token_hex(24))')
PLAYWRIGHT_BROWSER=

die() {
  printf 'full-check: %s\n' "$*" >&2
  exit 1
}

free_port() {
  python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
}

SOURCE_FRONTEND_PORT=$(free_port)
TARGET_FRONTEND_PORT=$(free_port)
SOURCE_SMTP_HTTP_PORT=$(free_port)
TARGET_SMTP_HTTP_PORT=$(free_port)
SOURCE_DASHBOARD_PORT=$(free_port)
TARGET_DASHBOARD_PORT=$(free_port)
while [ "$(printf '%s\n' "$SOURCE_FRONTEND_PORT" "$TARGET_FRONTEND_PORT" "$SOURCE_SMTP_HTTP_PORT" "$TARGET_SMTP_HTTP_PORT" "$SOURCE_DASHBOARD_PORT" "$TARGET_DASHBOARD_PORT" | sort -u | wc -l)" -ne 6 ]; do
  SOURCE_FRONTEND_PORT=$(free_port)
  TARGET_FRONTEND_PORT=$(free_port)
  SOURCE_SMTP_HTTP_PORT=$(free_port)
  TARGET_SMTP_HTTP_PORT=$(free_port)
  SOURCE_DASHBOARD_PORT=$(free_port)
  TARGET_DASHBOARD_PORT=$(free_port)
done

source_compose() {
  docker compose \
    --project-name "$SOURCE_PROJECT" \
    --env-file "$SOURCE_ENV" \
    -f "$PROJECT_DIR/docker-compose.yml" \
    -f "$PROJECT_DIR/docker-compose.full-check.yml" \
    "$@"
}

target_compose() {
  docker compose \
    --project-name "$TARGET_PROJECT" \
    --env-file "$TARGET_ENV" \
    -f "$PROJECT_DIR/docker-compose.yml" \
    -f "$PROJECT_DIR/docker-compose.full-check.yml" \
    "$@"
}

cleanup() {
  local status=$?
  set +e
  if [ "$status" -ne 0 ]; then
    printf 'full-check: source diagnostics follow\n' >&2
    source_compose ps >&2
    source_compose logs --no-color --tail 50 db backend frontend smtp-fixture >&2
    printf 'full-check: restore-target diagnostics follow\n' >&2
    target_compose ps >&2
    target_compose logs --no-color --tail 50 db backend frontend smtp-fixture >&2
  fi
  if ! target_compose down --volumes --remove-orphans >/dev/null 2>&1; then
    printf 'full-check: WARNING: restore-target cleanup failed\n' >&2
    status=1
  fi
  if ! source_compose down --volumes --remove-orphans >/dev/null 2>&1; then
    printf 'full-check: WARNING: source cleanup failed\n' >&2
    status=1
  fi
  if docker network inspect "$PROXY_NETWORK" >/dev/null 2>&1 && \
    ! docker network rm "$PROXY_NETWORK" >/dev/null 2>&1; then
    printf 'full-check: WARNING: proxy-network cleanup failed\n' >&2
    status=1
  fi
  for image_name in \
    "$SOURCE_PROJECT-backend" "$SOURCE_PROJECT-frontend" "$SOURCE_PROJECT-smtp-fixture" \
    "$TARGET_PROJECT-backend" "$TARGET_PROJECT-frontend" "$TARGET_PROJECT-smtp-fixture" \
    "freelancer-backend-test:$RUN_ID"; do
    if docker image inspect "$image_name" >/dev/null 2>&1 && \
      ! docker image rm "$image_name" >/dev/null 2>&1; then
      printf 'full-check: WARNING: image cleanup failed for %s\n' "$image_name" >&2
      status=1
    fi
  done
  case "$RUNTIME_DIR" in
    "${TMPDIR:-/tmp}"/essentials-freelancer-full-check.*) rm -rf -- "$RUNTIME_DIR" ;;
    *) printf 'full-check: refusing to remove unexpected runtime directory %s\n' "$RUNTIME_DIR" >&2 ;;
  esac
  exit "$status"
}
trap cleanup EXIT INT TERM

poll_url() {
  local url=$1 description=$2 deadline=$((SECONDS + 120))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if curl --fail --silent --show-error --output /dev/null --max-time 3 "$url"; then
      return
    fi
    sleep 1
  done
  die "timeout waiting for $description at $url"
}

write_env() {
  local path=$1 project=$2 db_password=$3 frontend_port=$4 dashboard_port=$5 smtp_port=$6
  umask 077
  {
    printf 'COMPOSE_PROJECT_NAME=%s\n' "$project"
    printf 'POSTGRES_PASSWORD=%s\n' "$db_password"
    printf 'JWT_SECRET=%s\n' "$JWT_SECRET"
    printf 'ADMIN_USERNAME=%s\n' "$ADMIN_USERNAME"
    printf 'ADMIN_PASSWORD=%s\n' "$ADMIN_PASSWORD"
    printf 'FRONTEND_PORT=%s\n' "$frontend_port"
    printf 'DASHBOARD_PORT=%s\n' "$dashboard_port"
    printf 'SMTP_HTTP_PORT=%s\n' "$smtp_port"
    printf 'SMTP_HOST=smtp-fixture\n'
    printf 'SMTP_PORT=1025\n'
    printf 'SMTP_FROM=freelancer@example.invalid\n'
    printf 'SMTP_USE_TLS=false\n'
    printf 'SMTP_TIMEOUT_SECONDS=1\n'
    printf 'LOGIN_RATE_LIMIT_PER_MINUTE=100\n'
    printf 'SMTP_RATE_LIMIT_PER_MINUTE=100\n'
    printf 'OFFSITE_REPOSITORY_CONFIGURED=true\n'
    printf 'OFFSITE_PASSWORD_FILE_CONFIGURED=true\n'
    printf 'PROXY_NETWORK_NAME=%s\n' "$PROXY_NETWORK"
    printf 'REPOSITORY_REVISION=%s\n' "$REVISION"
  } >"$path"
}

database_counts() {
  local stack=$1
  "$stack" exec -T db psql -U tracker -d tracker -At -F '|' -c \
    "SELECT (SELECT count(*) FROM clients), (SELECT count(*) FROM projects), (SELECT count(*) FROM time_entries), (SELECT count(*) FROM quotes), (SELECT count(*) FROM invoices), (SELECT count(*) FROM expenses), (SELECT count(*) FROM quote_catalog_items), (SELECT count(*) FROM quote_assistant_drafts), (SELECT count(*) FROM module_audit_events);" | tr -d '\r'
}

run_browser_e2e() {
  local base_url=$1 phase=$2
  (
    cd "$PROJECT_DIR/frontend"
    E2E_BASE_URL="$base_url" \
      E2E_USERNAME="$ADMIN_USERNAME" \
      E2E_PASSWORD="$ADMIN_PASSWORD" \
      E2E_PHASE="$phase" \
      PLAYWRIGHT_OUTPUT_DIR="$RUNTIME_DIR/playwright-$phase" \
      PLAYWRIGHT_CHROME_PATH="$PLAYWRIGHT_BROWSER" \
      npm run test:e2e
  )
}

for command in bash curl docker git mktemp node npm pdftotext python3 restic sha256sum sort tar; do
  command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done
docker compose version >/dev/null
write_env "$SOURCE_ENV" "$SOURCE_PROJECT" "$SOURCE_DB_PASSWORD" "$SOURCE_FRONTEND_PORT" "$SOURCE_DASHBOARD_PORT" "$SOURCE_SMTP_HTTP_PORT"
write_env "$TARGET_ENV" "$TARGET_PROJECT" "$TARGET_DB_PASSWORD" "$TARGET_FRONTEND_PORT" "$TARGET_DASHBOARD_PORT" "$TARGET_SMTP_HTTP_PORT"

printf 'full-check: backend tests and migration regression\n'
docker build --target test -t "freelancer-backend-test:$RUN_ID" "$PROJECT_DIR/backend"
docker run --rm "freelancer-backend-test:$RUN_ID"

printf 'full-check: frontend unit tests, production build, and dependency audit\n'
(
  cd "$PROJECT_DIR/frontend"
  npm ci
  npm test
  npm run build
  npm audit --audit-level=moderate
)

printf 'full-check: Android JVM tests and debug build\n'
if [ -x /home/tim/.cache/codex-toolchains/temurin17/bin/java ]; then
  export JAVA_HOME=/home/tim/.cache/codex-toolchains/temurin17
fi
if [ -z "${ANDROID_HOME:-}" ] && [ -d /home/tim/.cache/codex-toolchains/android-sdk ]; then
  export ANDROID_HOME=/home/tim/.cache/codex-toolchains/android-sdk
  export ANDROID_SDK_ROOT=$ANDROID_HOME
fi
(
  cd "$PROJECT_DIR/android"
  ./gradlew --no-daemon testDebugUnitTest assembleDebug
)

printf 'full-check: Compose, shell, fixture syntax, and secret checks\n'
source_compose config -q
bash -n "$PROJECT_DIR"/scripts/*.sh
python3 -m py_compile \
  "$PROJECT_DIR/tests/full-check/api_flow.py" \
  "$PROJECT_DIR/tests/full-check/smtp-fixture/smtp_fixture.py"
"$PROJECT_DIR/scripts/check-secrets.sh"
docker run --rm \
  -v "$PROJECT_DIR:/src:ro" \
  -w /src \
  koalaman/shellcheck-alpine:v0.10.0 sh -c 'shellcheck scripts/*.sh'

if command -v google-chrome >/dev/null 2>&1; then
  PLAYWRIGHT_BROWSER=$(command -v google-chrome)
elif command -v chromium >/dev/null 2>&1; then
  PLAYWRIGHT_BROWSER=$(command -v chromium)
else
  (cd "$PROJECT_DIR/frontend" && npx playwright install chromium)
fi

printf 'full-check: start disposable source stack\n'
docker network create "$PROXY_NETWORK" >/dev/null
source_compose up -d --build db smtp-fixture backend frontend
SOURCE_BASE_URL="http://127.0.0.1:$SOURCE_FRONTEND_PORT"
SOURCE_SMTP_URL="http://127.0.0.1:$SOURCE_SMTP_HTTP_PORT"
poll_url "$SOURCE_BASE_URL/api/ready" 'source readiness'
poll_url "$SOURCE_SMTP_URL/health" 'SMTP fixture'

printf 'full-check: API, PDF, SMTP, module, and receipt acceptance flow\n'
python3 "$PROJECT_DIR/tests/full-check/api_flow.py" \
  --base-url "$SOURCE_BASE_URL" \
  --username "$ADMIN_USERNAME" \
  --password "$ADMIN_PASSWORD" \
  --work-dir "$RUNTIME_DIR" \
  --smtp-api-url "$SOURCE_SMTP_URL" \
  --revision "$REVISION" \
  --phase source

printf 'full-check: browser navigation and axe accessibility checks\n'
run_browser_e2e "$SOURCE_BASE_URL" source

printf 'full-check: direct business export and manifest validation\n'
DIRECT_EXPORT_ROOT="$RUNTIME_DIR/direct-exports"
mkdir -p "$DIRECT_EXPORT_ROOT"
COMPOSE_PROJECT_NAME="$SOURCE_PROJECT" \
  FREELANCER_ENV_FILE="$SOURCE_ENV" \
  "$PROJECT_DIR/scripts/export-business-data.sh" "$DIRECT_EXPORT_ROOT"
DIRECT_EXPORT=$(find "$DIRECT_EXPORT_ROOT" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' -print -quit)
[ -n "$DIRECT_EXPORT" ] || die 'direct export was not created'
(cd "$DIRECT_EXPORT" && sha256sum --check --quiet SHA256SUMS)
grep -Fx "repository_commit=$REVISION" "$DIRECT_EXPORT/MANIFEST.txt" >/dev/null || die 'direct export revision mismatch'
grep -Fx 'secrets_included=no' "$DIRECT_EXPORT/MANIFEST.txt" >/dev/null || die 'direct export secret declaration missing'

printf 'full-check: encrypted local restic backup and restore rehearsal\n'
umask 077
printf 'synthetic-restic-%s\n' "$RUN_ID" >"$RESTIC_PASSWORD_FILE"
RESTIC_REPOSITORY="$RESTIC_REPOSITORY" RESTIC_PASSWORD_FILE="$RESTIC_PASSWORD_FILE" restic init
OFFSITE_EXPORT_ROOT="$RUNTIME_DIR/offsite-exports"
{
  printf 'RESTIC_REPOSITORY=%s\n' "$RESTIC_REPOSITORY"
  printf 'RESTIC_PASSWORD_FILE=%s\n' "$RESTIC_PASSWORD_FILE"
  printf 'FREELANCER_ENV_FILE=%s\n' "$SOURCE_ENV"
  printf 'LOCAL_EXPORT_ROOT=%s\n' "$OFFSITE_EXPORT_ROOT"
  printf 'RESTIC_KEEP_DAILY=1\nRESTIC_KEEP_WEEKLY=1\nRESTIC_KEEP_MONTHLY=1\n'
} >"$BACKUP_CONFIG"
printf 'full-check: disabled offsite job is rejected by module enforcement\n'
if COMPOSE_PROJECT_NAME="$SOURCE_PROJECT" \
  FREELANCER_BACKUP_CONFIG="$BACKUP_CONFIG" \
  "$PROJECT_DIR/scripts/offsite-backup.sh" >"$RUNTIME_DIR/disabled-backup.log" 2>&1; then
  die 'disabled offsite module unexpectedly created a backup'
fi
grep -F 'required module backup.offsite is not enabled' \
  "$RUNTIME_DIR/disabled-backup.log" >/dev/null || \
  die 'disabled offsite job failed for an unexpected reason'
poll_url "$SOURCE_BASE_URL/api/ready" 'source readiness after rejected backup job'
python3 "$PROJECT_DIR/tests/full-check/api_flow.py" \
  --base-url "$SOURCE_BASE_URL" \
  --username "$ADMIN_USERNAME" \
  --password "$ADMIN_PASSWORD" \
  --work-dir "$RUNTIME_DIR" \
  --revision "$REVISION" \
  --phase enable-backup
COMPOSE_PROJECT_NAME="$SOURCE_PROJECT" \
  FREELANCER_BACKUP_CONFIG="$BACKUP_CONFIG" \
  "$PROJECT_DIR/scripts/offsite-backup.sh"
RESTIC_REPOSITORY="$RESTIC_REPOSITORY" RESTIC_PASSWORD_FILE="$RESTIC_PASSWORD_FILE" restic check
SNAPSHOT_COUNT=$(RESTIC_REPOSITORY="$RESTIC_REPOSITORY" RESTIC_PASSWORD_FILE="$RESTIC_PASSWORD_FILE" restic snapshots --tag freelancer --json | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
[ "$SNAPSHOT_COUNT" -ge 1 ] || die 'restic snapshot is missing'
RESTIC_RESTORE_ROOT="$RUNTIME_DIR/restic-restore"
OFFSITE_EXPORT=$(find "$OFFSITE_EXPORT_ROOT" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' -print -quit)
[ -n "$OFFSITE_EXPORT" ] || die 'offsite export was not created'
RESTIC_REPOSITORY="$RESTIC_REPOSITORY" RESTIC_PASSWORD_FILE="$RESTIC_PASSWORD_FILE" \
  restic restore "latest:$OFFSITE_EXPORT" --tag freelancer --target "$RESTIC_RESTORE_ROOT"
RESTORED_EXPORT=$(find "$RESTIC_RESTORE_ROOT" -type f -name business.pg.dump -printf '%h\n' | head -n 1)
[ -n "$RESTORED_EXPORT" ] || die 'restic restore contains no business export'
(cd "$RESTORED_EXPORT" && sha256sum --check --quiet SHA256SUMS)
grep -Fx "repository_commit=$REVISION" "$RESTORED_EXPORT/MANIFEST.txt" >/dev/null || die 'restic-restored revision mismatch'
SOURCE_COUNTS=$(database_counts source_compose)

printf 'full-check: restore into a separately named empty Compose target\n'
target_compose build backend frontend smtp-fixture
COMPOSE_PROJECT_NAME="$TARGET_PROJECT" \
  FREELANCER_ENV_FILE="$TARGET_ENV" \
  "$PROJECT_DIR/scripts/restore-business-data.sh" "$RESTORED_EXPORT" --confirm-empty-target
target_compose up -d db smtp-fixture backend frontend
TARGET_BASE_URL="http://127.0.0.1:$TARGET_FRONTEND_PORT"
poll_url "$TARGET_BASE_URL/api/ready" 'restore-target readiness'

printf 'full-check: restored API, database counts, documents, and browser checks\n'
python3 "$PROJECT_DIR/tests/full-check/api_flow.py" \
  --base-url "$TARGET_BASE_URL" \
  --username "$ADMIN_USERNAME" \
  --password "$ADMIN_PASSWORD" \
  --work-dir "$RUNTIME_DIR" \
  --revision "$REVISION" \
  --phase restore
TARGET_COUNTS=$(database_counts target_compose)
[ "$SOURCE_COUNTS" = "$TARGET_COUNTS" ] || die "database counts differ: source=$SOURCE_COUNTS target=$TARGET_COUNTS"
run_browser_e2e "$TARGET_BASE_URL" restore

printf 'full-check: all automated checks passed (external services were simulated locally)\n'
