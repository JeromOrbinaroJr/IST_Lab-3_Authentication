from flask import Blueprint, render_template, session, request, redirect, url_for, flash, abort
from .db import get_db
from .security import login_required
from .rbac import rbac_required
from datetime import date as date_type

bp = Blueprint("notes", __name__)


def get_note_or_404(note_id: int, user_id: int):
    note = get_db().execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?",
        (note_id, user_id),
    ).fetchone()
    if note is None:
        abort(404)
    return note


# ── Список заметок ────────────────────────────────────────────────────────────

@bp.get("/notes")
@login_required
@rbac_required("student")
def index():
    db = get_db()
    user_id      = int(session.get("user_id"))
    selected_date = request.args.get("date")

    query  = "SELECT * FROM notes WHERE user_id = ?"
    params = [user_id]
    if selected_date:
        query += " AND date = ?"
        params.append(selected_date)
    query += " ORDER BY date, created_at"

    notes = db.execute(query, params).fetchall()

    return render_template(
        "notes/index.html",
        notes=notes,
        selected_date=selected_date,
        today=date_type.today().isoformat(),
    )


# ── Создать заметку ───────────────────────────────────────────────────────────

@bp.get("/notes/new")
@login_required
@rbac_required("student")
def new():
    selected_date = request.args.get("date", date_type.today().isoformat())
    return render_template("notes/form.html", note=None,
                           selected_date=selected_date, action="create")


@bp.post("/notes/new")
@login_required
@rbac_required("student")
def create():
    user_id = int(session.get("user_id"))
    note_date = request.form.get("date", "").strip()
    title     = request.form.get("title", "").strip()
    body      = request.form.get("body", "").strip()

    if not note_date:
        flash("Выберите дату.", "warning")
        return redirect(url_for("notes.new"))
    if not body:
        flash("Текст заметки не может быть пустым.", "warning")
        return redirect(url_for("notes.new", date=note_date))

    db = get_db()
    db.execute(
        "INSERT INTO notes (user_id, date, title, body) VALUES (?, ?, ?, ?)",
        (user_id, note_date, title, body),
    )
    db.commit()
    flash("Заметка создана.", "success")
    return redirect(url_for("notes.index", date=note_date))


# ── Редактировать заметку ─────────────────────────────────────────────────────

@bp.get("/notes/<int:note_id>/edit")
@login_required
@rbac_required("student")
def edit(note_id: int):
    note = get_note_or_404(note_id, int(session.get("user_id")))
    return render_template("notes/form.html", note=note,
                           selected_date=note["date"], action="edit")


@bp.post("/notes/<int:note_id>/edit")
@login_required
@rbac_required("student")
def update(note_id: int):
    user_id = int(session.get("user_id"))
    note    = get_note_or_404(note_id, user_id)

    note_date = request.form.get("date", "").strip()
    title     = request.form.get("title", "").strip()
    body      = request.form.get("body", "").strip()

    if not note_date:
        flash("Выберите дату.", "warning")
        return redirect(url_for("notes.edit", note_id=note_id))
    if not body:
        flash("Текст заметки не может быть пустым.", "warning")
        return redirect(url_for("notes.edit", note_id=note_id))

    db = get_db()
    db.execute(
        """UPDATE notes SET date = ?, title = ?, body = ?,
           updated_at = datetime('now') WHERE id = ?""",
        (note_date, title, body, note_id),
    )
    db.commit()
    flash("Заметка обновлена.", "success")
    return redirect(url_for("notes.index", date=note_date))


# ── Удалить заметку ───────────────────────────────────────────────────────────

@bp.post("/notes/<int:note_id>/delete")
@login_required
@rbac_required("student")
def delete(note_id: int):
    user_id = int(session.get("user_id"))
    note    = get_note_or_404(note_id, user_id)
    note_date = note["date"]

    get_db().execute("DELETE FROM notes WHERE id = ?", (note_id,))
    get_db().commit()
    flash("Заметка удалена.", "success")
    return redirect(url_for("notes.index", date=note_date))