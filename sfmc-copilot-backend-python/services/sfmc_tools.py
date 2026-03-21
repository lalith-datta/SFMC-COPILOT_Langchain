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
            - precision (int, optional): Precision (only used for Decimal fields, default 18)
            - scale (int, optional): Scale (only used for Decimal fields, default 2)
            - defaultValue (str, optional): Default value for the field. For dates representing 'current date', pass "GetDate()"
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
def search_data_extension(search_key: str) -> str:
    """Search the Data Extension in the user's SFMC account.

    Use this tool when the user asks to search for a Data Extension or you want to get the details such as DE external Key.
    Args:
        search_key: Name of the Data extension to search for (e.g. "Customer_Profiles")
    """
    logger.info("Tool called: search_data_extension(search_key=%s)", search_key)
    return sfmc_api_service.search_data_extension(search_key)


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
def create_automation(
    name: str, 
    description: str, 
    start_source: str = "Scheduled",
    schedule_frequency: str = "", 
    file_naming_pattern: str = "",
    query_id: str = ""
) -> str:
    """Creates an Automation in Salesforce Marketing Cloud Automation Studio.

    Use this tool when the user asks to create, set up, or build an automation.

    Args:
        name: Name of the automation (e.g. "Daily_Import")
        description: Description of what the automation does
        start_source: The trigger type. Must be either 'Scheduled' or 'FileDrop'.
        schedule_frequency: (Only for Scheduled) One of "Hourly", "Daily", "Weekly", "Monthly"
        file_naming_pattern: (Only for FileDrop) The filename pattern to watch for (e.g. "imports_*.csv")
        query_id: (Optional) Pass the Query ID returned by create_sql_query to attach it to this automation as a step.
    """
    logger.info("Tool called: create_automation(name=%s, source=%s, query_id=%s)", name, start_source, query_id)
    return sfmc_api_service.create_automation(
        name=name,
        description=description,
        start_source=start_source,
        schedule_frequency=schedule_frequency,
        file_naming_pattern=file_naming_pattern,
        query_id=query_id or None
    )


@tool
def get_subscriber_count() -> str:
    """Gets subscriber count and metrics from the SFMC account.

    Use this tool when the user asks about subscribers, subscriber count,
    how many subscribers they have, or subscriber metrics/stats.
    """
    logger.info("Tool called: get_subscriber_count()")
    return sfmc_api_service.get_subscriber_count()


@tool
def create_sql_query(
    name: str,
    query_text: str,
    target_data_extension_key: str,
    description: str = "",
    update_type: str = "Overwrite",
) -> str:
    """Creates an SQL Query Activity in Salesforce Marketing Cloud.

    Use this tool when the user asks to create an SQL query or write SQL for SFMC.
    You must generate the appropriate SQL query and pass it to this tool.
    
    Args:
        name: Name of the query activity (e.g. "Weekly_Active_Users_Query")
        query_text: The actual SQL SELECT statement to execute
        target_data_extension_key: The CustomerKey of the destination Data Extension to save results to
        description: Description of what the query does
        update_type: How to write the data, one of "Append", "Update", or "Overwrite" (default is "Overwrite")
    """
    logger.info("Tool called: create_sql_query(name=%s)", name)
    return sfmc_api_service.create_sql_query_activity(
        name=name,
        query_text=query_text,
        target_de_key=target_data_extension_key,
        description=description,
        update_type=update_type,
    )


# All tools to register with the Agent
ALL_TOOLS = [
    create_data_extension,
    search_data_extension,
    create_email_definition,
    create_automation,
    get_subscriber_count,
    create_sql_query,
]
