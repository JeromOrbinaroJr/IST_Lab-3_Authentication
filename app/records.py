from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from .db import get_db
from .security import (
    acl_edit_own_required,
    acl_read_own_required,
    acl_required,
    login_required,
)

bp = Blueprint("records", __name__, url_prefix="/records")


@bp.get("/")
@login_required
def list_records():
    db = get_db()
    role = session.get("role")
    user_id = int(session.get("user_id"))

    # Deans/admins can see everything (full), teachers can see everything for edit workflow,
    # students only see their own.
    if role in {"admin", "dean", "teacher"}:
        rows = db.execute(
            """
            SELECT r.id, r.owner_user_id, r.title, r.created_at, u.username AS owner_username
            FROM records r
            JOIN users u ON u.id = r.owner_user_id
            ORDER BY r.id DESC
            """
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT r.id, r.owner_user_id, r.title, r.created_at, u.username AS owner_username
            FROM records r
            JOIN users u ON u.id = r.owner_user_id
            WHERE r.owner_user_id = ?
            ORDER BY r.id DESC
            """,
            (user_id,),
        ).fetchall()

    return render_template("records_list.html", records=rows)


def _record_owner(record_id: int):
    db = get_db()
    row = db.execute(
        "SELECT owner_user_id FROM records WHERE id = ?",
        (record_id,),
    ).fetchone()
    if row is None:
        abort(404)
    return int(row["owner_user_id"])


@bp.get("/<int:record_id>")
@acl_read_own_required("records", owner_user_id_getter=_record_owner)
def view_record(record_id: int):
    db = get_db()
    row = db.execute(
        """
        SELECT r.id, r.owner_user_id, r.title, r.body, r.created_at, u.username AS owner_username
        FROM records r
        JOIN users u ON u.id = r.owner_user_id
        WHERE r.id = ?
        """,
        (record_id,),
    ).fetchone()
    if row is None:
        abort(404)
    return render_template("record_view.html", record=row)


@bp.get("/<int:record_id>/edit")
@acl_edit_own_required("records", owner_user_id_getter=_record_owner)
def edit_record(record_id: int):
    db = get_db()
    row = db.execute(
        "SELECT id, title, body FROM records WHERE id = ?",
        (record_id,),
    ).fetchone()
    if row is None:
        abort(404)
    return render_template("record_edit.html", record=row)


@bp.post("/<int:record_id>/edit")
@acl_edit_own_required("records", owner_user_id_getter=_record_owner)
def edit_record_post(record_id: int):
    title = (request.form.get("title") or "").strip()
    body = (request.form.get("body") or "").strip()
    if not title or not body:
        flash("Заполните заголовок и текст.")
        return redirect(url_for("records.edit_record", record_id=record_id))

    db = get_db()
    cur = db.execute(
        """
        UPDATE records
        SET title = ?, body = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (title, body, record_id),
    )
    if cur.rowcount == 0:
        abort(404)
    db.commit()
    flash("Запись обновлена.")
    return redirect(url_for("records.view_record", record_id=record_id))


@bp.post("/<int:record_id>/delete")
@acl_required("records", "full")
def delete_record(record_id: int):
    db = get_db()
    cur = db.execute("DELETE FROM records WHERE id = ?", (record_id,))
    if cur.rowcount == 0:
        abort(404)
    db.commit()
    flash("Запись удалена.")
    return redirect(url_for("records.list_records"))

