# MySQL Company Standards For PQ-AI

This document transcribes the company MySQL rules supplied in the June 2026 screenshots and applies them to PQ-AI.

## Project Enforcement

- MySQL is the only approved persistent database for PQ-AI.
- Application code, Docker entrypoints, local scripts, CI, tests against MySQL, and seed jobs must not execute database structure changes.
- Alembic is not used. Migration folders, migration commands, and automatic SQLAlchemy schema creation are forbidden for MySQL.
- Runtime SQL issued by the application must not use physical `DELETE`, `CREATE`, `DROP`, `ALTER`, `TRUNCATE`, `REPLACE`, or application-authored `SET` statements.
- The generated schema file [pq_ai_mysql_schema.sql](sql/pq_ai_mysql_schema.sql) is DBA approval material only. It must be executed manually through an approved database work order, not by application code.
- The company database does not support physical foreign keys for this project. References are stored as `*_id` columns and enforced in application logic through `logical_fk` metadata, existence checks, and reference checks.
- Frontend and API deletion flows must use disable/archive/status/version workflows. HTTP `DELETE` requests are rejected by middleware.

## Naming Rules

- Database, table, field, and index names use lowercase letters and underscores.
- Names should be meaningful, tied to the business domain, and not exceed 32 characters in this project.
- Do not use MySQL reserved words as database, table, or field names.
- Names must not start with `test`.
- Temporary tables, when approved by DBA workflow, use `tmp_` prefix and a date suffix, for example `tmp_table_20140401`.
- Stored procedures, triggers, views, UDF, and events are forbidden.
- Unique indexes use `uk_field[_field]`; non-unique indexes use `idx_field[_field]`.
- Business access account names follow the company convention: business write/read accounts use `business_wn` and `business_rn`; cross-business accounts use `accessgroup_business_w` and `accessgroup_business_r`.

## Database And Table Rules

- Default storage engine is InnoDB.
- Default character set is UTF-8. PQ-AI uses `utf8mb4` to support Chinese and symbol data safely.
- Charset changes must consider all related queries to avoid implicit conversion.
- A single schema must not exceed 500 tables.
- A single table must not exceed 50 fields.
- Tables and fields must have comments, except primary-key comments are optional.
- Do not store images, documents, or other large binary files in MySQL; store URIs and metadata instead.
- Tables with many string fields should stay below 30 million rows. Tables with mostly integer fields should stay below 50 million rows.
- Do not debug directly against production data. Data testing requires the special company application process.
- Use hot/cold separation, tiered storage, and historical archiving when volume grows.
- Cross-database queries are forbidden.
- Frontend business logic must not depend on partition tables.
- Split frequently used key fields from large or low-frequency fields where needed.
- Sharding or archive table suffixes must use numeric/date suffixes according to company format and DBA approval.

## Field Design Rules

- New business tables should include at least primary key, create time, create user, update time, and update user fields when the module owns user-level mutation history.
- Use `UNSIGNED` for non-negative numeric values where the type supports it.
- Use `INT UNSIGNED` for IPv4 storage when storing IPs numerically.
- Use `DECIMAL` instead of `FLOAT` or `DOUBLE` for precise values.
- Prefer appropriately small integer and varchar types. `VARCHAR(N)` is character count, not byte count.
- Do not use `TINYINT` in approved MySQL DDL. Boolean flags in the generated schema use `INT UNSIGNED`.
- Do not use `ENUM`.
- Do not use `TEXT` or `BLOB`; use bounded `VARCHAR` or split large payloads from hot tables. PQ-AI DDL maps legacy `Text` model fields to bounded `VARCHAR(2000)`.
- Use `VARBINARY` for case-sensitive variable binary/string content when needed.
- Use `DATE` for dates, `YEAR` for years, and `TIMESTAMP` for second-level timestamps.
- Prefer `NOT NULL` with explicit defaults. Existing nullable domain facts remain nullable only where absence has real business meaning and require review before production hardening.
- Avoid large CPU computations in SQL.

## Index Rules

- Every table must have a primary key.
- Preferred primary key is a non-business unsigned auto-increment key. PQ-AI currently keeps UUID string primary keys for application compatibility; converting to unsigned surrogate keys is a planned schema refactor requiring full API/seed/frontend migration.
- Physical foreign keys are forbidden. Enforce references in application logic.
- Each table should have no more than 5 indexes, and each index should have no more than 5 fields.
- Do not create duplicate or redundant indexes.
- Do not index nullable columns unless specifically approved with query evidence.
- Composite index order matters; high-cardinality columns should come first.
- Do not index low-cardinality fields such as gender-like flags.
- For long strings, use prefix indexes no longer than 8 characters or add a CRC32/MD5 helper column after DBA approval.
- Use covering indexes where they reduce IO and sorting.
- Remove redundant indexes after optimization.
- High-update tables must keep index count especially low.
- Batch updates should be split into small units because index maintenance is expensive.

## B-Tree Index Usage Rules

- Composite B-tree indexes are usable for full-key, range, and left-prefix lookups.
- A composite index `(a, b, c)` can fully serve predicates like `a = ? and b = ? and c = ?` or `a = ? and b = ? and c > ?`.
- The same index can serve left-prefix predicates like `a = ?` and prefix `LIKE 'abc%'`.
- If a middle column is skipped, only the leading prefix can be used.
- If a leading indexed column uses a range condition, following columns cannot be fully used.
- Join columns must have matching types and charsets, and the joined field should be the first indexed column.
- Indexes are not usable when the predicate does not start from the first index column, wraps the indexed column in a function, compares mismatched types, uses mismatched join charsets, uses leading wildcard `LIKE`, uses negative predicates, or uses broad `OR` patterns.

## SQL Design Rules

- Use prepared statements; never build SQL by string concatenation.
- Use `IN` instead of long `OR` chains, but keep `IN` values below 500.
- Avoid implicit type conversion. Numeric values must not be quoted; string values must be quoted.
- Avoid joins and subqueries. Do not exceed 3 joined tables. If unavoidable, prefer a clear join over a subquery.
- Do not apply arithmetic or functions to indexed columns in predicates.
- Reduce database round trips through controlled batching. Batch inserts must name columns explicitly and keep batch size reasonable.
- Split complex SQL into smaller statements and avoid large transactions.
- Fetch large result sets in pages; each page should stay below 500 rows and result sets below 1 MB.
- Use `UNION ALL` instead of `UNION`.
- Do not use frontend `count(*)` for business display paths; use cached/statistical tables or dedicated read/statistics paths.
- Never use `select *` in multi-table association queries.
- Avoid non-deterministic SQL functions such as `rand()`, `sysdate()`, and `current_user()` in business queries.
- `INSERT` statements must explicitly list fields.
- `INSERT INTO B SELECT * FROM A` is forbidden.
- A single SQL statement must not update multiple tables.
- Pagination must be designed for index usage.
- Application code must catch SQL exceptions and rollback explicitly when needed.
- Application code must not change transaction isolation.
- Important `WHERE`, `ORDER BY`, `GROUP BY`, `DISTINCT`, and join fields must be indexed when used in production paths.
- Use `GROUP BY a ORDER BY NULL` when sorting is not required.
- Leading wildcard search such as `LIKE '%abc'` is forbidden.
- Negative predicates such as `NOT IN`, `!=`, `NOT LIKE`, and `<>` are forbidden in production SQL.
- Do not check nullable columns in `WHERE`; use explicit status/default fields where possible.
- Use `EXPLAIN` to verify index usage and avoid `Using filesort` and `Using temporary`.
- Do not use SQL variables as field names in DML.
- Approved update statements must use indexed `WHERE` columns and must not rely on `LIMIT`.
- Be especially careful when generating SQL predicates; never allow conditions that can turn into always-true predicates.
- DML must not contain destructive full-data operations.
- DDL field additions must not use `AFTER`.
- `REPLACE INTO` is forbidden; use explicit query-plus-insert or `ON DUPLICATE KEY UPDATE` when approved.
- Avoid `SELECT DISTINCT a ... ORDER BY b LIMIT m,n` patterns.

## PQ-AI Schema Notes

- Current approved schema material is [docs/sql/pq_ai_mysql_schema.sql](sql/pq_ai_mysql_schema.sql).
- It contains 90 domain tables, no physical foreign keys, no unsupported numeric/string storage types, and 156 documented logical references.
- It uses `VARCHAR(36)` UUID primary keys for current application compatibility. Moving to unsigned auto-increment surrogate keys is a major planned refactor and must be approved separately.
- It preserves meaningful nullable fields where business absence is distinct from zero or empty string. Each nullable field must be reviewed before production hardening.
