import logging
from fastapi import FastAPI
from .api.routes import api_router
# Initialize database connection here

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Digital Twin API", version="1.0")

# Include API routes
app.include_router(api_router)

@app.get("/")
def read_root():
    return {"status": "API Running", "service": "DigitalTwinBackend"}

def run_migrations():
    """Placeholder for database migration setup (e.g., using Alembic)."""
    logging.info("Starting database migration process...")
    # Logic to connect to SQLite/Postgres and run migrations
    print("Migrations applied successfully.")

if __name__ == "__main__":
    # 1. Run migrations first
    run_migrations()
    
    # 2. Run the FastAPI application
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)