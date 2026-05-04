PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'dean', 'teacher', 'student')),
  password_hash TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Objects to protect (example domain entity for ACL demonstration)
CREATE TABLE IF NOT EXISTS records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT,
  FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_records_owner ON records(owner_user_id);

-- ACL: who (user/role) can do what with which object type
CREATE TABLE IF NOT EXISTS acl (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('role', 'user')),
  subject_value TEXT NOT NULL,
  object_type TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('read', 'read_own', 'edit_own', 'edit', 'full')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(subject_type, subject_value, object_type, action)
);

CREATE INDEX IF NOT EXISTS idx_acl_lookup ON acl(subject_type, subject_value, object_type, action);

