import React, { useMemo, useState, useEffect } from "react";

const API_BASE = "https://shadowaccess-zrjr.onrender.com";

function scoreClass(score) {
  if (score <= 25) return "scoreLow";
  if (score <= 50) return "scoreMed";
  if (score <= 75) return "scoreHigh";
  return "scoreCrit";
}

function confidenceBadge(confidence) {
  if (confidence === "VERIFIED") return "pill badgeVerified";
  return "pill badgeHeuristic";
}

export default function App() {
  const [tab, setTab] = useState("github");

  return (
    <div className="container">
      <div className="card">

        {/* HEADER */}
<div className="header">
  <div className="brand">
    {tab === "github" ? (
      <img src="/github-logo.png" alt="GitHub" className="githubLogo" />
    ) : (
      <img src="/drive-logo.png" alt="Google Drive" className="githubLogo" />
    )}
    <div>
      <div className="title">
        <span className="lockIcon">🔒</span> ShadowAccess
      </div>
      <div className="subtitle">
        {tab === "github"
          ? "GitHub access risk analysis"
          : "Google Drive sharing risk analysis"}
      </div>
    </div>
  </div>
</div>

        {/* TABS */}
        <div style={{ display: "flex", gap: 8, padding: "0 24px", borderBottom: "1px solid #2a2a2a", marginBottom: 0 }}>
          <button
            onClick={() => setTab("github")}
            style={{
              background: "none", border: "none", cursor: "pointer",
              padding: "12px 16px", fontSize: 14, fontWeight: 600,
              color: tab === "github" ? "#58a6ff" : "#888",
              borderBottom: tab === "github" ? "2px solid #58a6ff" : "2px solid transparent",
              marginBottom: -1
            }}
          >
            GitHub
          </button>
          <button
            onClick={() => setTab("drive")}
            style={{
              background: "none", border: "none", cursor: "pointer",
              padding: "12px 16px", fontSize: 14, fontWeight: 600,
              color: tab === "drive" ? "#58a6ff" : "#888",
              borderBottom: tab === "drive" ? "2px solid #58a6ff" : "2px solid transparent",
              marginBottom: -1
            }}
          >
            Google Drive
          </button>
        </div>

        {tab === "github" && <GitHubTab />}
        {tab === "drive" && <DriveTab />}
      </div>

      <footer className="footer">
        Built by <strong>Akshar Patel</strong> - Computer Science Student @ University of Illinois Urbana-Champaign
      </footer>
    </div>
  );
}

// ─── GITHUB TAB ───────────────────────────────────────────────────────────────

function GitHubTab() {
  const [owner, setOwner] = useState("");
  const [loading, setLoading] = useState(false);
  const [progressText, setProgressText] = useState("");
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    if (!loading) return;
    const steps = [
      "Fetching repositories…",
      "Analyzing permissions…",
      "Checking branch protection…",
      "Evaluating CODEOWNERS…",
      "Scoring risk profile…",
    ];
    let i = 0;
    setProgressText(steps[0]);
    const interval = setInterval(() => {
      i++;
      if (i < steps.length) setProgressText(steps[i]);
    }, 700);
    return () => clearInterval(interval);
  }, [loading]);

  async function scanOrg() {
    setLoading(true);
    setErr("");
    setData(null);
    try {
      const res = await fetch(`${API_BASE}/org?owner=${encodeURIComponent(owner)}`);
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || "Request failed");
      setData(json);
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setLoading(false);
      setProgressText("");
    }
  }

  return (
    <div className="content">
      <div className="introBox">
        <p>
          <strong>ShadowAccess</strong> inspects GitHub repositories and
          organizations to surface access control risks such as excessive admin
          permissions, missing <code>CODEOWNERS</code>, and unprotected branches.
        </p>
        <p className="muted">
          When GitHub limits visibility, risk scores are estimated and clearly labeled.
        </p>
      </div>

      <div className="row">
        <input
          className="input"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
          placeholder="Enter a GitHub username or org (e.g. vercel)"
        />
        <button
          className="btn"
          onClick={scanOrg}
          disabled={loading || owner.trim().length === 0}
        >
          {loading ? "Scanning…" : "Scan"}
        </button>
        <button className="pill" onClick={() => setShowHelp(true)}>
          How scoring works
        </button>
      </div>

      {loading && (
        <div className="meta" style={{ marginTop: 10 }}>
          ⏳ {progressText} <br />
          Estimated time: ~5–10 seconds
        </div>
      )}

      {err && <div className="error">Error: {err}</div>}

      {data?.repositories?.length > 0 && (
        <div className="grid">
          {data.repositories.map((r) => (
            <RepoCard key={r.repository} repo={r} />
          ))}
        </div>
      )}

      {showHelp && <ScoringModal onClose={() => setShowHelp(false)} />}
    </div>
  );
}

// ─── GOOGLE DRIVE TAB ─────────────────────────────────────────────────────────

function DriveTab() {
  const [authed, setAuthed] = useState(false);
  const [accessToken, setAccessToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  function connectDrive() {
    fetch(`${API_BASE}/auth/google`)
      .then((r) => r.json())
      .then(({ auth_url }) => {
        const popup = window.open(auth_url, "driveAuth", "width=500,height=600");
        window.addEventListener("message", function handler(e) {
          if (e.data?.type === "drive_authed") {
            setAccessToken(e.data.access_token);
            setAuthed(true);
            popup.close();
            window.removeEventListener("message", handler);
          }
        });
      })
      .catch(() => setErr("Failed to start Google auth."));
  }

  async function scanDrive() {
    setLoading(true);
    setErr("");
    setData(null);
    try {
      const res = await fetch(`${API_BASE}/drive/scan`, {
        headers: { "X-Drive-Token": accessToken }
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || "Scan failed");
      setData(json);
    } catch (e) {
      setErr(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="content">
      <div className="introBox">
        <p>
          <strong>ShadowAccess for Google Drive</strong> scans your files for
          risky sharing — public links, external users with edit access, and
          files that haven't been touched in years but are still shared.
        </p>
        <p className="muted">
          We only request read-only metadata access. No file contents are read.
        </p>
      </div>

      {!authed ? (
        <button className="btn" onClick={connectDrive}>
          Connect Google Drive
        </button>
      ) : (
        <button className="btn" onClick={scanDrive} disabled={loading}>
          {loading ? "Scanning…" : "Scan My Drive"}
        </button>
      )}

      {err && <div className="error" style={{ marginTop: 12 }}>Error: {err}</div>}

      {data && (
        <div style={{ marginTop: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
            <div className={`scoreBox ${scoreClass(data.overall_risk_score)}`}>
              {data.overall_risk_score}
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>Overall Drive Risk Score</div>
              <div className="muted">{data.total_files} files scanned</div>
            </div>
          </div>

          {data.risk_analysis?.length === 0 && (
            <div className="introBox"><p>✅ No sharing risks detected in your Drive.</p></div>
          )}

          <div className="grid">
            {data.risk_analysis?.map((risk, i) => (
              <div key={i} className="repoCard">
                <div className="repoTop">
                  <div>
                    <p className="repoName">{risk.rule}</p>
                    <div className="meta">{risk.detail}</div>
                  </div>
                  <div className={`scoreBox ${scoreClass(
                    risk.severity === "CRITICAL" ? 90 :
                    risk.severity === "HIGH" ? 70 :
                    risk.severity === "MEDIUM" ? 45 : 20
                  )}`}>
                    {risk.severity}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── SHARED COMPONENTS ────────────────────────────────────────────────────────

function RepoCard({ repo }) {
  const [open, setOpen] = useState(false);
  const score = repo.overall_risk_score ?? repo.risk_score ?? 0;
  const confidence = repo.confidence || "HEURISTIC";

  function copyReport() {
    navigator.clipboard.writeText(JSON.stringify(repo, null, 2));
  }

  function downloadReport() {
    const blob = new Blob([JSON.stringify(repo, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${repo.repository.replace("/", "_")}_shadowaccess_report.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="repoCard">
      <div className="repoTop">
        <div>
          <p className="repoName">{repo.repository}</p>
          <div className="meta">
            <span className={confidenceBadge(confidence)}>
              {confidence === "VERIFIED" ? "FULL VISIBILITY" : "LIMITED VISIBILITY"}
            </span>
          </div>
        </div>
        <div className={`scoreBox ${scoreClass(score)}`}>
          <div>{score}</div>
        </div>
      </div>

      {repo.note && <div className="meta" style={{ marginTop: 8 }}>{repo.note}</div>}

      <div className="row" style={{ marginTop: 10 }}>
        <button className="detailsBtn" onClick={() => setOpen((v) => !v)}>
          {open ? "Hide details" : "Show details"}
        </button>
        <button className="detailsBtn" onClick={copyReport}>Copy JSON</button>
        <button className="detailsBtn" onClick={downloadReport}>Download JSON</button>
      </div>

      {open && (
        <ul className="list">
          {(repo.risk_analysis || repo.top_risks || []).map((x, idx) => (
            <li key={idx}>
              <strong>{x.risk}</strong> (sev {x.severity}): {x.reason}
              {x.recommendation && <div className="meta">Fix: {x.recommendation}</div>}
            </li>
          ))}
          {(repo.risk_analysis || repo.top_risks || []).length === 0 && (
            <li>No risk factors returned.</li>
          )}
        </ul>
      )}
    </div>
  );
}

function ScoringModal({ onClose }) {
  return (
    <div className="modalBackdrop">
      <div className="modal">
        <h3>How ShadowAccess Scores Risk</h3>
        <p>ShadowAccess evaluates repository access risk using a <strong>0–100 normalized risk score</strong>.</p>
        <div className="scoreScale">
          <div><span className="dot low" /> 0–25 <strong> Low Risk</strong> — well-controlled access</div>
          <div><span className="dot med" /> 26–50 <strong> Moderate Risk</strong> — minor exposure</div>
          <div><span className="dot high" /> 51–75 <strong> High Risk</strong> — privilege or policy gaps</div>
          <div><span className="dot crit" /> 76–100 <strong> Critical Risk</strong> — urgent remediation needed</div>
        </div>
        <p style={{ marginTop: 12 }}>
          Scores combine <strong>verified GitHub data</strong> with <strong>heuristic estimation</strong> when visibility is restricted.
        </p>
        <ul>
          <li><strong>FULL VISIBILITY</strong>: All security signals accessible</li>
          <li><strong>LIMITED VISIBILITY</strong>: Risk score inferred from public metadata.</li>
        </ul>
        <p className="muted">This mirrors how real security tools behave under partial visibility.</p>
        <button className="btn" onClick={onClose}>Got it</button>
      </div>
    </div>
  );
}