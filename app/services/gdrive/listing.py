from typing import Any


def list_files_in_folder(service: Any, folder_id: str) -> list[dict]:
    all_files: list[dict] = []
    page_token: str | None = None

    while True:
        resp = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id,name,mimeType,size,modifiedTime,shortcutDetails(targetId,targetMimeType))",
                pageToken=page_token,
                pageSize=1000,
            )
            .execute()
        )

        files = resp.get("files", [])
        all_files.extend(files)

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return all_files