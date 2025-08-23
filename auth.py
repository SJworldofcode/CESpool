# auth.py
from flask import Blueprint, request, redirect, url_for, render_template_string, flash, session, abort
from functools import wraps
from hashlib import sha256
from templates import LOGIN_TMPL
from db import get_db

authbp = Blueprint("authbp", __name__)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("authbp.login", next=request.path))
        return f(*args, **kwargs)
    return wrapper

@authbp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        row = db.execute("SELECT id, password_hash, is_admin FROM users WHERE username=?", (username,)).fetchone()
        if row and row["password_hash"] == sha256(password.encode()).hexdigest():
            session["user_id"] = row["id"]
            session["username"] = username
            session["is_admin"] = bool(row["is_admin"]) if row["is_admin"] is not None else False
            return redirect(request.args.get("next") or url_for("todaybp.today"))
        flash("Invalid credentials", "error")
    return render_template_string(LOGIN_TMPL)

@authbp.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("authbp.login"))

@authbp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    from templates import BASE_TMPL  # lazy import to avoid circular
    if request.method == "POST":
        pw1 = request.form.get("pw1", "")
        pw2 = request.form.get("pw2", "")
        if not pw1 or pw1 != pw2:
            flash("Passwords do not match", "error")
        else:
            db = get_db()
            db.execute("UPDATE users SET password_hash=? WHERE id=?",
                       (sha256(pw1.encode()).hexdigest(), session["user_id"]))
            db.commit()
            flash("Password updated.")
            return redirect(url_for("authbp.account"))
    tmpl = """
    {% extends 'BASE_TMPL' %}{% block content %}
      <h3>Account</h3>
      <form method='post' class='card'>
        <label>New password<br><input type='password' name='pw1' required></label><br><br>
        <label>Confirm password<br><input type='password' name='pw2' required></label><br><br>
        <button class="btn btn-primary">Change password</button>
      </form>
    {% endblock %}
    """
    return render_template_string(tmpl, BASE_TMPL=BASE_TMPL)
