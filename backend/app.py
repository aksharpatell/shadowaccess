from flask import Flask, request, jsonify
from flask_cors import CORS

from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(
    __name__,
    static_folder="../dist",
    static_url_path="/"
)

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

app = Flask(__name__)
CORS(app)


@app.route("/")
def health_check():
    return "ShadowAccess is running"


@app.route("/repo")
def repo():
    owner = request.args.get("owner")
    repo_name = request.args.get("repo")

    if not owner or not repo_name:
        return jsonify({"error": "owner and repo are required"}), 400

    # Always fetch public metadata (available for public repos)
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
            "risk_model": {
                "method": "normalized_severity_weighting",
                "scale": "0–100",
                "interpretation": {
                    "0–25": "Low risk",
                    "26–50": "Moderate risk",
                    "51–75": "High risk",
                    "76–100": "Critical risk"
                }
            },
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
        # Heuristic mode: still returns meaningful score, not stuck at 50
        heuristic_risks = analyze_public_metadata(repo_meta)
        score = compute_repo_risk_score(heuristic_risks)

        return jsonify({
            "repository": f"{owner}/{repo_name}",
            "overall_risk_score": score,
            "confidence": "HEURISTIC",
            "note": "GitHub API restricted access to collaborators/branch protection/CODEOWNERS. Score inferred from public metadata.",
            "repo_metadata": {
                "private": repo_meta.get("private"),
                "archived": repo_meta.get("archived"),
                "fork": repo_meta.get("fork"),
                "default_branch": repo_meta.get("default_branch"),
                "pushed_at": repo_meta.get("pushed_at"),
                "stars": repo_meta.get("stargazers_count", 0)
            },
            "risk_analysis": heuristic_risks,
            "debug": str(e)  # keep while developing; remove later for demo
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

        except Exception:
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
                "note": "Score inferred from public metadata (GitHub access restricted)."
            })

    results.sort(key=lambda r: r.get("overall_risk_score", 0), reverse=True)

    return jsonify({
        "owner": owner,
        "repo_count": len(results),
        "repositories": results
    })


if __name__ == "__main__":
    app.run(debug=True)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")
