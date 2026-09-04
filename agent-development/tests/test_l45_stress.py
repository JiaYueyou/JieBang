import argparse
import importlib.util
import sys
from pathlib import Path


def _load_stress_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "stress_l45.py"
    spec = importlib.util.spec_from_file_location("stress_l45", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


async def test_offline_stress_injects_real_provider_timeout_and_recovers(monkeypatch):
    module = _load_stress_module()
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "fyz-src" / "backend"))
    import app.providers.llm as llm_module

    async def no_backoff(_seconds):
        return None

    monkeypatch.setattr(llm_module.asyncio, "sleep", no_backoff)
    report = await module.run(argparse.Namespace(
        live=False,
        fail_every=2,
        concurrency=1,
        runs=6,
        timeout=1,
        max_attempts=3,
        min_success_rate=.98,
        min_quality_rate=.95,
        max_p95_ms=120000,
    ))

    assert report["accepted"] is True
    assert report["retried_runs"] > 0
    assert report["total_retries"] > 0
    assert report["success_rate"] == 1.0
