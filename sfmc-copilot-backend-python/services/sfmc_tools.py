"""
SFMC Tool definitions for the LangChain Agent.

Each function decorated with @tool becomes automatically callable by the LLM.
The docstrings serve as the tool schema — the LLM reads them to understand
when and how to call each function.
"""

import logging
from langchain_core.tools import tool
from services.sfmc_api import sfmc_api_service

logger = logging.getLogger(__name__)


@tool
def create_data_extension(
    name: str,
    fields: list[dict],
    category_id: int = 0,
    is_sendable: bool = False,
    sendable_field_name: str | None = None,
) -> str:
    """Creates a Data Extension in Salesforce Marketing Cloud.

    Use this tool when the user asks to create, build, or set up a Data Extension (DE).

    Args:
        name: Name of the Data Extension (e.g. "Customer_Profiles")
        fields: List of field definitions. Each field is a dict with:
            - name (str): Field name (e.g. "Email", "FirstName")
            - type (str): One of Text, Number, Date, Boolean, EmailAddress, Phone, Decimal, Locale
            - isPrimaryKey (bool): Whether this field is the primary key
            - isRequired (bool): Whether this field is required
            - maxLength (int, optional): Max length for Text fields (default 254)
        category_id: SFMC folder ID where the DE will be created. Use 0 to auto-discover.
        is_sendable: Set to true if the user wants a sendable DE or mentions "send relationship"
        sendable_field_name: The field name to use as the sendable relationship field (e.g. "SubscriberKey")
    """
    logger.info("Tool called: create_data_extension(name=%s, fields=%d)", name, len(fields))
    return sfmc_api_service.create_data_extension(
        name, fields, category_id=category_id,
        is_sendable=is_sendable, sendable_field_name=sendable_field_name,
    )


@tool
def list_data_extensions() -> str:
    """Lists all Data Extensions in the user's SFMC account.

    Use this tool when the user asks to list, show, view, or check their Data Extensions.
    """
    logger.info("Tool called: list_data_extensions()")
    return sfmc_api_service.list_data_extensions()


@tool
def create_email_definition(name: str, subject: str) -> str:
    """Creates an Email Definition in Salesforce Marketing Cloud Content Builder.

    Use this tool when the user asks to create an email, email template, or email definition.

    Args:
        name: Name of the email definition (e.g. "Welcome_Email")
        subject: Email subject line
    """
    logger.info("Tool called: create_email_definition(name=%s)", name)
    return sfmc_api_service.create_email_definition(name, subject)


@tool
def create_automation(name: str, description: str, schedule_frequency: str) -> str:
    """Creates an Automation in Salesforce Marketing Cloud Automation Studio.

    Use this tool when the user asks to create, set up, or build an automation.

    Args:
        name: Name of the automation (e.g. "Daily_Import")
        description: Description of what the automation does
        schedule_frequency: One of "Hourly", "Daily", "Weekly", "Monthly"
    """
    logger.info("Tool called: create_automation(name=%s)", name)
    return sfmc_api_service.create_automation(name, description, schedule_frequency)


@tool
def get_subscriber_count() -> str:
    """Gets subscriber count and metrics from the SFMC account.

    Use this tool when the user asks about subscribers, subscriber count,
    how many subscribers they have, or subscriber metrics/stats.
    """
    logger.info("Tool called: get_subscriber_count()")
    return sfmc_api_service.get_subscriber_count()


# All tools to register with the Agent
ALL_TOOLS = [
    create_data_extension,
    list_data_extensions,
    create_email_definition,
    create_automation,
    get_subscriber_count,
]
