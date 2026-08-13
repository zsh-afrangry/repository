"""Read-only dashboard metrics sourced from the local repository."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _git_output(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_REPOSITORY_ROOT,
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise HTTPException(status_code=503, detail="当前环境无法读取 Git 提交记录。") from error
    return result.stdout.strip()


@router.get("/git-stats/")
def get_git_stats():
    month_start = date.today().replace(day=1).isoformat()
    return {
        "month_commits": int(_git_output("rev-list", "--count", f"--since={month_start} 00:00:00", "HEAD") or 0),
        "total_commits": int(_git_output("rev-list", "--count", "HEAD") or 0),
        "month_start": month_start,
    }
