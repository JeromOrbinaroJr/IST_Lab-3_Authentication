from flask import Blueprint, render_template, session, request, flash, redirect, url_for
from .db import get_db
from .security import login_required
from datetime import date, datetime, timedelta

bp = Blueprint("schedule", __name__)

DAYS = {1: "Понедельник", 2: "Вторник", 3: "Среда",
        4: "Четверг",     5: "Пятница", 6: "Суббота"}


def get_week_dates(anchor: date) -> dict[int, str]:
    """Возвращает {1: '2026-05-25', 2: '2026-05-26', ...} для недели anchor."""
    monday = anchor - timedelta(days=anchor.isoweekday() - 1)
    return {
        day_num: (monday + timedelta(days=day_num - 1)).isoformat()
        for day_num in range(1, 7)
    }


@bp.get("/schedule")
@login_required
def index():
    if not request.args.get("date") and not request.args.get("day"):
        return redirect(url_for("schedule.index", date=date.today().isoformat()))

    db = get_db()
    user_role = session.get("role")
    user_id   = session.get("user_id")

    group_id   = None
    group_name = None
    all_groups = db.execute("SELECT id, name FROM groups ORDER BY name").fetchall()

    selected_day  = request.args.get("day", type=int)
    selected_date = request.args.get("date")
    date_error    = None
    anchor        = date.today()

    if selected_date:
        try:
            dt = datetime.strptime(selected_date, "%Y-%m-%d").date()
            anchor = dt
            iso_day = dt.isoweekday()
            if iso_day == 7:
                date_error = "Воскресенье — выходной день, занятий нет."
                selected_day = None
            else:
                selected_day = iso_day
        except ValueError:
            date_error = "Неверный формат даты."
            selected_date = None

    # Даты каждого дня недели для текущей недели anchor
    week_dates = get_week_dates(anchor)

    if user_role in ("student", "starosta"):
        row = db.execute(
            "SELECT group_id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        group_id = row["group_id"] if row else None
        if group_id:
            g = db.execute("SELECT name FROM groups WHERE id = ?", (group_id,)).fetchone()
            group_name = g["name"] if g else None
        if not group_id:
            flash("Вы не привязаны ни к одной группе. Обратитесь к администратору.", "warning")
            return render_template("schedule.html", days=DAYS, schedule={},
                                   group_name=None, all_groups=[], notes_by_date={},
                                   user_role=user_role, selected_day=None,
                                   selected_date=None, date_error=None,
                                   week_dates=week_dates)
    else:
        gid_param = request.args.get("group_id", type=int)
        if gid_param:
            group_id = gid_param
            g = db.execute("SELECT name FROM groups WHERE id = ?", (group_id,)).fetchone()
            group_name = g["name"] if g else None

    schedule_by_day: dict = {}
    if group_id:
        query  = "SELECT day, time_start, time_end, subject, teacher, room FROM schedule WHERE group_id = ?"
        params = [group_id]
        if selected_day:
            query += " AND day = ?"
            params.append(selected_day)
        query += " ORDER BY day, time_start"
        for row in db.execute(query, params).fetchall():
            schedule_by_day.setdefault(row["day"], []).append(dict(row))

    notes_by_date: dict = {}
    if selected_date and user_role in ("student", "starosta") and not date_error:
        rows = db.execute(
            "SELECT * FROM notes WHERE user_id = ? AND date = ? ORDER BY created_at",
            (user_id, selected_date),
        ).fetchall()
        if rows:
            notes_by_date[selected_date] = [dict(r) for r in rows]

    return render_template(
        "schedule.html",
        days=DAYS,
        schedule=schedule_by_day,
        group_name=group_name,
        group_id=group_id,
        all_groups=all_groups,
        user_role=user_role,
        selected_day=selected_day,
        selected_date=selected_date,
        date_error=date_error,
        notes_by_date=notes_by_date,
        week_dates=week_dates,
    )