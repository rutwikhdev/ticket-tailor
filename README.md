# FastAPI + Nuxt starter

Simple full-stack project with a FastAPI API and a Nuxt/Vue frontend using TypeScript, Nuxt UI, Tailwind CSS, and Bun.

## Requirements

- Python 3.11+
- Bun 1.4+

## Run the API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. Swagger UI is at `http://localhost:8000/docs`.

## Run the frontend

In another terminal:

```bash
cd frontend
bun install
bun run dev
```

The frontend is available at `http://localhost:3000`.

Set `NUXT_PUBLIC_API_BASE_URL` when the API runs somewhere other than `http://localhost:8000`. The shared generic request helper lives in `frontend/utils/api.ts`.

## Test the API

```bash
cd backend
source .venv/bin/activate
pytest
```

## Run with Docker Compose

Start both services with one command from the project root:

```bash
docker compose up --build
```

The frontend is available at `http://localhost:3000` and the API at
`http://localhost:8000`.
