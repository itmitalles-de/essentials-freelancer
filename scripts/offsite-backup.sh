#!/usr/bin/env bash
# Export consistent business data and upload it to an encrypted restic repository.
set -Eeuo pipefail

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
CONFIG_FILE=${FREELANCER_BACKUP_CONFIG:-/etc/freelancer-backup.env}

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

for command in restic find sort; do
  command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done
[ -r "$RESTIC_PASSWORD_FILE" ] || die 'restic password file is not readable'
[ -r "$FREELANCER_ENV_FILE" ] || die 'Freelancer environment file is not readable'

export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE FREELANCER_ENV_FILE
if [ -n "${RCLONE_CONFIG:-}" ]; then
  [ -r "$RCLONE_CONFIG" ] || die 'rclone configuration is not readable'
  export RCLONE_CONFIG
fi

FREELANCER_REQUIRED_MODULES='export.business_data backup.offsite' \
  "$SCRIPT_DIR/export-business-data.sh" "$LOCAL_EXPORT_ROOT"
latest_export=$(find "$LOCAL_EXPORT_ROOT" -mindepth 1 -maxdepth 1 -type d \
  -name '20??????T??????Z' -printf '%f\t%p\n' | sort | tail -n 1 | cut -f 2-)
[ -n "$latest_export" ] || die 'no completed export was found'

restic backup --tag freelancer -- "$latest_export"
restic check
restic forget \
  --tag freelancer \
  --keep-daily "$RESTIC_KEEP_DAILY" \
  --keep-weekly "$RESTIC_KEEP_WEEKLY" \
  --keep-monthly "$RESTIC_KEEP_MONTHLY" \
  --prune

printf 'offsite-backup: encrypted snapshot and repository check completed\n'
