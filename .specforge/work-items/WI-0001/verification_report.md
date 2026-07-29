# 验证报告

## 结果汇总

| 指标 | 数值 |
|------|------|
| 总检查数 | 52 |
| 通过 | 37 |
| 失败 | 0 |
| 结论 | blocked |

## 验证命令

| 命令 | 状态 | 输出摘要 |
|------|------|----------|
| `grep down_revision/revision migrations/versions/001[2345]_*.py` | ✅ pass | Chain verified: 0012->0013->0014->0015, all down_revision correct (sf-verifier independent) |
| `grep RAW-import in app/datacontext/**` | ✅ pass | 0 matches - DataContext does not import raw models (REQ-CORE-016 code-level, sf-verifier independent) |
| `grep DDL patterns migration 0013` | ✅ pass | lineage_edge + data_snapshot + data_snapshot_input tables, content_fingerprint, status CHECK(BUILDING/READY/INVALIDATED), trg_data_snapshot_no_modify_ready trigger (sf-verifier independent) |
| `grep DDL patterns migration 0014` | ✅ pass | _published_at on CLEAN tables, financial_income/indicator multi-version + partial unique index is_current=true, quality_policy_ref + 10 DataItem seeds (sf-verifier independent) |
| `grep DDL patterns migration 0015` | ✅ pass | ck_collect_task_run_type CHECK, prevent_audit_event_modification trigger, DataGap pre_backfill_count/post_backfill_count/checksum_verified, raw_batch content_hash/fetched_at/schema_fingerprint (sf-verifier independent) |
| `glob deliverable files` | ✅ pass | All 19 TASKs files exist: app/datacontext/ (12 files), app/storage/models/{lineage,snapshot}.py, 29 test files, scripts/{db_migrate_disk,db_backup,db_restore,minute_archive}, compose.test.yml (sf-verifier independent) |
| `python -m pytest tests/integration/ tests/lineage/ ... --tb=short -q (executor)` | ✅ pass | 186 passed, 12 skipped, 0 failed, exit 0 (executor prior run; sf-verifier could not re-run) |
| `python -m pytest P4 regression tests (executor)` | ✅ pass | 12 passed, 0 failed, exit 0 (executor prior run) |
| `python -m py_compile (55 files, executor)` | ✅ pass | All 55 .py files compile, exit 0 (executor prior run) |
| `alembic upgrade head (0012->0015)` | ❌ skipped | WAITING_USER_EXECUTION - requires real PostgreSQL 16; never executed against real DB |
| `alembic downgrade 0014 (regression)` | ❌ skipped | Requires real PostgreSQL; not executed |
| `12 DB-dependent pytest cases (RAW evidence, CLEAN versioning, seqscan EXPLAIN, perf p95, snapshot immutability, etc.)` | ❌ skipped | All 12 carry @skip_no_pg marker; require real PG/TimescaleDB |

## 验收标准

| 需求 | 名称 | 状态 | 证据 |
|------|------|------|------|
| REQ-CORE-001 | DataItem metadata completeness (10 items, 9 fields) | ❌ blocked | EV-003 |
| REQ-CORE-002 | Worker LOST / Lease recovery + terminal irreversibility | ✅ pass | EV-008 |
| REQ-CORE-003 | run_type unified enum + DB CHECK | ❌ blocked | EV-004 |
| REQ-CORE-004 | Idempotency keys + force rerun | ✅ pass | EV-008 |
| REQ-CORE-005 | RAW batch evidence 5 fields + 7-hop chain | ❌ blocked | EV-004 |
| REQ-CORE-006 | CLEAN 8 properties + is_current unique | ❌ blocked | EV-003 |
| REQ-CORE-007 | Adjustment layering (no overwrite of raw) | ✅ pass | EV-008 |
| REQ-CORE-008 | Financial revision multi-version retention | ❌ blocked | EV-003 |
| REQ-CORE-009 | available_at <= as_of_time backtest constraint | ✅ pass | EV-008 |
| REQ-CORE-010 | FAILED data publish block | ✅ pass | EV-008 |
| REQ-CORE-011 | WARNING publish policy | ✅ pass | EV-008 |
| REQ-CORE-012 | DataGap VERIFIED closure | ❌ blocked | EV-004 |
| REQ-CORE-013 | lineage_edge table + recursive query p95<=3s | ❌ blocked | EV-002 |
| REQ-CORE-014 | AuditEvent 13-field logging | ✅ pass | EV-008 |
| REQ-CORE-015 | AuditEvent append-only | ❌ blocked | EV-004 |
| REQ-CORE-016 | DataContext does not read RAW | ✅ pass | EV-005 |
| REQ-CORE-017 | DataContext 5 query modes | ❌ blocked | EV-008 |
| REQ-CORE-018 | DataContext 6-frequency alignment | ✅ pass | EV-008 |
| REQ-CORE-019 | DataSnapshot immutable (READY) | ❌ blocked | EV-002 |
| REQ-CORE-020 | DataSnapshot reproducible + query-consistent | ❌ blocked | EV-002 |
| REQ-CORE-021 | Anti-lookahead 3 time modes | ✅ pass | EV-008 |
| REQ-CORE-022 | published_at / available_at separation | ✅ pass | EV-008 |
| REQ-CORE-023 | Historical pool + status point-in-time | ✅ pass | EV-008 |
| REQ-CORE-024 | Anti-lookahead test suite 100% pass | ✅ pass | EV-008 |
| REQ-CORE-025 | Unified query API 4 data types | ✅ pass | EV-008 |
| REQ-CORE-026 | Query result metadata | ✅ pass | EV-008 |
| REQ-CORE-027 | API no long-task + timeout 504 | ❌ blocked | EV-008 |
| REQ-CORE-028 | Ops query no seqscan on minute table | ❌ blocked | EV-008 |
| REQ-CORE-029 | DB migration-disk script 6 phases | ✅ pass | EV-006 |
| REQ-CORE-030 | Minute compression/archive/checksum baseline | ✅ pass | EV-006 |
| undefined | server-test isolated environment | ✅ pass | EV-006 |
| REQ-CORE-032 | Full backup script + 4 attributes + off-server copy | ✅ pass | EV-006 |
| REQ-CORE-033 | Restore script + 3-verify + health check | ✅ pass | EV-006 |
| REQ-CORE-034 | 10 test categories + real PG + coverage >=80% | ❌ blocked | EV-007 |
| REQ-CORE-035 | E2E 10x8 matrix real-data acceptance | ❌ blocked | EV-008 |

## 端到端测试

| 测试名称 | 状态 | 证据 |
|----------|------|------|
| Migration chain structural integrity (0012->0015) | ✅ pass | EV-001 |
| DataContext RAW-isolation boundary | ✅ pass | EV-005 |
| alembic upgrade head on real PostgreSQL | ❌ not_applicable | EV-012 |
| DB-dependent integration tests (12 cases) | ❌ not_applicable | EV-013 |
| Backup/restore drill on server-test | ❌ not_applicable | EV-013 |

## 副作用

No side effects. sf-verifier is read-only (permission.edit=deny); all verification used read-only grep/glob/read tools. No source files or governance artifacts were modified by the verifier. The changed_files_audit reports 0 unresolved violations (1 historical hard_stop_resolution resolved via prohibited_action_replaced).

## 结论

**结论：blocked**

Implementation is code-complete: all 19 TASKs' deliverables exist, 3 Alembic migrations (0013/0014/0015) have correct down_revision chain and DDL patterns matching DD-CORE-001..021, DataContext has zero RAW imports, and the executor reported 186 tests passed / 0 failed / 12 skipped. HOWEVER, the verification is BLOCKED because: (1) REQ-CORE-034 hard constraint #2 mandates ALL database tests run on real PostgreSQL 16 + TimescaleDB 2.28.3, but 12 DB-dependent tests are SKIPPED due to no PostgreSQL in this environment; (2) alembic upgrade head (0012->0015) is WAITING_USER_EXECUTION and was never executed against a real database; (3) trigger behavior (append-only audit_event, READY-immutable data_snapshot), run_type CHECK enforcement, lineage recursive-query performance (p95<=3s), API timeout/504, EXPLAIN-ANALYZE no-seqscan, backup/restore drill, and E2E 10x8 matrix all require real PG/TimescaleDB and are NOT runtime-verified. Per governance contract, database-dependent MUST requirements cannot pass with L1/L2 (file-exists/compile) evidence alone. The unblocking path is: execute the full test suite + alembic upgrade head + migration-downgrade regression in the server-test environment (compose.test.yml, real PG 16 + TimescaleDB 2.28.3, port 15432). Additionally, sf-verifier could not independently re-execute pytest because sf_safe_bash is broken on this Windows host (chcp 65001 prefix with ';' separator is invalid in cmd.exe); the pytest/py_compile numbers below are attributed to the executor's prior run, while all L1/L2 static verifications were performed independently by sf-verifier using read-only tools.

## Machine-readable Verification Contract

```json
{
  "work_item_id": "WI-0001",
  "workflow_type": "feature_spec",
  "verifier_agent": "sf-verifier",
  "verification_timestamp": "2026-07-29T05:10:00Z",
  "conclusion": "blocked",
  "overall_status": "blocked",
  "summary": "Implementation is code-complete: all 19 TASKs' deliverables exist, 3 Alembic migrations (0013/0014/0015) have correct down_revision chain and DDL patterns matching DD-CORE-001..021, DataContext has zero RAW imports, and the executor reported 186 tests passed / 0 failed / 12 skipped. HOWEVER, the verification is BLOCKED because: (1) REQ-CORE-034 hard constraint #2 mandates ALL database tests run on real PostgreSQL 16 + TimescaleDB 2.28.3, but 12 DB-dependent tests are SKIPPED due to no PostgreSQL in this environment; (2) alembic upgrade head (0012->0015) is WAITING_USER_EXECUTION and was never executed against a real database; (3) trigger behavior (append-only audit_event, READY-immutable data_snapshot), run_type CHECK enforcement, lineage recursive-query performance (p95<=3s), API timeout/504, EXPLAIN-ANALYZE no-seqscan, backup/restore drill, and E2E 10x8 matrix all require real PG/TimescaleDB and are NOT runtime-verified. Per governance contract, database-dependent MUST requirements cannot pass with L1/L2 (file-exists/compile) evidence alone. The unblocking path is: execute the full test suite + alembic upgrade head + migration-downgrade regression in the server-test environment (compose.test.yml, real PG 16 + TimescaleDB 2.28.3, port 15432). Additionally, sf-verifier could not independently re-execute pytest because sf_safe_bash is broken on this Windows host (chcp 65001 prefix with ';' separator is invalid in cmd.exe); the pytest/py_compile numbers below are attributed to the executor's prior run, while all L1/L2 static verifications were performed independently by sf-verifier using read-only tools.",
  "test_matrix": {
    "L1_unit": "pass",
    "L2_integration": "blocked",
    "L3_pbt": "not_applicable",
    "L4_e2e": "blocked",
    "L5_smoke": "blocked",
    "L6_regression": "pass",
    "L7_performance": "blocked",
    "L8_security": "not_applicable",
    "L9_compatibility": "blocked",
    "L10_uat": "not_applicable"
  },
  "test_summary": {
    "total": 198,
    "passed": 186,
    "failed": 0,
    "skipped": 12,
    "skipped_reason": "PostgreSQL/TimescaleDB not available in verifier environment; all 12 skips carry @skip_no_pg marker. REQ-CORE-034 requires real PG.",
    "source": "executor prior run (sf-verifier could not independently re-run due to broken sf_safe_bash on Windows cmd.exe)"
  },
  "code_quality": {
    "py_compile_passed": true,
    "files_checked": 55,
    "source": "executor prior run"
  },
  "categories": [
    {
      "name": "State machine (terminal irreversibility)",
      "files": "test_state_machine.py",
      "result": "12 PASS"
    },
    {
      "name": "Idempotency + force_rerun",
      "files": "test_idempotency.py, test_force_rerun.py",
      "result": "10 PASS"
    },
    {
      "name": "RAW evidence fields",
      "files": "test_raw_evidence.py",
      "result": "5 SKIP (PG)"
    },
    {
      "name": "CLEAN versioning",
      "files": "test_clean_version.py",
      "result": "4 SKIP (PG)"
    },
    {
      "name": "Quality gate",
      "files": "test_quality_gate.py",
      "result": "3 PASS"
    },
    {
      "name": "DataGap VERIFIED",
      "files": "test_datagap_verified.py",
      "result": "5 PASS, 1 SKIP (PG)"
    },
    {
      "name": "Lineage edge",
      "files": "test_lineage_edge.py",
      "result": "5 PASS, 1 SKIP (PG)"
    },
    {
      "name": "Anti-lookahead (6 scenarios)",
      "files": "test_backtest_mode.py, test_available_at_injection.py, test_published_available_separation.py, test_historical_pool.py, test_historical_status.py, test_adjustment_factor_timepoint.py",
      "result": "16 PASS"
    },
    {
      "name": "API contract",
      "files": "test_data_api.py",
      "result": "8 PASS"
    },
    {
      "name": "API timeout",
      "files": "test_api_timeout.py",
      "result": "1 PASS, 1 SKIP (PG)"
    },
    {
      "name": "Ops query no seqscan",
      "files": "test_ops_query_no_seqscan.py",
      "result": "3 SKIP (PG)"
    },
    {
      "name": "DataContext queries",
      "files": "test_datacontext_queries.py",
      "result": "2 PASS, 1 SKIP (PG)"
    },
    {
      "name": "Snapshot immutability",
      "files": "test_snapshot_immutability.py",
      "result": "5 PASS, 3 SKIP (PG)"
    },
    {
      "name": "Performance",
      "files": "test_perf_queries.py",
      "result": "2 SKIP (PG)"
    },
    {
      "name": "Backup checksum",
      "files": "test_backup_checksum.py",
      "result": "5 PASS"
    },
    {
      "name": "Restore verify",
      "files": "test_restore_verify.py",
      "result": "5 PASS"
    },
    {
      "name": "Server-test isolation",
      "files": "test_server_test_isolation.py",
      "result": "4 PASS"
    },
    {
      "name": "Migrate precheck",
      "files": "test_migrate_precheck.py",
      "result": "5 PASS"
    },
    {
      "name": "Alembic empty upgrade",
      "files": "test_empty_upgrade.py",
      "result": "9 PASS"
    },
    {
      "name": "Alembic existing upgrade",
      "files": "test_existing_upgrade.py",
      "result": "1 PASS, 1 SKIP (PG)"
    },
    {
      "name": "E2E 10x8 matrix",
      "files": "test_dataitem_matrix.py",
      "result": "80 PASS"
    },
    {
      "name": "P4 regression (pre-existing)",
      "files": "test_api.py, test_ops_api.py, test_state_machine.py, test_idempotency.py, test_p4_batch2_lineage.py, test_p4_minute_lineage.py, test_p4_routes.py",
      "result": "12 PASS, 0 FAIL"
    }
  ],
  "verification_commands": [
    {
      "command": "grep down_revision/revision migrations/versions/001[2345]_*.py",
      "status": "pass",
      "output_summary": "Chain verified: 0012->0013->0014->0015, all down_revision correct (sf-verifier independent)"
    },
    {
      "command": "grep RAW-import in app/datacontext/**",
      "status": "pass",
      "output_summary": "0 matches - DataContext does not import raw models (REQ-CORE-016 code-level, sf-verifier independent)"
    },
    {
      "command": "grep DDL patterns migration 0013",
      "status": "pass",
      "output_summary": "lineage_edge + data_snapshot + data_snapshot_input tables, content_fingerprint, status CHECK(BUILDING/READY/INVALIDATED), trg_data_snapshot_no_modify_ready trigger (sf-verifier independent)"
    },
    {
      "command": "grep DDL patterns migration 0014",
      "status": "pass",
      "output_summary": "_published_at on CLEAN tables, financial_income/indicator multi-version + partial unique index is_current=true, quality_policy_ref + 10 DataItem seeds (sf-verifier independent)"
    },
    {
      "command": "grep DDL patterns migration 0015",
      "status": "pass",
      "output_summary": "ck_collect_task_run_type CHECK, prevent_audit_event_modification trigger, DataGap pre_backfill_count/post_backfill_count/checksum_verified, raw_batch content_hash/fetched_at/schema_fingerprint (sf-verifier independent)"
    },
    {
      "command": "glob deliverable files",
      "status": "pass",
      "output_summary": "All 19 TASKs files exist: app/datacontext/ (12 files), app/storage/models/{lineage,snapshot}.py, 29 test files, scripts/{db_migrate_disk,db_backup,db_restore,minute_archive}, compose.test.yml (sf-verifier independent)"
    },
    {
      "command": "python -m pytest tests/integration/ tests/lineage/ ... --tb=short -q (executor)",
      "status": "pass",
      "output_summary": "186 passed, 12 skipped, 0 failed, exit 0 (executor prior run; sf-verifier could not re-run)"
    },
    {
      "command": "python -m pytest P4 regression tests (executor)",
      "status": "pass",
      "output_summary": "12 passed, 0 failed, exit 0 (executor prior run)"
    },
    {
      "command": "python -m py_compile (55 files, executor)",
      "status": "pass",
      "output_summary": "All 55 .py files compile, exit 0 (executor prior run)"
    },
    {
      "command": "alembic upgrade head (0012->0015)",
      "status": "skipped",
      "output_summary": "WAITING_USER_EXECUTION - requires real PostgreSQL 16; never executed against real DB"
    },
    {
      "command": "alembic downgrade 0014 (regression)",
      "status": "skipped",
      "output_summary": "Requires real PostgreSQL; not executed"
    },
    {
      "command": "12 DB-dependent pytest cases (RAW evidence, CLEAN versioning, seqscan EXPLAIN, perf p95, snapshot immutability, etc.)",
      "status": "skipped",
      "output_summary": "All 12 carry @skip_no_pg marker; require real PG/TimescaleDB"
    }
  ],
  "acceptance_criteria": [
    {
      "req_id": "REQ-CORE-001",
      "name": "DataItem metadata completeness (10 items, 9 fields)",
      "status": "blocked",
      "evidence": "EV-003",
      "note": "DDL + seeds present at code level; DB seed validation (SQL query non-null) requires real PG"
    },
    {
      "req_id": "REQ-CORE-002",
      "name": "Worker LOST / Lease recovery + terminal irreversibility",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-003",
      "name": "run_type unified enum + DB CHECK",
      "status": "blocked",
      "evidence": "EV-004",
      "note": "CHECK constraint present in migration DDL; runtime enforcement (INSERT rejected) requires real PG"
    },
    {
      "req_id": "REQ-CORE-004",
      "name": "Idempotency keys + force rerun",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-005",
      "name": "RAW batch evidence 5 fields + 7-hop chain",
      "status": "blocked",
      "evidence": "EV-004",
      "note": "Columns present in DDL; 7-hop query + p95<=3s requires real PG (5 tests skipped)"
    },
    {
      "req_id": "REQ-CORE-006",
      "name": "CLEAN 8 properties + is_current unique",
      "status": "blocked",
      "evidence": "EV-003",
      "note": "_published_at + partial unique index in DDL; version-interval + is_current test requires real PG (4 skipped)"
    },
    {
      "req_id": "REQ-CORE-007",
      "name": "Adjustment layering (no overwrite of raw)",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-008",
      "name": "Financial revision multi-version retention",
      "status": "blocked",
      "evidence": "EV-003",
      "note": "Tables + partial unique index in DDL; same-period-multi-version insert test requires real PG"
    },
    {
      "req_id": "REQ-CORE-009",
      "name": "available_at <= as_of_time backtest constraint",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-010",
      "name": "FAILED data publish block",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-011",
      "name": "WARNING publish policy",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-012",
      "name": "DataGap VERIFIED closure",
      "status": "blocked",
      "evidence": "EV-004",
      "note": "VERIFIED fields in DDL; state-machine VERIFIED enforcement test requires real PG (1 skipped)"
    },
    {
      "req_id": "REQ-CORE-013",
      "name": "lineage_edge table + recursive query p95<=3s",
      "status": "blocked",
      "evidence": "EV-002",
      "note": "Table + indexes in DDL; recursive query performance (p95<=3s) requires real PG (1 skipped)"
    },
    {
      "req_id": "REQ-CORE-014",
      "name": "AuditEvent 13-field logging",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-015",
      "name": "AuditEvent append-only",
      "status": "blocked",
      "evidence": "EV-004",
      "note": "Trigger in DDL; UPDATE/DELETE rejection runtime test requires real PG"
    },
    {
      "req_id": "REQ-CORE-016",
      "name": "DataContext does not read RAW",
      "status": "pass",
      "evidence": "EV-005"
    },
    {
      "req_id": "REQ-CORE-017",
      "name": "DataContext 5 query modes",
      "status": "blocked",
      "evidence": "EV-008",
      "note": "2 query tests pass; full-market no-seqscan requires real PG (1 skipped)"
    },
    {
      "req_id": "REQ-CORE-018",
      "name": "DataContext 6-frequency alignment",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-019",
      "name": "DataSnapshot immutable (READY)",
      "status": "blocked",
      "evidence": "EV-002",
      "note": "Trigger in DDL; READY immutability runtime test requires real PG (3 skipped)"
    },
    {
      "req_id": "REQ-CORE-020",
      "name": "DataSnapshot reproducible + query-consistent",
      "status": "blocked",
      "evidence": "EV-002",
      "note": "content_fingerprint in DDL; rebuild-same-fingerprint test requires real PG"
    },
    {
      "req_id": "REQ-CORE-021",
      "name": "Anti-lookahead 3 time modes",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-022",
      "name": "published_at / available_at separation",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-023",
      "name": "Historical pool + status point-in-time",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-024",
      "name": "Anti-lookahead test suite 100% pass",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-025",
      "name": "Unified query API 4 data types",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-026",
      "name": "Query result metadata",
      "status": "pass",
      "evidence": "EV-008"
    },
    {
      "req_id": "REQ-CORE-027",
      "name": "API no long-task + timeout 504",
      "status": "blocked",
      "evidence": "EV-008",
      "note": "1 timeout test passes; 504 runtime test requires real PG (1 skipped)"
    },
    {
      "req_id": "REQ-CORE-028",
      "name": "Ops query no seqscan on minute table",
      "status": "blocked",
      "evidence": "EV-008",
      "note": "EXPLAIN ANALYZE no-Seq-Scan requires real PG (3 skipped)"
    },
    {
      "req_id": "REQ-CORE-029",
      "name": "DB migration-disk script 6 phases",
      "status": "pass",
      "evidence": "EV-006"
    },
    {
      "req_id": "REQ-CORE-030",
      "name": "Minute compression/archive/checksum baseline",
      "status": "pass",
      "evidence": "EV-006"
    },
    {
      "req_id ": "REQ-CORE-031",
      "name": "server-test isolated environment",
      "status": "pass",
      "evidence": "EV-006"
    },
    {
      "req_id": "REQ-CORE-032",
      "name": "Full backup script + 4 attributes + off-server copy",
      "status": "pass",
      "evidence": "EV-006"
    },
    {
      "req_id": "REQ-CORE-033",
      "name": "Restore script + 3-verify + health check",
      "status": "pass",
      "evidence": "EV-006"
    },
    {
      "req_id": "REQ-CORE-034",
      "name": "10 test categories + real PG + coverage >=80%",
      "status": "blocked",
      "evidence": "EV-007",
      "note": "10 categories exist; HARD CONSTRAINT #2 requires ALL DB tests on real PG - 12 skipped violates this"
    },
    {
      "req_id": "REQ-CORE-035",
      "name": "E2E 10x8 matrix real-data acceptance",
      "status": "blocked",
      "evidence": "EV-008",
      "note": "80 E2E cases pass in mock/no-PG mode; REQ requires real PG/TimescaleDB per hard constraint"
    }
  ],
  "e2e_tests": [
    {
      "name": "Migration chain structural integrity (0012->0015)",
      "status": "pass",
      "evidence": "EV-001"
    },
    {
      "name": "DataContext RAW-isolation boundary",
      "status": "pass",
      "evidence": "EV-005"
    },
    {
      "name": "alembic upgrade head on real PostgreSQL",
      "status": "not_applicable",
      "evidence": "EV-012"
    },
    {
      "name": "DB-dependent integration tests (12 cases)",
      "status": "not_applicable",
      "evidence": "EV-013"
    },
    {
      "name": "Backup/restore drill on server-test",
      "status": "not_applicable",
      "evidence": "EV-013"
    }
  ],
  "side_effects": "No side effects. sf-verifier is read-only (permission.edit=deny); all verification used read-only grep/glob/read tools. No source files or governance artifacts were modified by the verifier. The changed_files_audit reports 0 unresolved violations (1 historical hard_stop_resolution resolved via prohibited_action_replaced).",
  "database_verification": {
    "status": "waiting_user_execution",
    "reason": "No PostgreSQL/TimescaleDB available in verifier environment. alembic upgrade head (0012->0015) requires real PostgreSQL 16 + TimescaleDB 2.28.3 in server-test (compose.test.yml, port 15432).",
    "blocking_migrations": [
      "0013_lineage_and_snapshot",
      "0014_clean_published_at_financial_dataitem",
      "0015_audit_runcheck_datagap_rawevidence"
    ]
  },
  "limitations": [
    {
      "id": "L1",
      "description": "No PostgreSQL/TimescaleDB: all DB-dependent tests properly skipped via @skip_no_pg. Requires server-test environment (compose.test.yml, port 15432). Violates REQ-CORE-034 hard constraint #2 until executed."
    },
    {
      "id": "L2",
      "description": "Python 3.13.12 vs required >=3.11,<3.12 (pyproject.toml): all tests pass on 3.13 but version mismatch exists."
    },
    {
      "id": "L3",
      "description": "psycopg2-binary==2.9.11 vs required psycopg[binary]>=3.2: ORM code compatible with both but production uses psycopg3."
    },
    {
      "id": "L4",
      "description": "sf_safe_bash broken on Windows host (chcp 65001 prefix with ';' invalid in cmd.exe): sf-verifier could not independently re-execute pytest; all L1/L2 static checks were performed independently via read-only tools."
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
      "actual_level": "L1",
      "status": "blocked",
      "command": "7-hop RAW chain query on real PG",
      "observed_result": "DDL columns present; query not executed (no PG)"
    },
    {
      "id": "EVREQ-CORE-013-3",
      "supports": [
        "REQ-CORE-013"
      ],
      "required_level": "L4",
      "actual_level": "L1",
      "status": "blocked",
      "command": "recursive lineage query p95<=3s",
      "observed_result": "Table+indexes present; perf not measured (no PG)"
    },
    {
      "id": "EVREQ-CORE-015-2",
      "supports": [
        "REQ-CORE-015"
      ],
      "required_level": "L3",
      "actual_level": "L1",
      "status": "blocked",
      "command": "UPDATE/DELETE audit_event rejection",
      "observed_result": "Trigger present in DDL; not runtime-tested (no PG)"
    },
    {
      "id": "EVREQ-CORE-028-2",
      "supports": [
        "REQ-CORE-028"
      ],
      "required_level": "L4",
      "actual_level": "L1",
      "status": "blocked",
      "command": "EXPLAIN ANALYZE no Seq Scan",
      "observed_result": "Not produced (no PG)"
    },
    {
      "id": "EVREQ-CORE-034-2",
      "supports": [
        "REQ-CORE-034"
      ],
      "required_level": "L4",
      "actual_level": "L2",
      "status": "blocked",
      "command": "ALL DB tests on real PG 16/TimescaleDB 2.28.3",
      "observed_result": "12 skipped; hard constraint violated"
    },
    {
      "id": "EVREQ-CORE-034-3",
      "supports": [
        "REQ-CORE-034"
      ],
      "required_level": "L3",
      "actual_level": "L1",
      "status": "blocked",
      "command": "alembic upgrade 0001->head + 0012->head",
      "observed_result": "WAITING_USER_EXECUTION; never run on real DB"
    }
  ],
  "missing_blocking_evidence": [
    "alembic upgrade head (0012->0015) execution log on real PostgreSQL 16",
    "alembic downgrade regression (0015->0014, 0014->0013) logs",
    "12 DB-dependent test cases execution on real PG/TimescaleDB (RAW evidence 7-hop, CLEAN versioning, DataGap VERIFIED enforcement, lineage recursive p95, API 504 timeout, ops EXPLAIN no-seqscan, snapshot READY immutability, perf p95, DataContext full-market, Alembic existing-upgrade)",
    "EXPLAIN ANALYZE evidence showing no Seq Scan on clean_stock_minute",
    "Lineage recursive-query p95<=3s performance measurement",
    "Backup/restore drill log on server-test (checksum reconciliation, 3-verify, /health 200)"
  ],
  "unblocking_path": "User must execute in server-test environment: (1) docker compose -f compose.test.yml up -d --wait; (2) alembic upgrade head; (3) python -m pytest tests/ -v (expect 0 skipped); (4) alembic downgrade 0014 && alembic upgrade head (regression); (5) backup/restore drill. Once 12 DB tests pass on real PG and alembic upgrade succeeds, re-run sf-verifier to flip conclusion from blocked to pass.",
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
