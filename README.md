# FinWise — Personal Finance Tracker

A privacy-first, AI-powered personal finance assistant for Indian users.

> **Disclaimer:** FinWise is not a bank or SEBI-registered advisor. Forecasts and
> suggestions are estimates, not guarantees. Never share your bank passwords or UPI PINs.

---

## Demo Login

| Field    | Value              |
|----------|--------------------|
| Email    | demo@finwise.app   |
| Password | Demo@1234          |

---

## Features

| Feature | Description |
|---|---|
| Multi-account tracking | Bank, cash, credit card, wallet, investment, loan |
| Auto-categorization | Rule-based keyword matching with confidence scores |
| Recurring detection | Detects subscriptions and recurring payments |
| Cash-flow forecast | 7/15/30-day balance forecast with assumptions shown |
| Savings goals | Progress tracking with trade-off suggestions |
| Health score | Transparent 0-100 score with factor breakdown |
| Anomaly detection | Z-score + duplicate detection, flagged for review |
| Receipt OCR | Upload receipt images, auto-extract merchant/amount/date |
| AI chat assistant | Natural-language queries answered from your own data |
| CSV import | Bulk import transactions from bank CSV exports |

---

## Architecture

```
frontend (React + Vite + TypeScript + Tailwind)
        |  HTTP/JSON
backend (FastAPI + SQLAlchemy)
        |  SQL
database (MySQL 8)

AI/ML services (all in backend/app/services/):
  categorization.py  — keyword rules + sklearn (future)
  recurring.py       — interval + amount similarity detection
  forecasting.py     — rule-based cashflow model
  anomaly.py         — z-score + duplicate detection
  health_score.py    — transparent 6-factor formula
  ocr.py             — Tesseract / mock
  chat.py            — retrieval-first NL assistant
  llm.py             — local Ollama/Qwen conversational layer with verified-data guardrails
```

---

## Quick Start (Docker — recommended)

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — change SECRET_KEY and REFRESH_SECRET_KEY

# 2. Start everything
docker-compose up --build

# Services:
#   Frontend:  http://localhost:3000
#   Backend:   http://localhost:8000
#   API docs:  http://localhost:8000/docs
```

The backend automatically runs `seed.py` on first start, creating the demo user
and 150 sample transactions.

---

## Local Development (without Docker)

### Prerequisites
- Python 3.11+
- Node 20+
- MySQL 8 running locally

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Configure database
cp ../.env.example .env
# Edit .env — set DATABASE_URL to your local MySQL

# Create database
mysql -u root -p -e "CREATE DATABASE finwise CHARACTER SET utf8mb4;"

# Run migrations (SQLAlchemy creates tables on startup)
# Seed demo data
python seed.py

# Start API server
uvicorn app.main:app --reload --port 8000
```

### Local AI Assistant (free)

FinWise uses **Ollama + Qwen 2.5 7B** by default for conversational responses. The model runs on your own computer, so there is no OpenAI API key or API credit required.

1. Install Ollama for Windows and make sure `ollama --version` works.
2. Pull the model once:

```powershell
ollama pull qwen2.5:7b
```

3. Keep Ollama available while using FinWise. You can verify the model with:

```powershell
ollama run qwen2.5:7b
```

4. In `backend/.env`, use:

```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OPENAI_ENABLED=false
```

The assistant uses FinWise's deterministic database logic for financial facts and actions, then gives the verified result to Qwen for natural-language explanation. This prevents the local model from inventing balances, expenses, goals or forecasts. Explicit account/budget/goal creation remains controlled by FinWise's backend logic.

### Frontend

```bash
cd frontend
npm install

# For local dev, the vite.config.ts proxies API calls to localhost:8000
npm run dev
# Opens at http://localhost:5173
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | MySQL connection string | `mysql+pymysql://finwise:finwise123@db:3306/finwise` |
| `SECRET_KEY` | JWT access token secret (32+ chars) | change-me |
| `REFRESH_SECRET_KEY` | JWT refresh token secret | change-me |
| `OCR_PROVIDER` | `tesseract` or `mock` | `tesseract` |
| `TESSERACT_CMD` | Path to tesseract binary | `/usr/bin/tesseract` |
| `FRONTEND_URL` | CORS allowed origin | `http://localhost:5173` |
| `OLLAMA_ENABLED` | Enable local conversational AI | `true` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Local model name | `qwen2.5:7b` |
| `OPENAI_ENABLED` | Optional cloud LLM | `false` |

---

## API Documentation

Interactive docs available at `http://localhost:8000/docs` (Swagger UI).

### Key endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login, get tokens |
| POST | `/auth/refresh` | Refresh access token |
| GET | `/users/me` | Get current user |
| GET | `/accounts` | List accounts |
| GET | `/transactions` | List with filters |
| POST | `/transactions/import-csv` | Bulk CSV import |
| POST | `/transactions/categorize-batch` | Re-run auto-categorization |
| GET | `/budgets/summary?month=YYYY-MM` | Spending vs budget |
| POST | `/recurring/detect` | Detect recurring payments |
| GET | `/recurring/subscriptions` | List subscriptions |
| GET | `/goals/{id}/plan` | Goal plan + trade-offs |
| GET | `/analytics/cashflow?days=30` | Cash-flow forecast |
| GET | `/analytics/health-score` | Financial health score |
| GET | `/analytics/anomalies` | Detected anomalies |
| POST | `/receipts/upload` | Upload + OCR receipt |
| POST | `/chat` | Natural-language query |

---

## CSV Import Format

```csv
date,description,amount,type,merchant
2024-07-01,Monthly salary,65000,income,Employer
2024-07-05,House rent,18000,expense,Landlord
2024-07-10,Swiggy order,450,expense,Swiggy
```

---

## Financial Health Score Formula

| Factor | Max Score | Formula |
|---|---|---|
| Savings Rate | 20 | `(income - expense) / income * 40` (capped at 20) |
| Budget Adherence | 20 | `% of budgets within limit * 20` |
| Emergency Fund | 20 | `months_covered / 6 * 20` (capped at 20) |
| Debt-to-Income | 15 | `15 - (debt / annual_income * 15)` |
| Recurring Burden | 10 | `10 - (recurring / monthly_income * 10)` |
| Spending Volatility | 15 | `15 - (weekly_cv * 15)` |

Grade: A (80+), B (65+), C (50+), D (35+), F (<35)

---

## Project Structure

```
FinWise/
  backend/
    app/
      core/         config, database, security
      models/       SQLAlchemy ORM models
      routers/      FastAPI route handlers
      schemas/      Pydantic request/response models
      services/     AI/ML: categorization, forecasting, anomaly, OCR, chat
    seed.py         Demo data seeder
    requirements.txt
    Dockerfile
  frontend/
    src/
      components/   Sidebar, StatCard, BudgetProgress, ConfirmDialog
      pages/        All 11 pages
      lib/          api.ts (axios), utils.ts
      store/        Zustand auth store
      types/        TypeScript interfaces
    Dockerfile
    nginx.conf
  schema.sql        MySQL DDL
  docker-compose.yml
  .env.example
  README.md
```

---

## Future Scope

- **SMS parsing** — Read UPI/bank SMS notifications (Android only, requires permission)
- **Account Aggregator** — RBI AA framework integration for automatic bank sync
- **Advanced ML** — Prophet/ARIMA time-series forecasting, BERT-based categorization
- **Push notifications** — Alert when balance drops below threshold or bill is due
- **Multi-currency** — Real-time exchange rates for foreign transactions
- **Tax reports** — Capital gains, 80C deductions summary for ITR filing
- **Family accounts** — Shared budgets and expense splitting


### Local OCR/PDF setup

For image receipts, install Tesseract OCR on Windows and keep `TESSERACT_CMD` pointed at `tesseract.exe`.
PDF receipts are rendered with PyMuPDF, so Poppler/pdf2image is not required. Run `pip install -r backend/requirements.txt` after pulling the updated project.

FinWise chat has a local database-grounded fallback and an optional OpenAI LLM mode. Receipt OCR uses local PDF/text extraction and Tesseract when available.

## FinWise portfolio intelligence (implemented)

This build supports an **optional OpenAI LLM** while preserving a local, database-grounded fallback. The assistant reads the authenticated user's data and can perform controlled actions such as creating accounts, recording income/expenses, creating budgets and goals, and contributing to goals. Destructive operations should remain confirmation-gated.

Implemented intelligence modules include:
- Financial Health Score with transparent factor breakdown.
- 30-day cash-flow forecasting with assumptions.
- Statistical anomaly detection and duplicate-import checks.
- Automatic transaction categorization with confidence scores.
- Recurring/subscription detection with monthly and annual cost.
- Goal planning and monthly contribution/trade-off analysis.
- Net-worth and emergency-fund coverage calculations.
- Data-driven budget recommendations from recent spending.
- What-if savings/spending simulation.
- Monthly financial report and month-over-month change metrics.
- Receipt OCR for text PDFs plus multi-page scanned PDFs/images using PyMuPDF + Tesseract.
- Password reset with hashed, single-use, 30-minute reset tokens.
- Access-token refresh handling in the frontend.
- Settings view/edit/save workflow that persists changes to the backend.
- Modern analytics dashboard and colored application background.

### AI scope

With `OPENAI_ENABLED=true`, the LLM handles natural-language conversation and uses FinWise tools for verified financial facts. With the LLM disabled, the deterministic local assistant remains available for supported finance operations. Financial numbers and write operations are grounded in authenticated application data rather than generated.

## FinWise AI Assistant (LLM)

The upgraded assistant supports optional natural-language conversation through the OpenAI Responses API while keeping financial facts grounded in FinWise's database. Set these values in `backend/.env`:

```env
OPENAI_ENABLED=true
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5.6-luna
```

If the key is missing or the provider is unavailable, the local deterministic FinWise assistant remains available. The LLM can retrieve verified financial snapshots/spending and can perform explicit account, budget, and goal creation through backend tools.

Never commit `backend/.env` or an API key to GitHub.

## Settings

The Personal Profile page now supports profile photos, editable personal details, preferences, validation, dynamic completeness, and persistent save/cancel behavior. Existing databases receive lightweight `users` table migrations automatically at backend startup.
