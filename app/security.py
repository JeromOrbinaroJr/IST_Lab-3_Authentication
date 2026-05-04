from functools import wraps

from flask import abort, redirect, session, url_for

from .db import get_db


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("auth.login"))
            if session.get("role") not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _has_acl(*, user_id: int | None, role: str | None, object_type: str, action: str) -> bool:
    """
    ACL is stored in DB table `acl`:
      (subject_type in {'role','user'}, subject_value, object_type, action)

    action hierarchy:
      full => edit => read
      read_own is treated separately (ownership-based read)
    """
    if not user_id or not role:
        return False

    implied_actions: set[str] = {action}
    if action == "read":
        implied_actions |= {"edit", "full"}
    elif action == "edit":
        implied_actions |= {"full"}

    db = get_db()
    for a in implied_actions:
        # role-based
        row = db.execute(
            """
            SELECT 1
            FROM acl
            WHERE subject_type = 'role'
              AND subject_value = ?
              AND object_type = ?
              AND action = ?
            """,
            (role, object_type, a),
        ).fetchone()
        if row is not None:
            return True

        # user-specific (optional)
        row = db.execute(
            """
            SELECT 1
            FROM acl
            WHERE subject_type = 'user'
              AND subject_value = ?
              AND object_type = ?
              AND action = ?
            """,
            (str(user_id), object_type, a),
        ).fetchone()
        if row is not None:
            return True

    return False


def acl_required(object_type: str, action: str):
    """
    Enforces ACL for a coarse-grained object type.
    Example: @acl_required("records", "edit")
    """

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("auth.login"))

            user_id = int(session.get("user_id"))
            role = session.get("role")
            if not _has_acl(user_id=user_id, role=role, object_type=object_type, action=action):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def acl_read_own_required(object_type: str, *, owner_user_id_getter):
    """
    For patterns like "student -> read own".
    owner_user_id_getter must return the owner_user_id for the current request context.
    """

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("auth.login"))

            user_id = int(session.get("user_id"))
            role = session.get("role")

            # full/read/edit allow bypassing ownership
            if _has_acl(user_id=user_id, role=role, object_type=object_type, action="read"):
                return view(*args, **kwargs)

            owner_id = owner_user_id_getter(*args, **kwargs)
            if owner_id != user_id:
                abort(403)

            if not _has_acl(user_id=user_id, role=role, object_type=object_type, action="read_own"):
                abort(403)

            return view(*args, **kwargs)

        return wrapped

    return decorator


def acl_edit_own_required(object_type: str, *, owner_user_id_getter):
    """
    For patterns like "student -> edit own".
    Allows edit/full (global) OR edit_own (only if owner == current user).
    """

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("auth.login"))

            user_id = int(session.get("user_id"))
            role = session.get("role")

            # Global edit/full can bypass ownership
            if _has_acl(user_id=user_id, role=role, object_type=object_type, action="edit"):
                return view(*args, **kwargs)

            owner_id = owner_user_id_getter(*args, **kwargs)
            if owner_id != user_id:
                abort(403)

            if not _has_acl(user_id=user_id, role=role, object_type=object_type, action="edit_own"):
                abort(403)

            return view(*args, **kwargs)

        return wrapped

    return decorator

