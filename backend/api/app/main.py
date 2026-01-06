from fastapi import FastAPI  # type: ignore
from app.routes import health, wards
from sqlalchemy import text  # type: ignore
from app.db import engine

app = FastAPI(
    title="Smart City Trash Bin API",
    version="1.0.0"
)

app.include_router(health.router)
app.include_router(wards.router)

@app.on_event("startup")
def startup_check():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Database connection verified")