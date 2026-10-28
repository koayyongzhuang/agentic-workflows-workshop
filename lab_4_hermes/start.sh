#!/usr/bin/env bash
# Lab 4: start Hermes Agent inside the workshop container (run by `make hermes`).
#   1. copy the workshop's Hermes settings into Hermes's home folder
#   2. start the citizen-services MCP server (port 8765, container only)
#   3. start the Hermes gateway, which runs scheduled (cron) jobs
#   4. start the web dashboard on port 9119 (open http://localhost:9119)
set -uo pipefail

export HERMES_HOME="${HERMES_HOME:-/root/.hermes}"
# The dashboard needs a login. These defaults are fine on your own laptop: the
# port is published on 127.0.0.1 only. Override them in .env if you like.
export HERMES_DASHBOARD_BASIC_AUTH_USERNAME="${HERMES_DASHBOARD_BASIC_AUTH_USERNAME:-workshop}"
export HERMES_DASHBOARD_BASIC_AUTH_PASSWORD="${HERMES_DASHBOARD_BASIC_AUTH_PASSWORD:-stack26}"
export HERMES_DASHBOARD_BASIC_AUTH_SECRET="${HERMES_DASHBOARD_BASIC_AUTH_SECRET:-stack26-workshop-local-only-0123456789abcdef}"

if ! command -v hermes >/dev/null; then
  echo "Hermes isn't installed in this container yet. Run: make up-build" >&2
  exit 1
fi
if ! command -v node >/dev/null; then
  echo "Node.js is missing, so the dashboard chat won't work. Rebuild the container: make up-build" >&2
  exit 1
fi
# Pick the model provider: HERMES_PROVIDER from .env if set, otherwise whichever
# key is filled in (Bedrock first, then OpenRouter, then OpenAI).
provider="${HERMES_PROVIDER:-}"
if [ -z "$provider" ]; then
  if [ -n "${AWS_BEARER_TOKEN_BEDROCK:-}" ]; then provider=bedrock
  elif [ -n "${OPENROUTER_API_KEY:-}" ]; then provider=openrouter
  elif [ -n "${OPENAI_API_KEY:-}" ]; then provider=openai
  else provider=bedrock
  fi
fi
case "$provider" in
  bedrock|aws)
    key_name=AWS_BEARER_TOKEN_BEDROCK
    export HERMES_PROVIDER=bedrock      # region comes from AWS_REGION in .env (default ap-southeast-1)
    export AWS_REGION="${AWS_REGION:-ap-southeast-1}"
    export HERMES_MODEL="${HERMES_MODEL:-global.anthropic.claude-sonnet-4-6}" ;;
  openrouter)
    key_name=OPENROUTER_API_KEY
    export HERMES_PROVIDER=openrouter
    export HERMES_MODEL="${HERMES_MODEL:-openai/gpt-6-luna}" ;;
  openai|openai-api)
    key_name=OPENAI_API_KEY
    export HERMES_PROVIDER=openai-api   # Hermes's name for OpenAI direct; plain "openai" means OpenRouter
    export HERMES_MODEL="${HERMES_MODEL:-gpt-6-luna}" ;;
  *)
    echo "HERMES_PROVIDER in .env must be bedrock, openrouter or openai (got: $provider)." >&2
    exit 1 ;;
esac
if [ -z "${!key_name:-}" ]; then
  echo "Warning: $key_name is empty in .env, so Hermes can't call the model." >&2
fi

mkdir -p "$HERMES_HOME"
# Copy the settings, filling in ${HERMES_PROVIDER} and ${HERMES_MODEL}.
sed -e "s|\${HERMES_PROVIDER}|$HERMES_PROVIDER|" -e "s|\${HERMES_MODEL}|$HERMES_MODEL|" \
  /app/lab_4_hermes/config.yaml > "$HERMES_HOME/config.yaml"
cp /app/lab_4_hermes/SOUL.md "$HERMES_HOME/SOUL.md"

python -m workshop.mcp_server --port 8765 > /tmp/citizen_mcp.log 2>&1 &
hermes gateway run > /tmp/hermes_gateway.log 2>&1 &
trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM

echo
echo "  Hermes Agent → http://localhost:9119   (Chrome)"
echo "  Model:         $HERMES_MODEL via $HERMES_PROVIDER"
echo "  Sign in as:    ${HERMES_DASHBOARD_BASIC_AUTH_USERNAME} / ${HERMES_DASHBOARD_BASIC_AUTH_PASSWORD}"
echo "  Stop with Ctrl-C. Logs: /tmp/citizen_mcp.log, /tmp/hermes_gateway.log"
echo
hermes dashboard --host 0.0.0.0 --port 9119 --no-open --skip-build
