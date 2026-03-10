"""
数据库迁移脚本 — SQLite ALTER TABLE

用法：
    cd backend
    python -m db.migrate
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"[migrate] 数据库文件不存在: {DB_PATH}，跳过迁移")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    migrations = [
        ("questions", "user_answer", "ALTER TABLE questions ADD COLUMN user_answer TEXT"),
        ("questions", "updated_at", "ALTER TABLE questions ADD COLUMN updated_at DATETIME"),
        ("questions", "review_status", "ALTER TABLE questions ADD COLUMN review_status VARCHAR(10) DEFAULT '待复习'"),
    ]

    applied = 0
    for table, column, sql in migrations:
        if _column_exists(cursor, table, column):
            print(f"[migrate] {table}.{column} 已存在，跳过")
        else:
            cursor.execute(sql)
            applied += 1
            print(f"[migrate] 已添加 {table}.{column}")

    conn.commit()
    conn.close()
    print(f"[migrate] 迁移完成，应用 {applied} 项变更")


if __name__ == "__main__":
    migrate()
