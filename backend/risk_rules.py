def analyze_permission_risk(collaborators: list[dict]) -> list[dict]:
    risks = []

    if not collaborators:
        # If you can read collaborators and it’s empty, that’s interesting but not “high risk”
        return risks

    admin_users = [c for c in collaborators if c.get("permissions", {}).get("admin")]

    for c in admin_users:
        risks.append({
            "risk": "HIGH",
            "severity": 9,
            "user": c.get("login"),
            "reason": "User has admin access (can modify settings, add users, delete repo).",
            "recommendation": "Limit admin access to maintainers only."
        })

    if len(collaborators) == 1:
        risks.append({
            "risk": "REVIEW",
            "severity": 7,
            "user": "REPO",
            "reason": "Single-maintainer repository (bus factor = 1).",
            "recommendation": "Add at least one additional maintainer."
        })

    # Privilege separation check
    if len(collaborators) > 1:
        all_admin = all(c.get("permissions", {}).get("admin") for c in collaborators)
        if all_admin:
            risks.append({
                "risk": "HIGH",
                "severity": 8,
                "user": "REPO",
                "reason": "All collaborators have admin access (no privilege separation).",
                "recommendation": "Introduce role separation and least privilege."
            })

    return risks


def analyze_branch_protection(branch_protection: dict | None) -> list[dict]:
    risks = []

    if branch_protection is None:
        risks.append({
            "risk": "HIGH",
            "severity": 7,
            "user": "REPO",
            "reason": "Branch protection is disabled on the default branch.",
            "recommendation": "Enable branch protection and require pull request reviews."
        })
        return risks

    # Minimal checks (GitHub’s JSON varies by plan/settings)
    required_reviews = branch_protection.get("required_pull_request_reviews")
    if not required_reviews:
        risks.append({
            "risk": "REVIEW",
            "severity": 6,
            "user": "REPO",
            "reason": "Branch protection does not require pull request reviews.",
            "recommendation": "Require at least 1 approving review before merge."
        })

    enforce_admins = branch_protection.get("enforce_admins")
    if not enforce_admins:
        risks.append({
            "risk": "REVIEW",
            "severity": 5,
            "user": "REPO",
            "reason": "Branch protection may not enforce rules for admins.",
            "recommendation": "Enforce branch protection rules for admins."
        })

    return risks


def analyze_codeowners(codeowners_text: str | None) -> list[dict]:
    risks = []
    if not codeowners_text:
        risks.append({
            "risk": "HIGH",
            "severity": 8,
            "user": "REPO",
            "reason": "No CODEOWNERS file found.",
            "recommendation": "Add CODEOWNERS to enforce review accountability."
        })
        return risks

    # Basic sanity: if file exists but empty/meaningless
    stripped = codeowners_text.strip()
    if len(stripped) < 5:
        risks.append({
            "risk": "REVIEW",
            "severity": 5,
            "user": "REPO",
            "reason": "CODEOWNERS exists but appears empty or ineffective.",
            "recommendation": "Add clear ownership rules for critical paths."
        })

    return risks


def analyze_public_metadata(repo_meta: dict) -> list[dict]:
    """
    Used when GitHub blocks collaborator/protection access.
    This is heuristic but useful — and returns non-50 scores.
    """
    risks = []

    # archived
    if repo_meta.get("archived"):
        risks.append({
            "risk": "HIGH",
            "severity": 8,
            "user": "REPO",
            "reason": "Repository is archived (maintenance likely stopped).",
            "recommendation": "Unarchive only if actively maintained, otherwise migrate/retire."
        })

    # stale pushes
    pushed_at = repo_meta.get("pushed_at")  # "YYYY-MM-DDTHH:MM:SSZ"
    if pushed_at:
        year = int(pushed_at[:4])
        if year <= 2023:
            risks.append({
                "risk": "REVIEW",
                "severity": 6,
                "user": "REPO",
                "reason": f"Repository appears stale (last push: {pushed_at}).",
                "recommendation": "Audit dependencies and ownership; confirm maintenance plan."
            })

    # no license
    if not repo_meta.get("license"):
        risks.append({
            "risk": "REVIEW",
            "severity": 5,
            "user": "REPO",
            "reason": "No license detected.",
            "recommendation": "Add an explicit OSS/proprietary license to reduce legal ambiguity."
        })

    # low oversight
    stars = repo_meta.get("stargazers_count", 0)
    watchers = repo_meta.get("watchers_count", 0)
    if stars == 0 and watchers == 0:
        risks.append({
            "risk": "REVIEW",
            "severity": 4,
            "user": "REPO",
            "reason": "Low external oversight (0 stars/watchers).",
            "recommendation": "Increase review rigor and add required checks."
        })

    # forks can inherit risk
    if repo_meta.get("fork"):
        risks.append({
            "risk": "REVIEW",
            "severity": 4,
            "user": "REPO",
            "reason": "Repository is a fork (inherits upstream risk/ownership decisions).",
            "recommendation": "Verify upstream security posture and review differences."
        })

    # issues disabled reduces governance
    if repo_meta.get("has_issues") is False:
        risks.append({
            "risk": "REVIEW",
            "severity": 4,
            "user": "REPO",
            "reason": "Issues are disabled (reduced governance visibility).",
            "recommendation": "Enable issues or use an equivalent tracking system."
        })

    return risks


def compute_repo_risk_score(risks: list[dict]) -> int:
    """
    Normalized severity weighting -> 0-100.
    - no risks => low score
    - multiple high severities => high score
    """
    if not risks:
        return 15

    # Sum severities, cap, then normalize
    total = 0
    for r in risks:
        total += int(r.get("severity", 0))

    # Normalize: assume ~30 severity is "high", clamp to 100
    score = int(min(100, (total / 30) * 100))
    if score < 0:
        score = 0
    return score
