from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

# ini konektor database, nanti dipasang ke app di app.py lewat db.init_app(app)
db = SQLAlchemy()

# daftar role yang valid, key = isi kolom 'role' di DB, value = label tampilan
ROLES = {
    "admin": "Admin",
    "sales": "Sales",
    "approver": "Approver",
}


# ini tabel 'customers' di database (master customer)
class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)  # id auto increment
    kode = db.Column("Kode", db.String(30), unique=True, nullable=False)  # kode customer, ga boleh dobel
    nama = db.Column("Nama", db.String(150), unique=True, nullable=False)  # nama customer, ga boleh dobel
    g_ng = db.Column("G_NG", db.String(10))
    sales = db.Column("Sales", db.String(100))
    telp = db.Column("Telp", db.String(40))
    npwp = db.Column("NPWP", db.String(40))
    created_by = db.Column("created_by", db.String(50))  # username yang bikin data
    updated_by = db.Column("updated_by", db.String(50))  # username yang terakhir ubah
    dihapus = db.Column("dihapus", db.Boolean, nullable=False, default=False)  # soft delete
    limit_kredit = db.Column("LimitKredit", db.Numeric(15, 2), nullable=False, default=0)
    top = db.Column("TOP", db.String(30))  # term of payment
    alamat = db.Column("Alamat", db.Text)
    discontinued = db.Column("discontinued", db.Boolean, nullable=False, default=False)  # nonaktif, ga muncul di form baru
    alamat_tagihan = db.Column("Alamat_Tagihan", db.Text)
    cara_bayar = db.Column("Cara_Bayar", db.String(50))
    other_bayar = db.Column("Other_Bayar", db.String(100))
    company = db.Column("Company", db.String(100))
    bu = db.Column("BU", db.String(50))
    kode_oracle = db.Column("Kode_Oracle", db.String(50))


# ini tabel 'quotations' (penawaran). status 'draft' = masih disimpan, belum dikirim
class Quotation(db.Model):
    __tablename__ = "quotations"

    id = db.Column(db.Integer, primary_key=True)
    nomor = db.Column(db.String(30), unique=True)  # DRF-0001, diisi setelah id didapat
    status = db.Column(db.String(20), nullable=False, default="draft")
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    sales = db.Column(db.String(100))
    item = db.Column(db.String(150))
    qty = db.Column(db.Integer, nullable=False, default=0)
    work = db.Column(db.String(50))
    notes = db.Column(db.Text)
    shape = db.Column(db.String(30))
    diameter = db.Column(db.Integer, nullable=False, default=0)
    length = db.Column(db.Integer, nullable=False, default=0)
    operators = db.Column(db.Integer, nullable=False, default=0)
    design_baru = db.Column(db.Boolean, nullable=False, default=False)
    material = db.Column(db.String(100))
    proses = db.Column(db.Text)  # JSON: daftar {nama, menit}
    consumables = db.Column(db.Text)  # JSON: daftar {nama, qty}
    created_by = db.Column(db.String(50))
    updated_by = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    customer = db.relationship("Customer")


# ini tabel 'users' di database (master user / login)
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)  # username login, ga boleh dobel
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="sales")  # harus ada di ROLES
    password_hash = db.Column(db.String(255), nullable=False)  # password disimpan sudah di-hash, bukan asli
    active = db.Column(db.Boolean, nullable=False, default=True)

    # dipanggil pas tambah/edit user, password di-hash dulu sebelum disimpan
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # dipanggil pas login, cek password yang diketik cocok atau ga
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # buat nampilin label role yang enak dibaca (contoh: "admin" -> "Admin")
    @property
    def role_label(self):
        return ROLES.get(self.role, self.role)
