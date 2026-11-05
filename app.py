import os

from flask import Flask, flash, redirect, render_template, request, url_for
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from auth import bp as auth_bp, login_required, roles_required
from models import ROLES, Customer, User, db

app = Flask(__name__, instance_relative_config=True)

# --- koneksi database ---
# urutan prioritas (yang menang):
#   1. env DATABASE_URL (kalau di-set, misal dari test_master.py)
#   2. instance/config.py  (meng-override ke MySQL server)
#   3. default sqlite file instance/ui_ux.db
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-ui-ux"),
    SQLALCHEMY_DATABASE_URI=os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(app.instance_path, "ui_ux.db").replace("\\", "/"),
    ),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
app.config.from_pyfile("config.py", silent=True)  # baca config tambahan dari instance/config.py
if os.environ.get("DATABASE_URL"):
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
os.makedirs(app.instance_path, exist_ok=True)
db.init_app(app)  # pasang konektor db (dari models.py) ke app
app.register_blueprint(auth_bp)  # daftarkan blueprint login/logout dari auth.py

# user default yang dibuat pertama kali (username, nama, role, password)
DEFAULT_USERS = (
    ("admin", "Admin Workshop", "admin", "admin123"),
    ("sales", "Rina Sales", "sales", "sales123"),
    ("approver", "Budi Approver", "approver", "approver123"),
)


# isi user default kalau tabel masih kosong / ga ada admin aktif
def seed_users():
    if User.query.first() is None:
        defaults = DEFAULT_USERS
    elif User.query.filter_by(role="admin", active=True).first() is None:
        defaults = (DEFAULT_USERS[0],)
    else:
        return
    for username, name, role, password in defaults:
        if User.query.filter_by(username=username).first() is not None:
            continue
        user = User(username=username, name=name, role=role, active=True)
        user.set_password(password)  # hash password dulu
        db.session.add(user)
    db.session.commit()


# dijalankan sekali saat app start: bikin tabel (kalau belum ada) + seed user
with app.app_context():
    db.create_all()
    seed_users()


# halaman utama (dashboard penawaran) -> templates/index.html
@app.route('/')
@login_required
def index():
    return render_template('index.html')


# halaman detail penawaran -> templates/detail.html
@app.route('/detail')
@login_required
def detail():
    return render_template('detail.html')


# halaman form penawaran baru -> templates/form.html
@app.route('/form')
@roles_required("admin", "sales")
def form():
    # ambil customer yang masih aktif buat dropdown "Customer" di form
    customers = Customer.query.filter_by(active=True).order_by(Customer.name).all()
    return render_template('form.html', customers=customers)


# halaman master (tab Proses) -> templates/master.html
@app.route('/master')
@roles_required("admin")
def master():
    return render_template('master.html')


# ---------------------------------------------------------------------------
# Master customer
# form-nya ada di templates/master_customers.html & customer_form.html
# ---------------------------------------------------------------------------


# validasi nama customer: wajib diisi, maks 150 char, dan ga boleh dobel
def _customer_errors(name, customer_id=None):
    errors = []
    if not name:
        errors.append("Nama customer wajib diisi.")
    elif len(name) > 150:
        errors.append("Nama customer maksimal 150 karakter.")
    else:
        query = Customer.query.filter(func.lower(Customer.name) == name.lower())
        if customer_id is not None:  # saat edit: kecualikan dirinya sendiri
            query = query.filter(Customer.id != customer_id)
        if query.first() is not None:
            errors.append("Nama customer sudah ada.")
    return errors


# halaman daftar customer -> templates/master_customers.html
@app.get('/master/customers')
@roles_required("admin")
def customers():
    items = Customer.query.order_by(Customer.name).all()
    return render_template('master_customers.html', items=items)


# tambah customer, data dari form "Tambah customer" di master_customers.html
@app.post('/master/customers/add')
@roles_required("admin")
def customer_add():
    name = (request.form.get("name") or "").strip()  # ambil input 'name', buang spasi ujung
    errors = _customer_errors(name)
    if errors:
        for error in errors:
            flash(error, "error")
        return redirect(url_for("customers"))  # balik ke daftar, tampilkan pesan error
    customer = Customer(name=name, active=True)  # bikin record baru
    db.session.add(customer)  # masuk antrian insert
    try:
        db.session.commit()  # simpan beneran ke database
        flash("Customer ditambahkan.", "success")
    except IntegrityError:  # kalau nama dobel (race), batalkan
        db.session.rollback()
        flash("Nama customer sudah ada.", "error")
    return redirect(url_for("customers"))


# ubah customer, form di templates/customer_form.html
@app.route('/master/customers/<int:customer_id>/edit', methods=["GET", "POST"])
@roles_required("admin")
def customer_edit(customer_id):
    customer = db.get_or_404(Customer, customer_id)  # 404 kalau id ga ada
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        errors = _customer_errors(name, customer.id)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "customer_form.html", customer=customer, name=name
            )
        customer.name = name
        try:
            db.session.commit()
            flash("Customer diperbarui.", "success")
            return redirect(url_for("customers"))
        except IntegrityError:
            db.session.rollback()
            flash("Nama customer sudah ada.", "error")
            return render_template(
                "customer_form.html", customer=customer, name=name
            )
    return render_template("customer_form.html", customer=customer)


# aktif/nonaktif customer (ga dihapus, cuma flip status)
@app.post('/master/customers/<int:customer_id>/toggle')
@roles_required("admin")
def customer_toggle(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    customer.active = not customer.active
    db.session.commit()
    flash(
        f"Customer {'diaktifkan' if customer.active else 'dinonaktifkan'}.",
        "success",
    )
    return redirect(url_for("customers"))


# ---------------------------------------------------------------------------
# Master user
# form-nya ada di templates/master_users.html & user_form.html
# ---------------------------------------------------------------------------


# ambil data dari form user lalu strip spasi ujung
def _user_data(form):
    return {
        "name": (form.get("name") or "").strip(),
        "username": (form.get("username") or "").strip(),
        "role": form.get("role") or "sales",
        "password": form.get("password") or "",
    }


# validasi user: nama/username wajib, role valid, password wajib (khusus tambah)
def _user_errors(data, user_id=None):
    errors = []
    if not data["name"]:
        errors.append("Nama user wajib diisi.")
    elif len(data["name"]) > 120:
        errors.append("Nama user maksimal 120 karakter.")
    if not data["username"]:
        errors.append("Username wajib diisi.")
    elif len(data["username"]) > 50:
        errors.append("Username maksimal 50 karakter.")
    else:
        query = User.query.filter(
            func.lower(User.username) == data["username"].lower()
        )
        if user_id is not None:  # saat edit: kecualikan dirinya
            query = query.filter(User.id != user_id)
        if query.first() is not None:
            errors.append("Username sudah dipakai.")
    if data["role"] not in ROLES:
        errors.append("Role tidak valid.")
    if user_id is None and not data["password"]:
        errors.append("Password wajib diisi.")
    return errors


# halaman daftar user + filter role -> templates/master_users.html
@app.get('/master/users')
@roles_required("admin")
def users():
    role = request.args.get("role", "")  # filter dari query string ?role=...
    query = User.query
    if role in ROLES:
        query = query.filter_by(role=role)
    items = query.order_by(User.name).all()
    return render_template(
        "master_users.html", items=items, roles=ROLES, role=role
    )


# tambah user, data dari form "Tambah user" di master_users.html
@app.post('/master/users/add')
@roles_required("admin")
def user_add():
    data = _user_data(request.form)
    errors = _user_errors(data)
    if errors:
        for error in errors:
            flash(error, "error")
        return redirect(url_for("users"))
    user = User(
        name=data["name"],
        username=data["username"],
        role=data["role"],
        active=True,
    )
    user.set_password(data["password"])  # hash password sebelum disimpan
    db.session.add(user)
    try:
        db.session.commit()
        flash("User ditambahkan.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Username sudah dipakai.", "error")
    return redirect(url_for("users"))


# ubah user, form di templates/user_form.html
@app.route('/master/users/<int:user_id>/edit', methods=["GET", "POST"])
@roles_required("admin")
def user_edit(user_id):
    user = db.get_or_404(User, user_id)
    if request.method == "POST":
        data = _user_data(request.form)
        errors = _user_errors(data, user.id)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "user_form.html", user=user, data=data, roles=ROLES
            )
        user.name = data["name"]
        user.username = data["username"]
        user.role = data["role"]
        if data["password"]:  # password cuma di-hash ulang kalau diisi (opsional saat edit)
            user.set_password(data["password"])
        try:
            db.session.commit()
            flash("User diperbarui.", "success")
            return redirect(url_for("users"))
        except IntegrityError:
            db.session.rollback()
            flash("Username sudah dipakai.", "error")
            return render_template(
                "user_form.html", user=user, data=data, roles=ROLES
            )
    data = {
        "name": user.name,
        "username": user.username,
        "role": user.role,
        "password": "",
    }
    return render_template("user_form.html", user=user, data=data, roles=ROLES)


# aktif/nonaktif user (ga dihapus, cuma flip status)
@app.post('/master/users/<int:user_id>/toggle')
@roles_required("admin")
def user_toggle(user_id):
    user = db.get_or_404(User, user_id)
    user.active = not user.active
    db.session.commit()
    flash(
        f"User {'diaktifkan' if user.active else 'dinonaktifkan'}.",
        "success",
    )
    return redirect(url_for("users"))


if __name__ == '__main__':
    app.run(debug=True)
