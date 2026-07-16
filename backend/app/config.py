from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    data_dir: Path
    db_path: Path
    frontend_dist_dir: Path
    log_level: str
    worker_idle_seconds: int
    worker_once: bool
    seed_dev_users: bool


def _default_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    project_root = _default_project_root()
    data_dir = Path(os.getenv("TEAMTOOLS_DATA_DIR", project_root / "data")).expanduser()
    db_path = Path(os.getenv("TEAMTOOLS_DB_PATH", data_dir / "teamtools.db")).expanduser()
    frontend_dist_dir = Path(
        os.getenv("TEAMTOOLS_FRONTEND_DIST", project_root / "frontend" / "dist")
    ).expanduser()
    log_level = os.getenv("TEAMTOOLS_LOG_LEVEL", "INFO")
    worker_idle_seconds = int(os.getenv("TEAMTOOLS_WORKER_IDLE_SECONDS", "3"))
    worker_once = os.getenv("TEAMTOOLS_WORKER_ONCE", "false").lower() in {"1", "true", "yes"}
    seed_dev_users = os.getenv("TEAMTOOLS_SEED_DEV_USERS", "false").lower() in {"1", "true", "yes"}

    return AppConfig(
        project_root=project_root,
        data_dir=data_dir,
        db_path=db_path,
        frontend_dist_dir=frontend_dist_dir,
        log_level=log_level,
        worker_idle_seconds=worker_idle_seconds,
        worker_once=worker_once,
        seed_dev_users=seed_dev_users,
    )
