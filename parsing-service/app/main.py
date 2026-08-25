"""Starts the JD and resume parsing API."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.jd_excel import router as jd_excel_router
from app.routers.jd_criteria import router as jd_criteria_router
from app.routers.resume import router as resume_router
from app.routers.scoring import router as scoring_router


app = FastAPI(title="UWC JD Parsing Service", version="1.0.0")
# Allow only configured frontend origins.
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "JD_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(jd_excel_router)
app.include_router(jd_criteria_router)
app.include_router(resume_router)
app.include_router(scoring_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Expose a dependency-light liveness check for Railway and local setup."""

    return {"status": "ok"}
