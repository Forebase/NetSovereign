-- NetEngine v0.4 durable local control plane (ordinary PostgreSQL 15+).
-- Each partition is explicit; JSONB is a representation, not the domain model.
BEGIN;
CREATE SCHEMA IF NOT EXISTS netengine_control;
CREATE TABLE IF NOT EXISTS netengine_control.schema_version(
  version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM netengine_control.schema_version WHERE version > 4) THEN
    RAISE EXCEPTION 'incompatible control-plane schema version';
  END IF;
END $$;
CREATE TABLE IF NOT EXISTS netengine_control.desired_revisions(
  revision_id text PRIMARY KEY, world_id text NOT NULL, parent_revision_id text,
  schema_version text NOT NULL, declaration_digest text NOT NULL,
  declaration jsonb NOT NULL, admission jsonb NOT NULL, accepted_at timestamptz NOT NULL,
  actor text, authority_manifest_digest text NOT NULL, boundary_policy_digest text,
  compatibility jsonb NOT NULL DEFAULT '{}', status text NOT NULL,
  FOREIGN KEY(parent_revision_id) REFERENCES netengine_control.desired_revisions(revision_id),
  UNIQUE(world_id,declaration_digest));
CREATE TABLE IF NOT EXISTS netengine_control.active_desired_revisions(
  world_id text PRIMARY KEY, revision_id text NOT NULL REFERENCES netengine_control.desired_revisions);
CREATE TABLE IF NOT EXISTS netengine_control.authoritative_records(
  record_id text PRIMARY KEY, world_id text NOT NULL, kind text NOT NULL, authority_id text NOT NULL,
  mandate_id text, desired_revision_id text NOT NULL REFERENCES netengine_control.desired_revisions,
  decision_reference text NOT NULL, status text NOT NULL, version integer NOT NULL CHECK(version>0),
  lifecycle jsonb NOT NULL, value jsonb NOT NULL, recorded_at timestamptz NOT NULL,
  UNIQUE(world_id,kind,record_id,version));
CREATE TABLE IF NOT EXISTS netengine_control.observations(
  observation_id text PRIMARY KEY, world_id text NOT NULL, resource_id text NOT NULL,
  provider_id text NOT NULL, binding_id text NOT NULL, capability text NOT NULL,
  provider_resource_id text, observation_type text NOT NULL, representation jsonb,
  digest text, health text NOT NULL, conformance text NOT NULL, observed_at timestamptz NOT NULL,
  stale_after timestamptz, execution_run_id text, operation_id text);
CREATE INDEX IF NOT EXISTS observations_latest ON netengine_control.observations(world_id,resource_id,observed_at DESC);
CREATE TABLE IF NOT EXISTS netengine_control.execution_plans(plan_id text PRIMARY KEY, fingerprint text NOT NULL UNIQUE, payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS netengine_control.execution_runs(run_id text PRIMARY KEY, plan_id text NOT NULL REFERENCES netengine_control.execution_plans, world_id text NOT NULL, current_state text NOT NULL, payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS netengine_control.operations(operation_id text PRIMARY KEY, run_id text NOT NULL REFERENCES netengine_control.execution_runs, world_id text NOT NULL, idempotency_key text NOT NULL, content_digest text NOT NULL, current_state text NOT NULL, payload jsonb NOT NULL, UNIQUE(world_id,idempotency_key));
CREATE TABLE IF NOT EXISTS netengine_control.attempts(attempt_id text PRIMARY KEY, operation_id text NOT NULL REFERENCES netengine_control.operations, number integer NOT NULL, payload jsonb NOT NULL, UNIQUE(operation_id,number));
CREATE TABLE IF NOT EXISTS netengine_control.transitions(transition_id text PRIMARY KEY, operation_id text NOT NULL REFERENCES netengine_control.operations, sequence integer NOT NULL, at timestamptz NOT NULL, payload jsonb NOT NULL, UNIQUE(operation_id,sequence));
CREATE TABLE IF NOT EXISTS netengine_control.evidence(evidence_id text PRIMARY KEY, run_id text NOT NULL REFERENCES netengine_control.execution_runs, operation_id text REFERENCES netengine_control.operations, created_at timestamptz NOT NULL, payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS netengine_control.checkpoints(checkpoint_id text PRIMARY KEY, run_id text NOT NULL REFERENCES netengine_control.execution_runs, world_id text NOT NULL, desired_revision_id text NOT NULL REFERENCES netengine_control.desired_revisions, previous_checkpoint_id text REFERENCES netengine_control.checkpoints, schema_version integer NOT NULL, plan_fingerprint text NOT NULL, created_at timestamptz NOT NULL, payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS netengine_control.leases(lock_key text PRIMARY KEY, owner text NOT NULL, acquired_at timestamptz NOT NULL, expires_at timestamptz NOT NULL, fencing_token bigint NOT NULL CHECK(fencing_token > 0), renewed_at timestamptz, released_at timestamptz, release_reason text, payload jsonb NOT NULL, CHECK(expires_at >= acquired_at));
CREATE TABLE IF NOT EXISTS netengine_control.reconciliations(reconciliation_id text PRIMARY KEY, world_id text NOT NULL, desired_revision_id text NOT NULL REFERENCES netengine_control.desired_revisions, trigger text NOT NULL, started_at timestamptz NOT NULL, completed_at timestamptz, result text NOT NULL, payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS netengine_control.drift(drift_id text PRIMARY KEY, reconciliation_id text REFERENCES netengine_control.reconciliations, world_id text NOT NULL, resource_id text NOT NULL, classification text NOT NULL, status text NOT NULL, first_detected_at timestamptz NOT NULL, last_detected_at timestamptz NOT NULL, payload jsonb NOT NULL);
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'observations_execution_run_fk' AND connamespace = 'netengine_control'::regnamespace) THEN
    ALTER TABLE netengine_control.observations ADD CONSTRAINT observations_execution_run_fk FOREIGN KEY(execution_run_id) REFERENCES netengine_control.execution_runs(run_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'observations_operation_fk' AND connamespace = 'netengine_control'::regnamespace) THEN
    ALTER TABLE netengine_control.observations ADD CONSTRAINT observations_operation_fk FOREIGN KEY(operation_id) REFERENCES netengine_control.operations(operation_id);
  END IF;
END $$;
INSERT INTO netengine_control.schema_version(version) VALUES(4) ON CONFLICT DO NOTHING;
COMMIT;
