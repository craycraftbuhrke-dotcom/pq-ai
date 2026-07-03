# MySQL Database Change Control

PQ-AI uses MySQL as the only approved persistent database. Application code, Docker entrypoints, local scripts, and CI jobs must not create, migrate, alter, or drop MySQL schema objects automatically.

The screenshots referenced in the request were not readable from the current workspace path. This document records the mandatory database-operation rules explicitly provided in text. Any additional screenshot-only MySQL standards must be uploaded into the repository or pasted into an issue before they can be transcribed here.

## Mandatory Rules

- Alembic is not used in this project.
- Runtime code must not call `Base.metadata.create_all`, `drop_all`, Alembic commands, or any equivalent automatic schema mutation against MySQL.
- Docker startup, local startup, tests, and seed scripts must not execute DDL against MySQL.
- Every database-structure change requires a human approval ticket and manual execution by the database owner or approved DBA.
- Schema changes include `CREATE DATABASE`, `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`, `CREATE/DROP INDEX`, constraints, foreign keys, views, triggers, stored procedures, partitions, character set/collation changes, and any operation that changes table or column definitions.
- Data seed or demo-data loading may run only after the approved schema already exists. Seed scripts must be idempotent and must not hide missing schema by creating tables.
- Tests may create transient SQLite in-memory schemas only through `tests.schema_guard.create_transient_test_schema`; this exception is for isolated unit tests and must never target MySQL.

## Required Approval Package

Each database-structure change must have a ticket containing:

- Business reason and affected module.
- Exact MySQL version and target database/schema.
- Forward SQL script.
- Rollback SQL script or explicit rollback limitation.
- Data-loss and lock-risk assessment.
- Estimated table size and expected execution time.
- Backup/snapshot confirmation.
- Maintenance window or online-change plan.
- Reviewer approvals from application owner and database owner.
- Post-execution verification SQL.
- Execution record with operator, timestamp, environment, and result.

## Project Workflow

1. Update SQLAlchemy models and application code only after the database change request is approved for development.
2. Put proposed SQL in the approval ticket or a reviewed document, not in an auto-running migration folder.
3. Execute SQL manually in the target MySQL environment after approval.
4. Run API smoke tests and browser verification after the DBA confirms execution.
5. Record the executed ticket ID in release notes or project documentation.

## Local Development

Local scripts assume the `pq_ai` database and required tables already exist. They may:

- Check connectivity.
- Load or refresh idempotent demo data.
- Start the API and frontend.

They must not:

- Create the database.
- Create or alter tables.
- Apply migration frameworks.
- Drop or truncate schema objects.
