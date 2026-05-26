PRAGMA foreign_keys = ON;

-- ── Пользователи ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT    NOT NULL UNIQUE,
  full_name     TEXT    NOT NULL,
  role          TEXT    NOT NULL CHECK (role IN ('admin', 'dean', 'teacher', 'curator', 'starosta', 'student')),
  password_hash TEXT    NOT NULL,
  is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- ── Защищаемые объекты (ACL, Часть 2) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS records (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER NOT NULL REFERENCES users(id),
  title        TEXT    NOT NULL,
  body         TEXT    NOT NULL DEFAULT '',
  created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT
);

-- ── Правила доступа ACL (Часть 2) ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS acl (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  subject_type  TEXT NOT NULL CHECK (subject_type IN ('role', 'user')),
  subject_value TEXT NOT NULL,
  object_type   TEXT NOT NULL,
  action        TEXT NOT NULL CHECK (action IN ('read', 'read_own', 'edit_own', 'edit', 'full')),
  UNIQUE (subject_type, subject_value, object_type, action)
);

-- ── Иерархия ролей RBAC (Часть 3) ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
  name         TEXT    PRIMARY KEY,
  display_name TEXT    NOT NULL,
  level        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS role_parents (
  role   TEXT NOT NULL REFERENCES roles(name) ON DELETE CASCADE,
  parent TEXT NOT NULL REFERENCES roles(name) ON DELETE CASCADE,
  PRIMARY KEY (role, parent)
);

CREATE TABLE IF NOT EXISTS role_permissions (
  role       TEXT NOT NULL REFERENCES roles(name) ON DELETE CASCADE,
  permission TEXT NOT NULL,
  PRIMARY KEY (role, permission)
);

-- ── Начальные данные: роли ────────────────────────────────────────────────────
INSERT OR IGNORE INTO roles (name, display_name, level) VALUES
  ('student',  'Студент',       0),
  ('starosta', 'Староста',      1),
  ('teacher',  'Преподаватель', 2),
  ('curator',  'Куратор',       3),
  ('dean',     'Деканат',       4),
  ('admin',    'Администратор', 5);

-- ── Начальные данные: цепочка наследования ───────────────────────────────────
INSERT OR IGNORE INTO role_parents (role, parent) VALUES
  ('starosta', 'student'),
  ('teacher',  'starosta'),
  ('curator',  'teacher'),
  ('dean',     'curator'),
  ('admin',    'dean');

-- ── Начальные данные: собственные права ролей ─────────────────────────────────
INSERT OR IGNORE INTO role_permissions (role, permission) VALUES
  ('student',  'view_schedule'),
  ('student',  'view_own_grades'),
  ('student',  'submit_request'),
  ('starosta', 'view_group_list'),
  ('starosta', 'manage_attendance'),
  ('starosta', 'submit_group_request'),
  ('teacher',  'edit_grades'),
  ('teacher',  'view_all_students'),
  ('teacher',  'create_record'),
  ('curator',  'view_group_progress'),
  ('curator',  'manage_group'),
  ('curator',  'approve_request'),
  ('dean',     'manage_teachers'),
  ('dean',     'view_reports'),
  ('dean',     'approve_all'),
  ('admin',    'manage_users'),
  ('admin',    'manage_roles'),
  ('admin',    'full_access');

-- ── ЛП1 (Осит Герман): Управление студентами и академическая адаптация ───────
CREATE TABLE IF NOT EXISTS academic_statuses (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS student_groups (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  name             TEXT    NOT NULL UNIQUE,
  max_students     INTEGER NOT NULL CHECK (max_students > 0),
  current_students INTEGER NOT NULL DEFAULT 0 CHECK (current_students >= 0)
);

CREATE TABLE IF NOT EXISTS teachers (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER UNIQUE,
  last_name   TEXT NOT NULL,
  first_name  TEXT NOT NULL,
  middle_name TEXT,
  degree      TEXT,
  position    TEXT NOT NULL,
  email       TEXT NOT NULL UNIQUE,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS disciplines (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT    NOT NULL UNIQUE,
  is_advanced INTEGER NOT NULL DEFAULT 0 CHECK (is_advanced IN (0, 1)),
  teacher_id  INTEGER NOT NULL REFERENCES teachers(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS students (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  student_card_number TEXT    NOT NULL UNIQUE,
  last_name           TEXT    NOT NULL,
  first_name          TEXT    NOT NULL,
  middle_name         TEXT,
  group_id            INTEGER NOT NULL REFERENCES student_groups(id) ON DELETE RESTRICT,
  status_id           INTEGER NOT NULL REFERENCES academic_statuses(id) ON DELETE RESTRICT,
  created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_students_group_id ON students(group_id);
CREATE INDEX IF NOT EXISTS idx_students_status_id ON students(status_id);

CREATE TABLE IF NOT EXISTS engagement_scores (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  discipline_id INTEGER NOT NULL REFERENCES disciplines(id) ON DELETE CASCADE,
  teacher_id    INTEGER NOT NULL REFERENCES teachers(id) ON DELETE RESTRICT,
  score         INTEGER NOT NULL CHECK (score BETWEEN 1 AND 10),
  reason        TEXT,
  created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_engagement_student_id ON engagement_scores(student_id);
CREATE INDEX IF NOT EXISTS idx_engagement_discipline_id ON engagement_scores(discipline_id);

CREATE TABLE IF NOT EXISTS transfer_history (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  old_group_id  INTEGER NOT NULL REFERENCES student_groups(id) ON DELETE RESTRICT,
  new_group_id  INTEGER NOT NULL REFERENCES student_groups(id) ON DELETE RESTRICT,
  transfer_date TEXT    NOT NULL DEFAULT (datetime('now')),
  basis         TEXT    NOT NULL,
  dean_user_id  INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_transfer_student_id ON transfer_history(student_id);

CREATE TABLE IF NOT EXISTS academic_debts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  discipline_id INTEGER NOT NULL REFERENCES disciplines(id) ON DELETE RESTRICT,
  debt_type     TEXT    NOT NULL,
  description   TEXT,
  occurred_on   TEXT    NOT NULL,
  status        TEXT    NOT NULL DEFAULT 'активная' CHECK (status IN ('активная', 'погашенная'))
);

CREATE INDEX IF NOT EXISTS idx_debts_student_id ON academic_debts(student_id);


-- ── Группы ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS groups (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT    NOT NULL UNIQUE  -- например «ИС-21», «ИС-22»
);

-- ── Привязка студентов/старост к группе ───────────────────────────────────────
-- Добавляем столбец group_id в users (NULL = не привязан к группе)
-- SQLite не поддерживает ADD COLUMN с REFERENCES, поэтому без FK-constraint
ALTER TABLE users ADD COLUMN group_id INTEGER REFERENCES groups(id);

-- ── Расписание ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schedule (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  group_id   INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  day        INTEGER NOT NULL CHECK (day BETWEEN 1 AND 6), -- 1=Пн, 6=Сб
  time_start TEXT    NOT NULL,  -- «09:00»
  time_end   TEXT    NOT NULL,  -- «10:30»
  subject    TEXT    NOT NULL,
  teacher    TEXT    NOT NULL,
  room       TEXT    NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_schedule_group ON schedule(group_id, day);

-- ── Заметки студентов ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notes (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date       TEXT    NOT NULL,  -- «2025-03-10»
  title      TEXT    NOT NULL DEFAULT '',
  body       TEXT    NOT NULL DEFAULT '',
  created_at TEXT    NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_notes_user_date ON notes(user_id, date);