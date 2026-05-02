# 🔐 Auth Service

Production-ready authentication microservice built with:

- **Falcon** (WSGI framework)
- **PostgreSQL** + **SQLAlchemy 2** (ORM)
- **JWT** access tokens + rotating **refresh tokens**
- **Apache Kafka** event streaming
- **bcrypt** password hashing
- **Swagger UI** / OpenAPI 3 docs
- **Docker** + **docker-compose**

---

## 📁 Project Structure

```
auth_service/
├── app/
│   ├── __init__.py            # Falcon app factory
│   ├── core/
│   │   ├── config.py          # Pydantic-settings config
│   │   ├── database.py        # SQLAlchemy engine + session
│   │   └── security.py        # JWT, bcrypt, token helpers
│   ├── models/
│   │   └── user.py            # User, Role, UserRole, RefreshToken ORM models
│   ├── schemas/
│   │   └── auth.py            # Pydantic request/response schemas
│   ├── services/
│   │   └── auth_service.py    # Business logic (register / login / refresh)
│   ├── resources/
│   │   ├── auth_resource.py   # Falcon route handlers
│   │   └── docs_resource.py   # Swagger UI + OpenAPI spec endpoints
│   ├── middleware/
│   │   └── auth_middleware.py # JWT middleware + rate limiter
│   ├── kafka/
│   │   └── producer.py        # Kafka producer + event helpers
│   └── openapi/
│       └── spec.py            # OpenAPI 3 JSON spec + Swagger UI HTML
├── migrations/
│   └── env.py                 # Alembic migration environment
├── scripts/
│   └── seed_db.py             # Create tables + seed default roles
├── tests/
│   └── test_auth_service.py   # Unit tests (9 tests, mocked DB)
├── .env.example
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── main.py
└── requirements.txt
```

---

## 🚀 Quick Start (Docker — recommended)

### 1. Copy and configure environment

```bash
cp .env.example .env
# Edit .env — at minimum change JWT_SECRET_KEY
```

### 2. Start all services

```bash
docker-compose up --build
```

This starts:
- PostgreSQL on `:5432`
- Kafka + Zookeeper on `:9092`
- Kafka UI on `:8080`
- Auth Service on `:8000`

### 3. Seed the database

```bash
docker-compose exec auth-service python scripts/seed_db.py
```

### 4. Open Swagger UI

```
http://localhost:8000/docs
```

---

## 🛠 Local Development (without Docker)

### Prerequisites

- Python 3.12+
- PostgreSQL running locally
- (Optional) Kafka running locally

### 1. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit DATABASE_URL, JWT_SECRET_KEY, etc.
```

### 4. Set up PostgreSQL

```sql
-- Run in psql as superuser
CREATE USER auth_user WITH PASSWORD 'auth_pass';
CREATE DATABASE auth_db OWNER auth_user;
GRANT ALL PRIVILEGES ON DATABASE auth_db TO auth_user;
```

### 5. Create tables and seed roles

```bash
python scripts/seed_db.py
```

Or use Alembic for migration-based setup:

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 6. (Optional) Set up Kafka

```bash
# Using Confluent's local script, or simply start docker-compose for just Kafka:
docker-compose up -d zookeeper kafka
```

> **Note:** The service degrades gracefully if Kafka is unavailable — events are logged to stdout instead.

### 7. Start the server

```bash
# Development (wsgiref)
python main.py

# Production (Gunicorn)
gunicorn main:application --bind 0.0.0.0:8000 --workers 4
```

---

## 📡 API Endpoints

| Method | Path         | Auth required | Description              |
|--------|-------------|---------------|--------------------------|
| POST   | /register   | No            | Create a new user        |
| POST   | /login      | No            | Authenticate, get tokens |
| POST   | /refresh    | No            | Rotate refresh token     |
| GET    | /health     | No            | Liveness probe           |
| GET    | /docs       | No            | Swagger UI               |
| GET    | /openapi.json | No          | Raw OpenAPI 3 spec       |

### Register

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "Str0ng!Pass",
    "username": "alice"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "Str0ng!Pass"
  }'
```

### Refresh Token

```bash
curl -X POST http://localhost:8000/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<your-refresh-token>"}'
```

### Protected endpoint (example)

```bash
curl -H "Authorization: Bearer <access_token>" \
     http://localhost:8000/some-protected-route
```

---

## 🔑 JWT Token Claims

```json
{
  "sub": "<user-uuid>",
  "roles": ["user"],
  "org_id": "<org-uuid-or-null>",
  "iat": 1714000000,
  "exp": 1714000900,
  "jti": "<unique-token-id>"
}
```

---

## 📨 Kafka Events

| Topic                     | Trigger                     |
|--------------------------|-----------------------------|
| `auth.user.created`      | Successful registration     |
| `auth.user.login.success`| Successful login            |
| `auth.user.login.failed` | Failed login attempt        |
| `auth.token.refreshed`   | Successful token rotation   |

All messages use a CloudEvents-style envelope:

```json
{
  "id": "<uuid>",
  "type": "auth.user.created",
  "source": "auth-service",
  "time": "2024-05-01T12:00:00Z",
  "data": { "user_id": "...", "email": "..." }
}
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

Expected output: **9 passed**

---

## 🔒 Security Notes

- Passwords are hashed with **bcrypt** (cost factor 12)
- Refresh tokens are **SHA-256 hashed** before DB storage
- Access tokens expire in **15 minutes** (configurable)
- Refresh tokens expire in **30 days** (configurable)
- Refresh tokens are **rotated** on every use (old token revoked)
- Rate limiting: **10 req / 60s** per IP (in-memory; swap with Redis for multi-process)
- All secrets loaded from **environment variables** — never hard-coded

---

## ⚙️ Configuration Reference

| Variable                          | Default                  | Description                        |
|-----------------------------------|--------------------------|------------------------------------|
| `DATABASE_URL`                    | postgresql://...         | PostgreSQL connection string       |
| `JWT_SECRET_KEY`                  | *required*               | HS256 signing key (min 32 chars)   |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 15                       | Access token TTL                   |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS`   | 30                       | Refresh token TTL                  |
| `KAFKA_BOOTSTRAP_SERVERS`         | localhost:9092           | Kafka broker address               |
| `RATE_LIMIT_REQUESTS`             | 10                       | Max requests per window            |
| `RATE_LIMIT_WINDOW_SECONDS`       | 60                       | Rate limit window                  |
| `DEFAULT_ROLE`                    | user                     | Role assigned at registration      |
