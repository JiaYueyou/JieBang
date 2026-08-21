"""Regression tests for safe snapshot transport repair."""

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "02_import_mysql_snapshot.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("import_mysql_snapshot", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_repairs_only_redacted_embedding_fraction_literals():
    statement = (
        "INSERT INTO `retrieval_index_entry` (`embedding`) VALUES "
        "('[0.[已脱敏证件], -0.[已脱敏证件], 0.25]');"
    )
    repaired, count = MODULE.repair_redacted_embedding_literals(statement)
    assert repaired.endswith("('[0.0, -0.0, 0.25]');")
    assert count == 2


def test_does_not_rewrite_non_embedding_statements():
    statement = "INSERT INTO `resume` (`text`) VALUES ('0.[已脱敏证件]');"
    assert MODULE.repair_redacted_embedding_literals(statement) == (statement, 0)
