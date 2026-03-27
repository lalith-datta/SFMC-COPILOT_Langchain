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
        elif method.upper() == "PATCH":
            json_body = body if isinstance(body, dict) else None
            content = body.encode() if isinstance(body, str) else None
            resp = self._client.patch(url, headers=headers, json=json_body, content=content, params=params)
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
    DEFAULT_CATEGORY_ID = 866434

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

                if field_type == "Text" :
                    col["length"] = int(field.get("maxLength", 254))

                if field_type == "EmailAddress" :
                    col["length"] = 254
                
                if field_type == "Phone" :
                    col["length"] = 50

                if field_type == "Locale" :
                    col["length"] = 5
                
                if field_type == "Decimal" :
                    col["length"] = int(field.get("precision", 18))
                    col["scale"] = int(field.get("scale", 2))

                # Handle default value if provided
                default_val = field.get("defaultValue")
                if default_val is not None:
                    # Handle special getdate logic for dates
                    if field_type == "Date" and str(default_val).strip().lower() in ["current date", "today", "now", "GetDate()"]:
                        col["defaultValue"] = "GetDate()"
                    else:
                        col["defaultValue"] = str(default_val)

                columns.append(col)

            payload["fields"] = columns

            logger.info("Creating DE payload: %s", payload)
            response = self._call_sfmc_api(url, method="POST", body=payload)
            logger.info("Created Data Extension '%s' successfully", name)
            return f"✅ Data Extension '{name}' created successfully in SFMC!\n\nDetails:\n{response}"

        except Exception as e:
            logger.error("Failed to create Data Extension '%s': %s", name, e)
            return f"❌ Failed to create Data Extension '{name}': {e}"

    # # ==================== LIST DATA EXTENSIONS ====================

    # def search_data_extension(self, search_key: str) -> str:
    #     """Search for a Data Extension in the SFMC account."""
    #     try:
    #         url = f"{self._base_uri()}/data/v1/customobjects"
    #         logger.info("Calling SFMC list DEs API: %s", url)
    #         response = self._call_sfmc_api(url, params={"$pageSize": "1","$page": "1", "$search": search_key})
    #         # logger.info("Found Data Extension '%s' successfully", response)
    #         # logger.info(type(response))
    #         payload = json.loads(response)
    #         External_key = payload["items"][0]["key"]
    #         return External_key
    #     except Exception as e:
    #         logger.error("Unable to find Data Extension: %s", e)
    #         return f"❌ Unable to find Data Extension: {e}"

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
        self, name: str, query_text: str, target_data_extension: str, description: str = "", update_type: str = "Overwrite"
    ) -> str:
        """Create an SQL Query Activity in SFMC."""
        try:
            url = f"{self._base_uri()}/automation/v1/queries"
            
            # Map update type string to SFMC ID: 0=Append, 1=Update, 2=Overwrite
            update_type_map = {"overwrite": 0, "update": 1, "append": 2}
            update_id = update_type_map.get(update_type.lower(), 0)
            target_de_key = self._get_data_extension_details(target_data_extension)["key"]

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


    def create_data_extract_activity(
        self, name: str, Data_Extension_Name: str, file_naming_pattern: str, type: str, description: str = "", interval: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> str:
        """Create a Data Extract Activity in SFMC."""
        try:
            url = f"{self._base_uri()}/automation/v1/dataextracts"
            update_type_map = {"Data Extension Extract": "bb94a04d-9632-4623-be47-daabc3f588a6", "UTF16 to ASCII Converter": "e7e14f95-b925-462d-b6b4-4a6b1dca7ca1"}
            interval_map = {"1 day": "1", "7 days": "2", "30 days": "3", "60 days": "5", "90 days": "6"}
            payload = {
                "name": name,
                "key": name.replace(" ", "_"),
                "description": description,
                "dataExtractTypeId": update_type_map.get(type),
                "fileSpec": file_naming_pattern,
                "extractTypeName": type,
                "dataFields": [
                    {
                        "name": "UsesLineFeed",
                        "type": "bool",
                        "value": "True"
                    }
                ]
            }

            if type == "UTF16 to ASCII Converter" and interval:
                payload["intervalType"] = interval_map.get(interval)
            if type == "UTF16 to ASCII Converter" and start_date and end_date:
                payload["startDate"] = start_date
                payload["endDate"] = end_date

            if type == "Data Extension Extract":
                customer_key = self._get_data_extension_details(Data_Extension_Name)["key"]
                payload["dataFields"].extend([
                    {
                        "name": "DECustomerKey",
                        "type": "string",
                        "value": customer_key
                    },
                    {
                        "name": "HasColumnHeaders",
                        "type": "bool",
                        "value": "True"
                    },
                    {
                        "name": "ColumnDelimiter",
                        "type": "string",
                        "value": ","
                    },
                    {
                        "name": "TextQualified",
                        "type": "bool",
                        "value": "True"
                    },
                ])
            response = self._call_sfmc_api(url, method="POST", body=payload)
            logger.info("Created Data Extract Activity '%s' successfully", name)

            try:
                resp_data = json.loads(response)
                data_extract_id = resp_data.get("dataExtractDefinitionId", "unknown_id")
                return f"✅ Data Extract Activity '{name}' created successfully!\nData Extract ID: `{data_extract_id}`\n\nDetails:\n{response}"
            except Exception as e:
                return f"✅ Failed to retreive the Data Extract Activity ID: {e}"

        except Exception as e:
            logger.error("Failed to create Data Extract Activity '%s': %s", name, e)
            return f"❌ Failed to create Data Extract Activity '{name}': {e}"


    # ==================== AUTOMATIONS ====================

    def create_automation(
        self, 
        name: str, 
        description: str = "",
        start_source: str = "Scheduled", 
        schedule_frequency: str = "", 
        file_naming_pattern: str = "",
        matching_type: str = "",
        folder_location: str = "",
    ) -> str:
        """Create an automation in SFMC."""
        try:
            url = f"{self._base_uri()}/automation/v1/automations"
            payload = {
                "name": name,
                "description": description,
            }
            matching_type_map = {"Begins with": 2, "Contains": 1, "Ends with": 3}
            if start_source.lower() == "filedrop":
                payload["startSource"] = {
                    "typeId": 2,
                    "fileDrop": {
                        "fileNamePattern": file_naming_pattern,
                        "fileNamePatternTypeId": matching_type_map.get(matching_type) if file_naming_pattern else 0,
                        "folderLocation": f"import\\{folder_location}\\",
                        "queueFiles": True,
                    }
                }
            else:
                freq_map = {
                    "hourly": "FREQ=HOURLY;INTERVAL=1",
                    "daily": "FREQ=DAILY;INTERVAL=1",
                    "weekly": "FREQ=WEEKLY;INTERVAL=1",
                    "monthly": "FREQ=MONTHLY;INTERVAL=1"
                }
                ical = freq_map.get(schedule_frequency.lower(), "FREQ=DAILY;INTERVAL=1")
                if "UNTIL" not in ical:
                    ical += ";UNTIL=20301231T000000"
                
                from datetime import datetime, timedelta, timezone
                start_dt = datetime.now(timezone.utc) + timedelta(minutes=5)
                start_date_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S")

                payload["startSource"] = {
                    "typeId": 1,
                    "schedule": {
                        "icalRecur": ical,
                        "startDate": start_date_str,
                        "timezoneId": 1
                    }
                }

            response = self._call_sfmc_api(url, method="POST", body=payload)
            logger.info("Created Automation '%s' successfully", name)
            return f"✅ Automation '{name}' created successfully!\n\n{response}"

        except Exception as e:
            logger.error("Failed to create Automation '%s': %s", name, e)
            return f"❌ Failed to create Automation '{name}': {e}"

    # Activity type → SFMC objectTypeId mapping
    _ACTIVITY_TYPE_MAP: dict[str, int] = {
        "sql_query": 300,
        "data_extract": 73,
        "file_transfer": 53,
        "import": 43,
    }

    def add_activity_to_automation(
        self,
        automation_name: str,
        activity_type: str,
        activity_id: str,
        step_number: int = 0,
    ) -> str:
        """Add an activity to a specific step in an existing SFMC automation."""
        try:
            # 1. Resolve objectTypeId
            object_type_id = self._ACTIVITY_TYPE_MAP.get(activity_type.lower().replace(" ", "_"))
            if not object_type_id:
                return f"❌ Unknown activity type '{activity_type}'. Must be one of: {', '.join(self._ACTIVITY_TYPE_MAP.keys())}"

            # 2. Search for the automation by name
            search_url = f"{self._base_uri()}/automation/v1/automations"
            search_response = self._call_sfmc_api(
                search_url, method="GET",
                params={"$pageSize": "10", "$page": "1", "$orderBy": "name", "$filter": f"name eq '{automation_name}'"}
            )
            search_data = json.loads(search_response)
            items = search_data.get("items", [])
            automation = None
            for item in items:
                if item.get("name") == automation_name:
                    automation = item
                    break
            if not automation:
                return f"❌ Automation '{automation_name}' not found in SFMC."

            automation_id = automation["id"]

            # 3. Get the full automation details (including current steps)
            detail_url = f"{self._base_uri()}/automation/v1/automations/{automation_id}"
            detail_response = self._call_sfmc_api(detail_url, method="GET")
            automation_detail = json.loads(detail_response)
            steps = automation_detail.get("steps", [])
            logger.info(f"Automation details: {automation_detail}")

            if automation_detail["typeId"] == 1:
                startSource = {
                    "typeId": automation_detail["typeId"],
                    "schedule": {
                        "icalRecur": automation_detail["schedule"]["icalRecur"],
                        "startDate": automation_detail["schedule"]["startDate"],
                        "timezoneId": automation_detail["schedule"]["timezoneId"],
                    },
                }
            elif automation_detail["typeId"] == 2:
                startSource = {
                    "typeId": automation_detail["typeId"],
                    "fileDrop": {
                        "fileNamePattern": automation_detail["fileTrigger"]["fileNamingPattern"] or "",
                        "fileNamePatternTypeId": 0,
                        "folderLocation": automation_detail["fileTrigger"]["folderLocationText"],
                        "queueFiles": automation_detail["fileTrigger"]["queueFiles"] or True,
                    }
                }

            payload = {
                "name": automation_detail["name"],
                "description": automation_detail["description"],
                "key": automation_detail["key"],
                "startSource": startSource,
                "categoryId": automation_detail["categoryId"],
            }

            patch_steps = []
            for step in steps:
                activities_in_step = []
                for act in step.get("activities", []):
                    activities_in_step.append({
                        "id": act["id"],
                        "name": act["name"],
                        "objectTypeId": act["objectTypeId"],
                        "activityObjectId": act["activityObjectId"],
                        "displayOrder": act["displayOrder"] - 1,
                    })
                patch_steps.append({
                    "annotation": "",
                    "stepNumber": step.get("step", 1) - 1,
                    "activities": activities_in_step,
                })


            # 4. Build the new activity entry
            new_activity = {
                "name": f"{activity_type}_activity",
                "objectTypeId": object_type_id,
                "activityObjectId": activity_id,
                
            }

            # 5. Push new activity into the correct step (1-indexed from user)
            # new_activity["displayOrder"] = 0

            if step_number > len(patch_steps) and len(patch_steps) > 0:
                new_activity["displayOrder"] = 0
                patch_steps.append({"annotation": "", "stepNumber": len(patch_steps), "activities": [new_activity]})
            elif step_number > 0:
                new_activity["displayOrder"] = len(patch_steps[step_number - 1].get("activities", []))
                patch_steps[step_number - 1]["activities"].append(new_activity)

            # 6. PATCH — send the full automation detail with modified steps
            payload["steps"] = patch_steps
            logger.info(f"Patch payload: {json.dumps(payload, indent=2)}")
            self._call_sfmc_api(detail_url, method="PATCH", body=payload)

            logger.info(
                "Added %s activity (id=%s) to Automation '%s' at Step %d",
                activity_type, activity_id, automation_name, step_number,
            )
            return (
                f"✅ Successfully added {activity_type} activity to Automation '{automation_name}' at Step {step_number}!\n"
                f"Activity ID: `{activity_id}`"
            )

        except Exception as e:
            logger.error("Failed to add activity to Automation '%s': %s", automation_name, e)
            return f"❌ Failed to add activity to Automation '{automation_name}': {e}"

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

    # ==================== FILE TRANSFER ACTIVITIES ====================
    def create_file_transfer_activity(
        self,
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
        """Create a File Transfer Activity in SFMC."""
        try:
            url = f"{self._base_uri()}/automation/v1/filetransfers"
            key_url = f"{self._base_uri()}/automation/v1/publickeys"
            file_location_url = f"{self._base_uri()}/automation/v1/ftpLocations"
            response_ftplocations = self._call_sfmc_api(file_location_url, method="GET")
            file_location_id = ""
            res_ftplocations = json.loads(response_ftplocations)
            for ftp_loc in res_ftplocations.get("items", []):
                if ftp_loc.get("name") == file_location:
                    file_location_id = ftp_loc.get("id")
                    break
            payload = {
                "name": name,
                "customerKey": name.replace(" ", "_"),
                "description": description,
                "fileSpec": file_naming_pattern,
                "fileTransferLocationId": file_location_id,
            }

            if file_action == "Manage File":
                payload["isCompressed"] = is_unzip
                payload["isEncrypted"] = decrypt_file
                payload["isUpload"] = False
                payload["maxFileAge"] = file_age
                payload["maxFileAgeScheduleOffset"] = file_offset
                payload["maxImportFrequency"] = import_frequency

                if decrypt_file:
                    response_decryption = self._call_sfmc_api(key_url, method="GET")
                    res_decryption = json.loads(response_decryption)
                    for res in res_decryption:
                        if res.get("name") == private_key:
                            payload["publicKeyManagementId"] = res.get("publicKeyManagementId")
                            break
                
            if file_action == "Move a File From Safehouse":
                payload["isUpload"] = True
                payload["isCompressed"] = 0
                payload["maxFileAge"] = 0
                payload["maxFileAgeScheduleOffset"] = 0
                payload["maxImportFrequency"] = 0
                payload["isEncrypted"] = False
                payload["isPgp"] = False

                if encryption_type:
                    response_encryption = self._call_sfmc_api(key_url, method="GET")
                    res_encryption = json.loads(response_encryption)
                    for res in res_encryption:
                        if res.get("name") == public_key:
                            payload["publicKeyManagementId"] = res.get("publicKeyManagementId")
                            break
                    payload["isEncrypted"] = True
                    if encryption_type == "PGP":
                        payload["isPgp"] = True
            
            logger.info("File Transfer Activity payload: %s", payload)
                
            response = self._call_sfmc_api(url, method="POST", body=payload)
            logger.info("Created File Transfer Activity '%s' successfully", name)
            try:
                res = json.loads(response)
                file_trasfer_activity_id = res['id']
                return f"✅ File Transfer Activity '{name}' created successfully! and here is the ID: {file_trasfer_activity_id}"
            except Exception as e:
                return f"✅ Failed to retreive the File Transfer Activity ID: {e}"
        except Exception as e:
            logger.error("Failed to create File Transfer Activity '%s': %s", name, e)
            return f"❌ Failed to create File Transfer Activity '{name}': {e}"

    # ==================== HELPERS ====================

    def _get_data_extension_details(self, name: str) -> dict:
        """Look up a Data Extension by name and return its id, key, and name.

        Uses the /data/v1/customobjects search API.
        Returns: {"id": "...", "key": "...", "name": "..."} or raises RuntimeError.
        """
        url = f"{self._base_uri()}/data/v1/customobjects"
        response = self._call_sfmc_api(url, params={"$pageSize": "1", "$page": "1", "$search": name})
        payload = json.loads(response)
        items = payload.get("items", [])
        for item in items:
            if item.get("name") == name:
                return {"id": item["id"], "key": item["key"], "name": item.get("name", name)}
        raise RuntimeError(f"Data Extension '{name}' not found in SFMC")

    # ==================== IMPORT ACTIVITIES ====================

    def create_import_activity(
        self,
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
        """Create an Import Activity (Data Copy) in SFMC."""
        try:
            url = f"{self._base_uri()}/automation/v1/imports"

            # Resolve update type
            update_type_map = {"add only": 1, "update only": 2, "add and update": 0, "overwrite": 4}
            update_type_id = update_type_map.get(update_type.lower(), 4)

            # Look up source and destination DE details
            source_de = self._get_data_extension_details(source_data_extension_name)
            destination_de = self._get_data_extension_details(destination_data_extension_name)

            logger.info(
                "Import: source DE '%s' (id=%s), destination DE '%s' (id=%s)",
                source_data_extension_name, source_de["id"],
                destination_data_extension_name, destination_de["id"],
            )

            # Common payload fields
            payload: dict = {
                "name": name,
                "customerKey": name.replace(" ", "_"),
                "description": description,
                "destinationObjectTypeId": 310,
                "destinationObjectId": destination_de["id"],
                "subscriberImportTypeId": 255,
                "updateTypeId": update_type_id,
                "fieldMappingType": "InferFromColumnHeadings",
                "fieldMappings": [],
                "isSequential": True,
                "allowErrors": allow_errors,
                "hasColumnHeader": True,
                "isOrderedImport": True,
                "sendEmailNotification": send_email_notification,
                "notificationEmailAddress": notification_email_address,
                "blankFileProcessingType": 0,
                "sourceCustomObjectId": source_de["id"],
                "sourceDataExtensionName": source_data_extension_name,
                "destinationName": destination_data_extension_name,
            }

            if data_source_type.lower() == "filelocation":
                # Resolve FTP location ID
                ftp_url = f"{self._base_uri()}/automation/v1/ftpLocations"
                response_ftp = self._call_sfmc_api(ftp_url, method="GET")
                res_ftp = json.loads(response_ftp)
                file_location_id = ""
                for ftp_loc in res_ftp.get("items", []):
                    if ftp_loc.get("name") == file_location_name:
                        file_location_id = ftp_loc.get("id")
                        break
                if not file_location_id:
                    return f"❌ File location '{file_location_name}' not found in SFMC FTP locations."

                payload["fileTransferLocationId"] = file_location_id
                payload["fileNamingPattern"] = file_naming_pattern
                payload["fileType"] = file_type
                payload["maxImportFrequencyHours"] = 0
                payload["maxFileAgeHours"] = 0
                payload["maxFileAgeScheduleOffsetHours"] = 0
                payload["standardQuotedStrings"] = True
                payload["dateFormatLocale"] = "en-US"
                payload["deleteFile"] = False
                payload["fileSpec"] = None
            else:
                # Data Extension source — fileSpec is _CustomObject
                payload["fileSpec"] = "_CustomObject"
                payload["destinationId"] = None

            logger.info("Import Activity payload: %s", payload)
            response = self._call_sfmc_api(url, method="POST", body=payload)
            logger.info("Created Import Activity '%s' successfully", name)

            try:
                resp_data = json.loads(response)
                import_id = resp_data.get("importDefinitionId", "unknown_id")
                return f"✅ Import Activity '{name}' created successfully!\nImport Definition ID: `{import_id}`\n\nDetails:\n{response}"
            except Exception:
                return f"✅ Import Activity '{name}' created successfully!\n\nDetails:\n{response}"

        except Exception as e:
            logger.error("Failed to create Import Activity '%s': %s", name, e)
            return f"❌ Failed to create Import Activity '{name}': {e}"


# Singleton instance
sfmc_api_service = SfmcApiService()
