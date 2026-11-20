import json
import os
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Flask, abort, flash, g, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

sys.path.append("./Model")
from model_workshop import ROLES, M_Workshop
from workshop import (
    BENTUK,
    CONSUMABLES,
    JENIS,
    MATERIALS,
    PROSES,
    hitung,
    muat_master,
    seed_master,
)

application = Flask(__name__)
application.secret_key = os.environ.get("SECRET_KEY", "dev-ui-ux")

DEFAULT_USERS = (
    ("admin", "Admin Workshop", "admin", "admin123"),
    ("sales", "Rina Sales", "sales", "sales123"),
    ("approver", "Budi Approver", "approver", "approver123"),
)

LABEL_STATUS = {
    "draft": "Draft",
    "submitted": "Menunggu approval",
    "approved": "Disetujui",
    "rejected": "Ditolak",
}


# waktu sekarang buat kolom created_at / updated_at
def tglwaktu():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# format rupiah di template: {{ h.tk|rupiah }}
@application.template_filter("rupiah")
def rupiah(value):
    return "Rp {:,.0f}".format(value or 0).replace(",", ".")


application.jinja_env.globals["hitung"] = hitung
application.jinja_env.globals["LABEL_STATUS"] = LABEL_STATUS


# isi user awal kalau tabel users masih kosong
def seed_users():
    m = M_Workshop()
    users = m.get_users()
    if not users:
        for username, name, role, password in DEFAULT_USERS:
            m.add_user(name, username, role, generate_password_hash(password))
    elif not any(u.role == "admin" and u.active for u in users):
        username, name, role, password = DEFAULT_USERS[0]
        if m.get_datauser(username) is None:
            m.add_user(name, username, role, generate_password_hash(password))


seed_users()
seed_master()
muat_master()


# isi g.user tiap request dari session
@application.before_request
def load_user():
    if request.endpoint == "static":
        return
    id_user = session.get("id_user")
    user = M_Workshop().get_user(id_user) if id_user else None
    g.user = user if user is not None and user.active else None


# halaman wajib login
def wajib_login(fungsi):
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect("/login?next=" + request.full_path)
        return fungsi(*args, **kwargs)

    wrapper.__name__ = fungsi.__name__
    return wrapper


# halaman wajib login + role tertentu
def wajib_role(*roles):
    def dekorator(fungsi):
        def wrapper(*args, **kwargs):
            if g.user is None:
                return redirect("/login?next=" + request.full_path)
            if g.user.role not in roles:
                flash("Anda tidak punya akses ke halaman ini.", "error")
                return redirect("/")
            return fungsi(*args, **kwargs)

        wrapper.__name__ = fungsi.__name__
        return wrapper

    return dekorator


# angka dari form; kosong/ngawur dianggap 0
def angka(nilai):
    try:
        return max(int(nilai or 0), 0)
    except ValueError:
        return 0


# persen di form (5) -> pecahan (0.05)
def persen(nilai):
    try:
        return max(float(nilai or 0), 0) / 100
    except ValueError:
        return 0


# ---------------------------- login ----------------------------


@application.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect("/")

    username = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = M_Workshop().get_datauser(username)
        if user is None or not user.active or not check_password_hash(user.password_hash, password):
            flash("Username atau password salah.", "error")
            return render_template("login.html", username=username), 401

        session.clear()
        session["logged_in"] = True
        session["id_user"] = user.id
        session["nama_user"] = user.name
        session["role"] = user.role
        next_url = request.args.get("next") or request.form.get("next") or "/"
        if not next_url.startswith("/") or next_url.startswith("//"):
            next_url = "/"
        return redirect(next_url)

    return render_template("login.html", username=username)


@application.route("/logout", methods=["POST"])
@wajib_login
def logout():
    session.clear()
    flash("Anda sudah keluar.", "success")
    return redirect("/login")


# ---------------------------- dashboard ----------------------------


@application.route("/")
@wajib_login
def index():
    m = M_Workshop()
    drafts = m.get_quotations("draft")
    submitted = m.get_quotations("kirim")
    menunggu = [q for q in submitted if q.status == "submitted"]
    disetujui = [q for q in submitted if q.status == "approved"]
    return render_template(
        "index.html",
        drafts=drafts,
        submitted=submitted,
        menunggu=menunggu,
        disetujui=disetujui,
        nilai_menunggu=sum(hitung(q)["harga"] for q in menunggu),
        nilai_disetujui=sum(hitung(q)["harga"] for q in disetujui),
    )


@application.route("/detailpenawaran/<int:quotation_id>")
@wajib_login
def detail(quotation_id):
    quotation = M_Workshop().get_quotation(quotation_id)
    if quotation is None:
        abort(404)
    return render_template(
        "detail.html",
        quotation=quotation,
        boleh_putus=g.user.role in ("admin", "approver"),
    )


# ---------------------------- penawaran ----------------------------

# isi awal form penawaran baru
def _empty_quotation():
    return {
        "customer_id": None,
        "item": "",
        "qty": 0,
        "work": JENIS[0],
        "notes": "",
        "shape": BENTUK[0],
        "diameter": 0,
        "length": 0,
        "tebal": 0,
        "lebar": 0,
        "operators": 0,
        "design_baru": False,
        "material": MATERIALS[0][0],
        "ll1": 0.05,
        "ll2": 0.01,
        "rm": 0.10,
        "proses": [{"nama": "", "menit": 0} for _ in range(4)],
        "consumables": [{"nama": "", "qty": 0} for _ in range(2)],
    }


# isi form dari penawaran yang sudah tersimpan
def _quotation_values(quotation):
    proses = json.loads(quotation.proses or "[]") or _empty_quotation()["proses"]
    proses += [{"nama": "", "menit": 0}] * (4 - len(proses))
    return {
        "customer_id": quotation.customer_id,
        "item": quotation.item or "",
        "qty": quotation.qty,
        "work": quotation.work or "",
        "notes": quotation.notes or "",
        "shape": quotation.shape or "",
        "diameter": quotation.diameter,
        "length": quotation.length,
        "tebal": quotation.tebal,
        "lebar": quotation.lebar,
        "operators": quotation.operators,
        "design_baru": quotation.design_baru,
        "material": quotation.material or "",
        "ll1": quotation.ll1,
        "ll2": quotation.ll2,
        "rm": quotation.rm,
        "proses": proses,
        "consumables": json.loads(quotation.consumables or "[]")
        or _empty_quotation()["consumables"],
    }


# pasangkan dua list input (nama + nilai) jadi list dict
def _json_rows(names, values, value_key):
    return [
        {"nama": (nama or "").strip(), value_key: angka(value)}
        for nama, value in zip(names, values)
    ]


# ambil input form penawaran
def _quotation_form(form):
    id_customer = angka(form.get("customer"))
    customer = M_Workshop().get_customer(id_customer) if id_customer else None
    return {
        "customer_id": customer.id if customer else None,
        "item": (form.get("item") or "").strip(),
        "qty": angka(form.get("qty")),
        "work": form.get("work") or "",
        "notes": (form.get("notes") or "").strip(),
        "shape": form.get("shape") or "",
        "diameter": angka(form.get("diameter")),
        "length": angka(form.get("length")),
        "tebal": angka(form.get("tebal")),
        "lebar": angka(form.get("lebar")),
        "operators": angka(form.get("operators")),
        "design_baru": form.get("design_baru") == "on",
        "material": form.get("material") or "",
        "ll1": persen(form.get("ll1")),
        "ll2": persen(form.get("ll2")),
        "rm": persen(form.get("rm")),
        "proses": _json_rows(
            form.getlist("proses_nama"), form.getlist("proses_menit"), "menit"
        ),
        "consumables": _json_rows(
            form.getlist("consumable_nama"), form.getlist("consumable_qty"), "qty"
        ),
    }


# ubah dict form jadi kolom tabel quotations
def _quotation_db(values):
    return {
        "customer_id": values["customer_id"],
        "item": values["item"],
        "qty": values["qty"],
        "work": values["work"],
        "notes": values["notes"],
        "shape": values["shape"],
        "diameter": values["diameter"],
        "length": values["length"],
        "tebal": values["tebal"],
        "lebar": values["lebar"],
        "operators": values["operators"],
        "design_baru": 1 if values["design_baru"] else 0,
        "material": values["material"],
        "ll1": values["ll1"],
        "ll2": values["ll2"],
        "rm": values["rm"],
        "proses": json.dumps(values["proses"]),
        "consumables": json.dumps(values["consumables"]),
    }


# customer aktif buat dropdown
def _form_customers():
    return M_Workshop().get_customers(True)


# nama item yang pernah diinput (saran di form)
def _form_items():
    return M_Workshop().get_item_unik()


# isi ulang form + pesan error
def _render_quotation_form(values, quotation=None, errors=()):
    for error in errors:
        flash(error, "error")
    return render_template(
        "form.html",
        customers=_form_customers(),
        values=values,
        quotation=quotation,
        jenis=JENIS,
        bentuk=BENTUK,
        proses_options=tuple(PROSES),
        materials=MATERIALS,
        consumables=tuple(CONSUMABLES),
        items=_form_items(),
    )


# validasi form penawaran
def _quotation_errors(values):
    errors = []
    if len(values["item"]) > 150:
        errors.append("Nama item maksimal 150 karakter.")
    if values["rm"] >= 1:
        errors.append("RM harus di bawah 100%.")
    return errors


@application.route("/formpenawaran", methods=["GET", "POST"])
@wajib_role("admin", "sales")
def form():
    if request.method == "GET":
        return _render_quotation_form(_empty_quotation())

    values = _quotation_form(request.form)
    errors = _quotation_errors(values)
    if errors:
        return _render_quotation_form(values, errors=errors)

    m = M_Workshop()
    id, nomor = m.get_nomor_baru()
    data = _quotation_db(values)
    data.update(
        {
            "id": id,
            "nomor": nomor,
            "status": "draft",
            "sales": g.user.name,
            "created_by": g.user.username,
            "updated_by": g.user.username,
            "created_at": tglwaktu(),
            "updated_at": tglwaktu(),
        }
    )
    pesan = m.add_quotation(data)
    if pesan != "":
        return _render_quotation_form(values, errors=(pesan,))
    flash("Draft penawaran disimpan.", "success")
    return redirect("/ubahpenawaran/%d" % id)


@application.route("/ubahpenawaran/<int:quotation_id>", methods=["GET", "POST"])
@wajib_role("admin", "sales")
def form_edit(quotation_id):
    m = M_Workshop()
    quotation = m.get_quotation(quotation_id)
    if quotation is None:
        abort(404)
    if quotation.status != "draft":
        flash("Penawaran yang sudah dikirim tidak bisa diubah.", "error")
        return redirect("/")

    if request.method == "POST":
        values = _quotation_form(request.form)
        errors = _quotation_errors(values)
        if errors:
            return _render_quotation_form(values, quotation, errors)
        data = _quotation_db(values)
        data["updated_by"] = g.user.username
        data["updated_at"] = tglwaktu()
        pesan = m.upd_quotation(quotation.id, data)
        if pesan != "":
            return _render_quotation_form(values, quotation, (pesan,))
        flash("Draft penawaran diperbarui.", "success")
        return redirect("/ubahpenawaran/%d" % quotation.id)

    return _render_quotation_form(_quotation_values(quotation), quotation)


@application.route("/hapuspenawaran/<int:quotation_id>", methods=["POST"])
@wajib_role("admin", "sales")
def form_delete(quotation_id):
    M_Workshop().del_quotation(quotation_id)
    flash("Draft penawaran dihapus.", "success")
    return redirect("/")


@application.route("/ajukanpenawaran/<int:quotation_id>", methods=["POST"])
@wajib_role("admin", "sales")
def form_ajukan(quotation_id):
    m = M_Workshop()
    quotation = m.get_quotation(quotation_id)
    if quotation is not None and quotation.status == "draft":
        m.upd_status_quotation(quotation.id, "submitted", g.user.username)
        flash("Penawaran diajukan ke MD.", "success")
    return redirect("/detailpenawaran/%d" % quotation_id)


@application.route("/putuspenawaran/<int:quotation_id>", methods=["POST"])
@wajib_role("admin", "approver")
def detail_putus(quotation_id):
    m = M_Workshop()
    quotation = m.get_quotation(quotation_id)
    status = request.form.get("status")
    if quotation is not None and quotation.status == "submitted" and status in ("approved", "rejected"):
        m.upd_status_quotation(quotation.id, status, g.user.username)
        flash(
            "Penawaran disetujui, harga siap keluar."
            if status == "approved"
            else "Penawaran ditolak.",
            "success",
        )
    return redirect("/detailpenawaran/%d" % quotation_id)


# ---------------------------- master workshop ----------------------------

MASTER = {
    "proses": {
        "judul": "Proses",
        "kolom": [
            {"nama": "nama", "label": "Nama proses", "tipe": "text"},
            {"nama": "kwh", "label": "Daya (kWh)", "tipe": "number"},
            {"nama": "depresiasi_jam", "label": "Depresiasi / jam", "tipe": "number", "uang": True},
        ],
    },
    "material": {
        "judul": "Material",
        "kolom": [
            {"nama": "nama", "label": "Nama material", "tipe": "text"},
            {"nama": "bentuk", "label": "Bentuk", "tipe": "text"},
            {"nama": "density", "label": "Density (kg/m³)", "tipe": "number"},
            {"nama": "harga_kg", "label": "Harga / kg", "tipe": "number", "uang": True},
        ],
    },
    "consumable": {
        "judul": "Consumables",
        "kolom": [
            {"nama": "nama", "label": "Nama consumable", "tipe": "text"},
            {"nama": "harga", "label": "Harga", "tipe": "number", "uang": True},
        ],
    },
    "jenis": {
        "judul": "Jenis pekerjaan",
        "kolom": [{"nama": "nama", "label": "Nama jenis pekerjaan", "tipe": "text"}],
    },
    "bentuk": {
        "judul": "Bentuk",
        "kolom": [{"nama": "nama", "label": "Nama bentuk", "tipe": "text"}],
    },
}


def _master_conf(kunci):
    conf = MASTER.get(kunci)
    if conf is None:
        abort(404)
    return conf


# data master dari form
def _master_data(conf, form):
    data = {"nama": (form.get("nama") or "").strip()}
    salah = []
    for kolom in conf["kolom"]:
        if kolom["nama"] == "nama":
            continue
        nilai = (form.get(kolom["nama"]) or "").strip()
        if kolom["tipe"] != "number":
            data[kolom["nama"]] = nilai
            continue
        try:
            data[kolom["nama"]] = max(float(nilai or 0), 0)
        except ValueError:
            salah.append(kolom["label"])
    return data, salah


# validasi nama & angka
def _master_errors(kunci, data, salah, id=0):
    errors = ["%s harus angka." % label for label in salah]
    if not data["nama"]:
        return errors + ["Nama wajib diisi."]
    if len(data["nama"]) > 100:
        return errors + ["Nama maksimal 100 karakter."]
    if M_Workshop().cek_nama_master(kunci, data["nama"], id):
        errors.append("Nama sudah ada.")
    return errors


def _render_master(kunci, conf, item=None, data=None, errors=()):
    for error in errors:
        flash(error, "error")
    return render_template(
        "master.html",
        daftar=MASTER,
        kunci=kunci,
        conf=conf,
        items=M_Workshop().get_master(kunci),
        item=item,
        data=data or {},
    )


@application.route("/master")
@wajib_role("admin")
def master():
    return redirect("/masterproses")


@application.route("/master<kunci>")
@wajib_role("admin")
def master_list(kunci):
    conf = _master_conf(kunci)
    return _render_master(kunci, conf)


@application.route("/tambahmaster<kunci>", methods=["POST"])
@wajib_role("admin")
def master_add(kunci):
    conf = _master_conf(kunci)
    data, salah = _master_data(conf, request.form)
    errors = _master_errors(kunci, data, salah)
    if errors:
        return _render_master(kunci, conf, data=data, errors=errors)
    pesan = M_Workshop().add_master(kunci, data)
    if pesan != "":
        return _render_master(kunci, conf, data=data, errors=(pesan,))
    muat_master()
    flash("%s ditambahkan." % conf["judul"], "success")
    return redirect("/master" + kunci)


@application.route("/ubahmaster<kunci>/<int:item_id>", methods=["GET", "POST"])
@wajib_role("admin")
def master_edit(kunci, item_id):
    conf = _master_conf(kunci)
    m = M_Workshop()
    item = m.get_master_satu(kunci, item_id)
    if item is None:
        abort(404)
    if request.method == "POST":
        data, salah = _master_data(conf, request.form)
        errors = _master_errors(kunci, data, salah, item.id)
        if errors:
            return _render_master(kunci, conf, item, data, errors)
        pesan = m.upd_master(kunci, item.id, data)
        if pesan != "":
            return _render_master(kunci, conf, item, data, (pesan,))
        muat_master()
        flash("%s diperbarui." % conf["judul"], "success")
        return redirect("/master" + kunci)
    data = {k["nama"]: getattr(item, k["nama"]) for k in conf["kolom"]}
    return _render_master(kunci, conf, item, data)


@application.route("/aktifmaster<kunci>/<int:item_id>", methods=["POST"])
@wajib_role("admin")
def master_toggle(kunci, item_id):
    conf = _master_conf(kunci)
    m = M_Workshop()
    item = m.get_master_satu(kunci, item_id)
    if item is None:
        abort(404)
    m.upd_master_aktif(kunci, item.id, not item.aktif)
    muat_master()
    flash("%s %s." % (item.nama, "diaktifkan" if not item.aktif else "dinonaktifkan"), "success")
    return redirect("/master" + kunci)


@application.route("/hapusmaster<kunci>/<int:item_id>", methods=["POST"])
@wajib_role("admin")
def master_hapus(kunci, item_id):
    conf = _master_conf(kunci)
    M_Workshop().del_master(kunci, item_id)
    muat_master()
    flash("%s dihapus." % conf["judul"], "success")
    return redirect("/master" + kunci)


# ---------------------------- master customer ----------------------------

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
}

KOLOM_CUSTOMER = {
    "kode": "Kode",
    "nama": "Nama",
    "g_ng": "G_NG",
    "sales": "Sales",
    "telp": "Telp",
    "npwp": "NPWP",
    "top": "TOP",
    "cara_bayar": "Cara_Bayar",
    "other_bayar": "Other_Bayar",
    "company": "Company",
    "bu": "BU",
    "alamat": "Alamat",
    "alamat_tagihan": "Alamat_Tagihan",
    "limit_kredit": "LimitKredit",
    "discontinued": "discontinued",
}


def _customer_data(form):
    data = {field: (form.get(field) or "").strip() for field in CUSTOMER_FIELDS}
    data["alamat"] = (form.get("alamat") or "").strip()
    data["alamat_tagihan"] = (form.get("alamat_tagihan") or "").strip()
    data["limit_kredit"] = (form.get("limit_kredit") or "0").strip()
    data["discontinued"] = form.get("discontinued") == "on"
    return data


def _customer_values(customer):
    data = {field: getattr(customer, field) or "" for field in CUSTOMER_FIELDS}
    data["alamat"] = customer.alamat or ""
    data["alamat_tagihan"] = customer.alamat_tagihan or ""
    data["limit_kredit"] = str(customer.limit_kredit or 0)
    data["discontinued"] = customer.discontinued
    return data


def _empty_customer():
    data = {field: "" for field in CUSTOMER_FIELDS}
    data.update(alamat="", alamat_tagihan="", limit_kredit="0", discontinued=False)
    return data


def _limit_kredit(value):
    try:
        number = Decimal(value or "0")
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _customer_db(data):
    hasil = {KOLOM_CUSTOMER[field]: data[field] for field in KOLOM_CUSTOMER}
    hasil["discontinued"] = 1 if data["discontinued"] else 0
    return hasil


def _customer_errors(data, id=0):
    errors = []
    m = M_Workshop()
    for field, (label, max_length) in CUSTOMER_FIELDS.items():
        if len(data[field]) > max_length:
            errors.append("%s maksimal %d karakter." % (label, max_length))

    if not data["kode"]:
        errors.append("Kode customer wajib diisi.")
    elif m.cek_kode_customer(data["kode"], id):
        errors.append("Kode customer sudah ada.")

    if not data["nama"]:
        errors.append("Nama customer wajib diisi.")
    elif m.cek_nama_customer(data["nama"], id):
        errors.append("Nama customer sudah ada.")

    limit = _limit_kredit(data["limit_kredit"])
    if limit is None:
        errors.append("Limit kredit harus angka.")
    elif limit < 0:
        errors.append("Limit kredit tidak boleh negatif.")
    return errors


@application.route("/mastercustomer")
@wajib_role("admin")
def customers():
    return render_template("master_customers.html", items=M_Workshop().get_customers())


@application.route("/tambahmastercustomer", methods=["GET", "POST"])
@wajib_role("admin")
def customer_add():
    if request.method == "GET":
        return render_template("customer_form.html", customer=None, data=_empty_customer())

    data = _customer_data(request.form)
    errors = _customer_errors(data)
    if errors:
        for error in errors:
            flash(error, "error")
        return render_template("customer_form.html", customer=None, data=data)

    db_data = _customer_db(data)
    db_data["created_by"] = g.user.username
    db_data["updated_by"] = g.user.username
    db_data["dihapus"] = 0
    pesan = M_Workshop().add_customer(db_data)
    if pesan != "":
        flash("Kode atau nama customer sudah ada.", "error")
        return render_template("customer_form.html", customer=None, data=data)
    flash("Customer ditambahkan.", "success")
    return redirect("/mastercustomer")


@application.route("/ubahmastercustomer/<int:customer_id>", methods=["GET", "POST"])
@wajib_role("admin")
def customer_edit(customer_id):
    m = M_Workshop()
    customer = m.get_customer(customer_id)
    if customer is None:
        abort(404)
    if request.method == "POST":
        data = _customer_data(request.form)
        errors = _customer_errors(data, customer.id)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("customer_form.html", customer=customer, data=data)
        db_data = _customer_db(data)
        db_data["updated_by"] = g.user.username
        pesan = m.upd_customer(customer.id, db_data)
        if pesan != "":
            flash("Kode atau nama customer sudah ada.", "error")
            return render_template("customer_form.html", customer=customer, data=data)
        flash("Customer diperbarui.", "success")
        return redirect("/mastercustomer")
    return render_template(
        "customer_form.html", customer=customer, data=_customer_values(customer)
    )


@application.route("/aktifmastercustomer/<int:customer_id>", methods=["POST"])
@wajib_role("admin")
def customer_toggle(customer_id):
    m = M_Workshop()
    customer = m.get_customer(customer_id)
    if customer is None:
        abort(404)
    m.upd_customer_nonaktif(customer.id, not customer.discontinued)
    flash(
        "Customer %s." % ("dinonaktifkan" if not customer.discontinued else "diaktifkan"),
        "success",
    )
    return redirect("/mastercustomer")


@application.route("/hapusmastercustomer/<int:customer_id>", methods=["POST"])
@wajib_role("admin")
def customer_delete(customer_id):
    M_Workshop().del_customer(customer_id)
    flash("Customer dihapus.", "success")
    return redirect("/mastercustomer")


# ---------------------------- master user ----------------------------


def _user_data(form):
    return {
        "name": (form.get("name") or "").strip(),
        "username": (form.get("username") or "").strip(),
        "role": form.get("role") or "sales",
        "password": form.get("password") or "",
    }


def _user_errors(data, id=0):
    errors = []
    if not data["name"]:
        errors.append("Nama user wajib diisi.")
    elif len(data["name"]) > 120:
        errors.append("Nama user maksimal 120 karakter.")
    if not data["username"]:
        errors.append("Username wajib diisi.")
    elif len(data["username"]) > 50:
        errors.append("Username maksimal 50 karakter.")
    elif M_Workshop().cek_username(data["username"], id):
        errors.append("Username sudah dipakai.")
    if data["role"] not in ROLES:
        errors.append("Role tidak valid.")
    if id == 0 and not data["password"]:
        errors.append("Password wajib diisi.")
    return errors


@application.route("/masteruser")
@wajib_role("admin")
def users():
    role = request.args.get("role", "")
    if role not in ROLES:
        role = ""
    return render_template(
        "master_users.html",
        items=M_Workshop().get_users(role),
        roles=ROLES,
        role=role,
    )


@application.route("/tambahmasteruser", methods=["POST"])
@wajib_role("admin")
def user_add():
    data = _user_data(request.form)
    errors = _user_errors(data)
    if errors:
        for error in errors:
            flash(error, "error")
        return redirect("/masteruser")
    pesan = M_Workshop().add_user(
        data["name"], data["username"], data["role"], generate_password_hash(data["password"])
    )
    if pesan != "":
        flash("Username sudah dipakai.", "error")
    else:
        flash("User ditambahkan.", "success")
    return redirect("/masteruser")


@application.route("/ubahmasteruser/<int:user_id>", methods=["GET", "POST"])
@wajib_role("admin")
def user_edit(user_id):
    m = M_Workshop()
    user = m.get_user(user_id)
    if user is None:
        abort(404)
    if request.method == "POST":
        data = _user_data(request.form)
        errors = _user_errors(data, user.id)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("user_form.html", user=user, data=data, roles=ROLES)
        hash_baru = generate_password_hash(data["password"]) if data["password"] else ""
        pesan = m.upd_user(user.id, data["name"], data["username"], data["role"], hash_baru)
        if pesan != "":
            flash("Username sudah dipakai.", "error")
            return render_template("user_form.html", user=user, data=data, roles=ROLES)
        flash("User diperbarui.", "success")
        return redirect("/masteruser")
    data = {
        "name": user.name,
        "username": user.username,
        "role": user.role,
        "password": "",
    }
    return render_template("user_form.html", user=user, data=data, roles=ROLES)


@application.route("/aktifmasteruser/<int:user_id>", methods=["POST"])
@wajib_role("admin")
def user_toggle(user_id):
    m = M_Workshop()
    user = m.get_user(user_id)
    if user is None:
        abort(404)
    m.upd_user_aktif(user.id, not user.active)
    flash("User %s." % ("diaktifkan" if not user.active else "dinonaktifkan"), "success")
    return redirect("/masteruser")


if __name__ == "__main__":
    application.run(debug=True)
