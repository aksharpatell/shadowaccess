from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

app = Flask(
    __name__,
    static_folder="../dist",
    static_url_path="/"
)
CORS(app, origins="*", supports_credentials=False)

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
    if path.startswith(("repo", "org", "health")):
        return jsonify({"error": "Not found"}), 404

    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    # Avoid macOS/AirPlay weirdness with 5000
    app.run(debug=True, port=5050)