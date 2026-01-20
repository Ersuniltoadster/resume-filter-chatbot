from io import BytesIO
from typing import Any

from googleapiclient.http import MediaIoBaseDownload


def download_file_bytes(service: Any, file_id: str) -> bytes:
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    return fh.getvalue()


def export_google_doc_bytes(service: Any, file_id: str, mime_type: str = "text/plain") -> bytes:
    request = service.files().export(fileId=file_id, mimeType=mime_type)
    return request.execute()