-- ccm-console v0.1.0: payload-blind, tenant-scoped read/workbench model.
-- Apply only through a reviewed PostgreSQL migration process with a least-privilege role.

BEGIN;

CREATE TABLE ccm_console_tenants (
  tenant_id text PRIMARY KEY CHECK (tenant_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  created_at timestamptz NOT NULL
);

CREATE TABLE ccm_assessment_views (
  tenant_id text NOT NULL REFERENCES ccm_console_tenants(tenant_id),
  assessment_id text NOT NULL CHECK (assessment_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  control_id text NOT NULL CHECK (control_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  control_version text NOT NULL CHECK (length(control_version) BETWEEN 1 AND 512),
  status text NOT NULL CHECK (status IN ('pass', 'fail', 'partial', 'not_assessed', 'error')),
  coverage text NOT NULL CHECK (coverage IN ('complete', 'partial', 'unavailable', 'error')),
  severity text NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'informational')),
  source_manifest_hash text NOT NULL CHECK (source_manifest_hash ~ '^sha256:[0-9a-f]{64}$'),
  assessed_at timestamptz NOT NULL,
  PRIMARY KEY (tenant_id, assessment_id)
);

CREATE TABLE ccm_evidence_reference_views (
  tenant_id text NOT NULL REFERENCES ccm_console_tenants(tenant_id),
  reference_id text NOT NULL CHECK (reference_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  evidence_id text NOT NULL CHECK (evidence_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  evidence_hash text NOT NULL CHECK (evidence_hash ~ '^sha256:[0-9a-f]{64}$'),
  collector_id text NOT NULL CHECK (collector_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  control_id text NOT NULL CHECK (control_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  observed_at timestamptz NOT NULL,
  availability text NOT NULL CHECK (availability IN ('complete', 'partial', 'unavailable', 'error')),
  source_manifest_hash text NOT NULL CHECK (source_manifest_hash ~ '^sha256:[0-9a-f]{64}$'),
  PRIMARY KEY (tenant_id, reference_id)
);

CREATE TABLE ccm_casework_views (
  tenant_id text NOT NULL REFERENCES ccm_console_tenants(tenant_id),
  case_id text NOT NULL CHECK (case_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  control_id text NOT NULL CHECK (control_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  control_version text NOT NULL CHECK (length(control_version) BETWEEN 1 AND 512),
  state text NOT NULL CHECK (state IN ('active', 'pending_closure', 'closed', 'rejected')),
  severity text NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'informational')),
  owner_team text NOT NULL CHECK (length(owner_team) BETWEEN 1 AND 512),
  owner_subject_id text NULL CHECK (owner_subject_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  due_at timestamptz NULL,
  source_case_manifest_hash text NOT NULL CHECK (source_case_manifest_hash ~ '^sha256:[0-9a-f]{64}$'),
  version integer NOT NULL CHECK (version >= 1),
  PRIMARY KEY (tenant_id, case_id)
);

CREATE TABLE ccm_console_work_updates (
  tenant_id text NOT NULL,
  update_id text NOT NULL CHECK (update_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  case_id text NOT NULL,
  actor_subject_id text NOT NULL CHECK (actor_subject_id ~ '^[a-z][a-z0-9_]{1,63}$'),
  message text NOT NULL CHECK (length(message) BETWEEN 1 AND 1000),
  created_at timestamptz NOT NULL,
  case_version integer NOT NULL CHECK (case_version >= 1),
  PRIMARY KEY (tenant_id, update_id),
  FOREIGN KEY (tenant_id, case_id) REFERENCES ccm_casework_views(tenant_id, case_id)
);

CREATE INDEX ccm_assessment_views_tenant_assessment_idx ON ccm_assessment_views (tenant_id, assessment_id);
CREATE INDEX ccm_evidence_reference_views_tenant_reference_idx ON ccm_evidence_reference_views (tenant_id, reference_id);
CREATE INDEX ccm_casework_views_tenant_case_idx ON ccm_casework_views (tenant_id, case_id);

CREATE FUNCTION ccm_console_reject_work_update_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'ccm_console_work_updates are append-only';
END;
$$;

CREATE TRIGGER ccm_console_work_updates_immutable
  BEFORE UPDATE OR DELETE ON ccm_console_work_updates
  FOR EACH ROW EXECUTE FUNCTION ccm_console_reject_work_update_mutation();

ALTER TABLE ccm_assessment_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE ccm_evidence_reference_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE ccm_casework_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE ccm_console_work_updates ENABLE ROW LEVEL SECURITY;
ALTER TABLE ccm_assessment_views FORCE ROW LEVEL SECURITY;
ALTER TABLE ccm_evidence_reference_views FORCE ROW LEVEL SECURITY;
ALTER TABLE ccm_casework_views FORCE ROW LEVEL SECURITY;
ALTER TABLE ccm_console_work_updates FORCE ROW LEVEL SECURITY;

CREATE POLICY ccm_assessment_views_tenant_policy ON ccm_assessment_views
  USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY ccm_evidence_reference_views_tenant_policy ON ccm_evidence_reference_views
  USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY ccm_casework_views_tenant_policy ON ccm_casework_views
  USING (tenant_id = current_setting('app.tenant_id', true));
CREATE POLICY ccm_console_work_updates_tenant_policy ON ccm_console_work_updates
  USING (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
