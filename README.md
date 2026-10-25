# 🤖 AI Project Management & Scrum Master System

An event-driven AI project management ecosystem featuring an **autonomous Discord AI Text Agent**, a **real-time AI Voice Scrum Master (Gemini Live)**, a **unified Litestar Backend**, and a **Next.js 15 Web Application**.

---

## 🏗️ Architecture & Component Overview

```
                                  ┌───────────────────────────┐
                                  │      Discord Server       │
                                  │  - Text Channels (#chat)  │
                                  │  - Voice Channels (🔊)    │
                                  └─────────────┬─────────────┘
                                                │
                     ┌──────────────────────────┴──────────────────────────┐
                     │ (Text Gateway)                         (Voice Gateway)
                     ▼                                                     ▼
        ┌─────────────────────────┐                           ┌─────────────────────────┐
        │      agent-bridge       │   HTTP Start / Stop       │     scrum-master-ai     │
        │  (Python Discord Bot)   ├──────────────────────────►│  (Node.js / Fastify:3001) │
        │  - LangChain + Gemini   │                           │  - @discordjs/voice     │
        │  - Taiga PM Toolset     │◄──────────────────────────┤  - Gemini Live WS API   │
        └────────────┬────────────┘   Kafka: meeting-events   └────────────┬────────────┘
                     │                                                     │
                     │ POST /api/identity/resolve                          │ POST /api/identity/resolve
                     │ (Bearer SERVICE_API_KEY)                            │ (Bearer SERVICE_API_KEY)
                     ▼                                                     ▼
        ┌───────────────────────────────────────────────────────────────────────────────┐
        │                                  backend/                                     │
        │                           (Litestar ASGI — Port 8000)                         │
        │  - Piccolo ORM + PostgreSQL (Neon)                                            │
        │  - Authentication (JWT), Organizations, Workspaces & Permissions              │
        │  - Identity Resolution & Fernet Token Decryption                              │
        │  - OAuth Integrations (Discord, Slack, Jira, Taiga, Google, GitHub)           │
        └───────────────────────────────────────▲───────────────────────────────────────┘
                                                │ REST API / Auth
                                                ▼
                                  ┌───────────────────────────┐
                                  │         website/          │
                                  │   (Next.js 15 — Port 3000)│
                                  │  - Workspace Dashboard    │
                                  │  - Team & PM Management   │
                                  │  - Tool Integrations UI   │
                                  └───────────────────────────┘
```

---

## 📁 Folder Structure & Responsibilities

| Directory | Language / Stack | Port | Purpose |
|---|---|---|---|
| **[`backend/`](backend/)** | Python 3.11+ / Litestar / Piccolo ORM | `8000` | Canonical central backend. Manages users, workspaces, permissions, auth, OAuth flows, and identity resolution. |
| **[`website/`](website/)** | Next.js 15 / React 19 / TypeScript / Tailwind | `3000` | Canonical web application. User dashboard, organization settings, team permissions, and third-party tool connections. |
| **[`agent-bridge/`](agent-bridge/)** | Python 3.11+ / Discord.py / LangChain / Gemini | `8003` | Autonomous Discord text bot. Listens to mentions (`@FYP`), parses intent, interacts with Taiga PM, manages memory, and triggers meetings. |
| **[`scrum-master-ai/`](scrum-master-ai/)** | Node.js 20+ / Fastify / `@discordjs/voice` | `3001` | Real-time voice meeting room. Connects Discord voice to Google Gemini Multimodal Live API over WebSockets for voice standups. |
| **[`docker/`](docker/)** | Docker Compose / KRaft | `9092, 27017, 6379` | Core event-driven infrastructure: Kafka (event broker), MongoDB (durable memory), Redis (fast context cache). |
| **[`scripts/`](scripts/)** | Bash / Shell | — | Operational scripts for Kafka topic creation, migrations, and health checks. |
| **[`docs/`](docs/)** | Markdown / Architecture specs | — | Architecture specifications, event schemas, and operational runbooks. |
| **[`discord-bot/`](discord-bot/)** | Python | — | Preserved prototype Discord bot for reference. |

---

## 🔄 Inter-Service Communication Flow

### 1. Identity & Permissions Resolution
When a user speaks in voice or mentions the bot in text:
1. `agent-bridge` or `scrum-master-ai` calls `POST http://127.0.0.1:8000/api/identity/resolve`.
2. Request headers include `Authorization: Bearer <SERVICE_API_KEY>`.
3. The root `backend` resolves the Discord user ID against workspace members, checks active subscription status, decrypts workspace PM tokens (e.g. Taiga credentials) via Fernet, and returns the verified profile.
4. If unlinked, the bot informs the user to link their account via the `website/` portal.

### 2. On-Demand Standup Meeting Flow
1. User types `@FYP start standup` in Discord text chat (`#general`).
2. `agent-bridge` calls `POST http://localhost:3001/integrations/discord/meetings/start` on `scrum-master-ai`.
3. `scrum-master-ai` auto-detects active humans in voice channels (`🔊 General`), resolves participant names via `backend`, and joins the channel via `@discordjs/voice`.
4. `scrum-master-ai` establishes a bidirectional WebSocket connection to Google's Gemini Multimodal Live API.
5. Inbound user audio (48kHz stereo Opus) is decoded and resampled to 16kHz mono PCM for Gemini.
6. Outbound Gemini speech (24kHz mono PCM) is resampled to 48kHz stereo Opus and played aloud to participants in real time.

### 3. Kafka Event Streaming & Durable Memory Sync
1. During the voice standup, `scrum-master-ai` publishes transcript chunks and action items to Kafka topic `agent-bridge.meeting-events`.
2. `agent-bridge`'s Kafka consumer receives the events and stores them in Redis (session buffer) and MongoDB (long-term memory).
3. Team members can subsequently ask `@FYP what was discussed in the standup?` or `@FYP what tasks were assigned?` in text chat, and `agent-bridge` retrieves the information via semantic vector search.

---

## 🚀 Getting Started

### 1. Environment Configuration
Copy `.env.example` or configure the root `.env` file:
```powershell
# Core Settings
BACKEND_URL=http://127.0.0.1:8000
SERVICE_API_KEY=svc_6Q22890ts96ox-oc0pavSc_OSWQZyueE8-J8AY5ytlo
DISCORD_BOT_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
MONGODB_URI=mongodb://127.0.0.1:27017/scrum-master-ai
REDIS_URL=redis://localhost:6379/0
KAFKA_BROKERS=localhost:9092
```

### 2. Start Infrastructure (Docker)
```powershell
docker compose -f docker/docker-compose.yml up -d kafka mongo redis
```

### 3. Start Root Backend (Litestar)
```powershell
cd backend
python main.py
```
*API available at `http://127.0.0.1:8000` (Docs: `http://127.0.0.1:8000/schema/swagger`)*

### 4. Start Web Application (Next.js)
```powershell
cd website
pnpm dev # or npm run dev
```
*Frontend running at `http://localhost:3000`*

### 5. Start Voice Scrum Master (`scrum-master-ai`)
```powershell
cd scrum-master-ai
npm run dev
```
*Voice service running at `http://localhost:3001`*

### 6. Start AI Text Agent (`agent-bridge`)
```powershell
cd agent-bridge
python main.py
```
*Discord bot logged in and listening for `@FYP` mentions.*

---

## 🧪 Testing

```powershell
# Voice Service Unit Tests (36 tests)
cd scrum-master-ai
npm test

# AI Text Agent Unit Tests
cd agent-bridge
pytest tests/
```
