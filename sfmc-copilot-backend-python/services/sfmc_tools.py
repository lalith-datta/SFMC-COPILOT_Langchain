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


# @tool
# def search_data_extension(search_key: str) -> str:
#     """Search the Data Extension in the user's SFMC account.

#     Use this tool when the user asks to search for a Data Extension or you want to get the details such as DE external Key.
#     Args:
#         search_key: Name of the Data extension to search for (e.g. "Customer_Profiles")
#     """
#     logger.info("Tool called: search_data_extension(search_key=%s)", search_key)
#     return sfmc_api_service.search_data_extension(search_key)


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
    folder_location: str,
    description: str = "",
    start_source: str = "Scheduled",
    schedule_frequency: str = "", 
    file_naming_pattern: str | None = None,
    matching_type: str | None = None,
    
) -> str:
    """Creates an Automation in Salesforce Marketing Cloud Automation Studio.

    Use this tool when the user asks to create, set up, or build an automation.
    After creating the automation, use add_activity_to_automation to add activities to it.

    IMPORTANT: Only `name` and `start_source` are required. All other parameters are optional.
    Do NOT ask the user for file_naming_pattern, matching_type, or folder_location unless they
    explicitly provide them. Just create the automation with what the user gives you.

    Args:
        name: Name of the automation (e.g. "Daily_Import")
        description: (Optional) Description of what the automation does
        start_source: The trigger type. Either 'Scheduled' (default) or 'FileDrop'.
        schedule_frequency: (Optional, Scheduled only) One of "Hourly", "Daily", "Weekly", "Monthly"
        file_naming_pattern: (Optional, FileDrop only) Filename pattern. Only pass if user provides it.
        matching_type: (Optional, FileDrop only) One of "Begins with", "Contains", "Ends with". Only pass if user provides it.
        folder_location: (FileDrop only) Folder location.
    """
    logger.info("Tool called: create_automation(name=%s, source=%s)", name, start_source)
    return sfmc_api_service.create_automation(
        name=name,
        description=description,
        start_source=start_source,
        schedule_frequency=schedule_frequency,
        file_naming_pattern=file_naming_pattern or None,
        matching_type=matching_type or None,
        folder_location=folder_location,
    )


@tool
def add_activity_to_automation(
    automation_name: str,
    activity_type: str,
    activity_id: str,
    step_number: int = 1,
) -> str:
    """Adds an activity to a specific step in an existing SFMC Automation.

    Use this tool AFTER creating an activity (SQL Query, Data Extract, File Transfer, or Import)
    to attach it to an automation at a specific step number.

    Args:
        automation_name: The exact name of the existing automation to add the activity to
        activity_type: Type of activity. Must be one of: "sql_query", "data_extract", "file_transfer", "import"
        activity_id: The ID of the activity returned when it was created (e.g. queryDefinitionId, dataExtractDefinitionId, etc.)
        step_number: The step number to place the activity in (1-indexed, default: 1). Multiple activities in the same step run in parallel.
    """
    logger.info("Tool called: add_activity_to_automation(automation=%s, type=%s, id=%s, step=%d)",
                automation_name, activity_type, activity_id, step_number)
    return sfmc_api_service.add_activity_to_automation(
        automation_name=automation_name,
        activity_type=activity_type,
        activity_id=activity_id,
        step_number=step_number,
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
    target_data_extension: str,
    description: str = "",
    update_type: str = "Overwrite",
) -> str:
    """Creates an SQL Query Activity in Salesforce Marketing Cloud.

    Use this tool when the user asks to create an SQL query or write SQL for SFMC.
    You must generate the appropriate SQL query and pass it to this tool.
    
    Args:
        name: Name of the query activity (e.g. "Weekly_Active_Users_Query")
        query_text: The actual SQL SELECT statement to execute
        target_data_extension: The Name of the Target Data Extension to save results to
        description: Description of what the query does
        update_type: How to write the data, one of "Append", "Update", or "Overwrite" (default is "Overwrite")
    """
    logger.info("Tool called: create_sql_query(name=%s)", name)
    return sfmc_api_service.create_sql_query_activity(
        name=name,
        query_text=query_text,
        target_data_extension=target_data_extension,
        description=description,
        update_type=update_type,
    )

@tool
def create_data_extract_activity(
    name: str,
    Data_Extension_Name: str,
    file_naming_pattern: str,
    type: str,
    interval: str = "",
    start_date: str = "",
    end_date: str = "",
    description: str = "",
    
) -> str:
    """Creates an Data Extract Activity in Salesforce Marketing Cloud.

    Use this tool when the user asks to create an Data Extract Activity.
    
    Args:
        name: Name of the query activity (e.g. "Weekly_Active_Users_Query")
        Data_Extension_Name: This is the Name of the Data Extension you want to export
        file_naming_pattern: The name of the file produced in the Safehouse. It should end in .csv for Data Extension extracts.
        type: The type of data extract activity. Must be one of "Data Extension Extract" or "UTF16 to ASCII Converter".
        interval: (Optional) The interval at which the data extract activity should run. Must be one of "1 day", "7 days", "30 days", "60 days", "90 days",.
        start_date: (Optional) The start date of the data extract activity. Format: MM/DD/YYYY
        end_date: (Optional) The end date of the data extract activity. Format: MM/DD/YYYY
        description: Description of what the query does
    """
    logger.info("Tool called: create_data_extract_activity(name=%s)", name)
    return sfmc_api_service.create_data_extract_activity(
        name=name,
        Data_Extension_Name=Data_Extension_Name,
        file_naming_pattern=file_naming_pattern,
        type=type,
        interval=interval or None,
        start_date=start_date or None,
        end_date=end_date or None,
        description=description,
    )

@tool
def create_file_transfer_activity(
    name: str,
    file_naming_pattern: str,
    file_action: str,
    file_location: str,
    encryption_type: str ="",
    is_unzip: bool =False,
    decrypt_file: bool =False,
    public_key: str ="",
    private_key: str ="",
    description: str = "",
    file_age: int = 0,
    file_offset: int = 0,
    import_frequency: int = 0,
    
) -> str:
    """Creates an File Transfer Activity in Salesforce Marketing Cloud.

    Use this tool when the user asks to create an File Transfer Activity.
    
    Args:
        name: Name of the file transfer activity.
        file_naming_pattern: The name of the file produced in the Safehouse. OR naming pattern for the file to be extracted.
        file_action: The type of file transfer activity. Must be one of "Manage File" or "Move a File From Safehouse".
        file_location: The Source file location of the file to be extracted or the destination file location for the file to be moved.
        encryption_type: (Optional) The type of encryption to be used. Must be one of "PGP" or "GPG".
        is_unzip: (Optional) Whether the file should be unzipped. Must be one of "True" or "False".
        decrypt_file: (Optional) Whether the file should be decrypted. Must be one of "True" or "False".
        public_key: (Optional) The public key to be used for encryption.
        private_key: (Optional) The private key to be used for decryption.
        description: (Optional) Description of what the file transfer activity does.
        file_age: (Optional) The age of the file to be extracted. 
        file_offset: (Optional) The offset of the file to be extracted. 
        import_frequency: (Optional) The frequency of the file transfer activity. 
    """
    logger.info("Tool called: create_file_transfer_activity(name=%s)", name)
    return sfmc_api_service.create_file_transfer_activity(
        name=name,
        file_naming_pattern=file_naming_pattern,
        file_action=file_action,
        encryption_type=encryption_type,
        file_location=file_location,
        is_unzip=is_unzip,
        decrypt_file=decrypt_file,
        public_key=public_key,
        private_key=private_key,
        description=description,
        file_age=file_age,
        file_offset=file_offset,
        import_frequency=import_frequency,
    )


@tool
def create_import_activity(
    name: str,
    source_data_extension_name: str,
    destination_data_extension_name: str,
    data_source_type: str = "DataExtension",
    update_type: str = "Overwrite",
    file_location_name: str = "",
    file_naming_pattern: str = "",
    file_type: str = "CSV",
    description: str = "",
    allow_errors: bool = True,
    send_email_notification: bool = False,
    notification_email_address: str = "",
) -> str:
    """Creates an Import Activity (Data Copy) in Salesforce Marketing Cloud.

    Use this tool when the user asks to create an import activity, data copy activity,
    or wants to copy/import data between Data Extensions or from a file location into a Data Extension.

    There are two data source types:
    - "DataExtension": Copy data from one DE to another (source DE → destination DE).
    - "FileLocation": Import data from a file on an FTP location into a destination DE.

    Args:
        name: Name of the import activity (e.g. "Daily_Customer_Import")
        source_data_extension_name: Name of the source Data Extension to read data from
        destination_data_extension_name: Name of the destination Data Extension to write data to
        data_source_type: Either "DataExtension" (copy between DEs) or "FileLocation" (import from file). Default: "DataExtension"
        update_type: How to handle existing data. One of "Add Only", "Update Only", "Add and Update", "Overwrite". Default: "Overwrite"
        file_location_name: (Only for FileLocation) Name of the FTP location (e.g. "ExactTarget Enhanced FTP")
        file_naming_pattern: (Only for FileLocation) The filename or pattern to import (e.g. "customers_import.csv")
        file_type: (Only for FileLocation) File format, one of "CSV" or "TAB". Default: "CSV"
        description: Optional description of the import activity
        allow_errors: Whether to allow errors during import. Default: True
        send_email_notification: Whether to send email notification on completion. Default: False
        notification_email_address: Email address for notifications (required if send_email_notification is True)
    """
    logger.info("Tool called: create_import_activity(name=%s, source=%s, dest=%s, type=%s)",
                name, source_data_extension_name, destination_data_extension_name, data_source_type)
    return sfmc_api_service.create_import_activity(
        name=name,
        source_data_extension_name=source_data_extension_name,
        destination_data_extension_name=destination_data_extension_name,
        data_source_type=data_source_type,
        update_type=update_type,
        file_location_name=file_location_name,
        file_naming_pattern=file_naming_pattern,
        file_type=file_type,
        description=description,
        allow_errors=allow_errors,
        send_email_notification=send_email_notification,
        notification_email_address=notification_email_address,
    )


# All tools to register with the Agent
ALL_TOOLS = [
    create_data_extension,
    # search_data_extension,
    create_email_definition,
    create_automation,
    add_activity_to_automation,
    get_subscriber_count,
    create_sql_query,
    create_data_extract_activity,
    create_file_transfer_activity,
    create_import_activity,
]
