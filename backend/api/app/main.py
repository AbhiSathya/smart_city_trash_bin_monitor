from fastapi import FastAPI  # type: ignore
from app.routes import health, wards
from app.auth import auth_routes
from sqlalchemy import text  # type: ignore
from app.db import engine
from fastapi.middleware.cors import CORSMiddleware  # type: ignore

app = FastAPI(
    title="Smart City Trash Bin API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(wards.router)
app.include_router(auth_routes.router)


@app.on_event("startup")
def startup_check():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Database connection verified")