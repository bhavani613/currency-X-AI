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
