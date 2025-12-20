import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_API = "https://api.github.com"


def github_headers():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ShadowAccess",
        }

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ShadowAccess",
    }


def github_get(url: str, accept: str | None = None):
    headers = github_headers()
    if accept:
        headers["Accept"] = accept
    return requests.get(url, headers=headers)


def get_public_repo(owner: str, repo: str) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    r = github_get(url)
    if r.status_code != 200:
        raise Exception(f"GitHub API error {r.status_code}: {r.text}")
    return r.json()


def get_org_repos(owner: str) -> list[dict]:
    # Works for both orgs and users
    repos = []
    page = 1
    per_page = 100

    while True:
        url = f"{GITHUB_API}/users/{owner}/repos?per_page={per_page}&page={page}&type=all&sort=updated"
        r = github_get(url)
        if r.status_code != 200:
            raise Exception(f"GitHub API error {r.status_code}: {r.text}")

        batch = r.json()
        if not isinstance(batch, list) or len(batch) == 0:
            break

        repos.extend(batch)
        if len(batch) < per_page:
            break
        page += 1

    return repos


def get_repo_collaborators(owner: str, repo: str) -> list[dict]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/collaborators?per_page=100"
    r = github_get(url)

    # 403 happens often (public repos / missing perms) — let caller handle
    if r.status_code == 404:
        return []
    if r.status_code != 200:
        raise Exception(f"GitHub API error {r.status_code}: {r.text}")

    return r.json()


def get_branch_protection(owner: str, repo: str) -> dict | None:
    # Need default branch name first
    repo_meta = get_public_repo(owner, repo)
    default_branch = repo_meta.get("default_branch", "main")

    url = f"{GITHUB_API}/repos/{owner}/{repo}/branches/{default_branch}/protection"
    r = github_get(url)

    if r.status_code == 404:
        # No protection enabled
        return None

    if r.status_code != 200:
        # Common: 403 "Resource not accessible by personal access token"
        raise Exception(f"GitHub API error {r.status_code}: {r.text}")

    return r.json()


def get_codeowners(owner: str, repo: str) -> str | None:
    # CODEOWNERS can live in multiple locations
    paths = [
        ".github/CODEOWNERS",
        "CODEOWNERS",
        "docs/CODEOWNERS",
    ]

    for path in paths:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
        r = github_get(url, accept="application/vnd.github+json")

        if r.status_code == 404:
            continue

        if r.status_code != 200:
            # 403 is common — caller handles
            raise Exception(f"GitHub API error {r.status_code}: {r.text}")

        content_b64 = r.json().get("content", "")
        if not content_b64:
            return None

        decoded = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
        return decoded

    return None
