# MySQL Schema Audit

Audit date: 2026-07-02

## Scope

This audit reviews the PQ-AI database model, generated MySQL DDL, runtime database behavior, and documentation against the company MySQL standards.

## Completed Corrections

- Removed SQLAlchemy physical foreign-key declarations from the domain model.
- Added `logical_fk` metadata for application-enforced references.
- Added application reference checks for legacy direct delete helpers so reference protection no longer depends on database constraints.
- Rejected HTTP `DELETE` requests through middleware.
- Added a MySQL runtime statement guard for destructive/schema-changing statements: `DELETE`, `CREATE`, `DROP`, `ALTER`, `TRUNCATE`, and `REPLACE`.
- Removed product-code physical delete calls from API routes and removed frontend DELETE proxy/call paths. Existing delete routes now validate existence and return 405 through the shared delete policy.
- Reworked update/import paths that used delete-and-reinsert semantics:
  - Program version vehicle/color binding updates now insert missing bindings without deleting existing bindings.
  - Quality measurement metric updates now upsert by `metric_code`.
  - Measurement repeat readings now upsert by `repeat_no + metric_code`.
  - Robot path execution rows now upsert by `device_execution_id + path_segment_id`.
- Renamed long material governance table names:
  - `material_characteristic_definition` -> `mat_char_definition`
  - `material_characteristic_applicability` -> `mat_char_applicability`
- Renamed ORM index and unique-constraint names to company prefixes and 32-character limits.
- Generated [sql/pq_ai_mysql_schema.sql](sql/pq_ai_mysql_schema.sql) as a DBA review script with no physical foreign keys.

## Static Checks Passed

- Tables: 74.
- Logical references: 123.
- Physical foreign keys in SQLAlchemy metadata: 0.
- Table names, field names, model index names, and model unique names are within 32 characters.
- Single-table field counts are within the 50-column limit.
- Single-table index counts are within the 5-index limit.
- Generated DDL does not contain physical foreign-key constraints.
- Generated DDL does not use `TINYINT`, `FLOAT`, `DOUBLE`, `TEXT`, `BLOB`, or `ENUM`.
- Generated DDL maps boolean flags to `INT UNSIGNED`.
- Generated DDL maps floating values to `DECIMAL(18,6)`.
- Generated DDL maps legacy text model fields to bounded `VARCHAR(2000)`.

## Known Compatibility Decisions

- The DDL uses `CREATE TABLE` because it is a DBA work-order artifact. It must not be executed by application code, Docker, CI, seed scripts, or tests against MySQL.
- Current application primary keys remain `VARCHAR(36)` UUIDs. The company-preferred unsigned auto-increment surrogate key model requires a broader approved migration across API payloads, seed data, UI state, logical references, and existing data.
- Some fields remain nullable where absence is semantically meaningful, such as optional instrument, calibration, reference, raw file URI, material batch, and approval timestamps. Production hardening should replace avoidable nulls with explicit status/default fields.
- JSON remains in controlled lineage and feature/evidence fields. It is allowed only for structured metadata and must not store images, binary files, or uncontrolled large documents.
- Existing delete route declarations remain only to return a controlled 405 response for old clients. They should be replaced with explicit disable/archive/status/version endpoints in the next product refactor.
- Application-authored `SET` statements are forbidden by rules and code review. The runtime SQL guard does not block driver-level `SET` statements to avoid breaking MySQL client initialization.

## Required Next Refactors

1. Replace all remaining 405 delete route declarations with explicit disable/archive/status/version endpoints.
2. Add `create_user` and `update_user` fields where user-level mutation provenance is required, or document why audit-log-only provenance is sufficient.
3. Review nullable fields and introduce explicit status/default fields where the company DBA requires strict `NOT NULL`.
4. Plan a separate approved migration from UUID primary keys to unsigned surrogate primary keys if mandated for production.
5. Add query-level review for production list/search endpoints:
   - no leading wildcard search,
   - no negative predicates,
   - no frontend `count(*)` display dependency on hot paths,
   - page sizes below 500 rows,
   - explicit projection for multi-table queries.
6. Add EXPLAIN evidence for high-frequency dashboard, list, and AI feature queries before production rollout.

## DBA Review Artifacts

- Company standards: [mysql-company-standards.md](mysql-company-standards.md)
- Change control: [database-change-control.md](database-change-control.md)
- Full generated DDL: [sql/pq_ai_mysql_schema.sql](sql/pq_ai_mysql_schema.sql)
