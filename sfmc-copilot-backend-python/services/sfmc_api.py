"""
SFMC REST API Client Service.

Handles actual API calls to Salesforce Marketing Cloud for:
- Data Extensions (CRUD)
- Email Definitions
- Automations
- Subscriber queries
"""

import logging

import httpx
import json

from config import settings
from services.sfmc_auth import sfmc_auth_service

logger = logging.getLogger(__name__)

# Valid SFMC field types and their aliases
_FIELD_TYPE_MAP: dict[str, str] = {
    "text": "Text", "string": "Text", "varchar": "Text", "char": "Text",
    "number": "Number", "integer": "Number", "int": "Number", "long": "Number",
    "decimal": "Decimal", "float": "Decimal", "double": "Decimal",
    "date": "Date", "datetime": "Date", "timestamp": "Date",
    "boolean": "Boolean", "bool": "Boolean", "bit": "Boolean",
    "emailaddress": "EmailAddress", "email": "EmailAddress", "email address": "EmailAddress",
    "phone": "Phone", "telephone": "Phone", "tel": "Phone",
    "locale": "Locale",
}


class SfmcApiService:
    def __init__(self) -> None:
        self._client = httpx.Client(timeout=30.0)

    # -------------------- helpers --------------------

    def _base_uri(self) -> str:
        return settings.sfmc_rest_base_uri.rstrip("/")

    def _call_sfmc_api(
        self, url: str, method: str = "GET",
        body: dict | str | None = None,
        params: dict | None = None,
    ) -> str:
        """Make an authenticated request to the SFMC REST API."""
        headers = {
            "Authorization": f"Bearer {sfmc_auth_service.get_access_token()}",
            "Content-Type": "application/json",
        }

        if method.upper() == "GET":
            resp = self._client.get(url, headers=headers, params=params)
        else:
            json_body = body if isinstance(body, dict) else None
            content = body.encode() if isinstance(body, str) else None
            resp = self._client.post(url, headers=headers, json=json_body, content=content, params=params)

        if not resp.is_success:
            raise RuntimeError(f"SFMC API returned {resp.status_code}: {resp.text}")

        return resp.text

    @staticmethod
    def _normalize_field_type(field_type: str | None) -> str:
        """Normalize a field type to a valid SFMC fieldType."""
        if not field_type:
            return "Text"
        normalized = _FIELD_TYPE_MAP.get(field_type.lower().strip())
        if normalized:
            return normalized
        logger.warning("Unknown field type '%s', defaulting to Text", field_type)
        return "Text"

    # Default SFMC category (folder) ID for Data Extensions
    DEFAULT_CATEGORY_ID = 70553

    # ==================== DATA EXTENSIONS ====================

    def create_data_extension(
        self,
        name: str,
        fields: list[dict],
        category_id: int = 0,
        is_sendable: bool = False,
        sendable_field_name: str | None = None,
    ) -> str:
        """Create a Data Extension with the given name, fields, and settings."""
        try:
            url = f"{self._base_uri()}/data/v1/customobjects"

            payload: dict = {
                "name": name,
                "customerKey": name.replace(" ", "_"),
            }

            # Use provided categoryId, or fall back to default
            effective_id = category_id if category_id > 0 else self.DEFAULT_CATEGORY_ID
            payload["categoryId"] = effective_id
            logger.info("Using categoryId: %d for DE '%s'", effective_id, name)

            # Sendable DE configuration
            if is_sendable:
                payload["isSendable"] = True
                payload["isTestable"] = True

                de_field = sendable_field_name
                if not de_field:
                    # Default: use the first primary key field
                    for f in fields:
                        if f.get("isPrimaryKey"):
                            de_field = f["name"]
                            break
                    if not de_field and fields:
                        de_field = fields[0]["name"]

                if de_field:
                    payload["sendableCustomObjectField"] = de_field
                    payload["sendableSubscriberField"] = "_SubscriberKey"
                    logger.info("DE '%s' set as sendable with field '%s' → _SubscriberKey", name, de_field)

            # Build field columns
            columns = []
            for ordinal, field in enumerate(fields):
                field_type = self._normalize_field_type(field.get("type", "Text"))
                is_pk = bool(field.get("isPrimaryKey", False))
                is_req = bool(field.get("isRequired", False))

                col: dict = {
                    "name": field["name"],
                    "type": field_type,
                    "maskType": "None",
                    "storageType": "Plain",
                    "description": "",
                    "ordinal": ordinal,
                    "isNullable": not (is_pk or is_req),
                    "isPrimaryKey": is_pk,
                    "isTemplateField": False,
                    "isInheritable": True,
                    "isOverridable": True,
                    "isHidden": False,
                    "isReadOnly": False,
                    "mustOverride": False,
                }

                if field_type == "Text":
                    col["length"] = int(field.get("maxLength", 254))

                columns.append(col)

            payload["fields"] = columns

            logger.info("Creating DE payload: %s", payload)
            response = self._call_sfmc_api(url, method="POST", body=payload)
            logger.info("Created Data Extension '%s' successfully", name)
            return f"✅ Data Extension '{name}' created successfully in SFMC!\n\nDetails:\n{response}"

        except Exception as e:
            logger.error("Failed to create Data Extension '%s': %s", name, e)
            return f"❌ Failed to create Data Extension '{name}': {e}"

    # ==================== LIST DATA EXTENSIONS ====================

    def search_data_extension(self, search_key: str) -> str:
        """Search for a Data Extension in the SFMC account."""
        try:
            url = f"{self._base_uri()}/data/v1/customobjects"
            logger.info("Calling SFMC list DEs API: %s", url)
            response = self._call_sfmc_api(url, params={"$pageSize": "1","$page": "1", "$search": search_key})
            # logger.info("Found Data Extension '%s' successfully", response)
            # logger.info(type(response))
            payload = json.loads(response)
            External_key = payload["items"][0]["key"]
            return External_key
        except Exception as e:
            logger.error("Unable to find Data Extension: %s", e)
            return f"❌ Unable to find Data Extension: {e}"

    # ==================== EMAIL ====================

    def create_email_definition(self, name: str, subject: str, html_content: str | None = None) -> str:
        """Create an email definition in SFMC."""
        try:
            url = f"{self._base_uri()}/messaging/v1/email/definitions"
            payload = {
                "name": name,
                "definitionKey": name.replace(" ", "_"),
                "content": {"customerKey": name.replace(" ", "_") + "_content"},
                "subscriptions": {"dataExtension": "All Subscribers"},
            }

            response = self._call_sfmc_api(url, method="POST", body=payload)
            logger.info("Created Email Definition '%s' successfully", name)
            return f"✅ Email Definition '{name}' created successfully!\n\n**Subject:** {subject}\n{response}"

        except Exception as e:
            logger.error("Failed to create Email Definition '%s': %s", name, e)
            return f"❌ Failed to create Email Definition '{name}': {e}"

    # ==================== SQL QUERY ACTIVITIES ====================
    DEFAULT_SQL_QUERY_CATEGORY_ID = 70556
    def create_sql_query_activity(
        self, name: str, query_text: str, target_de_key: str, description: str = "", update_type: str = "Overwrite"
    ) -> str:
        """Create an SQL Query Activity in SFMC."""
        try:
            url = f"{self._base_uri()}/automation/v1/queries"
            
            # Map update type string to SFMC ID: 0=Append, 1=Update, 2=Overwrite
            update_type_map = {"overwrite": 0, "update": 1, "append": 2}
            update_id = update_type_map.get(update_type.lower(), 0)

            payload = {
                "name": name,
                "key": name.replace(" ", "_"),
                "description": description,
                "queryText": query_text,
                "targetKey": target_de_key,
                "targetUpdateTypeId": update_id,
                "categoryId": self.DEFAULT_SQL_QUERY_CATEGORY_ID
            }

            response = self._call_sfmc_api(url, method="POST", body=payload)
            logger.info("Created SQL Query Activity '%s' successfully", name)
            
            # Extract queryId from response if available (useful for chaining)
            import json
            try:
                resp_data = json.loads(response)
                query_id = resp_data.get("queryDefinitionId", "unknown_id")
                return f"✅ SQL Query Activity '{name}' created successfully!\nQuery ID: `{query_id}`\n\nDetails:\n{response}"
            except Exception:
                return f"✅ SQL Query Activity '{name}' created successfully!\n\nDetails:\n{response}"

        except Exception as e:
            logger.error("Failed to create SQL Query Activity '%s': %s", name, e)
            return f"❌ Failed to create SQL Query Activity '{name}': {e}"

    # ==================== AUTOMATIONS ====================

    def create_automation(
        self, 
        name: str, 
        description: str, 
        start_source: str = "Scheduled", 
        schedule_frequency: str = "", 
        file_naming_pattern: str = "",
        query_id: str | None = None
    ) -> str:
        """Create an automation in SFMC with an optional SQL query step."""
        try:
            url = f"{self._base_uri()}/automation/v1/automations"
            payload = {
                "name": name,
                "description": description,
            }

            if start_source.lower() == "filedrop":
                payload["type"] = "triggered"
                # For now, leaving folderLocationId unconfigured per user request. 
                # SFMC may require it for a fully valid File Drop setup.
                payload["fileTrigger"] = {
                    "fileNamingPattern": file_naming_pattern or f"{name}_%%Year%%%%Month%%%%Day%%.csv",
                    "isPublished": True
                }
            else:
                # Map simple frequency to iCal Recur string
                freq_map = {
                    "hourly": "FREQ=HOURLY;INTERVAL=1",
                    "daily": "FREQ=DAILY;INTERVAL=1",
                    "weekly": "FREQ=WEEKLY;INTERVAL=1",
                    "monthly": "FREQ=MONTHLY;INTERVAL=1"
                }
                ical = freq_map.get(schedule_frequency.lower(), "FREQ=DAILY;INTERVAL=1")
                # Append an arbitrary UNTIL date far in the future if missing
                if "UNTIL" not in ical:
                    ical += ";UNTIL=20301231T000000"
                
                # Dynamic start date: 5 mins from now
                from datetime import datetime, timedelta, timezone
                start_dt = datetime.now(timezone.utc) + timedelta(minutes=5)
                # SFMC schedule dates often require no 'Z' but strict +/- offsets or no offset if timezoneId is 1 (UTC is not strictly timezone 1, Central Time is usually timezoneId 2, but UTC might be 1).
                # User's example: "startDate": "2024-08-11T06:00:00-04:00"
                start_date_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S")

                payload["startSource"] = {
                    "typeId": 1,
                    "schedule": {
                        "icalRecur": ical,
                        "startDate": start_date_str,
                        "timezoneId": 1
                    }
                }

            # If a query_id was provided, stitch it into the Automation as Step 1
            if query_id:
                payload["steps"] = [
                    {
                        "name": "Step 1",
                        "activities": [
                            {
                                "name": "SQL_Query_Step",
                                "objectTypeId": 300,  # 300 = SQL Query Activity
                                "activityObjectId": query_id
                            }
                        ]
                    }
                ]

            response = self._call_sfmc_api(url, method="POST", body=payload)
            logger.info("Created Automation '%s' successfully", name)
            return f"✅ Automation '{name}' created successfully!\n\n{response}"

        except Exception as e:
            logger.error("Failed to create Automation '%s': %s", name, e)
            return f"❌ Failed to create Automation '{name}': {e}"

    # ==================== SUBSCRIBERS ====================

    def get_subscriber_count(self) -> str:
        """Get subscriber count from the All Subscribers list."""
        try:
            url = f"{self._base_uri()}/contacts/v1/addresses/count"
            body = '{"queryFilter":{"hasCriteria":false}}'
            logger.info("Calling SFMC subscriber count API: %s", url)
            response = self._call_sfmc_api(url, method="POST", body=body)
            return f"👥 **Subscriber Data from your SFMC Account:**\n\n{response}"
        except Exception as e:
            logger.error("Failed to get subscriber count: %s", e)
            return f"❌ Failed to get subscriber count: {e}"


# Singleton instance
sfmc_api_service = SfmcApiService()
