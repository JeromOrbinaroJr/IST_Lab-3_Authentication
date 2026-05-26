from flask import Blueprint, render_template, session, request, redirect, url_for, flash, abort
from .db import get_db
from .security import login_required
from .rbac import rbac_required
from datetime import date as date_type

bp = Blueprint("notes", __name__)


def get_user_group_id(user_id: int) -> int | None:
    row = get_db().execute(
        "SELECT group_id FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return row["group_id"] if row else None


def get_note_or_404(note_id: int, user_id: int):
    """Возвращает заметку только если она принадлежит пользователю."""
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
    db           = get_db()
    user_id      = int(session.get("user_id"))
    user_role    = session.get("role")
    selected_date = request.args.get("date")

    # Личные заметки
    query  = "SELECT * FROM notes WHERE user_id = ? AND is_group_note = 0"
    params = [user_id]
    if selected_date:
        query += " AND date = ?"
        params.append(selected_date)
    query += " ORDER BY date, created_at"
    personal_notes = db.execute(query, params).fetchall()

    # Групповые заметки (видны студентам и старосте своей группы)
    group_notes = []
    group_id = get_user_group_id(user_id)
    if group_id:
        query  = "SELECT n.*, u.full_name AS author_name FROM notes n JOIN users u ON n.user_id = u.id WHERE n.is_group_note = 1 AND n.group_id = ?"
        params = [group_id]
        if selected_date:
            query += " AND n.date = ?"
            params.append(selected_date)
        query += " ORDER BY n.date, n.created_at"
        group_notes = db.execute(query, params).fetchall()

    return render_template(
        "notes/index.html",
        personal_notes=personal_notes,
        group_notes=group_notes,
        selected_date=selected_date,
        today=date_type.today().isoformat(),
        user_role=user_role,
    )


# ── Создать заметку ───────────────────────────────────────────────────────────

@bp.get("/notes/new")
@login_required
@rbac_required("student")
def new():
    selected_date = request.args.get("date", date_type.today().isoformat())
    is_group      = request.args.get("group", "0") == "1"
    user_role     = session.get("role")
    return render_template("notes/form.html", note=None,
                           selected_date=selected_date, action="create",
                           is_group=is_group, user_role=user_role)


@bp.post("/notes/new")
@login_required
@rbac_required("student")
def create():
    user_id   = int(session.get("user_id"))
    user_role = session.get("role")
    note_date = request.form.get("date", "").strip()
    title     = request.form.get("title", "").strip()
    body      = request.form.get("body", "").strip()
    is_group  = request.form.get("is_group_note") == "1"

    if not note_date:
        flash("Выберите дату.", "warning")
        return redirect(url_for("notes.new"))
    if not body:
        flash("Текст заметки не может быть пустым.", "warning")
        return redirect(url_for("notes.new", date=note_date))

    # Групповую заметку может создать только староста
    group_id = None
    if is_group:
        if user_role != "starosta":
            abort(403)
        group_id = get_user_group_id(user_id)
        if not group_id:
            flash("Вы не привязаны к группе.", "warning")
            return redirect(url_for("notes.new", date=note_date))

    db = get_db()
    db.execute(
        """INSERT INTO notes (user_id, date, title, body, is_group_note, group_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, note_date, title, body, 1 if is_group else 0, group_id),
    )
    db.commit()
    flash("Заметка создана.", "success")
    return redirect(url_for("notes.index", date=note_date))


# ── Редактировать заметку ─────────────────────────────────────────────────────

@bp.get("/notes/<int:note_id>/edit")
@login_required
@rbac_required("student")
def edit(note_id: int):
    note      = get_note_or_404(note_id, int(session.get("user_id")))
    user_role = session.get("role")
    return render_template("notes/form.html", note=note,
                           selected_date=note["date"], action="edit",
                           is_group=bool(note["is_group_note"]),
                           user_role=user_role)


@bp.post("/notes/<int:note_id>/edit")
@login_required
@rbac_required("student")
def update(note_id: int):
    user_id   = int(session.get("user_id"))
    user_role = session.get("role")
    note      = get_note_or_404(note_id, user_id)

    note_date = request.form.get("date", "").strip()
    title     = request.form.get("title", "").strip()
    body      = request.form.get("body", "").strip()
    is_group  = request.form.get("is_group_note") == "1"

    if not note_date:
        flash("Выберите дату.", "warning")
        return redirect(url_for("notes.edit", note_id=note_id))
    if not body:
        flash("Текст заметки не может быть пустым.", "warning")
        return redirect(url_for("notes.edit", note_id=note_id))

    group_id = note["group_id"]
    if is_group and user_role != "starosta":
        abort(403)
    if is_group and not group_id:
        group_id = get_user_group_id(user_id)

    db = get_db()
    db.execute(
        """UPDATE notes SET date = ?, title = ?, body = ?, is_group_note = ?,
           group_id = ?, updated_at = datetime('now') WHERE id = ?""",
        (note_date, title, body, 1 if is_group else 0, group_id, note_id),
    )
    db.commit()
    flash("Заметка обновлена.", "success")
    return redirect(url_for("notes.index", date=note_date))


# ── Удалить заметку ───────────────────────────────────────────────────────────

@bp.post("/notes/<int:note_id>/delete")
@login_required
@rbac_required("student")
def delete(note_id: int):
    user_id   = int(session.get("user_id"))
    note      = get_note_or_404(note_id, user_id)
    note_date = note["date"]

    db = get_db()
    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    flash("Заметка удалена.", "success")
    return redirect(url_for("notes.index", date=note_date))