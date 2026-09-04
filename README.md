# CurrencyX AI

AI-powered cross-border payment intelligence and revenue recovery.

CurrencyX AI analyzes international payments, compares payment methods, runs a
safe demo Razorpay checkout, and recovers revenue from failed payments — using
a **deterministic financial engine as the source of truth**, with an optional
LLM layer that only explains already-calculated results.

---

## The Problem

1. **International payments are opaque.** Users often cannot see FX markup,
   processing fees, or why one payment method costs more than another.
2. **Failed payments lose revenue.** When a payment fails, the customer's
   intent is gone — and there is no structured way to bring it back.

CurrencyX AI addresses both: transparent, method-by-method cost analysis, and a
fail → analyze → recommend → retry → recovered-revenue loop.

---

## Main Features

- **Multi-currency payment analysis** — cost breakdown, recipient amount,
  exchange-rate estimate.
- **Payment method comparison** — up to 5 methods with fees, totals, and
  potential savings.
- **Authentication & user scoping** — JWT signup/login; recovery cases are
  always scoped to the authenticated user.
- **Razorpay integration** — real TEST-mode create-order + server-side
  signature verification.
- **Safe Razorpay Demo Mode** — simulated payments with clearly identified
  `demo_order_*` / `demo_payment_*` IDs. No real money is ever charged.
- **Revenue Recovery** — deterministic engine classifies a failed payment and
  generates a recovery recommendation (probability, risk, alternative method).
- **Retry → verified payment → recovered revenue tracking** — a retried payment
  that completes through the existing verified payment flow marks the case
  `EXECUTED` and counts its revenue exactly once.
- **Deterministic AI Advisor** — clear rule-based insights for any payment.
- **Optional LLM explanation layer** — humanized *explanations only*; the
  deterministic engine remains authoritative.

---

## Architecture

```
User
  │
  ▼
React + Vite Frontend  (frontend/)
  │  REST /api/v1 (JWT)
  ▼
FastAPI Backend  (backend/app/api → services)
  │
  ├─ Payment Analysis Engine      (services/payment_analyzer.py)
  ├─ Payment/recovery persistence (services/payment_repository.py,
  │                                services/revenue_recovery.py)
  ├─ Razorpay / Demo Mode         (api/razorpay_pay.py)
  ├─ Revenue Recovery Engine      (services/revenue_recovery.py)
  └─ Optional AI Explanation      (services/ai_provider.py)
  │
  ▼
PostgreSQL  (asyncpg / SQLAlchemy)
```

### Repository layout

```
backend/
  app/
    api/       FastAPI route handlers (thin)
    services/  Deterministic engines + optional AI layer
    models/    SQLAlchemy ORM models
    schemas/   Pydantic request/response models
    core/      JWT deps, security
    config.py  Environment-based settings
  tests/       pytest suite (isolated SQLite, never touches PostgreSQL)
  main.py      App entrypoint
frontend/
  src/
    pages/     Route-level React pages
    components/ UI components
    services/  API client + local storage
    context/   Auth context
```

---

## Demo Mode (Razorpay)

Set in `backend/.env`:

```
RAZORPAY_DEMO_MODE=true
```

When demo mode is on, the backend works **without any Razorpay credentials**:

- `POST /api/v1/payments/create-order` returns an ID prefixed `demo_order_`.
- `POST /api/v1/payments/verify` accepts `demo_payment_*` IDs.
- Every response is flagged `"demo": true` so the UI can tell the difference.
- **No real money is charged.** Real Razorpay TEST-mode logic is preserved and
  used whenever `RAZORPAY_DEMO_MODE=false` with valid credentials.

---

## AI / LLM Explanation — Honest Scope

- The **deterministic engines** (payment analysis, fee calculation, recovery
  probability/status, verification) are the **source of truth**.
- The optional LLM layer **only re-phrases and personalizes** already-calculated
  structured results. It never computes fees, rates, or outcomes, and it never
  changes stored data.
- When `AI_ENABLED=false` — or no API key / provider is available — the AI
  Advisor silently uses the deterministic rule-based response
  (`ai_enhanced: false`). The application **never fails** because AI is off.

### Supported providers (backend/.env)

| Provider       | Env vars                     | Notes                                  |
|----------------|------------------------------|----------------------------------------|
| `openai`       | `AI_PROVIDER=openai`, `OPENAI_API_KEY` | Requires a (paid) key.            |
| `ollama`       | `AI_PROVIDER=ollama`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Free/local LLM, no key. |
| `huggingface`  | `AI_PROVIDER=huggingface`, `HUGGINGFACE_API_KEY` | Free tier; key optional.    |

```
AI_ENABLED=false
AI_PROVIDER=ollama
```
---
## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 12+ (local service, see `backend/.env` for `DATABASE_URL`)
- Node.js 18+ / npm

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# DB tables are created automatically on startup.
uvicorn main:app --reload
```

Backend health:

- `http://127.0.0.1:8000/health` → `{"status":"healthy",...}`
- `http://127.0.0.1:8000/ready`  → database connectivity check
- Swagger UI: `http://127.0.0.1:8000/docs`

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend dev server: `http://localhost:5173`

### Environment variables

Copy `backend/.env.example` to `backend/.env` and set:

| Variable              | Purpose                                   |
|-----------------------|-------------------------------------------|
| `DATABASE_URL`        | SQLAlchemy async PostgreSQL URL           |
| `RAZORPAY_KEY_ID`     | Public Razorpay TEST key                  |
| `RAZORPAY_KEY_SECRET` | Secret — never shipped to the frontend    |
| `RAZORPAY_DEMO_MODE`  | `true` → simulated payments (default)     |
| `JWT_SECRET`          | JWT signing secret                        |
| `AI_ENABLED`          | `false` default; deterministic advisor    |
| `AI_PROVIDER`         | `openai` / `ollama` / `huggingface`       |
| `OPENAI_API_KEY`      | Only if `AI_PROVIDER=openai`              |

Never commit real secrets.

---

## Testing

Automated backend tests use an isolated in-memory SQLite database; they never
touch the development PostgreSQL data and need no Razorpay/OpenAI keys.

```powershell
cd backend
pip install -r requirements-dev.txt
venv\Scripts\python -m pytest tests -q
```

Covered flows:

- Password policy (weak / missing-class / spaced passwords rejected; strong accepted)
- Payment analysis request handling + validation
- Razorpay demo mode (create-order, verify, no real calls required)
- Revenue Recovery (failure → recommendation, duplicate prevention,
  cross-user isolation, retry, dismiss, complete, idempotency,
  recovered-revenue single counting)
- AI Advisor deterministic fallback (no key, missing key, provider outage)
- JWT-protected route guards (unauthenticated → 401)

Frontend production build:

```powershell
cd frontend
npm run build
```

---

## Key API Endpoints

| Method | Endpoint                                | Auth | Description                          |
|--------|------------------------------------------|------|--------------------------------------|
| POST   | `/api/v1/auth/signup`                    | —    | Register (strong-password policy)    |
| POST   | `/api/v1/auth/login`                     | —    | Login → JWT                         |
| POST   | `/api/v1/payments/analyze`               | —    | Payment analysis                    |
| POST   | `/api/v1/payments/create-order`          | —    | Razorpay (or demo) order            |
| POST   | `/api/v1/payments/verify`                | —    | Server-side signature verification  |
| POST   | `/api/v1/advisor/analyze`                | —    | Deterministic advisor insights      |
| POST   | `/api/v1/recovery/payment-attempts`      | JWT  | Record a payment attempt            |
| POST   | `/api/v1/recovery/analyze-failure`       | JWT  | Analyze failure → recommendation    |
| GET    | `/api/v1/recovery/cases`                 | JWT  | User's recovery cases               |
| POST   | `/api/v1/recovery/cases/{id}/retry`      | JWT  | Accept recommendation (prepares retry) |
| POST   | `/api/v1/recovery/cases/{id}/complete`   | JWT  | Mark recovered after verified success |
| POST   | `/api/v1/recovery/cases/{id}/dismiss`    | JWT  | Dismiss recommendation              |
| GET    | `/api/v1/recovery/summary`               | JWT  | At-risk / recovered / pending totals |

---

## Security Notes

- Passwords are stored as bcrypt hashes only.
- `RAZORPAY_KEY_SECRET` stays server-side; the frontend only ever receives the
  public `key_id` (or `"demo"` in demo mode).
- API keys are backend-only; they are never sent to or stored in the browser.
- All recovery routes are user-scoped — one user can never read or modify
  another user's cases.
