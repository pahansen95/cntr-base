#!/usr/bin/env bash

set -eEou pipefail

log() { printf 'LOG::%b\n' "$*" >&2; }

command -v 'DevAgent.sh' &> /dev/null || {
  log "DevAgent.sh not found in PATH"
  return 1
}

parse_name() {
  local name="${1:?Missing Name}"
  ### Split name by '/' & '.*'
  name="${name##*/}"
  name="${name%%.*}"
  ### Names can only have [a-zA-Z0-9_-] chars
  name="${name//[^a-zA-Z0-9_-]/}"
  printf '%s' "${name}"
}

declare ctx_name=; ctx_name="$(parse_name "${1:?Missing Context Name}")"; shift
log "Context Name: ${ctx_name}"
declare chat_name; chat_name="$(parse_name "${1:-"$(date '+%Y-%m-%d')"}")"
log "Chat Name: ${chat_name}"
DevAgent.sh DevAgent chat \
  "${WORK_DIR}/meta/Context/${ctx_name}.py" \
  "${WORK_DIR}/meta/ChatLog/${chat_name}.md"
