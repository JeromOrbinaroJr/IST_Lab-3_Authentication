from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .db import get_db
from .security import roles_required

bp = Blueprint("lp1", __name__, url_prefix="/students")


def _teacher_id_for_current_user(db):
    row = db.execute(
        "SELECT id FROM teachers WHERE user_id = ?",
        (session.get("user_id"),),
    ).fetchone()
    return row["id"] if row else None


@bp.get("/")
@roles_required("admin", "dean", "teacher")
def students_list():
    db = get_db()
    students = db.execute(
        """
        SELECT
          s.id,
          s.student_card_number,
          s.last_name,
          s.first_name,
          s.middle_name,
          g.name AS group_name,
          st.name AS status_name,
          (SELECT COUNT(*) FROM academic_debts d WHERE d.student_id = s.id AND d.status = 'активная') AS active_debts
        FROM students s
        JOIN student_groups g ON g.id = s.group_id
        JOIN academic_statuses st ON st.id = s.status_id
        ORDER BY s.last_name, s.first_name, s.id
        """
    ).fetchall()
    return render_template("lp1/students_list.html", students=students)


@bp.get("/new")
@roles_required("admin", "dean")
def students_new():
    db = get_db()
    groups = db.execute(
        "SELECT id, name, max_students, current_students FROM student_groups ORDER BY name"
    ).fetchall()
    statuses = db.execute("SELECT id, name FROM academic_statuses ORDER BY name").fetchall()
    return render_template("lp1/students_new.html", groups=groups, statuses=statuses)


@bp.post("/new")
@roles_required("admin", "dean")
def students_new_post():
    student_card_number = (request.form.get("student_card_number") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()
    first_name = (request.form.get("first_name") or "").strip()
    middle_name = (request.form.get("middle_name") or "").strip() or None
    group_id = request.form.get("group_id")
    status_id = request.form.get("status_id")

    if not student_card_number or not last_name or not first_name or not group_id or not status_id:
        flash("Заполните обязательные поля.")
        return redirect(url_for("lp1.students_new"))

    db = get_db()
    group = db.execute(
        "SELECT id, max_students, current_students FROM student_groups WHERE id = ?",
        (group_id,),
    ).fetchone()
    if not group:
        flash("Группа не найдена.")
        return redirect(url_for("lp1.students_new"))
    if int(group["current_students"]) >= int(group["max_students"]):
        flash("В выбранной группе достигнут лимит мест.")
        return redirect(url_for("lp1.students_new"))

    try:
        db.execute(
            """
            INSERT INTO students (student_card_number, last_name, first_name, middle_name, group_id, status_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (student_card_number, last_name, first_name, middle_name, group_id, status_id),
        )
        db.execute(
            "UPDATE student_groups SET current_students = current_students + 1 WHERE id = ?",
            (group_id,),
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось создать студента (проверьте уникальность номера билета).")
        return redirect(url_for("lp1.students_new"))

    flash("Студент добавлен.")
    return redirect(url_for("lp1.students_list"))


@bp.get("/<int:student_id>")
@roles_required("admin", "dean", "teacher")
def students_detail(student_id: int):
    db = get_db()
    student = db.execute(
        """
        SELECT
          s.*,
          g.name AS group_name,
          st.name AS status_name
        FROM students s
        JOIN student_groups g ON g.id = s.group_id
        JOIN academic_statuses st ON st.id = s.status_id
        WHERE s.id = ?
        """,
        (student_id,),
    ).fetchone()
    if not student:
        flash("Студент не найден.")
        return redirect(url_for("lp1.students_list"))

    transfers = db.execute(
        """
        SELECT
          th.id,
          th.transfer_date,
          th.basis,
          og.name AS old_group,
          ng.name AS new_group,
          u.full_name AS dean_name
        FROM transfer_history th
        JOIN student_groups og ON og.id = th.old_group_id
        JOIN student_groups ng ON ng.id = th.new_group_id
        LEFT JOIN users u ON u.id = th.dean_user_id
        WHERE th.student_id = ?
        ORDER BY th.id DESC
        """,
        (student_id,),
    ).fetchall()

    debts = db.execute(
        """
        SELECT
          d.id,
          d.debt_type,
          d.status,
          d.occurred_on,
          d.description,
          di.name AS discipline_name
        FROM academic_debts d
        JOIN disciplines di ON di.id = d.discipline_id
        WHERE d.student_id = ?
        ORDER BY d.id DESC
        """,
        (student_id,),
    ).fetchall()

    engagement = db.execute(
        """
        SELECT
          e.id,
          e.score,
          e.reason,
          e.created_at,
          di.name AS discipline_name,
          t.last_name || ' ' || t.first_name AS teacher_name
        FROM engagement_scores e
        JOIN disciplines di ON di.id = e.discipline_id
        JOIN teachers t ON t.id = e.teacher_id
        WHERE e.student_id = ?
        ORDER BY e.id DESC
        """,
        (student_id,),
    ).fetchall()

    return render_template(
        "lp1/students_detail.html",
        student=student,
        transfers=transfers,
        debts=debts,
        engagement=engagement,
    )


@bp.get("/<int:student_id>/transfer")
@roles_required("admin", "dean")
def students_transfer(student_id: int):
    db = get_db()
    student = db.execute(
        "SELECT id, group_id, last_name, first_name, middle_name FROM students WHERE id = ?",
        (student_id,),
    ).fetchone()
    if not student:
        flash("Студент не найден.")
        return redirect(url_for("lp1.students_list"))

    groups = db.execute(
        "SELECT id, name, max_students, current_students FROM student_groups ORDER BY name"
    ).fetchall()
    return render_template("lp1/students_transfer.html", student=student, groups=groups)


@bp.post("/<int:student_id>/transfer")
@roles_required("admin", "dean")
def students_transfer_post(student_id: int):
    new_group_id = request.form.get("new_group_id")
    basis = (request.form.get("basis") or "").strip()

    if not new_group_id or not basis:
        flash("Выберите новую группу и укажите основание.")
        return redirect(url_for("lp1.students_transfer", student_id=student_id))

    db = get_db()
    student = db.execute(
        "SELECT id, group_id FROM students WHERE id = ?",
        (student_id,),
    ).fetchone()
    if not student:
        flash("Студент не найден.")
        return redirect(url_for("lp1.students_list"))
    old_group_id = int(student["group_id"])
    if int(new_group_id) == old_group_id:
        flash("Новая группа совпадает со старой.")
        return redirect(url_for("lp1.students_transfer", student_id=student_id))

    active_debts = db.execute(
        "SELECT COUNT(*) AS cnt FROM academic_debts WHERE student_id = ? AND status = 'активная'",
        (student_id,),
    ).fetchone()["cnt"]
    if int(active_debts) > 0:
        flash("Нельзя перевести студента: есть активные академические задолженности.")
        return redirect(url_for("lp1.students_detail", student_id=student_id))

    new_group = db.execute(
        "SELECT id, max_students, current_students FROM student_groups WHERE id = ?",
        (new_group_id,),
    ).fetchone()
    if not new_group:
        flash("Новая группа не найдена.")
        return redirect(url_for("lp1.students_transfer", student_id=student_id))
    if int(new_group["current_students"]) >= int(new_group["max_students"]):
        flash("В выбранной группе достигнут лимит мест.")
        return redirect(url_for("lp1.students_transfer", student_id=student_id))

    try:
        db.execute(
            "UPDATE students SET group_id = ? WHERE id = ?",
            (new_group_id, student_id),
        )
        db.execute(
            "UPDATE student_groups SET current_students = current_students - 1 WHERE id = ?",
            (old_group_id,),
        )
        db.execute(
            "UPDATE student_groups SET current_students = current_students + 1 WHERE id = ?",
            (new_group_id,),
        )
        db.execute(
            """
            INSERT INTO transfer_history (student_id, old_group_id, new_group_id, basis, dean_user_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, old_group_id, new_group_id, basis, session.get("user_id")),
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось выполнить перевод.")
        return redirect(url_for("lp1.students_transfer", student_id=student_id))

    flash("Перевод выполнен.")
    return redirect(url_for("lp1.students_detail", student_id=student_id))


@bp.get("/<int:student_id>/debts/new")
@roles_required("admin", "dean")
def debt_new(student_id: int):
    if not student_id:
        return redirect(url_for("lp1.students_list"))
    db = get_db()
    student = db.execute(
        "SELECT id, last_name, first_name, middle_name FROM students WHERE id = ?",
        (student_id,),
    ).fetchone()
    if not student:
        flash("Студент не найден.")
        return redirect(url_for("lp1.students_list"))
    disciplines = db.execute("SELECT id, name FROM disciplines ORDER BY name").fetchall()
    return render_template("lp1/debt_new.html", student=student, disciplines=disciplines)


@bp.post("/<int:student_id>/debts/new")
@roles_required("admin", "dean")
def debt_new_post(student_id: int):
    # student_id comes from URL, keep form optional for reuse
    form_student_id = request.form.get("student_id", type=int)
    if form_student_id and form_student_id != student_id:
        flash("Некорректный студент.")
        return redirect(url_for("lp1.debt_new", student_id=student_id))
    discipline_id = request.form.get("discipline_id")
    debt_type = (request.form.get("debt_type") or "").strip()
    description = (request.form.get("description") or "").strip() or None
    occurred_on = (request.form.get("occurred_on") or "").strip()
    if not occurred_on:
        occurred_on = date.today().isoformat()

    if not discipline_id or not debt_type:
        flash("Заполните обязательные поля.")
        return redirect(url_for("lp1.debt_new", student_id=student_id))

    db = get_db()
    db.execute(
        """
        INSERT INTO academic_debts (student_id, discipline_id, debt_type, description, occurred_on)
        VALUES (?, ?, ?, ?, ?)
        """,
        (student_id, discipline_id, debt_type, description, occurred_on),
    )
    db.commit()
    flash("Задолженность добавлена.")
    return redirect(url_for("lp1.students_detail", student_id=student_id))


@bp.post("/debts/<int:debt_id>/close")
@roles_required("admin", "dean")
def debt_close(debt_id: int):
    db = get_db()
    debt = db.execute(
        "SELECT id, student_id FROM academic_debts WHERE id = ?",
        (debt_id,),
    ).fetchone()
    if not debt:
        flash("Задолженность не найдена.")
        return redirect(url_for("lp1.students_list"))
    db.execute("UPDATE academic_debts SET status = 'погашенная' WHERE id = ?", (debt_id,))
    db.commit()
    flash("Задолженность погашена.")
    return redirect(url_for("lp1.students_detail", student_id=debt["student_id"]))


@bp.get("/<int:student_id>/engagement/new")
@roles_required("teacher")
def engagement_new(student_id: int):
    if not student_id:
        return redirect(url_for("lp1.students_list"))

    db = get_db()
    student = db.execute(
        "SELECT id, last_name, first_name, middle_name FROM students WHERE id = ?",
        (student_id,),
    ).fetchone()
    if not student:
        flash("Студент не найден.")
        return redirect(url_for("lp1.students_list"))

    teacher_id = _teacher_id_for_current_user(db)
    if not teacher_id:
        flash("Для вашего пользователя не настроен профиль преподавателя.")
        return redirect(url_for("lp1.students_detail", student_id=student_id))

    disciplines = db.execute(
        "SELECT id, name FROM disciplines WHERE teacher_id = ? ORDER BY name",
        (teacher_id,),
    ).fetchall()
    return render_template("lp1/engagement_new.html", student=student, disciplines=disciplines)


@bp.post("/<int:student_id>/engagement/new")
@roles_required("teacher")
def engagement_new_post(student_id: int):
    form_student_id = request.form.get("student_id", type=int)
    if form_student_id and form_student_id != student_id:
        flash("Некорректный студент.")
        return redirect(url_for("lp1.engagement_new", student_id=student_id))
    discipline_id = request.form.get("discipline_id")
    score = request.form.get("score", type=int)
    reason = (request.form.get("reason") or "").strip() or None

    if not discipline_id or not score:
        flash("Заполните обязательные поля.")
        return redirect(url_for("lp1.engagement_new", student_id=student_id))

    db = get_db()
    teacher_id = _teacher_id_for_current_user(db)
    if not teacher_id:
        flash("Для вашего пользователя не настроен профиль преподавателя.")
        return redirect(url_for("lp1.students_detail", student_id=student_id))

    ok = db.execute(
        "SELECT 1 FROM disciplines WHERE id = ? AND teacher_id = ?",
        (discipline_id, teacher_id),
    ).fetchone()
    if not ok:
        flash("Нельзя поставить оценку по чужой дисциплине.")
        return redirect(url_for("lp1.students_detail", student_id=student_id))

    if score < 1 or score > 10:
        flash("Оценка должна быть от 1 до 10.")
        return redirect(url_for("lp1.engagement_new", student_id=student_id))

    db.execute(
        """
        INSERT INTO engagement_scores (student_id, discipline_id, teacher_id, score, reason)
        VALUES (?, ?, ?, ?, ?)
        """,
        (student_id, discipline_id, teacher_id, score, reason),
    )
    db.commit()
    flash("Оценка вовлеченности добавлена.")
    return redirect(url_for("lp1.students_detail", student_id=student_id))
