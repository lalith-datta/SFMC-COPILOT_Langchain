"""
Chat API router — REST endpoints for the SFMC Copilot.
"""

import logging

from fastapi import APIRouter, HTTPException

from models.schemas import ChatRequest, ChatResponse
from services.ai_gateway import ai_gateway_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Handle a chat message — routes to the appropriate LLM."""
    logger.info(
        "Received chat request: model=%s, message='%s'",
        request.preferred_model,
        request.message[:100],
    )

    try:
        result = ai_gateway_service.route(
            message=request.message,
            conversation_id=request.conversation_id or "default",
            preferred_model=request.preferred_model,
        )

        logger.info("Response generated via %s (%d chars)", result.model, len(result.text))
        return ChatResponse(text=result.text, model=result.model)

    except Exception as e:
        logger.error("Chat request failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "text": f"❌ Error: {e}\n\nPlease check that the AI services are running and properly configured.",
                "model": "error",
            },
        )


@router.get("/health")
def health() -> dict:
    """Health check endpoint to verify the backend is running."""
    return {"status": "UP", "service": "SFMC Copilot Backend"}
