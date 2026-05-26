from flask import Flask
from datetime import date

from .db import close_db, init_app as init_db_app
from .views import bp as views_bp
from .auth import bp as auth_bp
from .records import bp as records_bp
from .rbac_routes import bp as rbac_bp
from .lp1 import bp as lp1_bp
from .lp1_legacy import bp as lp1_legacy_bp
from .faculty import bp as faculty_bp
from .schedule import bp as schedule_bp
from .notes import bp as notes_bp
from .achievements import bp as achievements_bp
from .events       import bp as events_bp
from .programs     import bp as programs_bp
from .rating       import bp as rating_bp


def create_app():
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_mapping(
        SECRET_KEY="dev-secret-key-change-me",
        DATABASE="app.db",
    )

    init_db_app(app)
    app.teardown_appcontext(close_db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(rbac_bp)
    app.register_blueprint(lp1_bp)
    app.register_blueprint(lp1_legacy_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(achievements_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(programs_bp)
    app.register_blueprint(rating_bp)

    @app.context_processor
    def inject_today():
        return dict(today=date.today().isoformat())

    return app
