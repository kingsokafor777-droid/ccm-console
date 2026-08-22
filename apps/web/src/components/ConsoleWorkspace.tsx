"use client";

import { useMemo, useState } from "react";
import type { ConsolePreview, Severity } from "@/lib/types";

type Tab = "overview" | "evidence" | "casework";

function Badge({ value }: { value: string }) {
  return <span className={`badge ${value}`}>{value.replaceAll("_", " ")}</span>;
}

export function ConsoleWorkspace({ preview }: { preview: ConsolePreview }) {
  const [tab, setTab] = useState<Tab>("overview");
  const metrics = useMemo(() => overviewMetrics(preview), [preview]);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">CCM / CONSOLE</span>
          <h1>Evidence Operations</h1>
          <p>Executive visibility over supplied technical records and coordination state.</p>
        </div>
        <nav className="nav" aria-label="Console sections">
          {(["overview", "evidence", "casework"] as Tab[]).map((item) => (
            <button key={item} type="button" aria-current={tab === item ? "page" : undefined} onClick={() => setTab(item)}>
              {item === "casework" ? "Remediation workbench" : item === "evidence" ? "Evidence explorer" : "Executive overview"}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          Preview data is synthetic and payload-blind. A production console requires tenant-scoped API authentication and a controlled PostgreSQL deployment.
        </div>
      </aside>
      <main className="main">
        <div className="preview-banner"><span>SYNTHETIC LOCAL PREVIEW</span><span>NO LIVE CLOUD / NO RAW EVIDENCE</span></div>
        <header className="header">
          <div>
            <div className="eyebrow">Continuous control monitoring</div>
            <h2>{tab === "overview" ? "Decision-ready technical posture" : tab === "evidence" ? "Evidence reference inventory" : "Remediation coordination"}</h2>
            <p>Rendered from deterministic synthetic records. Missing or unavailable sources remain explicit coverage states; no view infers a pass, approval, or compliance result.</p>
          </div>
          <div className="scope-note">The workbench records coordination only. Exception decisions, risk acceptance, and closure verification remain separate casework controls.</div>
        </header>
        {tab === "overview" && <Overview preview={preview} metrics={metrics} />}
        {tab === "evidence" && <EvidenceExplorer preview={preview} />}
        {tab === "casework" && <Casework preview={preview} />}
      </main>
    </div>
  );
}

function Overview({ preview, metrics }: { preview: ConsolePreview; metrics: ReturnType<typeof overviewMetrics> }) {
  return <>
    <section className="metrics" aria-label="Synthetic posture metrics">
      <Metric label="Assessments" value={String(preview.assessments.length)} detail="supplied technical records" />
      <Metric label="Open cases" value={String(metrics.openCases.length)} detail={metrics.highest ? `highest: ${metrics.highest}` : "none active"} />
      <Metric label="Failing assessments" value={String(metrics.failing)} detail="not an enterprise risk rating" />
      <Metric label="Unavailable evidence" value={String(metrics.unavailable)} detail="explicit coverage gap" />
    </section>
    <section className="panel">
      <div className="panel-head"><h3>Assessment status</h3><span>assessment source time: 2026-08-21</span></div>
      <div className="table-wrap"><table><thead><tr><th>Control</th><th>Assessment</th><th>Coverage</th><th>Severity</th><th>Source time</th></tr></thead><tbody>{preview.assessments.map((item) => <tr key={item.assessment_id}><td><strong>{item.control_id}</strong><small>{item.assessment_id}</small></td><td><Badge value={item.status} /></td><td><Badge value={item.coverage} /></td><td><Badge value={item.severity} /></td><td className="trace">{item.assessed_at}</td></tr>)}</tbody></table></div>
    </section>
    <div className="empty-signal">{metrics.partial} partial-coverage assessment(s) and {metrics.unavailable} unavailable evidence reference(s) are shown as unresolved technical visibility, not positive evidence.</div>
  </>;
}

function overviewMetrics(preview: ConsolePreview) {
  const openCases = preview.cases.filter((item) => item.state === "active" || item.state === "pending_closure");
  const failing = preview.assessments.filter((item) => item.status === "fail").length;
  const partial = preview.assessments.filter((item) => item.coverage === "partial").length;
  const unavailable = preview.evidence.filter((item) => item.availability === "unavailable").length;
  const rank: Record<Severity, number> = { critical: 4, high: 3, medium: 2, low: 1, informational: 0 };
  const highest = [...openCases].sort((left, right) => rank[right.severity] - rank[left.severity])[0]?.severity;
  return { openCases, failing, partial, unavailable, highest };
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <article className="metric"><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></article>;
}

function EvidenceExplorer({ preview }: { preview: ConsolePreview }) {
  return <section className="panel"><div className="panel-head"><h3>Payload-blind evidence references</h3><span>hashes, provenance, availability only</span></div><div className="table-wrap"><table><thead><tr><th>Reference</th><th>Control</th><th>Collector</th><th>Availability</th><th>Integrity hash</th></tr></thead><tbody>{preview.evidence.map((item) => <tr key={item.reference_id}><td><strong>{item.reference_id}</strong><small>{item.evidence_id}</small></td><td>{item.control_id}</td><td>{item.collector_id}</td><td><Badge value={item.availability} /></td><td className="trace">{item.evidence_hash}</td></tr>)}</tbody></table></div><div className="empty-signal">The console shows no evidence payload, attachment, cloud credential, screenshot, or source-system content.</div></section>;
}

function Casework({ preview }: { preview: ConsolePreview }) {
  return <div className="case-layout"><section className="panel"><div className="panel-head"><h3>Owned remediation coordination</h3><span>optimistic versioning at API boundary</span></div><div className="table-wrap"><table><thead><tr><th>Case</th><th>State</th><th>Severity</th><th>Owner</th><th>Due</th></tr></thead><tbody>{preview.cases.map((item) => <tr key={item.case_id}><td><strong>{item.control_id}</strong><small>{item.case_id} · v{item.version}</small></td><td><Badge value={item.state} /></td><td><Badge value={item.severity} /></td><td>{item.owner_team}</td><td className="trace">{item.due_at ?? "not supplied"}</td></tr>)}</tbody></table></div></section><aside className="callout"><strong>Workstation boundary</strong><br />An authenticated operator can add a bounded coordination update, while a reviewer can reassign the coordination owner. Neither action executes remediation, approves an exception, accepts risk, or verifies closure.<br /><br /><span className="trace">API contract: POST /v1/cases/:id/updates · PATCH /v1/cases/:id/owner</span></aside></div>;
}
