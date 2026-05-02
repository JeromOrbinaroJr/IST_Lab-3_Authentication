import os
import sqlite3

from werkzeug.security import generate_password_hash


def upsert_user(con, *, username, full_name, role, password, is_active=True):
    password_hash = generate_password_hash(password)
    con.execute(
        """
        INSERT INTO users (username, full_name, role, password_hash, is_active)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
          full_name = excluded.full_name,
          role = excluded.role,
          password_hash = excluded.password_hash,
          is_active = excluded.is_active,
          updated_at = datetime('now')
        """,
        (username, full_name, role, password_hash, 1 if is_active else 0),
    )


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    db_path = os.path.join(repo_root, "instance", "app.db")
    if not os.path.exists(db_path):
        raise SystemExit(
            f"DB not found: {db_path}\nRun: python scripts\\init_db.py"
        )

    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys = ON;")
        upsert_user(
            con,
            username="admin",
            full_name="Администратор",
            role="admin",
            password="admin123",
        )
        upsert_user(
            con,
            username="dean1",
            full_name="Сотрудник деканата",
            role="dean",
            password="dean123",
        )
        upsert_user(
            con,
            username="teacher1",
            full_name="Преподаватель",
            role="teacher",
            password="teacher123",
        )
        upsert_user(
            con,
            username="student1",
            full_name="Студент",
            role="student",
            password="student123",
        )
        con.commit()
    finally:
        con.close()

    print("OK: seeded users (admin/dean/teacher/student)")


if __name__ == "__main__":
    main()

