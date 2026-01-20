from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.core.config import settings

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():
    if not settings.gdrive_service_account_json_path:
        raise ValueError("GDRIVE_SERVICE_ACCOUNT_JSON_PATH is not set")

    creds = Credentials.from_service_account_file(
        settings.gdrive_service_account_json_path,
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)