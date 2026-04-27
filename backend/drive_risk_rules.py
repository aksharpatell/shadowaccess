from datetime import datetime, timezone

def analyze_drive_file_risk(files):
    risks = []
    for f in files:
        file_risks = []
        permissions = f.get("permissions", [])
        name = f.get("name", "unknown")
        modified = f.get("modifiedTime", "")

        # Check for anyone-with-link access
        for perm in permissions:
            if perm.get("type") == "anyone":
                file_risks.append({
                    "rule": "PUBLIC_LINK_ACCESS",
                    "severity": "HIGH",
                    "detail": f'"{name}" is accessible to anyone with the link'
                })

        # Check for external domain sharing
        for perm in permissions:
            if perm.get("type") == "user":
                email = perm.get("emailAddress", "")
                if email and not email.endswith(("@gmail.com", "@googlemail.com")):
                    file_risks.append({
                        "rule": "EXTERNAL_USER_ACCESS",
                        "severity": "MEDIUM",
                        "detail": f'"{name}" shared with external user: {email}'
                    })

        # Check for stale sharing (not modified in 1+ year)
        if modified:
            try:
                mod_dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - mod_dt).days
                if age_days > 365 and permissions:
                    file_risks.append({
                        "rule": "STALE_SHARED_FILE",
                        "severity": "MEDIUM",
                        "detail": f'"{name}" has not been modified in {age_days} days but is still shared'
                    })
            except Exception:
                pass

        # Check for writer/owner permissions granted broadly
        for perm in permissions:
            if perm.get("role") in ("writer", "owner") and perm.get("type") == "anyone":
                file_risks.append({
                    "rule": "PUBLIC_WRITE_ACCESS",
                    "severity": "CRITICAL",
                    "detail": f'"{name}" allows anyone to edit'
                })

        risks.extend(file_risks)

    return risks


def compute_drive_risk_score(risks):
    if not risks:
        return 0

    severity_weights = {
        "CRITICAL": 40,
        "HIGH": 25,
        "MEDIUM": 10,
        "LOW": 5
    }

    total = sum(severity_weights.get(r.get("severity", "LOW"), 5) for r in risks)
    return min(100, total)