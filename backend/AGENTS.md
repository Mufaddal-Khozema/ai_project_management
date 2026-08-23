# Backend Architecture Guide

## Philosophy

We treat `litestar-fullstack` as a reference we pull from, not a framework we conform to. We only extract patterns that serve us directly — everything else is discarded.

## Constitution

### We believe in:
- **OpenAPI** — every request/response is structured, typed, and documented via Pydantic schemas. No raw dicts, no guesswork.
- **Typing** — robust type safety end-to-end. Litestar + Pydantic enforce this at the boundary.
- **Logging** — exceptions get logged. Important lifecycle events get logged. Use `structlog` or standard `logging` at module level.

### We don't believe in:
- **ORMs** — no SQLAlchemy models, no Alembic migrations.
- **Controllers** — no class-based controllers with `@Controller()`. Plain route functions only.
- **Service layer classes** — no `class UserService:`. Services are just modules of plain functions.

## Structure

```
backend/
├── routes/              # Route definitions (one file per domain)
│   ├── __init__.py      # Collects all routers
│   ├── auth.py
│   ├── users.py
│   ├── workspaces.py
│   ├── payments.py
│   └── health.py
├── services/            # Plain-function modules: orchestration logic
│   ├── auth.py
│   ├── users.py
│   └── workspace.py
├── repositories/        # Plain-function modules: sqeleton query wrappers
│   ├── user_repo.py
│   ├── workspace_repo.py
│   └── payment_repo.py
├── lib/                 # Pure utilities (no db, no litestar)
│   ├── email.py
│   ├── auth.py          # Token encode/decode, password hashing
│   └── db.py            # Connection pool, sqeleton builder helpers
├── schemas/             # Pydantic models (request/response)
│   ├── auth.py
│   ├── user.py
│   └── workspace.py
├── config.py            # Settings via pydantic-settings / python-dotenv
├── app.py               # Litestar app factory
├── requirements.txt
└── AGENTS.md
```

## Call Chain

```
Route → Service (module of functions) → Repository (module of sqeleton wrappers) → DB
```

Each layer is a plain module of functions — no classes, no `self`, no inheritance.

### Route

```python
@router.post("/users", dto=UserCreateDTO)
async def create_user(data: UserCreate, request: Request) -> UserResponse:
    logger.info("creating user", email=data.email)
    try:
        user = user_service.create(db_session, data)
        logger.info("user created", user_id=user.id)
        return user
    except DuplicateEmail as e:
        logger.warning("duplicate email", email=data.email)
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        logger.exception("user creation failed")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Service

```python
def create(db: Database, data: UserCreate) -> User:
    existing = user_repo.find_by_email(db, data.email)
    if existing:
        raise DuplicateEmail(f"Email {data.email} already registered")
    hashed = hash_password(data.password)
    return user_repo.insert(db, email=data.email, password_hash=hashed)
```

### Repository

```python
def find_by_email(db: Database, email: str) -> User | None:
    query = db.query.from_(table_user).select().where(table_user.email == email)
    return db.fetch_one(query)

def insert(db: Database, email: str, password_hash: str) -> User:
    query = db.query.from_(table_user).insert().set(
        table_user.email, email,
        table_user.password_hash, password_hash,
    )
    return db.fetch_one(query.returning(literal("*")))
```

## What we pull from litestar-fullstack

| Pull | Skip |
|---|---|
| Litestar app setup (`Litestar()`, plugins, middleware) | Domain-driven directory layout |
| OpenAPI via Pydantic (`@route`, `dto`) | SQLAlchemy models |
| Auth patterns (JWT middleware, OAuth flow) | Alembic migrations |
| Email integration patterns | Service layer *classes* |
| Exception handling patterns | Controller classes |
| Logging setup (structlog) | Repository *classes* |
| PyOTP for MFA | SAQ/worker setup |
| Litestar CLI (`run`, `reload`) | Vite integration |

## Decision Record

- We use **sqeleton** for query building — composable, typed, no ORM magic. Repositories are modules of functions wrapping sqeleton queries.
- We use **Litestar's native JWT** (`litestar-jwt`) for auth.
- We use **`httpx` + OAuth2** for social login flows.
- We use **`pyotp`** for TOTP/MFA.
- We send email via **`litestar-email`**.
- Config comes from **`python-dotenv`** + environment variables.
- No classes in services or repositories — just modules with plain functions.
