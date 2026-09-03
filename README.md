# Ticket Tailor Revenue Dashboard

A full-stack dashboard for reviewing ticket revenue, fees, refunds, and Stripe payouts. Webhook fixture records are reconciled in FastAPI and reported through a Nuxt UI frontend.

## Requirements

- Python 3.11+
- uv
- Bun 1.4+

## Local Setup

Install the backend dependencies and ingest the supplied webhook fixtures:

```bash
cd backend
uv sync --extra dev
uv run python -m src.webhook ../records.json ../records2.json
uv run python -m uvicorn app:app --reload --port 8000
uv run uvicorn app:app --reload --port 8000
# alternative
```

The seed command is explicit and safe to rerun. Existing events with equal or older source timestamps are logged but do not replace current records.

The API is available at `http://localhost:8000`; Swagger UI is at `http://localhost:8000/docs`.

In another terminal, install and run the frontend:

```bash
cd frontend
bun install
bun run dev
```

The frontend is available at `http://localhost:3000`.

Set `NUXT_PUBLIC_API_BASE_URL` when the API runs somewhere other than `http://localhost:8000`. Typed API methods live in `frontend/lib/api.ts`.

## Verification

```bash
cd backend
uv run pytest

cd ../frontend
bun run typecheck
bun run build
```

## Docker Compose

Start both services with one command from the project root:

```bash
docker compose up --build
```

Seed the persistent container database after the services are running:

```bash
docker compose exec backend python -m src.webhook /fixtures/records.json /fixtures/records2.json
```

The frontend is available at `http://localhost:3000` and the API at `http://localhost:8000`. SQLite data is retained in the `backend_data` volume. Use `docker compose down -v` when a clean database is required.

## API

- `POST /api/webhooks` ingests one charge, refund, or payout delivery.
- `GET /api/reports/overview` returns summary and breakdown figures.
- `GET /api/transactions` returns paginated sales or refunds.
- `GET /api/payouts` returns paginated payouts.

Reporting endpoints accept the period values `today`, `yesterday`, `this_week`, `last_week`, `this_month`, `last_month`, and `all_time`, plus an IANA browser timezone such as `Europe/London`. Monetary values are integer minor GBP units over the API and are formatted by the frontend.
