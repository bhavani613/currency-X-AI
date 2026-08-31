# CurrencyX AI - Backend

AI-powered cross-border payment intelligence API backend built with FastAPI.

## Prerequisites

- Python 3.10+
- pip
- PostgreSQL 12+ (running on `localhost:5433` — see Database setup below)

### Database

The project expects a PostgreSQL database named `currencyx`.  If you are
starting from scratch you can create it with the helper script:

```bash
python create_db.py
```

This script tries several common passwords for the `postgres` user.  If none
work, see the manual steps below.

**Manual setup (recommended for a fresh local installation):**

```bash
# 1. Initialise a fresh data directory with trust auth
initdb -D pgdata -U postgres --auth=trust

# 2. Start the server on port 5433 (keeps it separate from any existing
#    PostgreSQL instance that may already use port 5432)
pg_ctl -D pgdata -l logfile -o "-c listen_addresses=localhost -c port=5433" start

# 3. Create the database
psql -h localhost -p 5433 -U postgres -w -c "CREATE DATABASE currencyx"

# 4. (Optional) Set a password for the postgres user
psql -h localhost -p 5433 -U postgres -w -c "ALTER USER postgres WITH PASSWORD 'postgres'"
```

> **Note:** The `.env` file in this project is pre-configured for
> `localhost:5433` with the password `postgres`.  If you use a different
> setup, update the `DATABASE_URL` in `.env` accordingly.

## Setup (Windows)

1. Create virtual environment:

   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

   If you get an execution policy error, run this first (in PowerShell):

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Ensure the `.env` file is present (already configured for port 5433):

   ```bash
   # .env is already set up with the correct DATABASE_URL
   # DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/currencyx
   ```

   Database tables are created automatically on startup via the lifespan handler.

5. Run the backend server (development mode):

   ```bash
   uvicorn main:app --reload
   ```

   The API will be available at `http://127.0.0.1:8000`.

## API Endpoints

| Method | Endpoint                    | Description                                  |
|--------|-----------------------------|----------------------------------------------|
| GET    | `/`                         | Health check & welcome message               |
| GET    | `/health`                   | Detailed health status                       |
| GET    | `/api/v1/info`              | Basic API information                        |
| POST   | `/api/v1/payments/analyze`  | Analyze an international payment             |
| GET    | `/api/v1/payments/history`  | List recent payment analyses                 |
| GET    | `/api/v1/payments/{id}`     | Retrieve a single payment analysis by ID     |

## API Documentation

FastAPI automatically generates interactive API docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Project Structure

```
backend/
├── main.py                  # Main FastAPI application (router + lifespan)
├── requirements.txt         # Python dependencies
├── .gitignore               # Git ignore rules
├── README.md                # This file
├── .env                     # Environment configuration (git-ignored)
├── .env.example             # Template for .env
├── create_db.py             # Helper script to create the database
├── pgdata/                  # Local PostgreSQL data directory (port 5433)
└── app/
    ├── __init__.py
    ├── config.py            # Application configuration (pydantic-settings)
    ├── api/
    │   ├── __init__.py
    │   └── payments.py      # API routes (analyze, history, detail)
    ├── schemas/
    │   ├── __init__.py
    │   └── payment.py       # Pydantic request/response models
    ├── services/
    │   ├── __init__.py
    │   ├── payment_analyzer.py    # Business logic (cost calc, recommendations)
    │   └── payment_repository.py  # DB persistence layer
    ├── database/
    │   ├── __init__.py
    │   ├── base.py          # SQLAlchemy Base + metadata
    │   └── connection.py    # Async engine, session factory, init_db()
    └── models/
        ├── __init__.py
        └── payment.py       # SQLAlchemy ORM models
```