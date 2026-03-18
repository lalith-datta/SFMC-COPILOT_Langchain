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

    def list_data_extensions(self) -> str:
        """List all Data Extensions in the SFMC account."""
        try:
            url = f"{self._base_uri()}/data/v1/customobjects"
            logger.info("Calling SFMC list DEs API: %s", url)
            response = self._call_sfmc_api(url, params={"$pageSize": "50", "$search": "*"})
            return f"📊 **Your Data Extensions:**\n\n{response}"
        except Exception as e:
            logger.error("Failed to list Data Extensions: %s", e)
            return f"❌ Failed to list Data Extensions: {e}"

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

    # ==================== AUTOMATIONS ====================

    def create_automation(self, name: str, description: str, schedule_frequency: str) -> str:
        """Create an automation in SFMC."""
        try:
            url = f"{self._base_uri()}/automation/v1/automations"
            payload = {
                "name": name,
                "description": description,
                "type": "scheduled",
                "schedule": {"scheduleType": schedule_frequency},
            }

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
