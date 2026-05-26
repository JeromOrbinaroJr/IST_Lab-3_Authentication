from flask import Blueprint, render_template, session, request, flash
from .db import get_db
from .security import login_required
from datetime import date, datetime

bp = Blueprint("schedule", __name__)

DAYS = {1: "Понедельник", 2: "Вторник", 3: "Среда",
        4: "Четверг",     5: "Пятница", 6: "Суббота"}


@bp.get("/schedule")
@login_required
def index():
    db = get_db()
    user_role = session.get("role")
    user_id   = session.get("user_id")

    group_id   = None
    group_name = None
    all_groups = db.execute("SELECT id, name FROM groups ORDER BY name").fetchall()

    selected_day  = request.args.get("day", type=int)
    selected_date = request.args.get("date")        # строка вида "2025-03-10"
    date_error    = None

    # Если передана дата — вычислить день недели из неё
    if selected_date:
        try:
            dt = datetime.strptime(selected_date, "%Y-%m-%d").date()
            iso_day = dt.isoweekday()  # 1=Пн, 7=Вс
            if iso_day == 7:
                date_error = "Воскресенье — выходной день, занятий нет."
                selected_day = None
            else:
                selected_day = iso_day
        except ValueError:
            date_error = "Неверный формат даты."
            selected_date = None

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
                                   group_name=None, all_groups=[],
                                   user_role=user_role, selected_day=None,
                                   selected_date=None, date_error=None)
    else:
        gid_param = request.args.get("group_id", type=int)
        if gid_param:
            group_id = gid_param
            g = db.execute("SELECT name FROM groups WHERE id = ?", (group_id,)).fetchone()
            group_name = g["name"] if g else None

    schedule_by_day: dict = {}
    if group_id:
        query = """
            SELECT day, time_start, time_end, subject, teacher, room
            FROM schedule
            WHERE group_id = ?
        """
        params = [group_id]

        if selected_day:
            query += " AND day = ?"
            params.append(selected_day)

        query += " ORDER BY day, time_start"

        rows = db.execute(query, params).fetchall()
        for row in rows:
            schedule_by_day.setdefault(row["day"], []).append(dict(row))

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
        today=date.today().isoformat(),
    )