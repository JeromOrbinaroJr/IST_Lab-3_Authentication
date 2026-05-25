from flask import Blueprint, redirect, url_for

from .security import login_required

bp = Blueprint("lp1_legacy", __name__, url_prefix="/lp1")


@bp.get("/")
@login_required
def lp1_root():
    return redirect(url_for("lp1.students_list"))


@bp.get("/students")
@login_required
def lp1_students():
    return redirect(url_for("lp1.students_list"))

