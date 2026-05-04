# Виртуальный деканат — Python + SQLite

Командный проект: ИС «Виртуальный деканат».  
Стек: **Python + Flask + SQLite**.

Каждый участник отвечал за свою часть ЛР №3:
- **Часть 1** — аутентификация (постоянный пароль, хэширование)
- **Часть 2** — авторизация объектов (ACL)
- **Часть 3** — иерархическое ролевое управление доступом (RBAC)

---

## 1. Роли в системе

| Логин      | Пароль       | Роль          |
|------------|--------------|---------------|
| admin      | admin123     | Администратор |
| dean1      | dean123      | Деканат       |
| curator1   | curator123   | Куратор       |
| teacher1   | teacher123   | Преподаватель |
| starosta1  | starosta123  | Староста      |
| student1   | student123   | Студент       |

---

## 2. Быстрый старт

### 2.1 Установка зависимостей

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2.2 Инициализация БД

```bash
python scripts/init_db.py   # создаёт instance/app.db со всеми таблицами
python scripts/seed_db.py   # заполняет пользователей, ACL и иерархию ролей
```

### 2.3 Запуск

```bash
python app.py
```

Открыть в браузере: `http://127.0.0.1:5000`

---

## 3. Структура проекта

```
app/
  __init__.py       — фабрика Flask, регистрация blueprint'ов
  schema.sql        — схема всех таблиц (users, acl, records, roles, ...)
  db.py             — get_db()
  security.py       — декораторы login_required, roles_required, acl_required
  rbac.py           — иерархия ролей, декораторы rbac_required, permission_required
  auth.py           — blueprint: /login, /logout, /me/password
  views.py          — blueprint: /, /admin/users
  records.py        — blueprint: /records/ (ACL-демонстрация)
  rbac_routes.py    — blueprint: /rbac/ (RBAC-демонстрация)

scripts/
  init_db.py        — создание БД
  seed_db.py        — тестовые данные (пользователи + ACL + роли)

templates/
  base.html
  index.html
  rbac/             — шаблоны модуля RBAC

static/
  styles.css

instance/
  app.db            — SQLite БД (генерируется)
```

---

## 4. Схема БД

### Часть 1 — аутентификация

Таблица `users`:
- `username` — логин (unique)
- `password_hash` — хэш пароля `pbkdf2:sha256` (Werkzeug), пароль в открытом виде не хранится
- `role` — роль пользователя
- `is_active` — флаг активности

### Часть 2 — авторизация (ACL)

Таблица `records` — защищаемые объекты с владельцем (`owner_user_id`).

Таблица `acl` — правила доступа:
- `subject_type` — `role` или `user`
- `subject_value` — название роли или id пользователя
- `object_type` — тип объекта (например `records`)
- `action` — `read | read_own | edit_own | edit | full`

Иерархия действий: `full ⇒ edit ⇒ read`.

### Часть 3 — иерархия ролей (RBAC)

Таблица `roles` — справочник ролей с числовым уровнем.

Таблица `role_parents` — прямые связи наследования.

Таблица `role_permissions` — собственные права каждой роли.

---

## 5. Часть 1 — Аутентификация

**Выбранный вариант:** постоянный многократно используемый пароль.

**Маршруты:**
- `GET/POST /login` — вход по логину и паролю
- `POST /logout` — выход
- `GET /` — профиль (только после входа)
- `GET /admin/users` — список пользователей (только `admin`)
- `GET/POST /me/password` — смена пароля

**Реализация:**
- Хэширование паролей: `generate_password_hash` / `check_password_hash` (Werkzeug, алгоритм `pbkdf2:sha256`)
- Сессия: подписанная cookie Flask (`session`)
- Декораторы `login_required` и `roles_required(...)` в `app/security.py`

---

## 6. Часть 2 — Авторизация объектов (ACL)

**Выбранный вариант:** дискреционный способ с использованием списка прав доступа (Access Control List).

**Назначение прав для объектов типа `records`:**

| Роль     | Права                    |
|----------|--------------------------|
| student  | read_own, edit_own       |
| starosta | read_own, edit_own       |
| teacher  | edit                     |
| curator  | edit                     |
| dean     | full                     |
| admin    | full                     |

**Маршруты:**
- `GET /records/` — список записей
- `GET /records/<id>` — просмотр (по ACL + владение)
- `GET/POST /records/<id>/edit` — редактирование (по ACL + владение)
- `POST /records/<id>/delete` — удаление (только `full`)

**Реализация:** декораторы `acl_required`, `acl_read_own_required`, `acl_edit_own_required` в `app/security.py`.

---

## 7. Часть 3 — Иерархический RBAC

**Выбранный вариант:** иерархическое ролевое управление с наследованием прав.

**Иерархия:**

```
Студент (0) → Староста (1) → Преподаватель (2) → Куратор (3) → Деканат (4) → Администратор (5)
```

Каждая роль автоматически наследует все права ролей с более низким уровнем. Администратор обладает всеми правами системы.

**Маршруты:**
- `GET /rbac/` — обзор иерархии и таблица прав
- `GET /rbac/hierarchy` — данные из БД
- `GET /rbac/my-permissions` — права текущего пользователя с разбивкой по источнику
- `GET /rbac/area/<role>` — демонстрация проверки доступа к зоне
- `GET /rbac/grades` — пример `@rbac_required("teacher")`
- `GET /rbac/reports` — пример `@rbac_required("dean")`
- `GET /rbac/admin-panel` — пример `@rbac_required("admin")`

**Реализация:** модуль `app/rbac.py` — функции `has_role`, `get_inherited_roles`, `get_all_permissions` и декораторы `rbac_required`, `permission_required`.

---

## 8. Примечания

- `SECRET_KEY` в `app/__init__.py` задан как `dev-secret-key-change-me` — для боевого использования заменить на случайное значение.
- Таблицы `roles`, `role_parents`, `role_permissions` заполняются автоматически при запуске `seed_db.py`.
