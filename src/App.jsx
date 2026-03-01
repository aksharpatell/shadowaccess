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
  const [owner, setOwner] = useState("");
  const [loading, setLoading] = useState(false);
  const [progressText, setProgressText] = useState("");
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [showHelp, setShowHelp] = useState(false);

  const title = useMemo(() => {
    if (!data?.owner) return "ShadowAccess";
    return `ShadowAccess • ${data.owner}`;
  }, [data]);

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
      const res = await fetch(
        `${API_BASE}/org?owner=${encodeURIComponent(owner)}`
      );
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
    <div className="container">
      <div className="card">

        {/* HEADER */}
        <div className="header">
          <div className="brand">
            <img
              src="/github-logo.png"
              alt="GitHub"
              className="githubLogo"
            />
            <div>
            <div className="title">
            <span className="lockIcon">🔒</span> {title}
            </div>
              <div className="subtitle">
                GitHub access risk analysis with confidence-aware scoring
              </div>
            </div>
          </div>

          <button className="pill" onClick={() => setShowHelp(true)}>
            How scoring works
          </button>
        </div>

        {/* INTRO */}
        <div className="introBox">
          <p>
            <strong>ShadowAccess</strong> inspects GitHub repositories and
            organizations to surface access control risks such as excessive admin
            permissions, missing <code>CODEOWNERS</code>, and unprotected branches.
          </p>
          <p className="muted">
            When GitHub limits visibility, risk scores are estimated
            and clearly labeled to avoid false confidence.
          </p>
        </div>

        {/* CONTENT */}
        <div className="content">
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
        </div>
      </div>

      {/* FOOTER */}
      <footer className="footer">
        Built by <strong>Akshar Patel</strong> - Computer Science Student @ University of Illinois Urbana-Champaign
      </footer>

      {showHelp && <ScoringModal onClose={() => setShowHelp(false)} />}
    </div>
  );
}

function RepoCard({ repo }) {
  const [open, setOpen] = useState(false);

  const score = repo.overall_risk_score ?? repo.risk_score ?? 0;
  const confidence = repo.confidence || "HEURISTIC";
  
  function copyReport() {
    navigator.clipboard.writeText(JSON.stringify(repo, null, 2));
  }

  function downloadReport() {
    const blob = new Blob([JSON.stringify(repo, null, 2)], {
      type: "application/json",
    });

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
    {confidence === "VERIFIED"
      ? "FULL VISIBILITY"
      : "LIMITED VISIBILITY"}
  </span>
</div>
        </div>

        <div className={`scoreBox ${scoreClass(score)}`}>
          <div>{score}</div>
        </div>
      </div>

      {repo.note && (
        <div className="meta" style={{ marginTop: 8 }}>
          {repo.note}
        </div>
      )}

      <div className="row" style={{ marginTop: 10 }}>
        <button className="detailsBtn" onClick={() => setOpen((v) => !v)}>
          {open ? "Hide details" : "Show details"}
        </button>

        <button className="detailsBtn" onClick={copyReport}>
          Copy JSON
        </button>

        <button className="detailsBtn" onClick={downloadReport}>
          Download JSON
        </button>
      </div>

      {open && (
        <ul className="list">
          {(repo.risk_analysis || repo.top_risks || []).map((x, idx) => (
            <li key={idx}>
              <strong>{x.risk}</strong> (sev {x.severity}): {x.reason}
              {x.recommendation && (
                <div className="meta">Fix: {x.recommendation}</div>
              )}
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

        <p>
          ShadowAccess evaluates repository access risk using a{" "}
          <strong>0–100 normalized risk score</strong>.
        </p>

        <div className="scoreScale">
          <div><span className="dot low" /> 0–25 <strong> Low Risk</strong> — well-controlled access</div>
          <div><span className="dot med" /> 26–50 <strong> Moderate Risk</strong> — minor exposure</div>
          <div><span className="dot high" /> 51–75 <strong> High Risk</strong> — privilege or policy gaps</div>
          <div><span className="dot crit" /> 76–100 <strong> Critical Risk</strong> — urgent remediation needed</div>
        </div>

        <p style={{ marginTop: 12 }}>
          Scores combine <strong>verified GitHub data</strong> (permissions,
          branch protection, CODEOWNERS) with{" "}
          <strong>heuristic estimation</strong> when visibility is restricted.
        </p>

        <ul>
          <li><strong>FULL VISIBILITY</strong>: All security signals accessible</li>
          <li><strong>LIMITED VISIBILITY</strong>: GitHub restricted access. Risk score is inferred using public metadata.</li>
        </ul>

        <p className="muted">
          This mirrors how real security tools behave under partial visibility.
        </p>

        <button className="btn" onClick={onClose}>Got it</button>
      </div>
    </div>
  );
}

