from flask import Blueprint, render_template, session, request, redirect, url_for, flash, abort
from .db import get_db
from .security import login_required
from .rbac import rbac_required

bp = Blueprint("programs", __name__)


def get_student_rating(db, user_id: int) -> int:
    row = db.execute(
        "SELECT COALESCE(SUM(score), 0) AS total FROM achievements WHERE student_user_id = ? AND status = 'approved'",
        (user_id,),
    ).fetchone()
    return int(row["total"]) if row else 0


def check_eligibility(program, course: int | None, rating: int) -> str:
    """
    Возвращает: 'eligible' | 'not_yet' | 'ineligible'
    """
    min_c = program["min_course"]
    max_c = program["max_course"]
    min_r = program["min_rating"]

    course_ok = True
    if min_c and course and course < min_c:
        course_ok = False
    if max_c and course and course > max_c:
            return "ineligible"  # превышен максимальный курс

    rating_ok = rating >= min_r

    if course_ok and rating_ok:
        return "eligible"
    if not course_ok:
        return "not_yet"
    return "ineligible"


@bp.get("/programs")
@login_required
def index():
    db        = get_db()
    user_id   = int(session.get("user_id"))
    user_role = session.get("role")

    type_filter = request.args.get("type_id", type=int)

    query  = """SELECT p.*, pt.name AS type_name, u.full_name AS author_name
                FROM programs p
                JOIN program_types pt ON p.type_id = pt.id
                JOIN users u ON p.created_by_user_id = u.id
                WHERE 1=1"""
    params = []
    if user_role in ("student", "starosta"):
        query += " AND p.is_active = 1"
    if type_filter:
        query += " AND p.type_id = ?"
        params.append(type_filter)
    query += " ORDER BY p.deadline"

    programs   = db.execute(query, params).fetchall()
    prog_types = db.execute("SELECT * FROM program_types ORDER BY name").fetchall()

    # Для студентов считаем eligibility
    eligibility = {}
    if user_role in ("student", "starosta"):
        user_row = db.execute(
            "SELECT course FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        course = user_row["course"] if user_row else None
        rating = get_student_rating(db, user_id)

        for p in programs:
            eligibility[p["id"]] = check_eligibility(p, course, rating)

    return render_template(
        "programs/index.html",
        programs=programs,
        prog_types=prog_types,
        eligibility=eligibility,
        type_filter=type_filter,
        user_role=user_role,
    )


@bp.get("/programs/new")
@login_required
@rbac_required("teacher")
def new():
    prog_types = get_db().execute(
        "SELECT * FROM program_types ORDER BY name"
    ).fetchall()
    return render_template("programs/form.html", program=None,
                           prog_types=prog_types, action="create")


@bp.post("/programs/new")
@login_required
@rbac_required("teacher")
def create():
    user_id     = int(session.get("user_id"))
    title       = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    requirements = request.form.get("requirements", "").strip()
    type_id     = request.form.get("type_id", type=int)
    min_course  = request.form.get("min_course", type=int)
    max_course  = request.form.get("max_course", type=int)
    min_rating  = request.form.get("min_rating", type=int, default=0)
    deadline    = request.form.get("deadline", "").strip() or None
    url         = request.form.get("url", "").strip()

    if not title or not type_id:
        flash("Заполните обязательные поля.", "warning")
        return redirect(url_for("programs.new"))

    db = get_db()
    db.execute(
        """INSERT INTO programs
           (type_id, title, description, requirements, min_course, max_course,
            min_rating, deadline, url, created_by_user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (type_id, title, description, requirements,
         min_course, max_course, min_rating, deadline, url, user_id),
    )
    db.commit()
    flash("Программа добавлена.", "success")
    return redirect(url_for("programs.index"))


@bp.get("/programs/<int:program_id>/edit")
@login_required
@rbac_required("teacher")
def edit(program_id: int):
    db        = get_db()
    program   = db.execute("SELECT * FROM programs WHERE id = ?", (program_id,)).fetchone()
    prog_types = db.execute("SELECT * FROM program_types ORDER BY name").fetchall()
    if not program:
        abort(404)
    return render_template("programs/form.html", program=program,
                           prog_types=prog_types, action="edit")


@bp.post("/programs/<int:program_id>/edit")
@login_required
@rbac_required("teacher")
def update(program_id: int):
    title        = request.form.get("title", "").strip()
    description  = request.form.get("description", "").strip()
    requirements = request.form.get("requirements", "").strip()
    type_id      = request.form.get("type_id", type=int)
    min_course   = request.form.get("min_course", type=int)
    max_course   = request.form.get("max_course", type=int)
    min_rating   = request.form.get("min_rating", type=int, default=0)
    deadline     = request.form.get("deadline", "").strip() or None
    url          = request.form.get("url", "").strip()
    is_active    = 1 if request.form.get("is_active") else 0

    if not title or not type_id:
        flash("Заполните обязательные поля.", "warning")
        return redirect(url_for("programs.edit", program_id=program_id))

    db = get_db()
    db.execute(
        """UPDATE programs SET type_id=?, title=?, description=?, requirements=?,
           min_course=?, max_course=?, min_rating=?, deadline=?, url=?, is_active=?
           WHERE id=?""",
        (type_id, title, description, requirements, min_course, max_course,
         min_rating, deadline, url, is_active, program_id),
    )
    db.commit()
    flash("Программа обновлена.", "success")
    return redirect(url_for("programs.index"))