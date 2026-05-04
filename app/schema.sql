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