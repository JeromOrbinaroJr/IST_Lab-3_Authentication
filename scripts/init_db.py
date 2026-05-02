import os
import sqlite3


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    instance_dir = os.path.join(repo_root, "instance")
    os.makedirs(instance_dir, exist_ok=True)

    db_path = os.path.join(instance_dir, "app.db")
    schema_path = os.path.join(repo_root, "app", "schema.sql")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    con = sqlite3.connect(db_path)
    try:
        con.executescript(schema_sql)
        con.commit()
    finally:
        con.close()

    print(f"OK: initialized {db_path}")


if __name__ == "__main__":
    main()

