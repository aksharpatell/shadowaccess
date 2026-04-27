import React, { useState } from "react";

const API_BASE = "https://shadowaccess-zrjr.onrender.com";

function scoreClass(s) {
  if (s <= 25) return "scoreLow";
  if (s <= 50) return "scoreMed";
  if (s <= 75) return "scoreHigh";
  return "scoreCrit";
}

function severityBadgeClass(sev) {
  if (sev === "CRITICAL") return "pill badgeCrit";
  if (sev === "HIGH") return "pill badgeHigh";
  if (sev === "MEDIUM") return "pill badgeMed";
  return "pill badgeLow";
}

// ─── LANDING PAGE ─────────────────────────────────────────────────────────────

function Landing({ onEnter }) {
  return (
    <div className="landing">
      <div className="landing-badge">🔒 Access Risk Analysis</div>
      <h1>Shadow Access</h1>
      <p className="landing-sub">
        Find who still has access to your GitHub repos and Google Drive files —
        before they shouldn't.
      </p>
      <div className="landing-cta">
        <button className="btn-primary" onClick={onEnter}>Start Scanning</button>
        <a href="https://github.com/aksharpatell/shadowaccess" target="_blank" rel="noreferrer">
          <button className="btn-ghost">View on GitHub</button>
        </a>
      </div>
      <div className="landing-features">
        <div className="feature-card">
          <div className="feature-icon">🐙</div>
          <div className="feature-title">GitHub Scanner</div>
          <div className="feature-desc">Flags excessive admin access, missing branch protection, and no CODEOWNERS.</div>
        </div>
        <div className="feature-card">
          <div className="feature-icon">📁</div>
          <div className="feature-title">Drive Scanner</div>
          <div className="feature-desc">Finds files shared publicly or with external users that haven't been touched in years.</div>
        </div>
        <div className="feature-card">
          <div className="feature-icon">📊</div>
          <div className="feature-title">Risk Scoring</div>
          <div className="feature-desc">0–100 risk score per repo and file with severity labels and fix recommendations.</div>
        </div>
      </div>
    </div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────

export default function App() {
  const [page, setPage] = useState("landing");
  const [tab, setTab] = useState("github");

  if (page === "landing") {
    return <Landing onEnter={() => setPage("app")} />;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-brand" onClick={() => setPage("landing")}>
          <img src={tab === "github" ? "/github-logo.png" : "/drive-logo.png"} alt="logo" />
          <span className="app-brand-name">ShadowAccess</span>
        </div>

        <div className="app-tabs">
          <button
            className={`app-tab ${tab === "github" ? "active" : ""}`}
            onClick={() => setTab("github")}
          >
            <img src="/github-logo.png" alt="GitHub" />
            GitHub
          </button>
          <button
            className={`app-tab ${tab === "drive" ? "active" : ""}`}
            onClick={() => setTab("drive")}
          >
            <img src="/drive-logo.png" alt="Drive" />
            Google Drive
          </button>
        </div>
      </header>

      <main className="app-content">
        {tab === "github" && <GitHubTab />}
        {tab === "drive" && <DriveTab />}
      </main>

      <footer className="footer">
        Built by <strong>Akshar Patel</strong> · CS @ University of Illinois Urbana-Champaign
      </footer>
    </div>
  );
}

// ─── GITHUB TAB ───────────────────────────────────────────────────────────────

function GitHubTab() {
  const [owner, setOwner] = useState("");
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState("");
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [showHelp, setShowHelp] = useState(false);

  const steps = ["Fetching repositories…", "Analyzing permissions…", "Checking branch protection…", "Evaluating CODEOWNERS…", "Scoring risk profile…"];

  async function scan() {
    setLoading(true); setErr(""); setData(null);
    let i = 0; setStep(steps[0]);
    const iv = setInterval(() => { i++; if (i < steps.length) setStep(steps[i]); }, 700);
    try {
      const res = await fetch(`${API_BASE}/org?owner=${encodeURIComponent(owner)}`);
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || "Request failed");
      setData(json);
    } catch (e) { setErr(String(e.message || e)); }
    finally { clearInterval(iv); setLoading(false); setStep(""); }
  }

  const avg = data?.repositories?.length
    ? Math.round(data.repositories.reduce((s, r) => s + r.overall_risk_score, 0) / data.repositories.length)
    : null;

  return (
    <>
      <div className="scan-box">
        <h2>GitHub Access Scanner</h2>
        <p>Enter any GitHub username or org to scan their repositories for access control risks.</p>
        <div className="scan-row">
          <input
            className="scan-input"
            value={owner}
            onChange={e => setOwner(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !loading && owner.trim() && scan()}
            placeholder="e.g. vercel, aksharpatell"
          />
          <button className="btn" onClick={scan} disabled={loading || !owner.trim()}>
            {loading ? "Scanning…" : "Scan"}
          </button>
          <button className="btn-secondary" onClick={() => setShowHelp(true)}>How it works</button>
        </div>
        {loading && (
          <>
            <div className="progress-bar"><div className="progress-fill" /></div>
            <div className="progress-text">{step}</div>
          </>
        )}
        {err && <div className="error">Error: {err}</div>}
      </div>

      {data?.repositories?.length > 0 && (
        <>
          <div className="score-summary">
            <div className={`score-big ${scoreClass(avg)}`}>{avg}</div>
            <div className="score-info">
              <h3>Average Risk Score</h3>
              <p>{data.repo_count} repositories scanned for <strong>{data.owner}</strong></p>
            </div>
          </div>

          <div className="results-header">
            <span className="results-title">Repositories</span>
            <span className="results-meta">sorted by highest risk</span>
          </div>

          <div className="grid">
            {data.repositories.map(r => <RepoCard key={r.repository} repo={r} />)}
          </div>
        </>
      )}

      {showHelp && <ScoringModal onClose={() => setShowHelp(false)} />}
    </>
  );
}

// ─── GOOGLE DRIVE TAB ─────────────────────────────────────────────────────────

function DriveTab() {
  const [authed, setAuthed] = useState(false);
  const [accessToken, setAccessToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  function connect() {
    fetch(`${API_BASE}/auth/google`)
      .then(r => r.json())
      .then(({ auth_url }) => {
        const popup = window.open(auth_url, "driveAuth", "width=500,height=600");
        window.addEventListener("message", function handler(e) {
          if (e.data?.type === "drive_authed") {
            setAccessToken(e.data.access_token);
            setAuthed(true);
            popup?.close();
            window.removeEventListener("message", handler);
          }
        });
      })
      .catch(() => setErr("Failed to start Google auth."));
  }

  async function scan() {
    setLoading(true); setErr(""); setData(null);
    try {
      const res = await fetch(`${API_BASE}/drive/scan`, { headers: { "X-Drive-Token": accessToken } });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.error || "Scan failed");
      setData(json);
    } catch (e) { setErr(String(e.message || e)); }
    finally { setLoading(false); }
  }

  // Group risks by file name
  function groupByFile(risks) {
    const map = {};
    for (const r of risks) {
      const match = r.detail.match(/^"([^"]+)"/);
      const name = match ? match[1] : "Unknown file";
      if (!map[name]) map[name] = [];
      map[name].push(r);
    }
    return Object.entries(map).sort((a, b) => {
      const weight = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
      const maxA = Math.max(...a[1].map(r => weight[r.severity] || 0));
      const maxB = Math.max(...b[1].map(r => weight[r.severity] || 0));
      return maxB - maxA;
    });
  }

  if (!authed) {
    return (
      <div className="drive-connect-box">
        <img src="/drive-logo.png" alt="Google Drive" />
        <h3>Connect Google Drive</h3>
        <p>ShadowAccess scans your files for risky sharing — public links, external users with edit access, and stale shares.</p>
        <button className="btn" onClick={connect}>Connect Google Drive</button>
        {err && <div className="error">{err}</div>}
      </div>
    );
  }

  const grouped = data ? groupByFile(data.risk_analysis || []) : [];

  return (
    <>
      <div className="scan-box">
        <h2>Google Drive Scanner</h2>
        <p>Scan your Drive for risky file sharing — public links, external editors, and forgotten shares.</p>
        <button className="btn" onClick={scan} disabled={loading}>
          {loading ? "Scanning…" : "Scan My Drive"}
        </button>
        {loading && (
          <>
            <div className="progress-bar"><div className="progress-fill" /></div>
            <div className="progress-text">Scanning your Drive files…</div>
          </>
        )}
        {err && <div className="error">Error: {err}</div>}
      </div>

      {data && (
        <>
          <div className="score-summary">
            <div className={`score-big ${scoreClass(data.overall_risk_score)}`}>{data.overall_risk_score}</div>
            <div className="score-info">
              <h3>Drive Risk Score</h3>
              <p>{data.total_files} files scanned · {data.risk_analysis?.length || 0} risks found across {grouped.length} files</p>
            </div>
          </div>

          {grouped.length === 0 ? (
            <div className="scan-box" style={{ textAlign: "center", color: "var(--muted)" }}>
              ✅ No sharing risks detected in your Drive.
            </div>
          ) : (
            <>
              <div className="results-header">
                <span className="results-title">Risky Files</span>
                <span className="results-meta">sorted by highest severity</span>
              </div>
              {grouped.map(([name, risks]) => (
  <DriveFileCard key={name} name={name} risks={risks} accessToken={accessToken} />
))}
            </>
          )}
        </>
      )}
    </>
  );
}

function DriveFileCard({ name, risks, accessToken, onFixed }) {
  const [open, setOpen] = useState(false);
  const [fixing, setFixing] = useState({});
  const [fixed, setFixed] = useState({});
  const hasCrit = risks.some(r => r.severity === "CRITICAL");
  const hasHigh = risks.some(r => r.severity === "HIGH");
  const topSev = hasCrit ? "CRITICAL" : hasHigh ? "HIGH" : risks[0]?.severity;
  const dotColor = { CRITICAL: "#f87171", HIGH: "#fb923c", MEDIUM: "#facc15", LOW: "#4ade80" };

  async function revokeAccess(risk) {
    setFixing(v => ({ ...v, [risk.rule + risk.file_id]: true }));
    try {
      const res = await fetch(`${API_BASE}/drive/revoke-access`, {
        method: "POST",
        headers: { "X-Drive-Token": accessToken, "Content-Type": "application/json" },
        body: JSON.stringify({ file_id: risk.file_id })
      });
      if (res.ok) setFixed(v => ({ ...v, [risk.rule + risk.file_id]: true }));
    } catch (e) { console.error(e); }
    finally { setFixing(v => ({ ...v, [risk.rule + risk.file_id]: false })); }
  }

  const canFix = (rule) => ["PUBLIC_LINK_ACCESS", "PUBLIC_WRITE_ACCESS"].includes(rule);
  const activeRisks = risks.filter(r => !fixed[r.rule + r.file_id]);

  if (activeRisks.length === 0) return null;

  return (
    <div className="drive-file-card">
      <div className="drive-file-header" onClick={() => setOpen(v => !v)}>
        <span className="drive-file-name" title={name}>📄 {name}</span>
        <div className="drive-file-badges">
          <span className={severityBadgeClass(topSev)}>{topSev}</span>
          <span className="pill" style={{ color: "var(--muted)" }}>{activeRisks.length} issue{activeRisks.length !== 1 ? "s" : ""}</span>
          <span style={{ color: "var(--muted)", fontSize: 12 }}>{open ? "▲" : "▼"}</span>
        </div>
      </div>
      {open && (
        <div className="drive-file-risks">
          {activeRisks.map((r, i) => (
            <div key={i} className="drive-risk-row" style={{ justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-start", flex: 1 }}>
                <div className="drive-risk-dot" style={{ background: dotColor[r.severity] || "#888", marginTop: 4 }} />
                <div className="drive-risk-text">
                  <strong style={{ color: "var(--text)" }}>{r.rule}</strong> — {r.detail.replace(/^"[^"]+" /, "")}
                  {r.link && (
                    <a href={r.link} target="_blank" rel="noreferrer"
                      style={{ marginLeft: 8, color: "var(--accent2)", fontSize: 11, fontWeight: 700 }}>
                      Open file →
                    </a>
                  )}
                </div>
              </div>
              {canFix(r.rule) && r.file_id && (
                <button
                  onClick={() => revokeAccess(r)}
                  disabled={fixing[r.rule + r.file_id]}
                  style={{
                    marginLeft: 12, padding: "5px 10px", borderRadius: 8,
                    border: "1px solid rgba(239,68,68,0.4)", background: "rgba(239,68,68,0.1)",
                    color: "#f87171", fontSize: 11, fontWeight: 700, cursor: "pointer",
                    whiteSpace: "nowrap", flexShrink: 0
                  }}
                >
                  {fixing[r.rule + r.file_id] ? "Fixing…" : "Revoke Access"}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── REPO CARD ────────────────────────────────────────────────────────────────

function RepoCard({ repo }) {
  const [open, setOpen] = useState(false);
  const score = repo.overall_risk_score ?? 0;
  const confidence = repo.confidence || "HEURISTIC";

  function download() {
    const blob = new Blob([JSON.stringify(repo, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${repo.repository.replace("/", "_")}_shadowaccess.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="repoCard">
      <div className="repoTop">
        <div style={{ flex: 1, minWidth: 0 }}>
          <p className="repoName">{repo.repository}</p>
          <div className="meta" style={{ marginTop: 6 }}>
            <span className={`pill ${confidence === "VERIFIED" ? "badgeVerified" : "badgeHeuristic"}`}>
              {confidence === "VERIFIED" ? "✓ Full Visibility" : "~ Limited Visibility"}
            </span>
          </div>
        </div>
        <div className={`scoreBox ${scoreClass(score)}`}>{score}</div>
      </div>

      {repo.note && <div className="meta" style={{ marginTop: 8 }}>{repo.note}</div>}

      <div className="row" style={{ marginTop: 12 }}>
        <button className="detailsBtn" onClick={() => setOpen(v => !v)}>
          {open ? "Hide" : "Details"}
        </button>
        <button className="detailsBtn" onClick={() => navigator.clipboard.writeText(JSON.stringify(repo, null, 2))}>
          Copy
        </button>
        <button className="detailsBtn" onClick={download}>Download</button>
      </div>

      {open && (
        <ul className="list">
          {(repo.risk_analysis || repo.top_risks || []).map((x, i) => (
            <li key={i}>
              <strong>{x.risk}</strong> ({x.severity}): {x.reason}
              {x.recommendation && <div className="meta">Fix: {x.recommendation}</div>}
            </li>
          ))}
          {(repo.risk_analysis || repo.top_risks || []).length === 0 && <li>No risk factors returned.</li>}
        </ul>
      )}
    </div>
  );
}

// ─── SCORING MODAL ────────────────────────────────────────────────────────────

function ScoringModal({ onClose }) {
  return (
    <div className="modalBackdrop">
      <div className="modal">
        <h3>How ShadowAccess Scores Risk</h3>
        <p style={{ fontSize: 13, color: "var(--muted)", margin: "8px 0 14px" }}>
          Each repo gets a 0–100 risk score based on permission data, branch protection, and CODEOWNERS.
        </p>
        <div className="scoreScale">
          <div><span className="dot low" /> 0–25 <strong>Low</strong> — well-controlled</div>
          <div><span className="dot med" /> 26–50 <strong>Moderate</strong> — minor exposure</div>
          <div><span className="dot high" /> 51–75 <strong>High</strong> — privilege gaps</div>
          <div><span className="dot crit" /> 76–100 <strong>Critical</strong> — urgent action needed</div>
        </div>
        <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 14 }}>
          <strong style={{ color: "var(--text)" }}>✓ Full Visibility</strong> — verified GitHub data used.<br />
          <strong style={{ color: "var(--text)" }}>~ Limited Visibility</strong> — estimated from public metadata.
        </p>
        <button className="btn" style={{ marginTop: 18 }} onClick={onClose}>Got it</button>
      </div>
    </div>
  );
}