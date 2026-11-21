#!/bin/sh
# Authentication stays in the operator's local SSH configuration and agent.
set -eu
: "${ASSISTANT_VPS_SSH_HOST:?Set ASSISTANT_VPS_SSH_HOST to your local SSH host alias}"
exec ssh -- "$ASSISTANT_VPS_SSH_HOST" "$@"
