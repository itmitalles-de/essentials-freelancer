#!/usr/bin/env bash
# Create invented disposable data and verify the complete API/PDF core flow.
set -Eeuo pipefail

BASE_URL=${SMOKE_BASE_URL:-http://127.0.0.1:8080}
USERNAME=${SMOKE_USERNAME:-}
PASSWORD=${SMOKE_PASSWORD:-}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
WORK_DIR=$(mktemp -d)

die() {
  printf 'smoke: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  rm -rf -- "$WORK_DIR"
}
trap cleanup EXIT INT TERM

for command in curl head python3; do
  command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done
[ -n "$USERNAME" ] || die 'SMOKE_USERNAME is required'
[ -n "$PASSWORD" ] || die 'SMOKE_PASSWORD is required'

json_value() {
  local key=$1
  python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$key"
}

health=$(curl --fail --silent --show-error "$BASE_URL/api/health")
[ "$(printf '%s' "$health" | json_value status)" = ok ] || die 'health endpoint failed'

login_payload=$(python3 -c 'import json,sys; print(json.dumps({"username": sys.argv[1], "password": sys.argv[2]}))' "$USERNAME" "$PASSWORD")
login=$(curl --fail --silent --show-error \
  --header 'Content-Type: application/json' \
  --data "$login_payload" "$BASE_URL/api/auth/login")
token=$(printf '%s' "$login" | json_value access_token)
[ -n "$token" ] || die 'login returned no token'

api_json() {
  local method=$1 path=$2 payload=${3:-}
  if [ -n "$payload" ]; then
    curl --fail --silent --show-error \
      --request "$method" \
      --header "Authorization: Bearer $token" \
      --header 'Content-Type: application/json' \
      --data "$payload" "$BASE_URL$path"
  else
    curl --fail --silent --show-error \
      --request "$method" \
      --header "Authorization: Bearer $token" \
      "$BASE_URL$path"
  fi
}

client=$(api_json POST /api/clients "{\"name\":\"Example Smoke Client $STAMP\",\"email\":\"billing@example.invalid\",\"hourly_rate\":\"80.00\"}")
client_id=$(printf '%s' "$client" | json_value id)
project=$(api_json POST /api/projects "{\"client_id\":$client_id,\"name\":\"Synthetic Smoke Project $STAMP\",\"hourly_rate\":\"90.00\"}")
project_id=$(printf '%s' "$project" | json_value id)
entry=$(api_json POST /api/time-entries "{\"client_id\":$client_id,\"project_id\":$project_id,\"date\":\"$(date -u +%Y-%m-%d)\",\"description\":\"Synthetic smoke work\",\"duration_minutes\":60}")
entry_id=$(printf '%s' "$entry" | json_value id)
invoice=$(api_json POST /api/invoices "{\"client_id\":$client_id,\"time_entry_ids\":[$entry_id]}")
invoice_id=$(printf '%s' "$invoice" | json_value id)
invoice_number=$(printf '%s' "$invoice" | json_value invoice_number)

curl --fail --silent --show-error \
  --header "Authorization: Bearer $token" \
  --output "$WORK_DIR/invoice.pdf" \
  "$BASE_URL/api/invoices/$invoice_id/pdf"
[ "$(head -c 5 "$WORK_DIR/invoice.pdf")" = '%PDF-' ] || die 'invoice download is not a PDF'

quote=$(api_json POST /api/quotes "{\"client_id\":$client_id,\"project_id\":$project_id,\"line_items\":[{\"description\":\"Synthetic follow-up package\",\"quantity\":1,\"unit\":\"flat\",\"unit_price\":250}]}")
quote_id=$(printf '%s' "$quote" | json_value id)
api_json PUT "/api/quotes/$quote_id/status" '{"status":"sent"}' >/dev/null
api_json PUT "/api/quotes/$quote_id/status" '{"status":"accepted"}' >/dev/null
converted=$(api_json POST "/api/quotes/$quote_id/convert")
converted_invoice_id=$(printf '%s' "$converted" | json_value converted_invoice_id)
if [ -z "$converted_invoice_id" ] || [ "$converted_invoice_id" = None ]; then
  die 'quote conversion returned no invoice'
fi

printf 'smoke: customer -> project -> time -> invoice %s -> PDF and quote conversion passed\n' "$invoice_number"
