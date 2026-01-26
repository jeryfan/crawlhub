#!/bin/bash
WORKSPACE_ROOT=$(pwd)

export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
corepack enable
cd $WORKSPACE_ROOT/admin && pnpm install
pipx install uv

echo "alias start-app=\"cd $WORKSPACE_ROOT/app && uv run python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload\"" >> ~/.bashrc
echo "alias start-worker=\"cd $WORKSPACE_ROOT/app && uv run python -m celery -A app.celery worker -P threads -c 1 --loglevel INFO -Q mail\"" >> ~/.bashrc
echo "alias start-admin=\"cd $WORKSPACE_ROOT/admin && pnpm dev\"" >> ~/.bashrc
echo "alias start-admin-prod=\"cd $WORKSPACE_ROOT/admin && pnpm build && pnpm start\"" >> ~/.bashrc
echo "alias start-containers=\"cd $WORKSPACE_ROOT/docker && docker-compose -f docker-compose.middleware.yaml -p fastapi --env-file middleware.env up -d\"" >> ~/.bashrc
echo "alias stop-containers=\"cd $WORKSPACE_ROOT/docker && docker-compose -f docker-compose.middleware.yaml -p fastapi --env-file middleware.env down\"" >> ~/.bashrc

source /home/vscode/.bashrc
