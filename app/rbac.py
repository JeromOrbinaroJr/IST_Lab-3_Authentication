"""
rbac.py — Иерархическое ролевое управление доступом (Часть 3, ЛР №3).

Иерархия ролей (каждая роль наследует права всех ролей ниже неё):
  student → starosta → teacher → curator → dean → admin
"""

import sqlite3
from functools import wraps
from flask import session, redirect, url_for, flash, abort, g

# Иерархия ролей (определяется один раз, хранится также в БД)
# Список от наименьших прав к наибольшим.
ROLE_HIERARCHY: list[str] = [
    "student",   # студент
    "starosta",  # староста
    "teacher",   # преподаватель
    "curator",   # куратор
    "dean",      # деканат
    "admin",     # администратор
]

ROLE_DISPLAY_NAMES: dict[str, str] = {
    "student":  "Студент",
    "starosta": "Староста",
    "teacher":  "Преподаватель",
    "curator":  "Куратор",
    "dean":     "Деканат",
    "admin":    "Администратор",
}

# Права доступа к объектам по ролям.
# Каждая роль наследует все права ролей ниже неё.
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "student":  ["view_schedule", "view_own_grades", "submit_request"],
    "starosta": ["view_group_list", "manage_attendance", "submit_group_request"],
    "teacher":  ["edit_grades", "view_all_students", "create_record"],
    "curator":  ["view_group_progress", "manage_group", "approve_request"],
    "dean":     ["manage_teachers", "view_reports", "approve_all"],
    "admin":    ["manage_users", "manage_roles", "full_access"],
}


# Функции работы с иерархией

def get_role_level(role: str) -> int:
    """Возвращает числовой уровень роли (0 = минимум прав)."""
    try:
        return ROLE_HIERARCHY.index(role)
    except ValueError:
        return -1


def get_inherited_roles(role: str) -> list[str]:
    """
    Возвращает список всех ролей, права которых унаследованы данной ролью
    (включая саму роль).

    Пример: get_inherited_roles("teacher") → ["student", "starosta", "teacher"]
    """
    level = get_role_level(role)
    if level < 0:
        return []
    return ROLE_HIERARCHY[: level + 1]


def get_all_permissions(role: str) -> list[str]:
    """
    Возвращает полный список прав пользователя с учётом наследования.
    """
    permissions: list[str] = []
    for r in get_inherited_roles(role):
        permissions.extend(ROLE_PERMISSIONS.get(r, []))
    return permissions


def has_role(user_role: str, required_role: str) -> bool:
    """
    Проверяет, обладает ли пользователь с ролью *user_role* правами роли
    *required_role* (напрямую или через наследование).

    Пример: has_role("teacher", "starosta") → True
             has_role("student", "teacher")  → False
    """
    user_level = get_role_level(user_role)
    required_level = get_role_level(required_role)
    if user_level < 0 or required_level < 0:
        return False
    return user_level >= required_level


def has_permission(user_role: str, permission: str) -> bool:
    """Проверяет наличие конкретного права у пользователя."""
    return permission in get_all_permissions(user_role)


# Декораторы Flask

def rbac_required(min_role: str):
    """
    Декоратор: доступ разрешён только пользователям с уровнем роли >= min_role.

    Пример:
        @app.route("/grades/edit")
        @rbac_required("teacher")
        def edit_grades(): ...
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Необходима авторизация.", "warning")
                return redirect(url_for("auth.login"))
            user_role = session.get("role", "")
            if not has_role(user_role, min_role):
                flash(
                    f"Недостаточно прав. Требуется роль: "
                    f"{ROLE_DISPLAY_NAMES.get(min_role, min_role)}.",
                    "danger",
                )
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def permission_required(permission: str):
    """
    Декоратор: доступ разрешён только пользователям, у которых есть
    конкретное право (с учётом наследования).
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Необходима авторизация.", "warning")
                return redirect(url_for("auth.login"))
            user_role = session.get("role", "")
            if not has_permission(user_role, permission):
                flash(f"Нет права: «{permission}».", "danger")
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


# Работа с БД

def init_role_tables(db: sqlite3.Connection) -> None:
    """Создаёт таблицы иерархии ролей, если они не существуют."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS roles (
            name         TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            level        INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS role_parents (
            role   TEXT NOT NULL REFERENCES roles(name),
            parent TEXT NOT NULL REFERENCES roles(name),
            PRIMARY KEY (role, parent)
        );

        CREATE TABLE IF NOT EXISTS role_permissions (
            role       TEXT NOT NULL REFERENCES roles(name),
            permission TEXT NOT NULL,
            PRIMARY KEY (role, permission)
        );
    """)
    db.commit()


def seed_role_tables(db: sqlite3.Connection) -> None:
    """Заполняет таблицы иерархии ролей начальными данными."""
    # Роли
    for level, name in enumerate(ROLE_HIERARCHY):
        db.execute(
            "INSERT OR IGNORE INTO roles (name, display_name, level) VALUES (?, ?, ?)",
            (name, ROLE_DISPLAY_NAMES[name], level),
        )

    # Отношения «дочерняя → родительская» (прямые связи, не транзитивные)
    for i in range(1, len(ROLE_HIERARCHY)):
        child  = ROLE_HIERARCHY[i]
        parent = ROLE_HIERARCHY[i - 1]
        db.execute(
            "INSERT OR IGNORE INTO role_parents (role, parent) VALUES (?, ?)",
            (child, parent),
        )

    # Права каждой роли (только «собственные», без учёта наследования)
    for role, perms in ROLE_PERMISSIONS.items():
        for perm in perms:
            db.execute(
                "INSERT OR IGNORE INTO role_permissions (role, permission) VALUES (?, ?)",
                (role, perm),
            )

    db.commit()


def get_hierarchy_from_db(db: sqlite3.Connection) -> list[dict]:
    """
    Возвращает список ролей из БД с информацией о родителе.
    Используется для отображения на странице администрирования.
    """
    rows = db.execute("""
        SELECT r.name, r.display_name, r.level,
               rp.parent AS parent_role
        FROM roles r
        LEFT JOIN role_parents rp ON r.name = rp.role
        ORDER BY r.level
    """).fetchall()
    return [dict(row) for row in rows]
