"""
SFMC Copilot Backend — FastAPI Application Entry Point.

Replaces the Spring Boot application with a lightweight FastAPI server
serving the same endpoints on port 8080.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers.chat import router as chat_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(threadName)s] %(levelname)-5s %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("SFMC Copilot Backend (Python / FastAPI + LangChain)")
    logger.info("Server running on http://localhost:%d", settings.server_port)
    logger.info("Gemini configured: %s", bool(settings.gemini_api_key))
    logger.info("SFMC configured: %s", bool(settings.sfmc_client_id))
    logger.info("=" * 60)
    yield


# Create FastAPI app
app = FastAPI(
    title="SFMC Copilot Backend",
    description="AI-powered Salesforce Marketing Cloud assistant with LangChain Agent + Gemini",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware (replaces WebConfig.java)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.server_port,
        reload=True,
    )
