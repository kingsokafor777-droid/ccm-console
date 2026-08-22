import type { ConsolePreview } from "@/lib/types";

export const preview: ConsolePreview = {
  synthetic: true,
  generated_at: "2026-08-22T00:00:00Z",
  assessments: [
    { assessment_id: "assessment_identity_mfa", control_id: "identity_mfa_coverage", status: "partial", coverage: "complete", severity: "high", assessed_at: "2026-08-21T00:00:00Z" },
    { assessment_id: "assessment_storage_encryption", control_id: "storage_encryption", status: "pass", coverage: "complete", severity: "medium", assessed_at: "2026-08-21T00:00:00Z" },
    { assessment_id: "assessment_logging_coverage", control_id: "logging_coverage", status: "not_assessed", coverage: "unavailable", severity: "low", assessed_at: "2026-08-21T00:00:00Z" }
  ],
  evidence: [
    { reference_id: "reference_identity_mfa", evidence_id: "evidence_identity_mfa", evidence_hash: "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", collector_id: "collector_aws_identity", control_id: "identity_mfa_coverage", observed_at: "2026-08-21T00:00:00Z", availability: "complete" },
    { reference_id: "reference_storage_encryption", evidence_id: "evidence_storage_encryption", evidence_hash: "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", collector_id: "collector_aws_storage", control_id: "storage_encryption", observed_at: "2026-08-21T00:00:00Z", availability: "complete" },
    { reference_id: "reference_logging_unavailable", evidence_id: "evidence_logging_unavailable", evidence_hash: "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc", collector_id: "collector_aws_logging", control_id: "logging_coverage", observed_at: "2026-08-21T00:00:00Z", availability: "unavailable" }
  ],
  cases: [
    { case_id: "case_identity_mfa", control_id: "identity_mfa_coverage", state: "active", severity: "high", owner_team: "cloud_security", due_at: "2026-08-30T00:00:00Z", version: 3 },
    { case_id: "case_logging_coverage", control_id: "logging_coverage", state: "pending_closure", severity: "medium", owner_team: "platform_operations", due_at: "2026-09-05T00:00:00Z", version: 2 }
  ]
};
