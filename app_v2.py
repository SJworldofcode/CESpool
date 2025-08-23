# app_v2.py
from flask import Flask, redirect, url_for
from jinja2 import DictLoader

from constants import APP_SECRET, APP_VERSION
from templates import BASE_TMPL, LOGIN_TMPL, TODAY_TMPL, HISTORY_TMPL, STATS_TMPL
from db import get_db, close_db
from auth import authbp
from routes_today import todaybp
from routes_history import historybp
from routes_admin import adminbp

def create_app():
    app = Flask(__name__)
    app.secret_key = APP_SECRET

    # Make templates available without a filesystem
    app.jinja_loader = DictLoader({
        "BASE_TMPL": BASE_TMPL,
        "LOGIN_TMPL": LOGIN_TMPL,
        "TODAY_TMPL": TODAY_TMPL,
        "HISTORY_TMPL": HISTORY_TMPL,
        "STATS_TMPL": STATS_TMPL,
    })

    # Blueprints
    app.register_blueprint(authbp)
    app.register_blueprint(todaybp)
    app.register_blueprint(historybp)
    app.register_blueprint(adminbp)

    # Root
    @app.route("/")
    def root():
        return redirect(url_for("todaybp.today"))

    # DB teardown
    @app.teardown_appcontext
    def _close_db(error=None):
        close_db(error)

    # # Debug routes
    # @app.route("/__version__")
    # def __version__():
    #     return "SINGLE-POOL v2", 200, {"Content-Type": "text/plain"}
    #
    # @app.route("/__routes__")
    # def __routes__():
    #     return {"routes": [str(r) for r in app.url_map.iter_rules()]}

    return app

if __name__ == "__main__":
    app = create_app()
    print("Carpool v2 modular app starting…")
    app.run(debug=True, host="0.0.0.0", port=5002)
