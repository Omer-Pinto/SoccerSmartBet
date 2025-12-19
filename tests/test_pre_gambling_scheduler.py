from __future__ import annotations

import sys
from pathlib import Path

# Ensure tests import THIS worktree's `src/` package (src-layout) even if another
# editable install exists elsewhere on the machine.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from apscheduler.triggers.cron import CronTrigger

from soccersmartbet.pre_gambling_flow.scheduler import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_JOB_ID,
    build_scheduler,
    load_config,
)


def _trigger_field_expressions(trigger: CronTrigger, field_name: str) -> list[str]:
    for field in trigger.fields:
        if field.name == field_name:
            return [str(expr) for expr in field.expressions]
    raise AssertionError(f"CronTrigger missing expected field: {field_name}")


def test_load_config_loads_repo_yaml() -> None:
    config = load_config(DEFAULT_CONFIG_PATH)

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

    jobs = scheduler.get_jobs()
    assert len(jobs) == 1

    job = jobs[0]
    assert job.id == DEFAULT_JOB_ID
    assert isinstance(job.trigger, CronTrigger)

    trigger: CronTrigger = job.trigger
    assert getattr(trigger.timezone, "key", str(trigger.timezone)) == "UTC"
    assert _trigger_field_expressions(trigger, "hour") in (["9"], ["09"])
    assert _trigger_field_expressions(trigger, "minute") == ["30"]
