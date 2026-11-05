from functools import wraps

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import func

from models import User, db

# blueprint ini didaftarkan ke app di app.py lewat app.register_blueprint(auth_bp)
bp = Blueprint("auth", __name__)


# jalan otomatis TIAP request (sebelum route dijalankan)
# isi g.user berdasarkan session, jadi semua route bisa akses user yang lagi login
@bp.before_app_request
def load_user():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    # kalau user ga ada atau dinonaktifkan, g.user jadi None (dianggap belum login)
    g.user = user if user is not None and user.active else None


# decorator: halaman wajib login, kalau belum -> lempar ke /login
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped


# decorator: wajib login + role tertentu, kalau role ga cocok -> balik ke index
def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("auth.login", next=request.full_path))
            if g.user.role not in roles:
                flash("Anda tidak punya akses ke halaman ini.", "error")
                return redirect(url_for("index"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


# halaman login, data masuk dari templates/login.html (form username + password)
@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:  # kalau udah login, langsung masuk ke index
        return redirect(url_for("index"))

    username = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        # cari user by username (case-insensitive)
        user = User.query.filter(
            func.lower(User.username) == username.lower()
        ).first()
        if user is None or not user.active or not user.check_password(password):
            flash("Username atau password salah.", "error")
            return render_template("login.html", username=username), 401

        # sukses -> simpan id user ke session (cookie)
        session.clear()
        session["user_id"] = user.id
        # balik ke halaman yang tadi mau dibuka (kalau ada 'next')
        next_url = request.args.get("next") or request.form.get("next") or ""
        if not next_url.startswith("/") or next_url.startswith("//"):
            next_url = url_for("index")
        return redirect(next_url)

    return render_template("login.html", username=username)


# tombol "Keluar" di templates/base.html submit POST ke sini
@bp.post("/logout")
@login_required
def logout():
    session.clear()  # hapus session, user jadi logout
    flash("Anda sudah keluar.", "success")
    return redirect(url_for("auth.login"))
