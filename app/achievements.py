from flask import Blueprint, render_template, session, request, redirect, url_for, flash, abort
from .db import get_db
from .security import login_required
from .rbac import rbac_required

bp = Blueprint("achievements", __name__)


@bp.get("/achievements")
@login_required
@rbac_required("student")
def index():
    db        = get_db()
    user_id   = int(session.get("user_id"))
    user_role = session.get("role")

    if user_role in ("student", "starosta"):
        achievements = db.execute(
            """SELECT a.*, ac.name AS category_name
               FROM achievements a
               JOIN achievement_categories ac ON a.category_id = ac.id
               WHERE a.student_user_id = ?
               ORDER BY a.created_at DESC""",
            (user_id,),
        ).fetchall()
    else:
        # Преподаватель/admin — видят все
        status_filter = request.args.get("status", "pending")
        achievements = db.execute(
            """SELECT a.*, ac.name AS category_name,
                      u.full_name AS student_name
               FROM achievements a
               JOIN achievement_categories ac ON a.category_id = ac.id
               JOIN users u ON a.student_user_id = u.id
               WHERE a.status = ?
               ORDER BY a.created_at""",
            (status_filter,),
        ).fetchall()

    categories = db.execute(
        "SELECT * FROM achievement_categories ORDER BY name"
    ).fetchall()

    return render_template(
        "achievements/index.html",
        achievements=achievements,
        categories=categories,
        user_role=user_role,
        status_filter=request.args.get("status", "pending"),
    )


@bp.get("/achievements/new")
@login_required
@rbac_required("student")
def new():
    db = get_db()
    categories = db.execute(
        "SELECT * FROM achievement_categories ORDER BY name"
    ).fetchall()
    return render_template("achievements/form.html", categories=categories)


@bp.post("/achievements/new")
@login_required
@rbac_required("student")
def create():
    user_id     = int(session.get("user_id"))
    category_id = request.form.get("category_id", type=int)
    title       = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not category_id or not title:
        flash("Заполните обязательные поля.", "warning")
        return redirect(url_for("achievements.new"))

    db = get_db()
    db.execute(
        """INSERT INTO achievements (student_user_id, category_id, title, description)
           VALUES (?, ?, ?, ?)""",
        (user_id, category_id, title, description),
    )
    db.commit()
    flash("Достижение отправлено на проверку.", "success")
    return redirect(url_for("achievements.index"))


@bp.get("/achievements/<int:achievement_id>")
@login_required
def detail(achievement_id: int):
    db        = get_db()
    user_id   = int(session.get("user_id"))
    user_role = session.get("role")

    a = db.execute(
        """SELECT a.*, ac.name AS category_name, u.full_name AS student_name
           FROM achievements a
           JOIN achievement_categories ac ON a.category_id = ac.id
           JOIN users u ON a.student_user_id = u.id
           WHERE a.id = ?""",
        (achievement_id,),
    ).fetchone()
    if not a:
        abort(404)

    # Студент видит только своё
    if user_role in ("student", "starosta") and a["student_user_id"] != user_id:
        abort(403)

    return render_template("achievements/detail.html", a=a, user_role=user_role)


@bp.post("/achievements/<int:achievement_id>/review")
@login_required
@rbac_required("teacher")
def review(achievement_id: int):
    reviewer_id = int(session.get("user_id"))
    action      = request.form.get("action")  # "approve" | "reject"
    score       = request.form.get("score", type=int, default=0)
    comment     = request.form.get("comment", "").strip()

    if action not in ("approve", "reject"):
        abort(400)

    status = "approved" if action == "approve" else "rejected"

    db = get_db()
    db.execute(
        """UPDATE achievements
           SET status = ?, score = ?, reviewer_user_id = ?,
               reviewer_comment = ?, reviewed_at = datetime('now')
           WHERE id = ?""",
        (status, score if status == "approved" else 0,
         reviewer_id, comment, achievement_id),
    )
    db.commit()
    flash(f"Достижение {'одобрено' if status == 'approved' else 'отклонено'}.", "success")
    return redirect(url_for("achievements.index"))