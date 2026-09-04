# CurrencyX AI — Backend

FastAPI backend for CurrencyX AI: payment analysis, Razorpay (demo or TEST
mode), JWT authentication, revenue recovery, and an optional AI explanation
layer. The deterministic engines remain the source of truth.

## Stack

- FastAPI + uvicorn
- SQLAlchemy (async) + asyncpg → PostgreSQL
- Pydantic v2 schemas
- PyJWT (bearer tokens) + bcrypt (password hashes)
- Razorpay SDK (TEST mode) or built-in Demo Mode

## Setup (Windows)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend/.env` (see `.env.example`). The key value is `DATABASE_URL`,
e.g.:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/currencyx
RAZORPAY_DEMO_MODE=true
```

Database tables are created automatically on startup. Then run:

```powershell
uvicorn main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- Readiness (DB): `http://127.0.0.1:8000/ready`

## Common Endpoints

| Method | Endpoint                              | Auth | Description                           |
|--------|---------------------------------------|------|---------------------------------------|
| POST   | `/api/v1/auth/signup`                 | —    | Register (strong-password policy)     |
| POST   | `/api/v1/auth/login`                  | —    | Login → JWT                          |
| POST   | `/api/v1/payments/analyze`            | —    | Payment analysis                     |
| POST   | `/api/v1/payments/create-order`       | —    | Razorpay demo/TEST order             |
| POST   | `/api/v1/payments/verify`             | —    | Server-side signature verification   |
| POST   | `/api/v1/advisor/analyze`             | —    | Deterministic advisor insights       |
| POST   | `/api/v1/recovery/payment-attempts`   | JWT  | Record a payment attempt             |
| POST   | `/api/v1/recovery/analyze-failure`    | JWT  | Analyze failure → recovery recommendation |
| GET    | `/api/v1/recovery/cases`              | JWT  | List the user's recovery cases       |
| GET    | `/api/v1/recovery/cases/{id}`         | JWT  | Case detail (matches attempt OR rec id) |
| POST   | `/api/v1/recovery/cases/{id}/retry`   | JWT  | Accept recommendation (prepares retry) |
| POST   | `/api/v1/recovery/cases/{id}/complete`| JWT  | Mark recovered after verified success |
| POST   | `/api/v1/recovery/cases/{id}/dismiss` | JWT  | Dismiss a recommendation             |
| GET    | `/api/v1/recovery/summary`            | JWT  | At-risk / recovered / pending totals |

## Demo Mode

`RAZORPAY_DEMO_MODE=true` (default) lets the whole payment flow run with no
credentials: `demo_order_*` / `demo_payment_*` IDs, no real charges, and a
`"demo": true` flag on responses. Setting it to `false` requires valid
`RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` and enables the real TEST-mode flow.
The secret is never sent to the frontend.

## Optional AI Explanation Layer

- Deterministic logic (analysis, fees, recovery) always runs and is authoritative.
- `AI_ENABLED=false` (default) → rule-based advisor response (`ai_enhanced: false`).
- `AI_ENABLED=true` + valid provider (`openai` / `ollama` / `huggingface`)
  → LLM-generated explanations merged in (`ai_enhanced: true`).
- Missing key / provider outage → safe deterministic fallback, never crashes.

## Tests

```powershell
pip install -r requirements-dev.txt
venv\Scripts\python -m pytest tests -q
```

Tests run against an in-memory SQLite database (never your PostgreSQL data) and
require no Razorpay or OpenAI credentials.

## Project Structure

```
backend/
├── main.py               # FastAPI app + lifespan + health/ready
├── create_db.py          # Optional DB bootstrap helper
├── requirements.txt      # Runtime dependencies
├── requirements-dev.txt  # Test-only dependencies
├── pytest.ini
├── tests/                # pytest suite (isolated SQLite)
└── app/
    ├── config.py         # pydantic-settings env config
    ├── api/              # Route handlers (thin)
    ├── services/         # Deterministic engines + AI provider wrapper
    ├── models/           # SQLAlchemy ORM models
    ├── schemas/          # Pydantic request/response models
    ├── core/             # JWT deps, security helpers
    └── database/         # Engine, session, Base metadata
```
