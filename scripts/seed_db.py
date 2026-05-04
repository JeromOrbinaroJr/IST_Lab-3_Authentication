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


def upsert_acl(con, *, subject_type, subject_value, object_type, action):
    con.execute(
        """
        INSERT INTO acl (subject_type, subject_value, object_type, action)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(subject_type, subject_value, object_type, action) DO NOTHING
        """,
        (subject_type, subject_value, object_type, action),
    )


def seed_records(con):
    # Example protected objects. We'll attach them to existing users by username.
    users = {
        row["username"]: int(row["id"])
        for row in con.execute("SELECT id, username FROM users").fetchall()
    }
    for username, title, body in [
        ("student1", "Заявление студента", "Это запись принадлежит student1."),
        ("teacher1", "Заметки преподавателя", "Это запись принадлежит teacher1."),
    ]:
        owner_id = users.get(username)
        if owner_id is None:
            continue
        con.execute(
            """
            INSERT INTO records (owner_user_id, title, body)
            VALUES (?, ?, ?)
            """,
            (owner_id, title, body),
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
        con.row_factory = sqlite3.Row
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

        # ACL for object_type = "records"
        # Example from the assignment:
        # - преподаватель -> edit
        # - студент -> read own
        # - деканат -> full
        upsert_acl(
            con,
            subject_type="role",
            subject_value="teacher",
            object_type="records",
            action="edit",
        )
        upsert_acl(
            con,
            subject_type="role",
            subject_value="student",
            object_type="records",
            action="read_own",
        )
        upsert_acl(
            con,
            subject_type="role",
            subject_value="student",
            object_type="records",
            action="edit_own",
        )
        upsert_acl(
            con,
            subject_type="role",
            subject_value="dean",
            object_type="records",
            action="full",
        )

        # Keep admin powerful for administration/demo.
        upsert_acl(
            con,
            subject_type="role",
            subject_value="admin",
            object_type="records",
            action="full",
        )

        seed_records(con)
        con.commit()
    finally:
        con.close()

    print("OK: seeded users + ACL + sample records (admin/dean/teacher/student)")


if __name__ == "__main__":
    main()

