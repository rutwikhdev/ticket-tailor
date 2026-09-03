# Ticket Tailor

<img width="1388" height="854" alt="beautiful-screenshot-1788465422370" src="https://github.com/user-attachments/assets/8de23dfe-53fb-4c83-8e84-70bd09a8af0c" />

<img width="1388" height="854" alt="beautiful-screenshot-1788465616354" src="https://github.com/user-attachments/assets/7c27d08b-71bf-441c-9190-db22708e0880" />

<img width="1388" height="854" alt="beautiful-screenshot-1788465624509" src="https://github.com/user-attachments/assets/ac3ddf4e-0d1c-48aa-985e-f34e2cf3ae14" />


## Running the project with Docker Compose

Start both services with one command from the project root:

```bash
docker compose up --build
```
The frontend is available at `http://localhost:3000`.

Rerun again

```bash
docker compose down -v
docker compose up -d 
```

`docker compose down -v` also wipes the `backend_data` volume so fixtures are reseeded on the next start.

## API

- `POST /api/webhooks` ingests one charge, refund, or payout delivery.
- `GET /api/reports/overview` returns summary and breakdown figures.
- `GET /api/transactions` returns paginated sales or refunds.
- `GET /api/payouts` returns paginated payouts.

Reporting endpoints accept the period values `today`, `yesterday`, `this_week`, `last_week`, `this_month`, `last_month`, and `all_time`, plus an IANA browser timezone such as `Europe/London`. Monetary values are integer minor GBP units over the API and are formatted by the frontend.

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
uv run uvicorn app:app --reload --port 8000
```

The seed command is explicit and safe to rerun. Existing events with equal or older source timestamps are logged but do not replace current records.

The API is available at `http://localhost:8000`; Swagger UI is at `http://localhost:8000/docs`.

In another terminal, install and run the frontend:

```bash
cd frontend
bun install
bun run dev
```

Set `NUXT_PUBLIC_API_BASE_URL` when the API runs somewhere other than `http://localhost:8000`. Typed API methods live in `frontend/lib/api.ts`.

## Verification

```bash
cd backend
uv run pytest

cd ../frontend
bun run typecheck
bun run build
```

