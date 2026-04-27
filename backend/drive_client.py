from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def get_shared_files(token_info):
    creds = Credentials(
        token=token_info["access_token"],
        refresh_token=token_info.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_info["client_id"],
        client_secret=token_info["client_secret"],
    )

    service = build("drive", "v3", credentials=creds)
    results = []
    page_token = None

    while True:
        response = service.files().list(
            q="sharedWithMe=true or (visibility='anyoneWithLink') or (visibility='anyoneCanFind')",
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType, shared, sharingUser, owners, permissions, createdTime, modifiedTime, webViewLink, parents)",
            pageToken=page_token,
            pageSize=100
        ).execute()
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    # Collect all unique parent IDs
    parent_ids = set()
    for f in results:
        for pid in f.get("parents", []):
            parent_ids.add(pid)

    # Fetch folder names in batches of 100
    folder_map = {}
    parent_list = list(parent_ids)
    for i in range(0, len(parent_list), 100):
        batch = parent_list[i:i+100]
        query = " or ".join([f"id='{pid}'" for pid in batch])
        try:
            folder_resp = service.files().list(
                q=query,
                fields="files(id, name, mimeType)",
                pageSize=100
            ).execute()
            for folder in folder_resp.get("files", []):
                folder_map[folder["id"]] = folder["name"]
        except Exception:
            pass

    # Attach folder name to each file
    for f in results:
        parents = f.get("parents", [])
        if parents:
            f["folder_name"] = folder_map.get(parents[0], "My Drive")
            f["folder_id"] = parents[0]
        else:
            f["folder_name"] = "My Drive"
            f["folder_id"] = "root"

    return results