#!/usr/bin/env bash
# Export consistent business data and upload it to an encrypted restic repository.
set -Eeuo pipefail

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
CONFIG_FILE=${FREELANCER_BACKUP_CONFIG:-/etc/freelancer-backup.env}
MODE=${1:-backup}

die() {
  printf 'offsite-backup: %s\n' "$*" >&2
  exit 1
}

[ -f "$CONFIG_FILE" ] || die "missing $CONFIG_FILE"
# shellcheck disable=SC1090
source "$CONFIG_FILE"

: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY must be set}"
: "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE must be set}"
: "${FREELANCER_ENV_FILE:?FREELANCER_ENV_FILE must be set}"
LOCAL_EXPORT_ROOT=${LOCAL_EXPORT_ROOT:-"$PROJECT_DIR/backups"}
RESTIC_KEEP_DAILY=${RESTIC_KEEP_DAILY:-7}
RESTIC_KEEP_WEEKLY=${RESTIC_KEEP_WEEKLY:-5}
RESTIC_KEEP_MONTHLY=${RESTIC_KEEP_MONTHLY:-12}
RESTIC_APPLY_RETENTION=${RESTIC_APPLY_RETENTION:-false}
BACKUP_EVIDENCE_FILE=${BACKUP_EVIDENCE_FILE:-}

for command in restic find sort python3 sha256sum; do
  command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done
[ -r "$RESTIC_PASSWORD_FILE" ] || die 'restic password file is not readable'
[ -r "$FREELANCER_ENV_FILE" ] || die 'Freelancer environment file is not readable'

export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE FREELANCER_ENV_FILE
if [ -n "${RCLONE_CONFIG:-}" ]; then
  [ -r "$RCLONE_CONFIG" ] || die 'rclone configuration is not readable'
  export RCLONE_CONFIG
fi

case "$MODE" in
  --inventory-only)
    restic snapshots --tag freelancer --json | python3 -c '
import datetime, hashlib, json, sys
items = json.load(sys.stdin)
latest = max(items, key=lambda item: item.get("time", ""), default=None)
print(json.dumps({
    "snapshot_count": len(items),
    "latest_snapshot_id_redacted": (
        "sha256:" + hashlib.sha256(latest["id"].encode()).hexdigest()[:12]
        if latest and latest.get("id") else None
    ),
    "latest_snapshot_time_utc": latest.get("time") if latest else None,
}, sort_keys=True))
'
    exit 0
    ;;
  backup) ;;
  *) die 'usage: offsite-backup.sh [--inventory-only]' ;;
esac

FREELANCER_REQUIRED_MODULES='export.business_data backup.offsite' \
  "$SCRIPT_DIR/export-business-data.sh" "$LOCAL_EXPORT_ROOT"
latest_export=$(find "$LOCAL_EXPORT_ROOT" -mindepth 1 -maxdepth 1 -type d \
  -name '20??????T??????Z' -printf '%f\t%p\n' | sort | tail -n 1 | cut -f 2-)
[ -n "$latest_export" ] || die 'no completed export was found'

backup_result=$(restic backup --json --tag freelancer -- "$latest_export")
snapshot_id=$(printf '%s\n' "$backup_result" | python3 -c '
import json, sys
snapshot_id = None
for line in sys.stdin:
    try:
        item = json.loads(line)
    except json.JSONDecodeError:
        continue
    snapshot_id = item.get("snapshot_id") or snapshot_id
if not snapshot_id:
    raise SystemExit("restic backup did not return a snapshot ID")
print(snapshot_id)
')
case "$snapshot_id" in
  ''|*[!0-9a-f]*) die 'restic returned an invalid snapshot ID' ;;
esac
restic check
case "$RESTIC_APPLY_RETENTION" in
  true)
    restic forget \
      --tag freelancer \
      --keep-daily "$RESTIC_KEEP_DAILY" \
      --keep-weekly "$RESTIC_KEEP_WEEKLY" \
      --keep-monthly "$RESTIC_KEEP_MONTHLY" \
      --prune
    ;;
  false) ;;
  *) die 'RESTIC_APPLY_RETENTION must be true or false' ;;
esac

if [ -n "$BACKUP_EVIDENCE_FILE" ]; then
  evidence_dir=$(dirname -- "$BACKUP_EVIDENCE_FILE")
  mkdir -p -- "$evidence_dir"
  umask 077
  BACKUP_EVIDENCE_FILE="$BACKUP_EVIDENCE_FILE" \
    SNAPSHOT_ID="$snapshot_id" RETENTION_APPLIED="$RESTIC_APPLY_RETENTION" \
    python3 -c '
import datetime, json, os, pathlib
path = pathlib.Path(os.environ["BACKUP_EVIDENCE_FILE"])
path.write_text(json.dumps({
    "completed_at_utc": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
    "snapshot_id": os.environ["SNAPSHOT_ID"],
    "repository_check": "passed",
    "retention_applied": os.environ["RETENTION_APPLIED"] == "true",
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
'
fi

snapshot_redacted=$(printf '%s' "$snapshot_id" | sha256sum | cut -c 1-12)
printf 'offsite-backup: encrypted snapshot sha256:%s and repository check completed\n' \
  "$snapshot_redacted"
