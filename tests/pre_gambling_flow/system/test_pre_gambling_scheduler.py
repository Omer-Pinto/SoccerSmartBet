from __future__ import annotations

import sys
from pathlib import Path

import pytest
from apscheduler.triggers.cron import CronTrigger

# Ensure tests import THIS worktree's `src/` package (src-layout) even if another
# editable install exists elsewhere on the machine.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from soccersmartbet.pre_gambling_flow.scheduler import DEFAULT_JOB_ID, build_scheduler, load_config


def _trigger_field_expressions(trigger: CronTrigger, field_name: str) -> list[str]:
    for field in trigger.fields:
        if field.name == field_name:
            return [str(expr) for expr in field.expressions]
    raise AssertionError(f"CronTrigger missing expected field: {field_name}")


def test_load_config_loads_yaml_from_path(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
scheduler:
  enabled: true
  timezone: UTC
  daily_time: "14:00"
""".lstrip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert isinstance(config, dict)
    assert "scheduler" in config
    assert config["scheduler"]["enabled"] is True
    assert config["scheduler"]["timezone"] == "UTC"
    assert config["scheduler"]["daily_time"] == "14:00"


def test_build_scheduler_registers_one_cron_job() -> None:
    config: dict = {
        "scheduler": {
            "enabled": True,
            "timezone": "UTC",
            "daily_time": "09:30",
        }
    }

    def job_func() -> None:
        return None

    scheduler = build_scheduler(config, job_func)
    try:
        jobs = scheduler.get_jobs()
        assert len(jobs) == 1

        job = jobs[0]
        assert job.id == DEFAULT_JOB_ID
        assert isinstance(job.trigger, CronTrigger)

        trigger: CronTrigger = job.trigger
        assert getattr(trigger.timezone, "key", str(trigger.timezone)) == "UTC"
        assert _trigger_field_expressions(trigger, "hour") == ["9"]
        assert _trigger_field_expressions(trigger, "minute") == ["30"]
    finally:
        # Defensive shutdown: scheduler isn't started in this test.
        # APScheduler raises if shutdown() is called while not running.
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_build_scheduler_rejects_non_bool_enabled() -> None:
    with pytest.raises(ValueError, match=r"scheduler\.enabled"):
        build_scheduler({"scheduler": {"enabled": "false"}}, lambda: None)
