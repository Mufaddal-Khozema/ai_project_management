#!/bin/bash
# start-dev.sh — Start all microservices locally for development

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Starting CoordinaAI microservice stack from $ROOT"

# ── 1. Shared Infrastructure (Docker) ──────────────────────────────────────────
echo "[1/4] Starting Docker infrastructure (Kafka, Redis, Mongo, Kafka UI)..."
docker compose -f "$ROOT/docker/docker-compose.yml" up -d kafka kafka-init kafka-ui redis mongo
echo "  Kafka UI  → http://localhost:8080"
echo "  Redis     → localhost:6379"
echo "  MongoDB   → localhost:27017"

# ── 2. Litestar Root Backend (Port 8000) ───────────────────────────────────────
echo "[2/4] Starting Litestar Root Backend..."
cd "$ROOT/backend"
if [ -d "venv" ]; then
  source venv/bin/activate || source venv/Scripts/activate 2>/dev/null || true
fi
granian --interface asgi main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "  Root Backend → http://localhost:8000/docs (pid $BACKEND_PID)"

# ── 3. Next.js SaaS Website (Port 3000) ────────────────────────────────────────
echo "[3/4] Starting Next.js Web Dashboard..."
cd "$ROOT/website"
npm run dev &
WEB_PID=$!
echo "  Web Dashboard → http://localhost:3000 (pid $WEB_PID)"

# ── 4. Scrum Master AI Voice Bot (Port 3001) ───────────────────────────────────
echo "[4/4] Starting Scrum Master AI (Voice Bot Backend)..."
cd "$ROOT/scrum-master-ai"
npm run dev &
VOICE_PID=$!
echo "  Voice Bot API → http://localhost:3001 (pid $VOICE_PID)"

echo ""
echo "─────────────────────────────────────────────────────────"
echo "Core microservices are running. To start the Discord Text Bot:"
echo ""
echo "  cd $ROOT/agent-bridge && python main.py"
echo ""
echo "Press Ctrl+C to stop background services."
echo "─────────────────────────────────────────────────────────"

trap "kill $BACKEND_PID $WEB_PID $VOICE_PID 2>/dev/null; docker compose -f $ROOT/docker/docker-compose.yml stop kafka kafka-ui redis mongo" EXIT
wait
