import uuid
from services.sfmc_api import sfmc_api_service

run_id = str(uuid.uuid4())[:6]
automation_name = f"Test_Automation_StartSource_{run_id}"

print(f"Creating Automation: {automation_name}")
response = sfmc_api_service.create_automation(
    name=automation_name,
    description="Testing the new startSource payload structure",
    start_source="Scheduled",
    schedule_frequency="Daily"
)
print(response)
