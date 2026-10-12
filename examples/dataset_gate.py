from pathlib import Path

from anrixa_audit import AuditRun, check_exists, check_minimum

DATASET = Path("dataset.jsonl")

run = AuditRun("dataset-qualification", metadata={"schema": "example"})
run.check("DATASET_EXISTS", check_exists(DATASET, kind="file"))
run.check("ROW_COVERAGE", check_minimum(0.995, 0.99))
run.require("SEALED_OVERLAP", actual=0, expected=0)

report = run.finalize()
print(report.render_text(), end="")
raise SystemExit(report.exit_code)
