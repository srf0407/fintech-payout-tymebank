## Fintech Payouts (TymeBank) — Backend Quickstart

### Prerequisites
- Python 3.9+ (virtualenv created at `venv/`)
- Docker (for PostgreSQL)

### Environment
Create `backend/app/.env` with your values. Example:
```
POSTGRES_USER=app_user
POSTGRES_PASSWORD=password123
POSTGRES_DB=fintech_tymbank_db

DATABASE_URL=postgresql://app_user:password123@localhost:5433/fintech_tymbank_db
SECRET_KEY=dev-secret
WEBHOOK_SECRET=dev-webhook
```

### Start Postgres
From the repository root:
```
docker compose up -d db
```

### Database migrations
Run Alembic migrations (exact command you used on Windows PowerShell):
```
venv\Scripts\alembic.exe -c backend/app/db/alembic.ini upgrade head
```
Alternative (works cross-shell):
```
./venv/Scripts/python.exe -m alembic -c backend/app/db/alembic.ini upgrade head
```

Verify tables (inside the container):
```
docker exec -it fintech_postgres psql -U app_user -d fintech_tymbank_db -c "\\dt"
docker exec -it fintech_postgres psql -U app_user -d fintech_tymbank_db -c "\\d+ payouts"
```

### Run the API
```
./venv/Scripts/uvicorn.exe backend.app.main:app --reload
```

### Routes (high-level)
- `GET /health` — Health check.
- `GET /` — Root info.
- `POST /payouts` — Create payout (idempotent via `Idempotency-Key` header). Calls mock provider with retries.
- `GET /payouts?page=N` — Paginated payouts list.
- `POST /webhooks/payments` — Receive provider webhooks (HMAC/JWT verification, idempotent).

Notes:
- Schema/types use Pydantic v2; DB uses async SQLAlchemy + asyncpg.
- Observability: structured logging with correlation IDs.
- Security: inputs validated, secrets in `.env`, UTC timestamps, ISO 4217 currency.


