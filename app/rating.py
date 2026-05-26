from flask import Blueprint, render_template, session, request
from .db import get_db
from .security import login_required
from .rbac import rbac_required

bp = Blueprint("rating", __name__)


@bp.get("/rating")
@login_required
@rbac_required("student")
def index():
    db        = get_db()
    user_id   = int(session.get("user_id"))
    user_role = session.get("role")

    if user_role in ("student", "starosta"):
        # Личный рейтинг + место в группе
        user_row = db.execute(
            "SELECT group_id, course FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        group_id = user_row["group_id"] if user_row else None

        my_score = db.execute(
            """SELECT COALESCE(SUM(score), 0) AS total
               FROM achievements WHERE student_user_id = ? AND status = 'approved'""",
            (user_id,),
        ).fetchone()["total"]

        my_achievements = db.execute(
            """SELECT a.*, ac.name AS category_name
               FROM achievements a
               JOIN achievement_categories ac ON a.category_id = ac.id
               WHERE a.student_user_id = ? AND a.status = 'approved'
               ORDER BY a.score DESC""",
            (user_id,),
        ).fetchall()

        # Рейтинг группы
        group_rating = []
        if group_id:
            group_rating = db.execute(
                """SELECT u.full_name, u.id AS uid,
                          COALESCE(SUM(a.score), 0) AS total_score
                   FROM users u
                   LEFT JOIN achievements a ON a.student_user_id = u.id
                                           AND a.status = 'approved'
                   WHERE u.group_id = ? AND u.role IN ('student', 'starosta')
                   GROUP BY u.id
                   ORDER BY total_score DESC""",
                (group_id,),
            ).fetchall()

        return render_template(
            "rating/index.html",
            my_score=my_score,
            my_achievements=my_achievements,
            group_rating=group_rating,
            user_id=user_id,
            user_role=user_role,
        )

    # Преподаватель/admin — общий рейтинг всех студентов
    all_rating = db.execute(
        """SELECT u.full_name, u.course, g.name AS group_name,
                  COALESCE(SUM(a.score), 0) AS total_score
           FROM users u
           LEFT JOIN achievements a ON a.student_user_id = u.id
                                   AND a.status = 'approved'
           LEFT JOIN groups g ON u.group_id = g.id
           WHERE u.role IN ('student', 'starosta')
           GROUP BY u.id
           ORDER BY total_score DESC""",
    ).fetchall()

    return render_template(
        "rating/index.html",
        all_rating=all_rating,
        user_role=user_role,
    )