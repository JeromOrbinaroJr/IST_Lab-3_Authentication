from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .security import login_required

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login():
    if session.get("user_id"):
        return redirect(url_for("views.index"))
    return render_template("login.html")


@bp.post("/login")
def login_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if not username or not password:
        flash("Введите логин и пароль.")
        return redirect(url_for("auth.login"))

    db = get_db()
    user = db.execute(
        "SELECT id, username, full_name, role, is_active, password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if user is None:
        flash("Неверный логин или пароль.")
        return redirect(url_for("auth.login"))

    if not user["is_active"]:
        flash("Пользователь отключён.")
        return redirect(url_for("auth.login"))

    if not check_password_hash(user["password_hash"], password):
        flash("Неверный логин или пароль.")
        return redirect(url_for("auth.login"))

    session.clear()
    session["user_id"] = int(user["id"])
    session["username"] = user["username"]
    session["full_name"] = user["full_name"]
    session["role"] = user["role"]
    return redirect(url_for("views.index"))


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.get("/me/password")
@login_required
def change_password():
    return render_template("change_password.html")


@bp.post("/me/password")
@login_required
def change_password_post():
    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    new_password2 = request.form.get("new_password2") or ""

    if not current_password or not new_password or not new_password2:
        flash("Заполните все поля.")
        return redirect(url_for("auth.change_password"))

    if new_password != new_password2:
        flash("Новый пароль и подтверждение не совпадают.")
        return redirect(url_for("auth.change_password"))

    db = get_db()
    user = db.execute(
        "SELECT id, password_hash FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if user is None:
        session.clear()
        flash("Сессия устарела. Войдите снова.")
        return redirect(url_for("auth.login"))

    if not check_password_hash(user["password_hash"], current_password):
        flash("Текущий пароль неверный.")
        return redirect(url_for("auth.change_password"))

    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), user["id"]),
    )
    db.commit()
    flash("Пароль обновлён.")
    return redirect(url_for("views.index"))

