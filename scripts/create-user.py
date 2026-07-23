from __future__ import annotations

import argparse
import getpass
import secrets
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_config
from app.db import hash_password, initialize_database, open_connection, utc_now


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="创建或更新 TeamTools 登录账号")
    parser.add_argument("--username", required=True, help="登录账号")
    parser.add_argument("--display-name", required=True, help="页面展示名称")
    parser.add_argument("--role", choices=["admin", "user"], required=True, help="账号角色")
    parser.add_argument("--password", help="登录密码；不传时交互输入")
    parser.add_argument("--default-system-code", help="普通用户默认系统编码")
    parser.add_argument("--initial-password-seed", help="管理员重置密码使用的初始化密码来源；不传时使用本次登录密码")
    parser.add_argument("--update", action="store_true", help="账号已存在时更新密码、角色和展示名")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    password = args.password or getpass.getpass("请输入登录密码：")
    if len(password) < 8:
        print("密码至少 8 位", file=sys.stderr)
        return 2
    initial_password_seed = args.initial_password_seed or password

    config = get_config()
    initialize_database(config.db_path, seed_dev_users_enabled=False)
    now = utc_now()
    with open_connection(config.db_path) as conn:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (args.username,)).fetchone()
        if existing and not args.update:
            print("账号已存在；如需覆盖请增加 --update", file=sys.stderr)
            return 1
        if existing:
            conn.execute(
                """
                UPDATE users
                SET display_name = ?, password_hash = ?, role = ?, default_system_code = ?,
                    initial_password_seed = ?,
                    enabled = 1, updated_at = ?
                WHERE username = ?
                """,
                (
                    args.display_name,
                    hash_password(password),
                    args.role,
                    args.default_system_code,
                    initial_password_seed,
                    now,
                    args.username,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO users(id, username, display_name, password_hash, role,
                                  default_system_code, initial_password_seed, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    "user-" + secrets.token_hex(8),
                    args.username,
                    args.display_name,
                    hash_password(password),
                    args.role,
                    args.default_system_code,
                    initial_password_seed,
                    now,
                    now,
                ),
            )
        conn.commit()

    print(f"账号已就绪：{args.username} ({args.role})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
