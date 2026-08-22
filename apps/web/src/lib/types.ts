export type Severity = "critical" | "high" | "medium" | "low" | "informational";
export type Coverage = "complete" | "partial" | "unavailable" | "error";

export type Assessment = {
  assessment_id: string;
  control_id: string;
  status: "pass" | "fail" | "partial" | "not_assessed" | "error";
  coverage: Coverage;
  severity: Severity;
  assessed_at: string;
};

export type Evidence = {
  reference_id: string;
  evidence_id: string;
  evidence_hash: string;
  collector_id: string;
  control_id: string;
  observed_at: string;
  availability: Coverage;
};

export type Case = {
  case_id: string;
  control_id: string;
  state: "active" | "pending_closure" | "closed" | "rejected";
  severity: Severity;
  owner_team: string;
  due_at: string | null;
  version: number;
};

export type ConsolePreview = {
  synthetic: true;
  generated_at: string;
  assessments: Assessment[];
  evidence: Evidence[];
  cases: Case[];
};
