from __future__ import annotations

import json
import os
from collections import defaultdict
from copy import deepcopy

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from .security import roles_required

bp = Blueprint("faculty", __name__, url_prefix="/faculty")


DEFAULT_DEPARTMENTS = [
    {"id": 1, "name": "Прикладная математика", "abbr": "ПМ", "room": 305},
    {"id": 2, "name": "УИТС", "abbr": "УИТС", "room": 412},
]

DEFAULT_POSITIONS = [
    {"id": 1, "name": "Профессор", "category": "ППС"},
    {"id": 2, "name": "Доцент", "category": "ППС"},
    {"id": 3, "name": "Старший преподаватель", "category": "ППС"},
    {"id": 4, "name": "Ассистент", "category": "ППС"},
]

DEFAULT_TEACHERS = [
    {
        "id": 1,
        "last_name": "Бычков",
        "first_name": "Сергей",
        "middle_name": "Юрьевич",
        "degree": "к.т.н.",
        "email": "bychkov@example.edu",
        "department_id": 2,
        "position_id": 2,
    },
    {
        "id": 2,
        "last_name": "Подвигина",
        "first_name": "Елена",
        "middle_name": "Анатольевна",
        "degree": "к.т.н.",
        "email": "podvigina@example.edu",
        "department_id": 2,
        "position_id": 2,
    },
    {
        "id": 3,
        "last_name": "Ибатулин",
        "first_name": "Михаил",
        "middle_name": "Юрьевич",
        "degree": "к.т.н.",
        "email": "ibatulin@example.edu",
        "department_id": 2,
        "position_id": 3,
    },
    {
        "id": 4,
        "last_name": "Холщевникова",
        "first_name": "Наталья",
        "middle_name": "Николаевна",
        "degree": "к.ф.-м.н.",
        "email": "kholshchevnikova@example.edu",
        "department_id": 1,
        "position_id": 1,
    },
]

DEFAULT_DISCIPLINES = [
    {"id": 1, "name": "Базы данных - Бычков Сергей Юрьевич", "type": "лекции", "hours": 72, "department_id": 2},
    {"id": 2, "name": "Основы проектирования и разработки Web-приложений - Подвигина Елена Анатольевна", "type": "лабораторные", "hours": 72, "department_id": 2},
    {"id": 3, "name": "Машинное обучение и интеллектуальные системы - Ибатулин Михаил Юрьевич", "type": "практика", "hours": 72, "department_id": 2},
    {"id": 4, "name": "Функциональный анализ - Холщевникова Наталья Николаевна", "type": "лекции", "hours": 64, "department_id": 1},
]

DEFAULT_QUALIFICATIONS = [
    {"teacher_id": 1, "discipline_id": 1, "level": "ведущий преподаватель"},
    {"teacher_id": 2, "discipline_id": 2, "level": "ведущий преподаватель"},
    {"teacher_id": 3, "discipline_id": 3, "level": "ведущий преподаватель"},
    {"teacher_id": 4, "discipline_id": 4, "level": "ведущий преподаватель"},
]

DEFAULT_APPOINTMENTS = [
    {"teacher_id": 1, "position_id": 2, "date": "2025-09-01", "rate": 1.0},
    {"teacher_id": 2, "position_id": 2, "date": "2025-09-01", "rate": 1.0},
    {"teacher_id": 3, "position_id": 3, "date": "2025-02-01", "rate": 1.0},
    {"teacher_id": 4, "position_id": 1, "date": "2024-09-01", "rate": 1.0},
]

DEPARTMENTS = deepcopy(DEFAULT_DEPARTMENTS)
POSITIONS = deepcopy(DEFAULT_POSITIONS)
TEACHERS = deepcopy(DEFAULT_TEACHERS)
DISCIPLINES = deepcopy(DEFAULT_DISCIPLINES)
QUALIFICATIONS = deepcopy(DEFAULT_QUALIFICATIONS)
APPOINTMENTS = deepcopy(DEFAULT_APPOINTMENTS)


@bp.get("/")
@roles_required("admin", "dean", "curator", "teacher", "starosta", "student")
def index():
    _load_state()
    can_manage = session.get("role") in {"admin", "dean"}
    view_model = _build_view_model()

    return render_template(
        "faculty/index.html",
        **view_model,
        positions=POSITIONS,
        can_manage=can_manage,
    )


@bp.post("/admin")
@roles_required("admin", "dean")
def admin_update():
    _load_state()
    _update_departments()
    _update_disciplines()
    _update_teachers()
    _update_appointments()
    _save_state()
    flash("Учебный план обновлён.")
    return redirect(url_for("faculty.index"))


def _build_view_model():
    departments = {item["id"]: dict(item) for item in DEPARTMENTS}
    positions = {item["id"]: item for item in POSITIONS}
    disciplines = {item["id"]: item for item in DISCIPLINES}
    teacher_qualifications = defaultdict(list)
    teacher_load = defaultdict(int)

    for qualification in QUALIFICATIONS:
        discipline = disciplines[qualification["discipline_id"]]
        teacher_qualifications[qualification["teacher_id"]].append(
            {
                "discipline": discipline["name"],
                "level": qualification["level"],
                "hours": discipline["hours"],
                "type": discipline["type"],
                "department_id": discipline["department_id"],
            }
        )
        teacher_load[qualification["teacher_id"]] += int(discipline["hours"])

    appointment_by_teacher = {
        appointment["teacher_id"]: {
            **appointment,
            "position": positions[appointment["position_id"]]["name"],
        }
        for appointment in APPOINTMENTS
    }

    teachers = []
    for teacher in TEACHERS:
        department = departments[teacher["department_id"]]
        position = positions[teacher["position_id"]]
        full_name = f"{teacher['last_name']} {teacher['first_name']} {teacher['middle_name']}"
        enriched = {
            **teacher,
            "full_name": full_name,
            "initials": f"{teacher['first_name'][0]}{teacher['last_name'][0]}",
            "department": department,
            "position": position,
            "qualifications": teacher_qualifications[teacher["id"]],
            "load_hours": teacher_load[teacher["id"]],
            "appointment": appointment_by_teacher.get(teacher["id"]),
        }
        teachers.append(enriched)

    for department in departments.values():
        department_teachers = [item for item in teachers if item["department_id"] == department["id"]]
        department_disciplines = [item for item in DISCIPLINES if item["department_id"] == department["id"]]
        department["teachers"] = department_teachers
        department["disciplines"] = department_disciplines
        department["hours"] = sum(int(item["hours"]) for item in department_disciplines)

    stats = {
        "teachers": len(TEACHERS),
        "departments": len(DEPARTMENTS),
        "disciplines": len(DISCIPLINES),
        "hours": sum(int(item["hours"]) for item in DISCIPLINES),
    }

    return {
        "departments": list(departments.values()),
        "teachers": teachers,
        "appointments": appointment_by_teacher,
        "stats": stats,
    }


def _update_departments():
    for department in DEPARTMENTS:
        department_id = department["id"]
        name = _form_text(f"department_{department_id}_name", department["name"])
        abbr = _form_text(f"department_{department_id}_abbr", department["abbr"])
        room = request.form.get(f"department_{department_id}_room", type=int)
        department["name"] = name
        department["abbr"] = abbr
        department["room"] = room if room is not None else department["room"]


def _update_disciplines():
    valid_departments = {item["id"] for item in DEPARTMENTS}
    for discipline in DISCIPLINES:
        discipline_id = discipline["id"]
        department_id = request.form.get(f"discipline_{discipline_id}_department_id", type=int)
        hours = request.form.get(f"discipline_{discipline_id}_hours", type=int)
        discipline["name"] = _form_text(f"discipline_{discipline_id}_name", discipline["name"])
        discipline["type"] = _form_text(f"discipline_{discipline_id}_type", discipline["type"])
        discipline["hours"] = hours if hours is not None and hours > 0 else discipline["hours"]
        if department_id in valid_departments:
            discipline["department_id"] = department_id


def _update_teachers():
    valid_departments = {item["id"] for item in DEPARTMENTS}
    valid_positions = {item["id"] for item in POSITIONS}
    for teacher in TEACHERS:
        teacher_id = teacher["id"]
        department_id = request.form.get(f"teacher_{teacher_id}_department_id", type=int)
        position_id = request.form.get(f"teacher_{teacher_id}_position_id", type=int)
        teacher["last_name"] = _form_text(f"teacher_{teacher_id}_last_name", teacher["last_name"])
        teacher["first_name"] = _form_text(f"teacher_{teacher_id}_first_name", teacher["first_name"])
        teacher["middle_name"] = _form_text(f"teacher_{teacher_id}_middle_name", teacher["middle_name"])
        teacher["degree"] = _form_text(f"teacher_{teacher_id}_degree", teacher["degree"])
        teacher["email"] = _form_text(f"teacher_{teacher_id}_email", teacher["email"])
        if department_id in valid_departments:
            teacher["department_id"] = department_id
        if position_id in valid_positions:
            teacher["position_id"] = position_id


def _update_appointments():
    valid_positions = {item["id"] for item in POSITIONS}
    for appointment in APPOINTMENTS:
        teacher_id = appointment["teacher_id"]
        position_id = request.form.get(f"appointment_{teacher_id}_position_id", type=int)
        rate = request.form.get(f"appointment_{teacher_id}_rate", type=float)
        appointment["date"] = _form_text(f"appointment_{teacher_id}_date", appointment["date"])
        if position_id in valid_positions:
            appointment["position_id"] = position_id
        if rate is not None and rate > 0:
            appointment["rate"] = rate


def _form_text(name, fallback):
    value = (request.form.get(name) or "").strip()
    return value if value else fallback


def _state_path():
    return os.path.join(current_app.instance_path, "faculty_plan.json")


def _load_state():
    try:
        with open(_state_path(), "r", encoding="utf-8") as state_file:
            state = json.load(state_file)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    _replace_list(DEPARTMENTS, state.get("departments"), DEFAULT_DEPARTMENTS)
    _replace_list(POSITIONS, state.get("positions"), DEFAULT_POSITIONS)
    _replace_list(TEACHERS, state.get("teachers"), DEFAULT_TEACHERS)
    _replace_list(DISCIPLINES, state.get("disciplines"), DEFAULT_DISCIPLINES)
    _replace_list(QUALIFICATIONS, state.get("qualifications"), DEFAULT_QUALIFICATIONS)
    _replace_list(APPOINTMENTS, state.get("appointments"), DEFAULT_APPOINTMENTS)


def _save_state():
    os.makedirs(current_app.instance_path, exist_ok=True)
    state = {
        "departments": DEPARTMENTS,
        "positions": POSITIONS,
        "teachers": TEACHERS,
        "disciplines": DISCIPLINES,
        "qualifications": QUALIFICATIONS,
        "appointments": APPOINTMENTS,
    }
    with open(_state_path(), "w", encoding="utf-8") as state_file:
        json.dump(state, state_file, ensure_ascii=False, indent=2)


def _replace_list(target, saved, default):
    target.clear()
    target.extend(deepcopy(saved if isinstance(saved, list) else default))
