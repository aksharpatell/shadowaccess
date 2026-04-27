from datetime import datetime, timezone

def analyze_drive_file_risk(files):
    risks = []
    for f in files:
        file_risks = []
        permissions = f.get("permissions", [])
        name = f.get("name", "unknown")
        folder_name = f.get("folder_name", "My Drive")
        folder_id = f.get("folder_id", "root")
		folder_name = f.get("folder_name", "My Drive")
		folder_id = f.get("folder_id", "root")
        modified = f.get("modifiedTime", "")

        # Check for anyone-with-link access
        for perm in permissions:
            if perm.get("type") == "anyone":
                file_risks.append({
                    "rule": "PUBLIC_LINK_ACCESS",
                    "severity": "HIGH",
                    "detail": f'"{name}" is accessible to anyone with the link', "link": f.get("webViewLink", ""), "file_id": f.get("id", ""), "folder_name": folder_name, "folder_id": folder_id
                })

        # Check for external domain sharing
        for perm in permissions:
            if perm.get("type") == "user":
                email = perm.get("emailAddress", "")
                if email and not email.endswith(("@gmail.com", "@googlemail.com")):
                    file_risks.append({
                        "rule": "EXTERNAL_USER_ACCESS",
                        "severity": "MEDIUM",
                        "detail": f'"{name}" shared with external user: {email}', "link": f.get("webViewLink", ""), "file_id": f.get("id", ""), "folder_name": folder_name, "folder_id": folder_id
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
                        "detail": f'"{name}" has not been modified in {age_days} days but is still shared', "link": f.get("webViewLink", ""), "file_id": f.get("id", ""), "folder_name": folder_name, "folder_id": folder_id
                    })
            except Exception:
                pass

        # Check for writer/owner permissions granted broadly
        for perm in permissions:
            if perm.get("role") in ("writer", "owner") and perm.get("type") == "anyone":
                file_risks.append({
                    "rule": "PUBLIC_WRITE_ACCESS",
                    "severity": "CRITICAL",
                    "detail": f'"{name}" allows anyone to edit', "link": f.get("webViewLink", ""), "file_id": f.get("id", ""), "folder_name": folder_name, "folder_id": folder_id
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

    # Count unique files affected
    import re
    affected_files = set()
    for r in risks:
        match = re.match(r'^"([^"]+)"', r.get("detail", ""))
        if match:
            affected_files.add(match.group(1))

    total_files = max(len(affected_files), 1)

    # Score based on worst offenders, normalized by file count
    critical = sum(1 for r in risks if r.get("severity") == "CRITICAL")
    high = sum(1 for r in risks if r.get("severity") == "HIGH")
    medium = sum(1 for r in risks if r.get("severity") == "MEDIUM")

    raw = (critical * 40 + high * 15 + medium * 5)
    normalized = raw / total_files

    return min(100, int(normalized))