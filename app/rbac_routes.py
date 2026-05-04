"""
rbac_routes.py — Blueprint для демонстрации иерархического RBAC (Часть 3).

Маршруты:
  GET  /rbac/                    — главная страница модуля, иерархия ролей
  GET  /rbac/hierarchy           — дерево ролей из БД
  GET  /rbac/demo                — интерактивная демонстрация наследования
  GET  /rbac/area/<min_role>     — страница, доступная только роли >= min_role
  GET  /rbac/my-permissions      — права текущего пользователя (с наследованием)
"""

from flask import (
    Blueprint, render_template, session, abort, flash, redirect, url_for, g
)
from .rbac import (
    rbac_required, get_inherited_roles, get_all_permissions,
    has_role, ROLE_HIERARCHY, ROLE_DISPLAY_NAMES, ROLE_PERMISSIONS,
    get_hierarchy_from_db,
)

bp = Blueprint("rbac", __name__, url_prefix="/rbac")


def get_db():
    """Возвращает соединение с БД из g (должно быть инициализировано в app)."""
    from flask import g
    import sqlite3, os
    if "db" not in g:
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "instance", "app.db"
        )
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


# Главная страница RBAC

@bp.route("/")
def index():
    """Обзор иерархии ролей и описание модуля."""
    hierarchy = []
    for name in ROLE_HIERARCHY:
        inherited = get_inherited_roles(name)
        all_perms = get_all_permissions(name)
        own_perms = ROLE_PERMISSIONS.get(name, [])
        hierarchy.append({
            "name":        name,
            "display":     ROLE_DISPLAY_NAMES[name],
            "inherited":   inherited,
            "own_perms":   own_perms,
            "all_perms":   all_perms,
        })
    return render_template("rbac/index.html", hierarchy=hierarchy)


# Дерево ролей из БД

@bp.route("/hierarchy")
def hierarchy():
    """Отображает иерархию ролей, прочитанную из БД."""
    db = get_db()
    roles = get_hierarchy_from_db(db)
    return render_template("rbac/hierarchy.html", roles=roles,
                           role_display=ROLE_DISPLAY_NAMES)


# Права текущего пользователя

@bp.route("/my-permissions")
def my_permissions():
    """Показывает все права авторизованного пользователя с учётом наследования."""
    if "user_id" not in session:
        flash("Войдите в систему.", "warning")
        return redirect(url_for("auth.login"))

    user_role   = session.get("role", "")
    inherited   = get_inherited_roles(user_role)
    all_perms   = get_all_permissions(user_role)
    breakdown   = {r: ROLE_PERMISSIONS.get(r, []) for r in inherited}

    return render_template(
        "rbac/my_permissions.html",
        user_role=user_role,
        user_display=ROLE_DISPLAY_NAMES.get(user_role, user_role),
        inherited=inherited,
        all_perms=all_perms,
        breakdown=breakdown,
        role_display=ROLE_DISPLAY_NAMES,
    )


# Защищённые зоны (демонстрация декоратора rbac_required)

AREA_DESCRIPTIONS = {
    "student":  "Личный кабинет студента — расписание, оценки, заявления.",
    "starosta": "Кабинет старосты — журнал посещаемости группы.",
    "teacher":  "Кабинет преподавателя — выставление оценок, записи.",
    "curator":  "Кабинет куратора — успеваемость группы, заявки.",
    "dean":     "Деканат — отчёты, управление преподавателями.",
    "admin":    "Администрирование — управление пользователями и ролями.",
}

@bp.route("/area/<min_role>")
def area(min_role: str):
    """
    Защищённая зона. Доступна пользователю, если его роль >= min_role.
    Демонстрирует работу декоратора rbac_required и наследование прав.
    """
    if min_role not in ROLE_HIERARCHY:
        abort(404)

    # Ручная проверка (без декоратора) — чтобы показать сообщение «403»
    # прямо в шаблоне, а не через abort, что нагляднее для лабораторной.
    if "user_id" not in session:
        flash("Для доступа необходима авторизация.", "warning")
        return redirect(url_for("auth.login"))

    user_role = session.get("role", "")
    allowed   = has_role(user_role, min_role)

    return render_template(
        "rbac/area.html",
        min_role=min_role,
        min_display=ROLE_DISPLAY_NAMES[min_role],
        description=AREA_DESCRIPTIONS[min_role],
        user_role=user_role,
        user_display=ROLE_DISPLAY_NAMES.get(user_role, user_role),
        allowed=allowed,
        all_areas=[
            (r, ROLE_DISPLAY_NAMES[r]) for r in ROLE_HIERARCHY
        ],
    )


# Пример маршрутов с декоратором (реальная защита)

@bp.route("/grades")
@rbac_required("teacher")
def grades():
    """Доступно только преподавателям и выше."""
    return render_template("rbac/protected.html",
                           title="Оценки",
                           required_role="teacher",
                           role_display=ROLE_DISPLAY_NAMES)


@bp.route("/reports")
@rbac_required("dean")
def reports():
    """Доступно только деканату и администраторам."""
    return render_template("rbac/protected.html",
                           title="Отчёты деканата",
                           required_role="dean",
                           role_display=ROLE_DISPLAY_NAMES)


@bp.route("/admin-panel")
@rbac_required("admin")
def admin_panel():
    """Только для администраторов."""
    return render_template("rbac/protected.html",
                           title="Панель администратора",
                           required_role="admin",
                           role_display=ROLE_DISPLAY_NAMES)
