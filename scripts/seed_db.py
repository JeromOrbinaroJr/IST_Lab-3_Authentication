import os
import sqlite3

from werkzeug.security import generate_password_hash

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.rbac import init_role_tables, seed_role_tables


def upsert_user(con, *, username, full_name, role, password, is_active=True, group_id=None, course=None):
    password_hash = generate_password_hash(password)
    con.execute(
        """
        INSERT INTO users (username, full_name, role, password_hash, is_active, group_id, course)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
          full_name = excluded.full_name,
          role = excluded.role,
          password_hash = excluded.password_hash,
          is_active = excluded.is_active,
          group_id = excluded.group_id,
          course = excluded.course,
          updated_at = datetime('now')
        """,
        (username, full_name, role, password_hash, 1 if is_active else 0, group_id, course),
    )


def upsert_acl(con, *, subject_type, subject_value, object_type, action):
    con.execute(
        """
        INSERT INTO acl (subject_type, subject_value, object_type, action)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(subject_type, subject_value, object_type, action) DO NOTHING
        """,
        (subject_type, subject_value, object_type, action),
    )


def seed_records(con):
    users = {
        row["username"]: int(row["id"])
        for row in con.execute("SELECT id, username FROM users").fetchall()
    }
    for username, title, body in [
        ("student1",  "Заявление студента",     "Это запись принадлежит student1."),
        ("teacher1",  "Заметки преподавателя",  "Это запись принадлежит teacher1."),
        ("starosta1", "Список посещаемости",    "Это запись принадлежит starosta1."),
    ]:
        owner_id = users.get(username)
        if owner_id is None:
            continue
        con.execute(
            "INSERT INTO records (owner_user_id, title, body) VALUES (?, ?, ?)",
            (owner_id, title, body),
        )


def upsert_status(con, *, name, description=None):
    con.execute(
        """
        INSERT INTO academic_statuses (name, description)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET description = excluded.description
        """,
        (name, description),
    )


def upsert_group(con, *, name, max_students):
    con.execute(
        """
        INSERT INTO student_groups (name, max_students)
        VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET max_students = excluded.max_students
        """,
        (name, max_students),
    )


def upsert_teacher(con, *, user_id, last_name, first_name, middle_name, degree, position, email):
    con.execute(
        """
        INSERT INTO teachers (user_id, last_name, first_name, middle_name, degree, position, email)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
          user_id = excluded.user_id,
          last_name = excluded.last_name,
          first_name = excluded.first_name,
          middle_name = excluded.middle_name,
          degree = excluded.degree,
          position = excluded.position
        """,
        (user_id, last_name, first_name, middle_name, degree, position, email),
    )


def upsert_discipline(con, *, name, is_advanced, teacher_id):
    con.execute(
        """
        INSERT INTO disciplines (name, is_advanced, teacher_id)
        VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
          is_advanced = excluded.is_advanced,
          teacher_id = excluded.teacher_id
        """,
        (name, 1 if is_advanced else 0, teacher_id),
    )


def upsert_student(con, *, student_card_number, last_name, first_name, middle_name, group_id, status_id):
    con.execute(
        """
        INSERT INTO students (student_card_number, last_name, first_name, middle_name, group_id, status_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_card_number) DO UPDATE SET
          last_name = excluded.last_name,
          first_name = excluded.first_name,
          middle_name = excluded.middle_name,
          group_id = excluded.group_id,
          status_id = excluded.status_id
        """,
        (student_card_number, last_name, first_name, middle_name, group_id, status_id),
    )


def recompute_group_counts(con):
    con.execute("UPDATE student_groups SET current_students = 0")
    con.execute(
        """
        UPDATE student_groups
        SET current_students = (
          SELECT COUNT(*) FROM students s WHERE s.group_id = student_groups.id
        )
        """
    )


def upsert_schedule_group(con, *, name):
    con.execute(
        """
        INSERT INTO groups (name)
        VALUES (?)
        ON CONFLICT(name) DO NOTHING
        """,
        (name,),
    )


def insert_lesson(con, *, group_id, day, time_start, time_end, subject, teacher, room=""):
    con.execute(
        """
        INSERT INTO schedule (group_id, day, time_start, time_end, subject, teacher, room)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (group_id, day, time_start, time_end, subject, teacher, room),
    )


def seed_schedule(con):
    upsert_schedule_group(con, name="ИС-21")
    upsert_schedule_group(con, name="ИС-22")

    schedule_groups = {
        row["name"]: int(row["id"])
        for row in con.execute("SELECT id, name FROM groups").fetchall()
    }

    lessons = [
        # group,   day, start,  end,     subject,                  teacher,           room
        ("ИС-21",  1, "09:00", "10:30", "Математический анализ",  "Иванов И.И.",     "А-101"),
        ("ИС-21",  1, "10:45", "12:15", "Базы данных",            "Петров П.П.",     "Б-205"),
        ("ИС-21",  1, "13:00", "14:30", "Информационные системы", "Сидорова О.В.",   "В-312"),
        ("ИС-21",  2, "09:00", "10:30", "Английский язык",        "Смирнова А.Н.",   "Д-11"),
        ("ИС-21",  2, "10:45", "12:15", "Физкультура",            "Козлов М.С.",     "Спортзал"),
        ("ИС-21",  3, "09:00", "10:30", "Базы данных",            "Петров П.П.",     "Б-205"),
        ("ИС-21",  3, "10:45", "12:15", "Математический анализ",  "Иванов И.И.",     "А-101"),
        ("ИС-21",  3, "13:00", "14:30", "Физика",                 "Новиков Д.А.",    "А-203"),
        ("ИС-21",  4, "09:00", "10:30", "Информационные системы", "Сидорова О.В.",   "В-312"),
        ("ИС-21",  4, "10:45", "12:15", "Английский язык",        "Смирнова А.Н.",   "Д-11"),
        ("ИС-21",  5, "09:00", "10:30", "Физика",                 "Новиков Д.А.",    "А-203"),
        ("ИС-21",  5, "10:45", "12:15", "Физкультура",            "Козлов М.С.",     "Спортзал"),
        ("ИС-22",  1, "09:00", "10:30", "Линейная алгебра",       "Фёдоров С.Н.",    "А-102"),
        ("ИС-22",  1, "10:45", "12:15", "Программирование",       "Белова Т.И.",     "Компьютерный зал"),
        ("ИС-22",  2, "09:00", "10:30", "Программирование",       "Белова Т.И.",     "Компьютерный зал"),
        ("ИС-22",  2, "10:45", "12:15", "Линейная алгебра",       "Фёдоров С.Н.",    "А-102"),
        ("ИС-22",  3, "09:00", "10:30", "История",                "Орлова М.В.",     "Г-15"),
        ("ИС-22",  3, "10:45", "12:15", "Физкультура",            "Козлов М.С.",     "Спортзал"),
        ("ИС-22",  4, "09:00", "10:30", "История",                "Орлова М.В.",     "Г-15"),
        ("ИС-22",  4, "10:45", "12:15", "Программирование",       "Белова Т.И.",     "Компьютерный зал"),
        ("ИС-22",  5, "09:00", "10:30", "Линейная алгебра",       "Фёдоров С.Н.",    "А-102"),
        ("ИС-22",  5, "10:45", "12:15", "Английский язык",        "Смирнова А.Н.",   "Д-11"),
    ]

    for group_name, day, ts, te, subj, teacher, room in lessons:
        g_id = schedule_groups.get(group_name)
        if g_id is None:
            continue
        insert_lesson(con, group_id=g_id, day=day, time_start=ts,
                      time_end=te, subject=subj, teacher=teacher, room=room)

    # Привязать пользователей к группам
    con.execute(
        "UPDATE users SET group_id = (SELECT id FROM groups WHERE name = 'ИС-21') WHERE username = 'student1'"
    )
    con.execute(
        "UPDATE users SET group_id = (SELECT id FROM groups WHERE name = 'ИС-21') WHERE username = 'starosta1'"
    )


def seed_achievements_meta(con):
    for name, score in [
        ("Олимпиада",       10),
        ("Конференция",      5),
        ("Спорт",            3),
        ("Волонтёрство",     2),
        ("Творчество",       2),
        ("Сертификат/курс",  1),
        ("Прочее",           1),
    ]:
        con.execute(
            "INSERT OR IGNORE INTO achievement_categories (name, base_score) VALUES (?, ?)",
            (name, score),
        )

    for name in ["Университетская", "Федеральная", "Частный фонд / Благотворительность"]:
        con.execute(
            "INSERT OR IGNORE INTO program_types (name) VALUES (?)", (name,)
        )


def seed_events(con, created_by_user_id):
    for title, description, event_date, location in [
        ("Студенческая олимпиада по ИТ",
         "Межвузовская олимпиада по информационным технологиям.",
         "2026-06-10", "Главный корпус, ауд. 301"),
        ("Конференция молодых учёных",
         "Ежегодная научно-практическая конференция.",
         "2026-06-20", "Актовый зал"),
        ("Волонтёрская акция «Чистый город»",
         "Городская экологическая акция.",
         "2026-05-30", "Площадь у главного корпуса"),
    ]:
        con.execute(
            """INSERT INTO events (title, description, event_date, location, created_by_user_id)
               VALUES (?, ?, ?, ?, ?)""",
            (title, description, event_date, location, created_by_user_id),
        )


def seed_programs(con, created_by_user_id):
    type_ids = {
        row["name"]: row["id"]
        for row in con.execute("SELECT id, name FROM program_types").fetchall()
    }
    for title, type_name, description, requirements, min_course, max_course, min_rating, deadline, url in [
        ("Повышенная академическая стипендия",
         "Университетская",
         "Стипендия для студентов с высокими академическими результатами.",
         "Средний балл не ниже 4.5, отсутствие задолженностей.",
         1, 6, 20, "2026-09-15", ""),
        ("Стипендия Президента РФ",
         "Федеральная",
         "Государственная стипендия для выдающихся студентов.",
         "Не ниже 3 курса, победитель олимпиад или конференций.",
         3, 6, 30, "2026-10-01", "https://grants.extech.ru"),
        ("Грант фонда «Потенциал»",
         "Частный фонд / Благотворительность",
         "Поддержка студентов, занимающихся научной деятельностью.",
         "Не ниже 2 курса, публикация или участие в конференции.",
         2, 6, 10, "2026-08-01", ""),
    ]:
        con.execute(
            """INSERT INTO programs
               (type_id, title, description, requirements, min_course, max_course,
                min_rating, deadline, url, created_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (type_ids[type_name], title, description, requirements,
             min_course, max_course, min_rating, deadline, url, created_by_user_id),
        )


def seed_extra_users(con):
    # Получаем id групп заранее
    groups = {
        row["name"]: row["id"]
        for row in con.execute("SELECT id, name FROM groups").fetchall()
    }
    is21 = groups.get("ИС-21")
    is22 = groups.get("ИС-22")

    extra_users = [
        # username,      full_name,                    role,       password,       group_id, course
        ("student2",  "Морозова Екатерина Дмитриевна", "student",  "student223",   is21,     2),
        ("student3",  "Фёдоров Алексей Игоревич",      "student",  "student323",   is21,     2),
        ("student4",  "Белякова Ольга Николаевна",      "student",  "student423",   is22,     1),
        ("student5",  "Громов Никита Павлович",         "student",  "student523",   is22,     1),
        ("starosta2", "Зайцева Марина Андреевна",       "starosta", "starosta223",  is22,     1),
        ("teacher2",  "Соколов Андрей Владимирович",    "teacher",  "teacher223",   None,     None),
        ("teacher3",  "Лебедева Наталья Юрьевна",       "teacher",  "teacher323",   None,     None),
        ("curator2",  "Попов Дмитрий Сергеевич",        "curator",  "curator223",   None,     None),
    ]

    for username, full_name, role, password, group_id, course in extra_users:
        upsert_user(
            con,
            username=username,
            full_name=full_name,
            role=role,
            password=password,
            group_id=group_id,
            course=course,
        )


def seed_extra_programs(con, created_by_user_id):
    type_ids = {
        row["name"]: row["id"]
        for row in con.execute("SELECT id, name FROM program_types").fetchall()
    }
    programs = [
        # title, type_name, description, requirements, min_c, max_c, min_rating, deadline, url
        ("Стипендия Правительства РФ",
         "Федеральная",
         "Стипендия для студентов, обучающихся по приоритетным направлениям.",
         "Не ниже 2 курса, средний балл не ниже 4.0.",
         2, 6, 15, "2026-11-01", ""),
        ("Грант РФФИ для молодых учёных",
         "Федеральная",
         "Финансирование научных проектов студентов и аспирантов.",
         "Наличие научной публикации или участие в конференции.",
         3, 6, 20, "2026-07-15", "https://rscf.ru"),
        ("Стипендия фонда «Сколково»",
         "Частный фонд / Благотворительность",
         "Поддержка студентов с предпринимательскими проектами в сфере ИТ.",
         "Наличие стартап-идеи или прототипа, не ниже 2 курса.",
         2, 5, 10, "2026-09-30", "https://sk.ru"),
        ("Именная стипендия университета",
         "Университетская",
         "Стипендия имени профессора Иванова для лучших студентов кафедры.",
         "1 курс, отличные оценки по профильным дисциплинам.",
         1, 2, 5, "2026-10-15", ""),
        ("Грант фонда «Будущее России»",
         "Частный фонд / Благотворительность",
         "Поддержка социально активных студентов.",
         "Участие в волонтёрских или общественных проектах, не ниже 1 курса.",
         1, 6, 5, "2026-08-20", ""),
    ]
    for title, type_name, description, requirements, min_c, max_c, min_r, deadline, url in programs:
        con.execute(
            """INSERT OR IGNORE INTO programs
               (type_id, title, description, requirements, min_course, max_course,
                min_rating, deadline, url, created_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (type_ids[type_name], title, description, requirements,
             min_c, max_c, min_r, deadline, url, created_by_user_id),
        )


def seed_extra_achievements(con):
    # Получаем id пользователей и категорий
    users = {
        row["username"]: row["id"]
        for row in con.execute("SELECT id, username FROM users").fetchall()
    }
    cats = {
        row["name"]: row["id"]
        for row in con.execute("SELECT id, name FROM achievement_categories").fetchall()
    }
    teacher_id = users.get("teacher1")

    achievements = [
        # username, category, title, description, status, score
        ("student1", "Олимпиада",
         "Призёр олимпиады СТАНКИН по программированию",
         "2 место на внутривузовской олимпиаде, апрель 2026.",
         "approved", 8),
        ("student1", "Конференция",
         "Участие в конференции молодых учёных",
         "Доклад на тему «Применение ИИ в образовании», март 2026.",
         "approved", 5),
        ("student1", "Волонтёрство",
         "Волонтёр акции «Чистый город»",
         "Участие в городской экологической акции, май 2026.",
         "approved", 2),
        ("student2", "Спорт",
         "Призёр первенства университета по шахматам",
         "3 место, март 2026.",
         "approved", 3),
        ("student2", "Сертификат/курс",
         "Сертификат Яндекс Практикум — Python-разработчик",
         "Пройден курс по Python, февраль 2026.",
         "approved", 1),
        ("student3", "Конференция",
         "Участие в StudentHack 2026",
         "Хакатон по веб-разработке, команда заняла 4 место.",
         "approved", 3),
        ("student3", "Олимпиада",
         "Участник олимпиады по математике",
         "Всероссийский этап, апрель 2026.",
         "pending", 0),
        ("student4", "Творчество",
         "Участие в конкурсе студенческих проектов",
         "Проект «Умный деканат» представлен на выставке.",
         "approved", 2),
        ("student5", "Волонтёрство",
         "Организатор студенческого мероприятия",
         "Помощь в организации дня открытых дверей университета.",
         "pending", 0),
        ("starosta1", "Конференция",
         "Доклад на межвузовской конференции",
         "Тема: «Ролевые модели управления доступом», май 2026.",
         "approved", 5),
    ]

    for username, cat_name, title, description, status, score in achievements:
        user_id = users.get(username)
        cat_id  = cats.get(cat_name)
        if not user_id or not cat_id:
            continue

        reviewer_id  = teacher_id if status != "pending" else None
        reviewed_at  = "2026-05-15 10:00:00" if status != "pending" else None

        con.execute(
            """INSERT INTO achievements
               (student_user_id, category_id, title, description,
                status, score, reviewer_user_id, reviewed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, cat_id, title, description,
             status, score, reviewer_id, reviewed_at),
        )


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    db_path = os.path.join(repo_root, "instance", "app.db")
    if not os.path.exists(db_path):
        raise SystemExit(f"DB not found: {db_path}\nRun: python scripts\\init_db.py")

    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys = ON;")
        con.row_factory = sqlite3.Row

        # Пользователи
        upsert_user(con, username="admin",    full_name="Администратор",      role="admin",    password="admin123")
        upsert_user(con, username="dean1",    full_name="Сотрудник деканата", role="dean",     password="dean123")
        upsert_user(con, username="teacher1", full_name="Преподаватель",      role="teacher",  password="teacher123")
        upsert_user(con, username="student1", full_name="Студент",            role="student",  password="student123")
        upsert_user(con, username="starosta1", full_name="Староста", role="starosta", password="starosta123")
        upsert_user(con, username="curator1",  full_name="Куратор", role="curator",  password="curator123")

        # ACL для records
        upsert_acl(con, subject_type="role", subject_value="teacher",  object_type="records", action="edit")
        upsert_acl(con, subject_type="role", subject_value="student",  object_type="records", action="read_own")
        upsert_acl(con, subject_type="role", subject_value="student",  object_type="records", action="edit_own")
        upsert_acl(con, subject_type="role", subject_value="dean",     object_type="records", action="full")
        upsert_acl(con, subject_type="role", subject_value="admin",    object_type="records", action="full")
        upsert_acl(con, subject_type="role", subject_value="starosta", object_type="records", action="read_own")
        upsert_acl(con, subject_type="role", subject_value="starosta", object_type="records", action="edit_own")
        upsert_acl(con, subject_type="role", subject_value="curator",  object_type="records", action="edit")

        seed_records(con)

        # Иерархия ролей
        init_role_tables(con)
        seed_role_tables(con)

        # Расписание
        seed_schedule(con)

        # Курс для тестовых студентов
        con.execute("UPDATE users SET course = 2 WHERE username = 'student1'")
        con.execute("UPDATE users SET course = 3 WHERE username = 'starosta1'")

        # Достижения, мероприятия, программы
        admin_id = con.execute(
            "SELECT id FROM users WHERE username = 'admin'"
        ).fetchone()["id"]
        teacher_id_user = con.execute(
            "SELECT id FROM users WHERE username = 'teacher1'"
        ).fetchone()["id"]

        seed_achievements_meta(con)
        seed_events(con, created_by_user_id=teacher_id_user)
        seed_programs(con, created_by_user_id=admin_id)

        # Дополнительные пользователи, программы, достижения
        seed_extra_users(con)
        seed_extra_programs(con, created_by_user_id=admin_id)
        seed_extra_achievements(con)

        # ЛП1: справочники и тестовые данные
        upsert_status(con, name="активный", description="Студент обучается в штатном режиме")
        upsert_status(con, name="в академическом отпуске", description="Временное приостановление обучения")
        upsert_status(con, name="отчислен", description="Обучение прекращено")

        upsert_group(con, name="ПИ-101", max_students=30)
        upsert_group(con, name="ПИ-101 (углубл.)", max_students=15)

        users = {
            row["username"]: int(row["id"])
            for row in con.execute("SELECT id, username FROM users").fetchall()
        }
        teacher_user_id = users.get("teacher1")
        upsert_teacher(
            con,
            user_id=teacher_user_id,
            last_name="Иванов",
            first_name="Иван",
            middle_name="Иванович",
            degree="к.т.н.",
            position="доцент",
            email="teacher1@example.edu",
        )
        teacher_id = con.execute(
            "SELECT id FROM teachers WHERE email = ?",
            ("teacher1@example.edu",),
        ).fetchone()["id"]

        upsert_discipline(con, name="Базы данных", is_advanced=False, teacher_id=teacher_id)
        upsert_discipline(con, name="Алгоритмы (углубл.)", is_advanced=True, teacher_id=teacher_id)

        group_id = con.execute("SELECT id FROM student_groups WHERE name = ?", ("ПИ-101",)).fetchone()["id"]
        status_id = con.execute("SELECT id FROM academic_statuses WHERE name = ?", ("активный",)).fetchone()["id"]

        upsert_student(
            con,
            student_card_number="S-0001",
            last_name="Петров",
            first_name="Пётр",
            middle_name="Петрович",
            group_id=group_id,
            status_id=status_id,
        )
        upsert_student(
            con,
            student_card_number="S-0002",
            last_name="Сидорова",
            first_name="Анна",
            middle_name=None,
            group_id=group_id,
            status_id=status_id,
        )
        recompute_group_counts(con)

        con.commit()
    finally:
        con.close()

    print("OK: seeded users + ACL + records + role hierarchy + LP1 demo data + schedule + achievements + events + programs")


if __name__ == "__main__":
    main()

