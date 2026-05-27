#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-leann@zeus.diffbot.com}"
REMOTE_DIR="${REMOTE_DIR:-~/zeus/materials-event-modeling}"
SSH_OPTS=(-A -o BatchMode=yes -o ConnectTimeout=10)

ssh "${SSH_OPTS[@]}" "$REMOTE" "mkdir -p $REMOTE_DIR"

rsync -az --delete \
  -e "ssh -A -o BatchMode=yes -o ConnectTimeout=10" \
  --exclude ".venv/" \
  --exclude "data/raw/**" \
  --exclude "data/interim/**" \
  --exclude "data/processed/**" \
  --exclude "outputs/" \
  --exclude "checkpoints/" \
  --exclude "runs/" \
  --exclude "wandb/" \
  ./ "$REMOTE:$REMOTE_DIR/"

ssh "${SSH_OPTS[@]}" "$REMOTE" \
  "cd $REMOTE_DIR && mkdir -p data/raw data/interim data/processed && printf '\n' > data/raw/.gitkeep && printf '\n' > data/interim/.gitkeep && printf '\n' > data/processed/.gitkeep && git status --short"

