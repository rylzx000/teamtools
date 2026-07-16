from __future__ import annotations

from datetime import datetime, timezone

from .config import get_config
from .db import initialize_database


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_worker() -> None:
    config = get_config()
    initialize_database(config.db_path, seed_dev_users_enabled=config.seed_dev_users)
    print(
        "[worker] browser-ai-call MVP mode: "
        f"not claiming waiting_ai_call tasks | db={config.db_path} | at={_utc_now()}"
    )
    print("[worker] exit; browser handles DeepSeek calls in current MVP")


if __name__ == "__main__":
    run_worker()
