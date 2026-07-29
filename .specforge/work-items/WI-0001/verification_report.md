# 验证报告

## 结果汇总

| 指标 | 数值 |
|------|------|
| 总检查数 | 55 |
| 通过 | 55 |
| 失败 | 0 |
| 结论 | pass |

## 验证命令

| 命令 | 状态 | 输出摘要 |
|------|------|----------|
| `python -m pytest tests/ --import-mode=importlib -q (on svr3 server-test, real PG16+TimescaleDB)` | ✅ pass | 290 passed, 0 failed, 0 skipped in 2.30s. All @skip_no_pg tests executed against real database. Exit 0. |
| `alembic upgrade base (fresh PG16/TimescaleDB 2.28.3)` | ✅ pass | Full upgrade base→0015_audit_gap_rawev succeeded on fresh database. Alembic current: 0015_audit_gap_rawev (head). 78 tables across 7 schemas (audit:1, clean:18, lineage:1, meta:4, ops:12, quality:4, raw:11). 1 TimescaleDB hypertable (stock_minute). |
| `alembic downgrade 0014 && alembic downgrade 0013 && alembic downgrade 0012 (regression)` | ✅ pass | Downgrade 0015→0014→0013→0012 all succeeded. Each revision's downgrade() function executed cleanly. |
| `alembic upgrade 0013 && alembic upgrade 0014 && alembic upgrade head (regression re-upgrade)` | ✅ pass | Upgrade 0012→0013→0014→0015 succeeded. Final Alembic current: 0015_audit_gap_rawev (head). Confirmed migration chain is reversible. |
| `full_backup.sh (pg_dump custom format + SHA256)` | ✅ pass | Backup produced: pg_dump custom format, 378,230 bytes. SHA256: 2a881d8787464089e9d54ac1853ae028504050db6d282bc23ffc26b53486937d. |
| `verify.sh (backup integrity verification)` | ✅ pass | 78 tables, 1 hypertable, 10 data items confirmed. Alembic version: 0015_audit_gap_rawev. Checksum MATCHED. |
| `pg_restore to quantstock1_test_restore (independent DB)` | ✅ pass | Restore to independent database succeeded. All objects verified: 78 tables, 1 hypertable, 10 data items, same Alembic version 0015_audit_gap_rawev. |
| `grep down_revision/revision migrations/versions/001[2345]_*.py (sf-verifier independent)` | ✅ pass | Chain verified: 0012_p4_minute_governance -> 0013_lineage_and_snapshot -> 0014_pub_at_fin_dataitem -> 0015_audit_gap_rawev. All revision IDs <= VARCHAR(32). Shortened IDs: 0014_pub_at_fin_dataitem (24 chars), 0015_audit_gap_rawev (20 chars). |
| `grep DDL patterns migration 0013 (sf-verifier independent)` | ✅ pass | lineage_edge + data_snapshot + data_snapshot_input tables, content_fingerprint, status CHECK(BUILDING/READY/INVALIDATED), trg_data_snapshot_no_modify_ready trigger confirmed in source. |
| `grep DDL patterns migration 0014 (sf-verifier independent)` | ✅ pass | _published_at on 10 CLEAN tables, financial_income/indicator multi-version + partial unique index is_current=true, quality_policy_ref + 10 DataItem seeds confirmed in source. |
| `grep DDL patterns migration 0015 (sf-verifier independent)` | ✅ pass | ck_collect_task_run_type CHECK(INITIALIZE/INCREMENTAL/BACKFILL/REPAIR/RETRY) with historical fix-up, trg_audit_event_append_only trigger, DataGap pre_backfill_count/post_backfill_count/checksum_verified, raw_batch content_hash/fetched_at/schema_fingerprint confirmed in source. |
| `grep RAW-import in app/datacontext/** (sf-verifier independent)` | ✅ pass | 0 matches - DataContext does not import raw models (REQ-CORE-016). |
| `glob deliverable files (sf-verifier independent)` | ✅ pass | All deliverables exist: compose.test.yml, scripts/db_backup/full_backup.sh, scripts/db_restore/{restore.sh,verify.sh}, 65 test .py files, migration files. |

## 验收标准

| 需求 | 名称 | 状态 | 证据 |
|------|------|------|------|
| REQ-CORE-001 | DataItem metadata completeness (10 items, 9 fields) | ✅ pass | EV-008 |
| REQ-CORE-002 | Worker LOST / Lease recovery + terminal irreversibility | ✅ pass | EV-008 |
| REQ-CORE-003 | run_type unified enum + DB CHECK | ✅ pass | EV-013 |
| REQ-CORE-004 | Idempotency keys + force rerun | ✅ pass | EV-008 |
| REQ-CORE-005 | RAW batch evidence 5 fields + 7-hop chain | ✅ pass | EV-013 |
| REQ-CORE-006 | CLEAN 8 properties + is_current unique | ✅ pass | EV-013 |
| REQ-CORE-007 | Adjustment layering (no overwrite of raw) | ✅ pass | EV-008 |
| REQ-CORE-008 | Financial revision multi-version retention | ✅ pass | EV-013 |
| REQ-CORE-009 | available_at <= as_of_time backtest constraint | ✅ pass | EV-008 |
| REQ-CORE-010 | FAILED data publish block | ✅ pass | EV-008 |
| REQ-CORE-011 | WARNING publish policy | ✅ pass | EV-008 |
| REQ-CORE-012 | DataGap VERIFIED closure | ✅ pass | EV-013 |
| REQ-CORE-013 | lineage_edge table + recursive query p95<=3s | ✅ pass | EV-013 |
| REQ-CORE-014 | AuditEvent 13-field logging | ✅ pass | EV-008 |
| REQ-CORE-015 | AuditEvent append-only | ✅ pass | EV-013 |
| REQ-CORE-016 | DataContext does not read RAW | ✅ pass | EV-005 |
| REQ-CORE-017 | DataContext 5 query modes | ✅ pass | EV-013 |
| REQ-CORE-018 | DataContext 6-frequency alignment | ✅ pass | EV-008 |
| REQ-CORE-019 | DataSnapshot immutable (READY) | ✅ pass | EV-013 |
| REQ-CORE-020 | DataSnapshot reproducible + query-consistent | ✅ pass | EV-013 |
| REQ-CORE-021 | Anti-lookahead 3 time modes | ✅ pass | EV-008 |
| REQ-CORE-022 | published_at / available_at separation | ✅ pass | EV-008 |
| REQ-CORE-023 | Historical pool + status point-in-time | ✅ pass | EV-008 |
| REQ-CORE-024 | Anti-lookahead test suite 100% pass | ✅ pass | EV-008 |
| REQ-CORE-025 | Unified query API 4 data types | ✅ pass | EV-008 |
| REQ-CORE-026 | Query result metadata | ✅ pass | EV-008 |
| REQ-CORE-027 | API no long-task + timeout 504 | ✅ pass | EV-013 |
| REQ-CORE-028 | Ops query no seqscan on minute table | ✅ pass | EV-013 |
| REQ-CORE-029 | DB migration-disk script 6 phases | ✅ pass | EV-008 |
| REQ-CORE-030 | Minute compression/archive/checksum baseline | ✅ pass | EV-008 |
| REQ-CORE-031 | server-test isolated environment | ✅ pass | EV-008 |
| REQ-CORE-032 | Full backup script + 4 attributes + off-server copy | ✅ pass | EV-015 |
| REQ-CORE-033 | Restore script + 3-verify + health check | ✅ pass | EV-015 |
| REQ-CORE-034 | 10 test categories + real PG + coverage >=80% | ✅ pass | EV-013 |
| REQ-CORE-035 | E2E 10x8 matrix real-data acceptance | ✅ pass | EV-013 |

## 端到端测试

| 测试名称 | 状态 | 证据 |
|----------|------|------|
| Full test suite on real PostgreSQL 16 + TimescaleDB 2.28.3 (290 tests) | ✅ pass | EV-008 |
| Migration chain upgrade base->0015 on fresh PG16/TimescaleDB | ✅ pass | EV-012 |
| Migration downgrade+upgrade regression (0015->0012->0015) | ✅ pass | EV-014 |
| All DB-dependent tests (previously @skip_no_pg) on real PG16 | ✅ pass | EV-013 |
| Backup+checksum+restore drill on server-test | ✅ pass | EV-015 |
| Migration chain structural integrity (0012->0015) | ✅ pass | EV-001 |
| DataContext RAW-isolation boundary | ✅ pass | EV-005 |

## 副作用

No side effects. sf-verifier is read-only (permission.edit=deny). All verification used read-only grep/glob/read tools and referenced server execution logs. No source files or governance artifacts were modified by the verifier. The changed_files_audit reports 0 unresolved violations (1 historical hard_stop_resolution resolved via prohibited_action_replaced).

## 结论

**结论：pass**

VERIFICATION PASSED. Full test suite executed on real PostgreSQL 16.14 + TimescaleDB 2.28.3 on server svr3 (Linux CentOS/RHEL 8, Docker 26.1.3, Compose v2.27.0). 290 tests passed, 0 failed, 0 skipped — all 12 previously-skipped @skip_no_pg tests now execute and pass against the real database. Full migration chain base→0015_audit_gap_rawev succeeds on fresh PG16/TimescaleDB: 78 tables across 7 schemas, 1 TimescaleDB hypertable (stock_minute), all key objects verified (financial_income, financial_indicator, data_snapshot, lineage_edge, trg_audit_event_append_only trigger, ck_collect_task_run_type CHECK constraint, _published_at columns on 10 CLEAN tables, DataGap verified fields, RawBatch evidence fields, 10 meta.data_item seed records). Migration downgrade+upgrade regression (0015→0014→0013→0012→0013→0014→0015) succeeds with final state confirmed as 0015_audit_gap_rawev (head). Backup+checksum+restore drill completed: full_backup.sh produces pg_dump custom format (378,230 bytes, SHA256 verified), verify.sh confirms 78 tables + 1 hypertable + 10 data items + Alembic version, restore to independent DB (quantstock1_test_restore) succeeds with all objects verified. Bugs found and fixed during server verification: (1) Alembic revision IDs shortened to fit VARCHAR(32); (2) SET LOCAL statement_timeout parameter binding fixed; (3) Missing ORM model attributes added (_published_at, FinancialIncome/FinancialIndicator, DataGap fields, RawBatch fields); (4) Starlette 1.3 _IncludedRouter.original_router handling added. sf-verifier independently confirmed: migration chain integrity (0012→0013→0014_pub_at_fin_dataitem→0015_audit_gap_rawev, all down_revision correct), all DDL patterns present in migration source files (trg_audit_event_append_only, ck_collect_task_run_type CHECK, _published_at on 10 CLEAN tables, DataGap verified fields, RawBatch evidence fields, lineage_edge + data_snapshot tables, content_fingerprint, READY-immutability trigger), DataContext zero RAW imports, all deliverable files exist (compose.test.yml, 4 backup/restore scripts, 65 test files). No side effects — verifier is read-only.

## Machine-readable Verification Contract

```json
{
  "work_item_id": "WI-0001",
  "workflow_type": "feature_spec",
  "verifier_agent": "sf-verifier",
  "verification_timestamp": "2026-07-29T12:30:00Z",
  "conclusion": "pass",
  "overall_status": "pass",
  "summary": "VERIFICATION PASSED. Full test suite executed on real PostgreSQL 16.14 + TimescaleDB 2.28.3 on server svr3 (Linux CentOS/RHEL 8, Docker 26.1.3, Compose v2.27.0). 290 tests passed, 0 failed, 0 skipped — all 12 previously-skipped @skip_no_pg tests now execute and pass against the real database. Full migration chain base→0015_audit_gap_rawev succeeds on fresh PG16/TimescaleDB: 78 tables across 7 schemas, 1 TimescaleDB hypertable (stock_minute), all key objects verified (financial_income, financial_indicator, data_snapshot, lineage_edge, trg_audit_event_append_only trigger, ck_collect_task_run_type CHECK constraint, _published_at columns on 10 CLEAN tables, DataGap verified fields, RawBatch evidence fields, 10 meta.data_item seed records). Migration downgrade+upgrade regression (0015→0014→0013→0012→0013→0014→0015) succeeds with final state confirmed as 0015_audit_gap_rawev (head). Backup+checksum+restore drill completed: full_backup.sh produces pg_dump custom format (378,230 bytes, SHA256 verified), verify.sh confirms 78 tables + 1 hypertable + 10 data items + Alembic version, restore to independent DB (quantstock1_test_restore) succeeds with all objects verified. Bugs found and fixed during server verification: (1) Alembic revision IDs shortened to fit VARCHAR(32); (2) SET LOCAL statement_timeout parameter binding fixed; (3) Missing ORM model attributes added (_published_at, FinancialIncome/FinancialIndicator, DataGap fields, RawBatch fields); (4) Starlette 1.3 _IncludedRouter.original_router handling added. sf-verifier independently confirmed: migration chain integrity (0012→0013→0014_pub_at_fin_dataitem→0015_audit_gap_rawev, all down_revision correct), all DDL patterns present in migration source files (trg_audit_event_append_only, ck_collect_task_run_type CHECK, _published_at on 10 CLEAN tables, DataGap verified fields, RawBatch evidence fields, lineage_edge + data_snapshot tables, content_fingerprint, READY-immutability trigger), DataContext zero RAW imports, all deliverable files exist (compose.test.yml, 4 backup/restore scripts, 65 test files). No side effects — verifier is read-only.",
  "test_matrix": {
    "L1_unit": "pass",
    "L2_integration": "pass",
    "L3_pbt": "not_applicable",
    "L4_e2e": "pass",
    "L5_smoke": "pass",
    "L6_regression": "pass",
    "L7_performance": "pass",
    "L8_security": "not_applicable",
    "L9_compatibility": "pass",
    "L10_uat": "not_applicable"
  },
  "server_environment": {
    "server": "svr3 (Linux CentOS/RHEL 8, kernel 4.18.0-553.el8_10.x86_64)",
    "docker": "26.1.3",
    "docker_compose": "v2.27.0",
    "database": "PostgreSQL 16.14 on x86_64-pc-linux-musl (Alpine 15.2.0)",
    "timescaledb": "2.28.3 (pg_extension confirmed)",
    "python": "3.11.15 (inside quantstock1-test-api container)",
    "psycopg": "3.3.4",
    "sqlalchemy": "2.0.51",
    "alembic": "1.18.5",
    "compose_project": "quantstock1-test (isolated network, port 15432/18001)"
  },
  "test_summary": {
    "total": 290,
    "passed": 290,
    "failed": 0,
    "skipped": 0,
    "skipped_reason": "N/A — 0 skipped. All @skip_no_pg tests ran against real PostgreSQL 16.",
    "duration": "2.30s",
    "command": "python -m pytest tests/ --import-mode=importlib -q",
    "source": "server-test execution on svr3 (real PG16/TimescaleDB 2.28.3)"
  },
  "code_quality": {
    "py_compile_passed": true,
    "files_checked": 55,
    "source": "executor prior run + server compilation during pytest"
  },
  "categories": [
    {
      "name": "State machine (terminal irreversibility)",
      "files": "test_state_machine.py",
      "result": "PASS (incl. PG-dependent)"
    },
    {
      "name": "Idempotency + force_rerun",
      "files": "test_idempotency.py, test_force_rerun.py",
      "result": "PASS"
    },
    {
      "name": "RAW evidence fields (5 tests, previously @skip_no_pg)",
      "files": "test_raw_evidence.py",
      "result": "PASS on real PG16"
    },
    {
      "name": "CLEAN versioning (4 tests, previously @skip_no_pg)",
      "files": "test_clean_version.py",
      "result": "PASS on real PG16"
    },
    {
      "name": "Quality gate",
      "files": "test_quality_gate.py",
      "result": "PASS"
    },
    {
      "name": "DataGap VERIFIED (incl. 1 previously @skip_no_pg)",
      "files": "test_datagap_verified.py",
      "result": "PASS on real PG16"
    },
    {
      "name": "Lineage edge (incl. 1 previously @skip_no_pg perf)",
      "files": "test_lineage_edge.py",
      "result": "PASS on real PG16"
    },
    {
      "name": "Anti-lookahead (6 scenarios)",
      "files": "test_backtest_mode.py, test_available_at_injection.py, test_published_available_separation.py, test_historical_pool.py, test_historical_status.py, test_adjustment_factor_timepoint.py",
      "result": "PASS"
    },
    {
      "name": "API contract",
      "files": "test_data_api.py",
      "result": "PASS"
    },
    {
      "name": "API timeout (incl. 1 previously @skip_no_pg 504)",
      "files": "test_api_timeout.py",
      "result": "PASS on real PG16"
    },
    {
      "name": "Ops query no seqscan (3 tests, previously @skip_no_pg)",
      "files": "test_ops_query_no_seqscan.py",
      "result": "PASS on real PG16"
    },
    {
      "name": "DataContext queries (incl. 1 previously @skip_no_pg full-market)",
      "files": "test_datacontext_queries.py",
      "result": "PASS on real PG16"
    },
    {
      "name": "Snapshot immutability (incl. 3 previously @skip_no_pg)",
      "files": "test_snapshot_immutability.py",
      "result": "PASS on real PG16"
    },
    {
      "name": "Performance queries (2 tests, previously @skip_no_pg)",
      "files": "test_perf_queries.py",
      "result": "PASS on real PG16"
    },
    {
      "name": "Backup checksum",
      "files": "test_backup_checksum.py",
      "result": "PASS"
    },
    {
      "name": "Restore verify",
      "files": "test_restore_verify.py",
      "result": "PASS"
    },
    {
      "name": "Server-test isolation",
      "files": "test_server_test_isolation.py",
      "result": "PASS"
    },
    {
      "name": "Migrate precheck",
      "files": "test_migrate_precheck.py",
      "result": "PASS"
    },
    {
      "name": "Alembic empty upgrade",
      "files": "test_empty_upgrade.py",
      "result": "PASS"
    },
    {
      "name": "Alembic existing upgrade (incl. 1 previously @skip_no_pg)",
      "files": "test_existing_upgrade.py",
      "result": "PASS on real PG16"
    },
    {
      "name": "E2E 10x8 matrix",
      "files": "test_dataitem_matrix.py",
      "result": "PASS on real PG16"
    },
    {
      "name": "P4 regression (pre-existing)",
      "files": "test_api.py, test_ops_api.py, test_state_machine.py, test_idempotency.py, test_p4_batch2_lineage.py, test_p4_minute_lineage.py, test_p4_routes.py",
      "result": "PASS (0 regression)"
    }
  ],
  "verification_commands": [
    {
      "command": "python -m pytest tests/ --import-mode=importlib -q (on svr3 server-test, real PG16+TimescaleDB)",
      "status": "pass",
      "output_summary": "290 passed, 0 failed, 0 skipped in 2.30s. All @skip_no_pg tests executed against real database. Exit 0."
    },
    {
      "command": "alembic upgrade base (fresh PG16/TimescaleDB 2.28.3)",
      "status": "pass",
      "output_summary": "Full upgrade base→0015_audit_gap_rawev succeeded on fresh database. Alembic current: 0015_audit_gap_rawev (head). 78 tables across 7 schemas (audit:1, clean:18, lineage:1, meta:4, ops:12, quality:4, raw:11). 1 TimescaleDB hypertable (stock_minute)."
    },
    {
      "command": "alembic downgrade 0014 && alembic downgrade 0013 && alembic downgrade 0012 (regression)",
      "status": "pass",
      "output_summary": "Downgrade 0015→0014→0013→0012 all succeeded. Each revision's downgrade() function executed cleanly."
    },
    {
      "command": "alembic upgrade 0013 && alembic upgrade 0014 && alembic upgrade head (regression re-upgrade)",
      "status": "pass",
      "output_summary": "Upgrade 0012→0013→0014→0015 succeeded. Final Alembic current: 0015_audit_gap_rawev (head). Confirmed migration chain is reversible."
    },
    {
      "command": "full_backup.sh (pg_dump custom format + SHA256)",
      "status": "pass",
      "output_summary": "Backup produced: pg_dump custom format, 378,230 bytes. SHA256: 2a881d8787464089e9d54ac1853ae028504050db6d282bc23ffc26b53486937d."
    },
    {
      "command": "verify.sh (backup integrity verification)",
      "status": "pass",
      "output_summary": "78 tables, 1 hypertable, 10 data items confirmed. Alembic version: 0015_audit_gap_rawev. Checksum MATCHED."
    },
    {
      "command": "pg_restore to quantstock1_test_restore (independent DB)",
      "status": "pass",
      "output_summary": "Restore to independent database succeeded. All objects verified: 78 tables, 1 hypertable, 10 data items, same Alembic version 0015_audit_gap_rawev."
    },
    {
      "command": "grep down_revision/revision migrations/versions/001[2345]_*.py (sf-verifier independent)",
      "status": "pass",
      "output_summary": "Chain verified: 0012_p4_minute_governance -> 0013_lineage_and_snapshot -> 0014_pub_at_fin_dataitem -> 0015_audit_gap_rawev. All revision IDs <= VARCHAR(32). Shortened IDs: 0014_pub_at_fin_dataitem (24 chars), 0015_audit_gap_rawev (20 chars)."
    },
    {
      "command": "grep DDL patterns migration 0013 (sf-verifier independent)",
      "status": "pass",
      "output_summary": "lineage_edge + data_snapshot + data_snapshot_input tables, content_fingerprint, status CHECK(BUILDING/READY/INVALIDATED), trg_data_snapshot_no_modify_ready trigger confirmed in source."
    },
    {
      "command": "grep DDL patterns migration 0014 (sf-verifier independent)",
      "status": "pass",
      "output_summary": "_published_at on 10 CLEAN tables, financial_income/indicator multi-version + partial unique index is_current=true, quality_policy_ref + 10 DataItem seeds confirmed in source."
    },
    {
      "command": "grep DDL patterns migration 0015 (sf-verifier independent)",
      "status": "pass",
      "output_summary": "ck_collect_task_run_type CHECK(INITIALIZE/INCREMENTAL/BACKFILL/REPAIR/RETRY) with historical fix-up, trg_audit_event_append_only trigger, DataGap pre_backfill_count/post_backfill_count/checksum_verified, raw_batch content_hash/fetched_at/schema_fingerprint confirmed in source."
    },
    {
      "command": "grep RAW-import in app/datacontext/** (sf-verifier independent)",
      "status": "pass",
      "output_summary": "0 matches - DataContext does not import raw models (REQ-CORE-016)."
    },
    {
      "command": "glob deliverable files (sf-verifier independent)",
      "status": "pass",
      "output_summary": "All deliverables exist: compose.test.yml, scripts/db_backup/full_backup.sh, scripts/db_restore/{restore.sh,verify.sh}, 65 test .py files, migration files."
    }
  ],
  "acceptance_criteria": [
    {
      "req_id": "REQ-CORE-001",
      "name": "DataItem metadata completeness (10 items, 9 fields)",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-003",
        "EV-008",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-002",
      "name": "Worker LOST / Lease recovery + terminal irreversibility",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008",
        "EV-009"
      ]
    },
    {
      "req_id": "REQ-CORE-003",
      "name": "run_type unified enum + DB CHECK",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-004",
        "EV-012",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-004",
      "name": "Idempotency keys + force rerun",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008",
        "EV-009"
      ]
    },
    {
      "req_id": "REQ-CORE-005",
      "name": "RAW batch evidence 5 fields + 7-hop chain",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-004",
        "EV-008",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-006",
      "name": "CLEAN 8 properties + is_current unique",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-003",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-007",
      "name": "Adjustment layering (no overwrite of raw)",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-008",
      "name": "Financial revision multi-version retention",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-003",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-009",
      "name": "available_at <= as_of_time backtest constraint",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-010",
      "name": "FAILED data publish block",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-011",
      "name": "WARNING publish policy",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-012",
      "name": "DataGap VERIFIED closure",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-004",
        "EV-008",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-013",
      "name": "lineage_edge table + recursive query p95<=3s",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-002",
        "EV-008",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-014",
      "name": "AuditEvent 13-field logging",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-004",
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-015",
      "name": "AuditEvent append-only",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-004",
        "EV-012",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-016",
      "name": "DataContext does not read RAW",
      "status": "pass",
      "evidence": "EV-005",
      "evidence_refs": [
        "EV-005",
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-017",
      "name": "DataContext 5 query modes",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-008",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-018",
      "name": "DataContext 6-frequency alignment",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-019",
      "name": "DataSnapshot immutable (READY)",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-002",
        "EV-008",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-020",
      "name": "DataSnapshot reproducible + query-consistent",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-002",
        "EV-008",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-021",
      "name": "Anti-lookahead 3 time modes",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-022",
      "name": "published_at / available_at separation",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-003",
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-023",
      "name": "Historical pool + status point-in-time",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-024",
      "name": "Anti-lookahead test suite 100% pass",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-025",
      "name": "Unified query API 4 data types",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-026",
      "name": "Query result metadata",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-027",
      "name": "API no long-task + timeout 504",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-008",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-028",
      "name": "Ops query no seqscan on minute table",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-008",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-029",
      "name": "DB migration-disk script 6 phases",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-006",
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-030",
      "name": "Minute compression/archive/checksum baseline",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-006",
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-031",
      "name": "server-test isolated environment",
      "status": "pass",
      "evidence": "EV-008",
      "evidence_refs": [
        "EV-006",
        "EV-008"
      ]
    },
    {
      "req_id": "REQ-CORE-032",
      "name": "Full backup script + 4 attributes + off-server copy",
      "status": "pass",
      "evidence": "EV-015",
      "evidence_refs": [
        "EV-006",
        "EV-015"
      ]
    },
    {
      "req_id": "REQ-CORE-033",
      "name": "Restore script + 3-verify + health check",
      "status": "pass",
      "evidence": "EV-015",
      "evidence_refs": [
        "EV-006",
        "EV-015"
      ]
    },
    {
      "req_id": "REQ-CORE-034",
      "name": "10 test categories + real PG + coverage >=80%",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-007",
        "EV-008",
        "EV-012",
        "EV-013"
      ]
    },
    {
      "req_id": "REQ-CORE-035",
      "name": "E2E 10x8 matrix real-data acceptance",
      "status": "pass",
      "evidence": "EV-013",
      "evidence_refs": [
        "EV-008",
        "EV-013"
      ]
    }
  ],
  "e2e_tests": [
    {
      "name": "Full test suite on real PostgreSQL 16 + TimescaleDB 2.28.3 (290 tests)",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "name": "Migration chain upgrade base->0015 on fresh PG16/TimescaleDB",
      "status": "pass",
      "evidence": "EV-012"
    },
    {
      "name": "Migration downgrade+upgrade regression (0015->0012->0015)",
      "status": "pass",
      "evidence": "EV-014"
    },
    {
      "name": "All DB-dependent tests (previously @skip_no_pg) on real PG16",
      "status": "pass",
      "evidence": "EV-013"
    },
    {
      "name": "Backup+checksum+restore drill on server-test",
      "status": "pass",
      "evidence": "EV-015"
    },
    {
      "name": "Migration chain structural integrity (0012->0015)",
      "status": "pass",
      "evidence": "EV-001"
    },
    {
      "name": "DataContext RAW-isolation boundary",
      "status": "pass",
      "evidence": "EV-005"
    }
  ],
  "side_effects": "No side effects. sf-verifier is read-only (permission.edit=deny). All verification used read-only grep/glob/read tools and referenced server execution logs. No source files or governance artifacts were modified by the verifier. The changed_files_audit reports 0 unresolved violations (1 historical hard_stop_resolution resolved via prohibited_action_replaced).",
  "bugs_found_and_fixed": [
    {
      "id": "BUG-001",
      "description": "Alembic revision IDs exceeded VARCHAR(32): 0014_clean_published_at_financial_dataitem (41 chars) and 0015_audit_runcheck_datagap_rawevidence (39 chars)",
      "fix": "Shortened to 0014_pub_at_fin_dataitem (24 chars) and 0015_audit_gap_rawev (20 chars)",
      "commit": "8f73666"
    },
    {
      "id": "BUG-002",
      "description": "SET LOCAL statement_timeout parameter binding: PostgreSQL SET does not support parameterized values",
      "fix": "Changed to f-string interpolation for statement_timeout",
      "commit": "6a43292"
    },
    {
      "id": "BUG-003",
      "description": "Missing ORM model attributes: _published_at on 10 CLEAN models, FinancialIncome/FinancialIndicator models, DataGap verified fields, RawBatch evidence fields",
      "fix": "Added all missing ORM attributes to match migration DDL",
      "commit": "6a43292"
    },
    {
      "id": "BUG-004",
      "description": "Starlette 1.3 _IncludedRouter: route extraction needed to handle original_router attribute",
      "fix": "Added handling for _IncludedRouter.original_router",
      "commit": "d40ca76"
    }
  ],
  "git_commits": [
    {
      "hash": "5164e54",
      "message": "feat(step2): implement data foundation for server verification"
    },
    {
      "hash": "8f73666",
      "message": "fix(step2): shorten Alembic revision IDs to fit VARCHAR(32)"
    },
    {
      "hash": "6a43292",
      "message": "fix(step2): fix 13 test failures found during real PG16 verification"
    },
    {
      "hash": "c1919ae",
      "message": "fix(step2): fix remaining test failures for PG16 server verification"
    },
    {
      "hash": "d40ca76",
      "message": "fix(step2): handle Starlette 1.3 _IncludedRouter.original_router"
    }
  ],
  "governance_model": {
    "basis_checked": true,
    "upstream_coverage_checked": true,
    "required_evidence_checked": true,
    "project_integration_checked": true
  },
  "required_evidence_results": [
    {
      "id": "EVREQ-CORE-005-1",
      "supports": [
        "REQ-CORE-005"
      ],
      "required_level": "L4",
      "actual_level": "L4",
      "status": "pass",
      "command": "5 RAW evidence tests on real PG16 (test_raw_evidence.py)",
      "observed_result": "5 passed, 0 failed. RAW batch evidence fields (content_hash, fetched_at, schema_fingerprint) verified on real PG16."
    },
    {
      "id": "EVREQ-CORE-013-3",
      "supports": [
        "REQ-CORE-013"
      ],
      "required_level": "L4",
      "actual_level": "L4",
      "status": "pass",
      "command": "lineage recursive query test on real PG16 (test_lineage_edge.py)",
      "observed_result": "All lineage tests passed including recursive query performance test on real PG16."
    },
    {
      "id": "EVREQ-CORE-015-2",
      "supports": [
        "REQ-CORE-015"
      ],
      "required_level": "L3",
      "actual_level": "L4",
      "status": "pass",
      "command": "audit_event UPDATE/DELETE rejection on real PG16",
      "observed_result": "trg_audit_event_append_only trigger enforces append-only. Migration 0015 creates trigger, tests verify UPDATE/DELETE rejected."
    },
    {
      "id": "EVREQ-CORE-028-2",
      "supports": [
        "REQ-CORE-028"
      ],
      "required_level": "L4",
      "actual_level": "L4",
      "status": "pass",
      "command": "EXPLAIN ANALYZE no Seq Scan on real PG16 (test_ops_query_no_seqscan.py)",
      "observed_result": "3 ops query no-seqscan tests passed on real PG16 with TimescaleDB hypertable."
    },
    {
      "id": "EVREQ-CORE-034-2",
      "supports": [
        "REQ-CORE-034"
      ],
      "required_level": "L4",
      "actual_level": "L4",
      "status": "pass",
      "command": "ALL DB tests on real PG 16/TimescaleDB 2.28.3",
      "observed_result": "290 tests passed, 0 skipped. All 12 previously-skipped @skip_no_pg tests executed and passed. REQ-CORE-034 hard constraint #2 satisfied."
    },
    {
      "id": "EVREQ-CORE-034-3",
      "supports": [
        "REQ-CORE-034"
      ],
      "required_level": "L3",
      "actual_level": "L4",
      "status": "pass",
      "command": "alembic upgrade base->head on real PG16",
      "observed_result": "Full upgrade base->0015_audit_gap_rawev succeeded. 78 tables, 7 schemas, 1 hypertable. Alembic current: 0015_audit_gap_rawev (head)."
    }
  ],
  "missing_blocking_evidence": [],
  "migration_verification": {
    "status": "passed",
    "alembic_head": "0015_audit_gap_rawev",
    "tables_count": 78,
    "schemas": {
      "audit": 1,
      "clean": 18,
      "lineage": 1,
      "meta": 4,
      "ops": 12,
      "quality": 4,
      "raw": 11
    },
    "hypertables": [
      "stock_minute"
    ],
    "key_objects_verified": [
      "financial_income table",
      "financial_indicator table",
      "data_snapshot table",
      "data_snapshot_input table",
      "lineage_edge table",
      "trg_audit_event_append_only trigger",
      "ck_collect_task_run_type CHECK constraint",
      "_published_at columns on 10 CLEAN tables",
      "DataGap pre_backfill_count/post_backfill_count/checksum_verified/verified_at",
      "RawBatch content_hash/fetched_at/schema_fingerprint",
      "meta.data_item seed data (10 items with correct metadata)"
    ],
    "downgrade_upgrade_regression": "0015->0014->0013->0012->0013->0014->0015 all succeeded. Final: 0015_audit_gap_rawev (head)."
  },
  "backup_restore_verification": {
    "status": "passed",
    "backup_format": "pg_dump custom format",
    "backup_size_bytes": 378230,
    "backup_sha256": "2a881d8787464089e9d54ac1853ae028504050db6d282bc23ffc26b53486937d",
    "verify_result": "78 tables, 1 hypertable, 10 data items, Alembic 0015_audit_gap_rawev, checksum MATCHED",
    "restore_target": "quantstock1_test_restore (independent DB)",
    "restore_result": "pg_restore succeeded, all objects verified (78 tables, 1 hypertable, 10 data items, same Alembic version)"
  },
  "project_integration": {
    "status": "merged",
    "spec_version": "PSV-0001 -> PSV-0002",
    "merge_report_status": "success",
    "merged_entries": [
      "requirements.candidate.md -> requirements.md",
      "design.candidate.md -> design.md",
      "trace_delta.md -> trace_matrix.md"
    ]
  }
}
```
