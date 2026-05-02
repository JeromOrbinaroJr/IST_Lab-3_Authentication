from flask import Blueprint, render_template, session

from .db import get_db
from .security import login_required, roles_required

bp = Blueprint("views", __name__)


@bp.get("/")
@login_required
def index():
    return render_template(
        "index.html",
        user={
            "id": session.get("user_id"),
            "username": session.get("username"),
            "full_name": session.get("full_name"),
            "role": session.get("role"),
        },
    )


@bp.get("/admin/users")
@roles_required("admin")
def admin_users():
    db = get_db()
    users = db.execute(
        "SELECT id, username, full_name, role, is_active, created_at FROM users ORDER BY id"
    ).fetchall()
    return render_template("admin_users.html", users=users)

