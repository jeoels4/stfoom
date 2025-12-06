SyncService behavior and guarantees

Purpose
-------
This document describes the runtime guarantees and operator-facing behaviors of the SyncService (row-level smart sync).

Key guarantees
--------------
- Non-blocking: SyncService treats schema mismatches and common integrity constraint violations as non-fatal. If a pending change cannot be applied due to missing columns or IntegrityErrors (NOT NULL, UNIQUE, CHECK, FOREIGN KEY), SyncService will skip that change and continue processing the queue. This preserves availability and prevents the sync queue from stalling.

- Audit/Visibility: Skipped or failed changes are recorded in the `sync_errors` table inside the `sync_tracking.db`. Operators can inspect this table to see what was skipped (`table_name`, `record_id`, `error`, `timestamp`). This is intentionally conservative: data is not silently lost — it is skipped and logged.

- Idempotent provisioning: At startup, the `schema_provision.ensure_schema_ready()` function creates minimal skeleton tables and `created_at`/`updated_at` columns for tables listed in `SyncService.table_pk_map`. It also attempts to create simple triggers to set timestamps. This reduces first-run failures on fresh installs.

- Best-effort sanitization: Before applying changes to the server, SyncService removes keys that don't exist in the server schema (sanitization). If sanitization leaves an operation with no valid columns for insert/update, SyncService marks the change as synced (no-op) to avoid unnecessary failures.

Operational notes
-----------------
- When a change is skipped due to a constraint, the original change remains in `sync_changes` as unsynced unless it is explicitly marked synced by the code path. The `sync_errors` table contains a record of the skip so operators can re-apply changes after schema migrations.

- Typical maintenance workflow:
  1. Run schema migrations on the server to bring schemas in line with local schema.
  2. Query `sync_errors` for skipped changes and re-queue or investigate as needed.
  3. Re-run `sync_to_server()` to transfer skipped changes after migrations are applied.

- Logging: SyncService prints concise messages to stdout/stderr for operations and skipped items. Consider redirecting or capturing stdout in production if you need persistent logging.

Limitations & Risks
-------------------
- Data may remain unsynced until operators take action after schema migrations. The design prefers availability over perfect immediate consistency.

- The provisioner creates minimal skeleton tables only (primary key + timestamps). It does not attempt to guess full column types or defaults. For production-ready table creation, explicit migration scripts are required.

Files of interest
-----------------
- `app/stfoom/services/sync_service.py` — main sync implementation.
- `app/stfoom/services/schema_provision.py` — idempotent schema helper called at startup.
- `data/sync_tracking.db` — sync tracking DB (contains `sync_changes`, `sync_status`, `sync_metadata`, `sync_errors`).

Contact
-------
If you need stricter behavior (e.g., halt sync on constraint errors, automatic retries, or auto-migrations), we can implement those features — they require operational decisions about data integrity vs availability.