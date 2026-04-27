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
            fields="nextPageToken, files(id, name, mimeType, shared, sharingUser, owners, permissions, createdTime, modifiedTime, webViewLink)",
            pageToken=page_token,
            pageSize=100
        ).execute()

        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results