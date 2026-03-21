"""
AI Gateway Service — LangChain Agent with tool calling and conversation memory.

Uses ChatGoogleGenerativeAI with bound SFMC tools. The agent automatically
decides when to call tools based on the user's message — no manual intent
detection or keyword matching needed.

Conversation history is automatically managed by LangGraph's MemorySaver
checkpointer — messages are persisted per conversation thread with no manual
save/load code required.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from config import settings
from services.sfmc_tools import ALL_TOOLS

logger = logging.getLogger(__name__)


# ==================== SYSTEM PROMPT ====================

SYSTEM_PROMPT = """\
You are SFMC Copilot, an expert AI assistant for Salesforce Marketing Cloud (SFMC).

You have access to tools that can directly interact with the user's SFMC account.
When the user asks you to create, list, or query SFMC resources, USE THE TOOLS PROVIDED.

Your capabilities (via tools):
- Create Data Extensions with custom fields, types, and sendable configurations
- List existing Data Extensions
- Create Email Definitions in Content Builder
- Create SQL Query Activities by writing and deploying SQL
- Create Automations with schedules
- Query subscriber count and metrics

Guidelines:
1. When a user asks to create something, USE THE TOOL to actually create it — then report the result.
2. Format responses with markdown for readability (tables, bold, lists).
3. When reporting tool results, present them clearly. The action has ALREADY been executed.
4. Every time you create a Data Extension and respond to the user, you MUST provide the field details in a markdown table containing the exact columns: Name, Type, Primary Key, Required, Length, Default Value. Remember to extract and pass `defaultValue` inside the field schema if the user requests one.
5. For automations, specify the schedule and steps clearly. If the user asks for a File Drop trigger, explicitly pass `start_source="FileDrop"` and extract the file naming pattern.
6. When asked to schedule a query, FIRST use create_sql_query to get the Query ID and while creating the SQL query you would need the External key of the Target Data extension for that run the tool search_data_extension passing the name of the Data extension provided by the user to get the external key of the target data extension, THEN use create_automation passing that Query ID.
7. Always be helpful, professional, and concise.
8. If a user asks to create ANY resource (e.g., Data Extension, Automation, SQL Query, etc.) but DOES NOT provide the specific required details, DO NOT invent or assume them. Instead, politely ask the user to provide the missing details and suggest a clear, structured format for them to use. 
   - For Data Extensions, suggest: "- FieldName (DataType, Length/Precision, PrimaryKey?, Required?, DefaultValue)"
   - For Automations, suggest providing the schedule frequency, start source, and steps.
   - For SQL Queries, suggest providing the query logic and target Data Extension.
9. If a request is ambiguous, ask clarifying questions BEFORE calling a tool.
"""


@dataclass(frozen=True, slots=True)
class RoutingResult:
    """Result of agent execution."""

    text: str
    model: str


# ==================== AGENT SETUP ====================

# Conversation memory — automatically persists all messages per thread_id.
# Each conversation gets its own thread, so multi-turn context is preserved
# without any manual message tracking.
_memory = MemorySaver()


def _create_agent():
    """Create the LangChain agent with Gemini + SFMC tools + conversation memory."""
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — agent will fail on requests")
        return None

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.7,
        max_output_tokens=2048,
    )

    # Create a ReAct agent with tools and memory checkpointer.
    # The checkpointer automatically saves and restores conversation history
    # for each thread_id — no manual history management needed.
    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=SYSTEM_PROMPT,
        checkpointer=_memory,
    )

    logger.info(
        "LangChain Agent created with conversational memory: model=%s, tools=%s",
        settings.gemini_model,
        [t.name for t in ALL_TOOLS],
    )
    return agent


# Lazy-initialize the agent
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = _create_agent()
    return _agent


# ==================== PUBLIC API ====================

class AiGatewayService:
    """Gateway service — delegates to the LangChain Agent."""

    def route(self, message: str, conversation_id: str, preferred_model: str | None) -> RoutingResult:
        """Process a user message through the LangChain Agent."""
        agent = _get_agent()
        if agent is None:
            return RoutingResult(
                text="❌ Gemini API key not configured. Please set GEMINI_API_KEY in your .env file.",
                model="error",
            )

        try:
            thread_id = conversation_id or "default"
            logger.info("Invoking agent for thread=%s", thread_id)

            # The agent + checkpointer handles everything:
            # - Loads previous messages for this thread_id automatically
            # - Appends the new user message
            # - Runs the agent (with tool calls if needed)
            # - Saves all messages (user + AI + tool) back to the checkpoint
            result = agent.invoke(
                {"messages": [("user", message)]},
                config={"configurable": {"thread_id": thread_id}},
            )

            # Extract the final response text
            response_text = self._extract_response_text(result)

            logger.info("Agent response generated (%d chars)", len(response_text))
            return RoutingResult(text=response_text, model="gemini")

        except Exception as e:
            logger.error("Agent execution failed: %s", e, exc_info=True)
            return RoutingResult(
                text=f"❌ Error: {e}\n\nPlease check that Gemini is properly configured.",
                model="error",
            )

    @staticmethod
    def _extract_response_text(result: dict) -> str:
        """Extract the final text response from the agent result.

        LangChain's Gemini messages can return content as:
        - A plain string: "Hello!"
        - A list of content parts: [{"type": "text", "text": "Hello!"}]
        This method handles both formats.
        """
        messages = result.get("messages", [])

        # Walk messages in reverse to find the last AI message with content
        for msg in reversed(messages):
            if not hasattr(msg, "type") or msg.type != "ai":
                continue

            content = msg.content
            if not content:
                continue

            # If content is a plain string, return it
            if isinstance(content, str):
                return content

            # If content is a list of parts, join the text parts
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part["text"])
                if text_parts:
                    return "\n".join(text_parts)

        return "I processed your request but have no additional response."


# Singleton instance
ai_gateway_service = AiGatewayService()
