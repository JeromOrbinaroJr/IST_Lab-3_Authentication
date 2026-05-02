import os
import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        db_path = os.path.join(current_app.instance_path, current_app.config["DATABASE"])
        os.makedirs(current_app.instance_path, exist_ok=True)
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    pass

