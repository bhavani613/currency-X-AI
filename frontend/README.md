# CurrencyX AI — Frontend

React 19 + Vite single-page app for CurrencyX AI (see the root `../README.md`
for the full project overview).

## Stack

- React 19, React Router 7
- Vite 8 + oxlint
- `lucide-react` icons
- No UI framework — plain CSS (`src/index.css`)

## Pages

| Route            | Page                  | Notes                                   |
|------------------|-----------------------|-----------------------------------------|
| `/`              | Home                  | Payment analysis form                   |
| `/login`         | Login                 | JWT login                               |
| `/signup`        | Signup                | Strong-password client validation       |
| `/dashboard`     | Dashboard             | Stats + recent transactions (localStorage) |
| `/analyze`       | AnalyzePayment        | Payment analysis + method comparison    |
| `/checkout`      | Checkout              | Razorpay (or demo) checkout + verify    |
| `/success`       | PaymentSuccess        | Verified payment confirmation           |
| `/advisor`       | AI Advisor            | Deterministic insights (+ AI badge when `ai_enhanced`) |
| `/recovery`      | Revenue Recovery      | User's recovery cases                   |
| `/recovery/:id`  | RecoveryCaseDetail    | Case detail + retry/dismiss             |
| `/transactions`  | Transactions          | Local verified-transaction history      |
| `/profile`       | Profile               | User profile                            |

## Local services

- `src/services/api.js` — REST client for the FastAPI backend
  (`VITE_API_BASE_URL` or `http://127.0.0.1:8000/api/v1`).
- `src/services/transactionService.js` — prototype persistence of **verified**
  payments only (localStorage, deduplicated by Razorpay IDs).
- `src/services/retryPrefill.js` — restores original payment fields when a
  recovery retry navigates back through Analyze → Checkout.
- `src/context/AuthContext.jsx` — JWT session state.

## Develop

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`.

## Build

```powershell
npm run build
```

Output goes to `dist/`. The backend must be running on port 8000 (or set
`VITE_API_BASE_URL`) for live data; without it the app shows connection errors
gracefully.

## Deploy to Vercel

The frontend is a standalone Vite single-page app in this subdirectory. The
FastAPI backend is deployed **separately** — do not try to run the backend (or
PostgreSQL/Redis/RabbitMQ/Qdrant) inside the Vercel build.

### Project settings (Vercel dashboard)

When importing this repo (or the `frontend/` folder) into Vercel:

| Setting           | Value           | Notes                                                       |
|-------------------|-----------------|-------------------------------------------------------------|
| Framework Preset  | `Vite`          | Auto-detected; keep default.                                |
| Root Directory    | `frontend`      | The app lives in `frontend/`, not the repo root.             |
| Build Command     | `npm run build` | Vite default.                                               |
| Output Directory  | `dist`          | Vite default.                                               |
| Install Command   | `npm install`   | Uses the committed `package-lock.json`.                     |
| Node.js version   | `22`            | Pinned via `.nvmrc` (Vite 8 requires Node >= 20.19 / >= 22). |

### Environment variables

Set these in **Project Settings → Environment Variables** (Production).
They are baked into the build at deploy time:

| Variable             | Required | Description                                                  |
|----------------------|----------|--------------------------------------------------------------|
| `VITE_API_BASE_URL`  | **Yes**  | Absolute URL of the deployed FastAPI backend, e.g.           |
|                      |          | `https://currencyx-backend.onrender.com/api/v1`. Must NOT    |
|                      |          | be `localhost`/ `127.0.0.1` from a deployed environment.     |

Example:

```bash
vercel --cwd frontend --prod --build-env VITE_API_BASE_URL=https://currencyx-backend.onrender.com/api/v1
```

### SPA routing

`frontend/vercel.json` rewrites every non-asset path to `/index.html` so that
refreshing client-side routes (`/login`, `/signup`, `/transactions`,
`/checkout`, `/analyze`, `/advisor`, `/recovery`, …) does not return a 404.
Vercel serves the static `dist/assets/*` files first; only unmatched paths
fall through to the SPA shell.

### Backend (separate deployment)

The backend is **not** deployed by Vercel. To make the deployed frontend talk
to the backend:

1. Deploy `backend/` somewhere (e.g. Render/Railway/Fly.io with PostgreSQL).
2. Set the backend env var `CORS_ORIGINS` to include your Vercel domain
   (see `backend/.env.example`).
3. Set `VITE_API_BASE_URL` above to that backend's URL.

