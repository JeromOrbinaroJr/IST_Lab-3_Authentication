from flask import Blueprint, render_template, session, request, redirect, url_for, flash, abort
from .db import get_db
from .security import login_required
from .rbac import rbac_required

bp = Blueprint("events", __name__)


@bp.get("/events")
@login_required
def index():
    db        = get_db()
    user_role = session.get("role")
    show_all  = request.args.get("all") == "1" and user_role in ("teacher", "admin")

    if show_all:
        events = db.execute(
            """SELECT e.*, u.full_name AS author_name
               FROM events e JOIN users u ON e.created_by_user_id = u.id
               ORDER BY e.event_date""",
        ).fetchall()
    else:
        events = db.execute(
            """SELECT e.*, u.full_name AS author_name
               FROM events e JOIN users u ON e.created_by_user_id = u.id
               WHERE e.is_active = 1
               ORDER BY e.event_date""",
        ).fetchall()

    return render_template("events/index.html", events=events,
                           user_role=user_role, show_all=show_all)


@bp.get("/events/new")
@login_required
@rbac_required("teacher")
def new():
    return render_template("events/form.html", event=None, action="create")


@bp.post("/events/new")
@login_required
@rbac_required("teacher")
def create():
    user_id     = int(session.get("user_id"))
    title       = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    event_date  = request.form.get("event_date", "").strip()
    location    = request.form.get("location", "").strip()

    if not title or not event_date:
        flash("Заполните обязательные поля.", "warning")
        return redirect(url_for("events.new"))

    db = get_db()
    db.execute(
        """INSERT INTO events (title, description, event_date, location, created_by_user_id)
           VALUES (?, ?, ?, ?, ?)""",
        (title, description, event_date, location, user_id),
    )
    db.commit()
    flash("Мероприятие добавлено.", "success")
    return redirect(url_for("events.index"))


@bp.get("/events/<int:event_id>/edit")
@login_required
@rbac_required("teacher")
def edit(event_id: int):
    event = get_db().execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)
    ).fetchone()
    if not event:
        abort(404)
    return render_template("events/form.html", event=event, action="edit")


@bp.post("/events/<int:event_id>/edit")
@login_required
@rbac_required("teacher")
def update(event_id: int):
    title       = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    event_date  = request.form.get("event_date", "").strip()
    location    = request.form.get("location", "").strip()
    is_active   = 1 if request.form.get("is_active") else 0

    if not title or not event_date:
        flash("Заполните обязательные поля.", "warning")
        return redirect(url_for("events.edit", event_id=event_id))

    db = get_db()
    db.execute(
        """UPDATE events SET title=?, description=?, event_date=?,
           location=?, is_active=? WHERE id=?""",
        (title, description, event_date, location, is_active, event_id),
    )
    db.commit()
    flash("Мероприятие обновлено.", "success")
    return redirect(url_for("events.index"))