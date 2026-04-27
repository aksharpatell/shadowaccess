from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import secrets
from google_auth_oauthlib.flow import Flow
from drive_client import get_shared_files
from drive_risk_rules import analyze_drive_file_risk, compute_drive_risk_score

# Load env FIRST before reading any variables
load_dotenv()

app = Flask(
    __name__,
    static_folder="../dist",
    static_url_path="/"
)
CORS(app, origins=["https://shadowaccess.vercel.app", "http://localhost:5173"], supports_credentials=True)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

from github_client import (
    get_public_repo,
    get_repo_collaborators,
    get_branch_protection,
    get_codeowners,
    get_org_repos
)

from risk_rules import (
    analyze_permission_risk,
    analyze_branch_protection,
    analyze_codeowners,
    analyze_public_metadata,
    compute_repo_risk_score
)

import threading

#GOOGLE SHEETS
def log_to_sheet(owner, confidence, score, repo_count):
    try:
        requests.post(
            "https://script.google.com/macros/s/AKfycby2yF1RC3KIzcr2HKjqq7bUq8ileGyBIyNz8WUOqUcPcNBE1VtZqaLR6WaiCqybgsj5lQ/exec",
            json={"owner": owner, "confidence": confidence, "score": score, "repo_count": repo_count},
            timeout=5
        )
    except:
        pass

def log_async(owner, confidence, score, repo_count):
    threading.Thread(target=log_to_sheet, args=(owner, confidence, score, repo_count)).start()


@app.route("/health")
def health_check():
    return "ShadowAccess is running"


@app.route("/repo")
def repo():
    owner = request.args.get("owner")
    repo_name = request.args.get("repo")

    if not owner or not repo_name:
        return jsonify({"error": "owner and repo are required"}), 400

    repo_meta = get_public_repo(owner, repo_name)

    try:
        collaborators = get_repo_collaborators(owner, repo_name)
        branch_protection = get_branch_protection(owner, repo_name)
        codeowners = get_codeowners(owner, repo_name)

        permission_risks = analyze_permission_risk(collaborators)
        branch_risks = analyze_branch_protection(branch_protection)
        codeowner_risks = analyze_codeowners(codeowners)

        all_risks = permission_risks + branch_risks + codeowner_risks
        overall_score = compute_repo_risk_score(all_risks)

        return jsonify({
            "repository": f"{owner}/{repo_name}",
            "overall_risk_score": overall_score,
            "confidence": "VERIFIED",
            "repo_metadata": {
                "private": repo_meta.get("private"),
                "archived": repo_meta.get("archived"),
                "fork": repo_meta.get("fork"),
                "default_branch": repo_meta.get("default_branch"),
                "pushed_at": repo_meta.get("pushed_at"),
                "stars": repo_meta.get("stargazers_count", 0)
            },
            "risk_analysis": all_risks
        })

    except Exception as e:
        heuristic_risks = analyze_public_metadata(repo_meta)
        score = compute_repo_risk_score(heuristic_risks)

        return jsonify({
            "repository": f"{owner}/{repo_name}",
            "overall_risk_score": score,
            "confidence": "HEURISTIC",
            "note": "GitHub API restricted access. Score inferred from public metadata.",
            "repo_metadata": {
                "private": repo_meta.get("private"),
                "archived": repo_meta.get("archived"),
                "fork": repo_meta.get("fork"),
                "default_branch": repo_meta.get("default_branch"),
                "pushed_at": repo_meta.get("pushed_at"),
                "stars": repo_meta.get("stargazers_count", 0)
            },
            "risk_analysis": heuristic_risks,
            "debug": str(e)
        })


@app.route("/org")
def org():
    owner = request.args.get("owner")
    if not owner:
        return jsonify({"error": "owner is required"}), 400

    repos = get_org_repos(owner)
    results = []

    for repo_meta in repos:
        repo_name = repo_meta.get("name")
        full = f"{owner}/{repo_name}"

        try:
            collaborators = get_repo_collaborators(owner, repo_name)
            branch_protection = get_branch_protection(owner, repo_name)
            codeowners = get_codeowners(owner, repo_name)

            permission_risks = analyze_permission_risk(collaborators)
            branch_risks = analyze_branch_protection(branch_protection)
            codeowner_risks = analyze_codeowners(codeowners)

            all_risks = permission_risks + branch_risks + codeowner_risks
            score = compute_repo_risk_score(all_risks)

            results.append({
                "repository": full,
                "overall_risk_score": score,
                "confidence": "VERIFIED",
                "risk_count": len(all_risks),
                "top_risks": all_risks[:3],
                "repo_metadata": {
                    "archived": repo_meta.get("archived"),
                    "fork": repo_meta.get("fork"),
                    "pushed_at": repo_meta.get("pushed_at"),
                    "stars": repo_meta.get("stargazers_count", 0)
                }
            })

        except Exception as e:
            heuristic_risks = analyze_public_metadata(repo_meta)
            score = compute_repo_risk_score(heuristic_risks)

            results.append({
                "repository": full,
                "overall_risk_score": score,
                "confidence": "HEURISTIC",
                "risk_count": len(heuristic_risks),
                "top_risks": heuristic_risks[:3],
                "repo_metadata": {
                    "archived": repo_meta.get("archived"),
                    "fork": repo_meta.get("fork"),
                    "pushed_at": repo_meta.get("pushed_at"),
                    "stars": repo_meta.get("stargazers_count", 0)
                },
                "note": "Score inferred from public metadata (GitHub access restricted).",
                "debug": str(e)
            })

    results.sort(key=lambda r: r.get("overall_risk_score", 0), reverse=True)
    avg_score = int(sum(r["overall_risk_score"] for r in results) / len(results)) if results else 0
    dominant_confidence = "VERIFIED" if any(r.get("confidence") == "VERIFIED" for r in results) else "HEURISTIC"
    log_async(owner, dominant_confidence, avg_score, len(results))

    return jsonify({
        "owner": owner,
        "repo_count": len(results),
        "repositories": results
    })


# Serve React build for any non-API route
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    # Keep API routes from being swallowed
    if path.startswith(("repo", "org", "health", "auth", "drive")):
        return jsonify({"error": "Not found"}), 404

    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


@app.route("/auth/google")
def auth_google():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/drive"],
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
    access_type="offline",
    include_granted_scopes="false",
    prompt="consent"
    )
    from flask import session
    session["state"] = state
    return jsonify({"auth_url": auth_url})


@app.route("/auth/callback")
def auth_callback():
    import os
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/drive"],
        redirect_uri=GOOGLE_REDIRECT_URI,
    )

    authorization_response = request.url.replace("http://", "https://")
    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials

    token = creds.token
    refresh_token = creds.refresh_token or ""

    return f'''<script>
window.opener.postMessage({{
  type: "drive_authed",
  access_token: "{token}",
  refresh_token: "{refresh_token}"
}}, "*");
window.close();
</script>'''


@app.route("/drive/scan")
def drive_scan():
    access_token = request.headers.get("X-Drive-Token")
    if not access_token:
        return jsonify({"error": "Not authenticated"}), 401

    token_info = {
        "access_token": access_token,
        "refresh_token": None,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
    }

    files = get_shared_files(token_info)
    risks = analyze_drive_file_risk(files)
    score = compute_drive_risk_score(risks)

    return jsonify({
        "total_files": len(files),
        "overall_risk_score": score,
        "risk_analysis": risks
    })

@app.route("/drive/revoke-access", methods=["POST"])
def revoke_access():
    access_token = request.headers.get("X-Drive-Token")
    if not access_token:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.json
    file_id = data.get("file_id")
    if not file_id:
        return jsonify({"error": "file_id required"}), 400

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=access_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )
    service = build("drive", "v3", credentials=creds)

    # Find and delete the 'anyone' permission
    perms = service.permissions().list(fileId=file_id).execute()
    for perm in perms.get("permissions", []):
        if perm.get("type") == "anyone":
            service.permissions().delete(fileId=file_id, permissionId=perm["id"]).execute()

    return jsonify({"success": True})

if __name__ == "__main__":
    # Avoid macOS/AirPlay weirdness with 5000
    app.run(debug=True, port=5050)