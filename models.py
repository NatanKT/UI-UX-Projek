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
    name = db.Column(db.String(150), unique=True, nullable=False)  # nama customer, ga boleh dobel
    active = db.Column(db.Boolean, nullable=False, default=True)  # aktif/nonaktif, default aktif


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
