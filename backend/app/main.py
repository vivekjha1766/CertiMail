import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.routes_upload import router as upload_router
from backend.app.api.routes_mapping import router as mapping_router
from backend.app.api.routes_templates import router as templates_router
from backend.app.api.routes_smtp import router as smtp_router
from backend.app.api.routes_campaigns import router as campaigns_router
from backend.app.api.routes_logs import router as logs_router
from backend.app.api.routes_certificates import router as certificates_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("certimail")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting CertiMail Backend Service...")
    init_db()
    yield
    # Shutdown
    logger.info("Shutting down CertiMail Backend Service...")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Backend API for CertiMail — Certificate Distribution Dashboard",
    lifespan=lifespan
)

# CORS configuration for local React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(upload_router)
app.include_router(mapping_router)
app.include_router(templates_router)
app.include_router(smtp_router)
app.include_router(campaigns_router)
app.include_router(logs_router)
app.include_router(certificates_router)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
