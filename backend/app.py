from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    message: str


app = FastAPI(
    title="FastAPI + Nuxt API",
    version="0.1.0",
    description="The API for the FastAPI and Nuxt starter project.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="fastapi",
        message="The API is connected and ready.",
    )


@app.get("/api/hello", response_model=dict[str, str])
async def hello() -> dict[str, str]:
    return {"message": "Hello from FastAPI"}
