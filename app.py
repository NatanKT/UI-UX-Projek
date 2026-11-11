import json
import os
from decimal import Decimal, InvalidOperation

from flask import Flask, flash, g, redirect, render_template, request, url_for
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from auth import bp as auth_bp, login_required, roles_required
from models import ROLES, Customer, Quotation, User, db

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


# halaman utama (dashboard penawaran + section draft) -> templates/index.html
@app.route('/')
@login_required
def index():
    # draft = penawaran yang belum dikirim; section draft di halaman ini
    drafts = (
        Quotation.query.filter_by(status="draft")
        .order_by(Quotation.updated_at.desc())
        .all()
    )
    submitted = (
        Quotation.query.filter(Quotation.status != "draft")
        .order_by(Quotation.updated_at.desc())
        .all()
    )
    return render_template('index.html', drafts=drafts, submitted=submitted)


# halaman detail penawaran -> templates/detail.html
@app.route('/detail')
@login_required
def detail():
    return render_template('detail.html')


# ---------------------------------------------------------------------------
# Penawaran (draft dulu, belum ada proses kirim/approval)
# form-nya ada di templates/form.html
# ---------------------------------------------------------------------------


# pilihan dropdown proses & nama consumable default di form penawaran
PROSES_OPTIONS = ("Bubut", "Milling", "Drilling", "Grinding", "—")
CONSUMABLE_NAMES = ("Mata bor HSS Ø12", "Coolant")


# angka dari input form; kosong/ngawur dianggap 0 dan tidak boleh negatif
def _int(value):
    try:
        return max(int(value or 0), 0)
    except ValueError:
        return 0


# pasangkan dua list input (nama + nilai) jadi list dict buat disimpan sebagai JSON
def _json_rows(names, values, value_key):
    return [
        {"nama": (nama or "").strip(), value_key: _int(value)}
        for nama, value in zip(names, values)
    ]


# isi awal form penawaran baru
def _empty_quotation():
    return {
        "customer_id": None,
        "item": "",
        "qty": 0,
        "work": "Bubut",
        "notes": "",
        "shape": "Rod / Bulat",
        "diameter": 0,
        "length": 0,
        "operators": 0,
        "design_baru": False,
        "material": "ST 42 — Ø12 mm",
        "proses": [{"nama": p, "menit": 0} for p in PROSES_OPTIONS[:4]],
        "consumables": [{"nama": n, "qty": 0} for n in CONSUMABLE_NAMES],
    }


# isi form dari draft yang sudah tersimpan (halaman edit)
def _quotation_values(quotation):
    return {
        "customer_id": quotation.customer_id,
        "item": quotation.item or "",
        "qty": quotation.qty,
        "work": quotation.work or "",
        "notes": quotation.notes or "",
        "shape": quotation.shape or "",
        "diameter": quotation.diameter,
        "length": quotation.length,
        "operators": quotation.operators,
        "design_baru": quotation.design_baru,
        "material": quotation.material or "",
        "proses": json.loads(quotation.proses or "[]") or _empty_quotation()["proses"],
        "consumables": json.loads(quotation.consumables or "[]")
        or _empty_quotation()["consumables"],
    }


# ambil input form penawaran jadi dict (customer dicek ada di DB)
def _quotation_form(form):
    customer = db.session.get(Customer, _int(form.get("customer")))
    return {
        "customer_id": customer.id if customer else None,
        "item": (form.get("item") or "").strip(),
        "qty": _int(form.get("qty")),
        "work": form.get("work") or "",
        "notes": (form.get("notes") or "").strip(),
        "shape": form.get("shape") or "",
        "diameter": _int(form.get("diameter")),
        "length": _int(form.get("length")),
        "operators": _int(form.get("operators")),
        "design_baru": form.get("design_baru") == "on",
        "material": form.get("material") or "",
        "proses": _json_rows(
            form.getlist("proses_nama"), form.getlist("proses_menit"), "menit"
        ),
        "consumables": _json_rows(
            form.getlist("consumable_nama"), form.getlist("consumable_qty"), "qty"
        ),
    }


# salin dict hasil _quotation_form ke record
def _apply_quotation(quotation, values):
    for field, value in values.items():
        if field in ("proses", "consumables"):
            value = json.dumps(value)
        setattr(quotation, field, value)


# customer aktif buat dropdown "Customer" di form
def _form_customers():
    return (
        Customer.query.filter(
            Customer.dihapus.is_(False), Customer.discontinued.is_(False)
        )
        .order_by(Customer.nama)
        .all()
    )


# isi ulang form + pesan error (dipakai route simpan)
def _render_quotation_form(values, quotation=None, errors=()):
    for error in errors:
        flash(error, "error")
    return render_template(
        "form.html",
        customers=_form_customers(),
        values=values,
        quotation=quotation,
        proses_options=PROSES_OPTIONS,
    )


# halaman form penawaran baru -> templates/form.html
@app.route('/form')
@roles_required("admin", "sales")
def form():
    return _render_quotation_form(_empty_quotation())


# simpan penawaran sebagai draft, lalu buka lagi dalam mode edit
@app.post('/form')
@roles_required("admin", "sales")
def form_save():
    values = _quotation_form(request.form)
    if len(values["item"]) > 150:
        return _render_quotation_form(values, errors=("Nama item maksimal 150 karakter.",))
    quotation = Quotation(
        status="draft",
        sales=g.user.name,
        created_by=g.user.username,
        updated_by=g.user.username,
    )
    _apply_quotation(quotation, values)
    db.session.add(quotation)
    db.session.flush()  # dapat id dulu buat nomor draft
    quotation.nomor = f"DRF-{quotation.id:04d}"
    db.session.commit()
    flash("Draft penawaran disimpan.", "success")
    return redirect(url_for("form_edit", quotation_id=quotation.id))


# buka/perbarui draft -> templates/form.html
@app.route('/form/<int:quotation_id>', methods=["GET", "POST"])
@roles_required("admin", "sales")
def form_edit(quotation_id):
    quotation = db.get_or_404(Quotation, quotation_id)
    if quotation.status != "draft":
        flash("Penawaran yang sudah dikirim tidak bisa diubah.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        values = _quotation_form(request.form)
        if len(values["item"]) > 150:
            return _render_quotation_form(
                values, quotation, ("Nama item maksimal 150 karakter.",)
            )
        _apply_quotation(quotation, values)
        quotation.updated_by = g.user.username
        db.session.commit()
        flash("Draft penawaran diperbarui.", "success")
        return redirect(url_for("form_edit", quotation_id=quotation.id))
    return _render_quotation_form(_quotation_values(quotation), quotation)


# hapus draft dari section draft di dashboard
@app.post('/form/<int:quotation_id>/delete')
@roles_required("admin", "sales")
def form_delete(quotation_id):
    quotation = db.get_or_404(Quotation, quotation_id)
    db.session.delete(quotation)
    db.session.commit()
    flash("Draft penawaran dihapus.", "success")
    return redirect(url_for("index"))


# halaman master (tab Proses) -> templates/master.html
@app.route('/master')
@roles_required("admin")
def master():
    return render_template('master.html')


# ---------------------------------------------------------------------------
# Master customer
# form-nya ada di templates/master_customers.html & customer_form.html
# ---------------------------------------------------------------------------


# field teks customer + batas panjangnya (buat validasi server-side)
CUSTOMER_FIELDS = {
    "kode": ("Kode", 30),
    "nama": ("Nama", 150),
    "g_ng": ("G/NG", 10),
    "sales": ("Sales", 100),
    "telp": ("Telp", 40),
    "npwp": ("NPWP", 40),
    "top": ("TOP", 30),
    "cara_bayar": ("Cara bayar", 50),
    "other_bayar": ("Other bayar", 100),
    "company": ("Company", 100),
    "bu": ("BU", 50),
    "kode_oracle": ("Kode Oracle", 50),
}


# ambil semua input customer dari form, strip spasi ujung
def _customer_data(form):
    data = {field: (form.get(field) or "").strip() for field in CUSTOMER_FIELDS}
    data["alamat"] = (form.get("alamat") or "").strip()
    data["alamat_tagihan"] = (form.get("alamat_tagihan") or "").strip()
    data["limit_kredit"] = (form.get("limit_kredit") or "0").strip()
    data["discontinued"] = form.get("discontinued") == "on"
    return data


# isi data form dari record customer (halaman edit)
def _customer_values(customer):
    data = {field: getattr(customer, field) or "" for field in CUSTOMER_FIELDS}
    data["alamat"] = customer.alamat or ""
    data["alamat_tagihan"] = customer.alamat_tagihan or ""
    data["limit_kredit"] = str(customer.limit_kredit or 0)
    data["discontinued"] = customer.discontinued
    return data


# data kosong buat halaman tambah
def _empty_customer():
    data = {field: "" for field in CUSTOMER_FIELDS}
    data.update(alamat="", alamat_tagihan="", limit_kredit="0", discontinued=False)
    return data


# limit kredit disimpan sebagai Decimal; None artinya input bukan angka
def _limit_kredit(value):
    try:
        number = Decimal(value or "0")
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


# validasi customer: batas panjang, kode/nama wajib & unik, limit kredit angka
def _customer_errors(data, customer_id=None):
    errors = []
    for field, (label, max_length) in CUSTOMER_FIELDS.items():
        if len(data[field]) > max_length:
            errors.append(f"{label} maksimal {max_length} karakter.")

    for field, label in (("kode", "Kode customer"), ("nama", "Nama customer")):
        value = data[field]
        if not value:
            errors.append(f"{label} wajib diisi.")
            continue
        query = Customer.query.filter(
            func.lower(getattr(Customer, field)) == value.lower()
        )
        if customer_id is not None:  # saat edit: kecualikan dirinya sendiri
            query = query.filter(Customer.id != customer_id)
        if query.first() is not None:
            errors.append(f"{label} sudah ada.")

    limit = _limit_kredit(data["limit_kredit"])
    if limit is None:
        errors.append("Limit kredit harus angka.")
    elif limit < 0:
        errors.append("Limit kredit tidak boleh negatif.")
    return errors


# salin data form ke record customer
def _apply_customer(customer, data):
    for field in CUSTOMER_FIELDS:
        setattr(customer, field, data[field])
    customer.alamat = data["alamat"]
    customer.alamat_tagihan = data["alamat_tagihan"]
    customer.limit_kredit = _limit_kredit(data["limit_kredit"])
    customer.discontinued = data["discontinued"]


# halaman daftar customer -> templates/master_customers.html
@app.get('/master/customers')
@roles_required("admin")
def customers():
    items = (
        Customer.query.filter(Customer.dihapus.is_(False))
        .order_by(Customer.nama)
        .all()
    )
    return render_template('master_customers.html', items=items)


# tambah customer, form di templates/customer_form.html
@app.route('/master/customers/add', methods=["GET", "POST"])
@roles_required("admin")
def customer_add():
    if request.method == "GET":
        return render_template(
            "customer_form.html", customer=None, data=_empty_customer()
        )
    data = _customer_data(request.form)
    errors = _customer_errors(data)
    if errors:
        for error in errors:
            flash(error, "error")
        return render_template("customer_form.html", customer=None, data=data)
    customer = Customer(created_by=g.user.username, updated_by=g.user.username)
    _apply_customer(customer, data)
    db.session.add(customer)
    try:
        db.session.commit()  # simpan beneran ke database
        flash("Customer ditambahkan.", "success")
    except IntegrityError:  # kalau kode/nama dobel (race), batalkan
        db.session.rollback()
        flash("Kode atau nama customer sudah ada.", "error")
        return render_template("customer_form.html", customer=None, data=data)
    return redirect(url_for("customers"))


# ubah customer, form di templates/customer_form.html
@app.route('/master/customers/<int:customer_id>/edit', methods=["GET", "POST"])
@roles_required("admin")
def customer_edit(customer_id):
    customer = db.get_or_404(Customer, customer_id)  # 404 kalau id ga ada
    if request.method == "POST":
        data = _customer_data(request.form)
        errors = _customer_errors(data, customer.id)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "customer_form.html", customer=customer, data=data
            )
        _apply_customer(customer, data)
        customer.updated_by = g.user.username
        try:
            db.session.commit()
            flash("Customer diperbarui.", "success")
            return redirect(url_for("customers"))
        except IntegrityError:
            db.session.rollback()
            flash("Kode atau nama customer sudah ada.", "error")
            return render_template(
                "customer_form.html", customer=customer, data=data
            )
    return render_template(
        "customer_form.html", customer=customer, data=_customer_values(customer)
    )


# aktif/nonaktif customer (ga dihapus, cuma flip status discontinued)
@app.post('/master/customers/<int:customer_id>/toggle')
@roles_required("admin")
def customer_toggle(customer_id):
    customer = db.get_or_404(Customer, customer_id) 
    customer.discontinued = not customer.discontinued
    customer.updated_by = g.user.username
    db.session.commit()
    flash(
        f"Customer {'diaktifkan' if not customer.discontinued else 'dinonaktifkan'}.",
        "success",
    )
    return redirect(url_for("customers"))


# hapus customer = soft delete, data tetap tersimpan untuk histori
@app.post('/master/customers/<int:customer_id>/delete')
@roles_required("admin")
def customer_delete(customer_id):   
    customer = db.get_or_404(Customer, customer_id)
    customer.dihapus = True
    customer.updated_by = g.user.username
    db.session.commit()
    flash("Customer dihapus.", "success")
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
