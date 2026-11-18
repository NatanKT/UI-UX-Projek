from datetime import datetime
from types import SimpleNamespace

from connection import bersih, database

ROLES = {
    "admin": "Admin",
    "sales": "Sales",
    "approver": "Approver",
}

# kunci halaman master -> nama tabel
TABEL = {
    "proses": "master_proses",
    "material": "master_material",
    "consumable": "master_consumable",
    "jenis": "master_pilihan",
    "bentuk": "master_pilihan",
    "biaya": "master_biaya",
}


# ubah kolom tanggal jadi datetime (mysql ngasih datetime, sqlite ngasih teks)
def _waktu(nilai):
    if isinstance(nilai, datetime):
        return nilai
    if not nilai:
        return None
    return datetime.strptime(str(nilai)[:19], "%Y-%m-%d %H:%M:%S")


# baris tabel master -> objek yang bisa dibaca di template (item.nama, item.harga)
def _objek(baris):
    data = dict(baris)
    if "aktif" in data:
        data["aktif"] = bool(data["aktif"])
    return SimpleNamespace(**data)


def _user(baris):
    return SimpleNamespace(
        id=baris["id"],
        username=baris["username"],
        name=baris["name"],
        role=baris["role"],
        password_hash=baris["password_hash"],
        active=bool(baris["active"]),
        role_label=ROLES.get(baris["role"], baris["role"]),
    )


def _customer(baris):
    return SimpleNamespace(
        id=baris["id"],
        kode=baris["Kode"],
        nama=baris["Nama"],
        g_ng=baris["G_NG"],
        sales=baris["Sales"],
        telp=baris["Telp"],
        npwp=baris["NPWP"],
        created_by=baris["created_by"],
        updated_by=baris["updated_by"],
        dihapus=bool(baris["dihapus"]),
        limit_kredit=baris["LimitKredit"] or 0,
        top=baris["TOP"],
        alamat=baris["Alamat"],
        discontinued=bool(baris["discontinued"]),
        alamat_tagihan=baris["Alamat_Tagihan"],
        cara_bayar=baris["Cara_Bayar"],
        other_bayar=baris["Other_Bayar"],
        company=baris["Company"],
        bu=baris["BU"],
        kode_oracle=baris["Kode_Oracle"],
    )


def _quotation(baris):
    data = dict(baris)
    customer = None
    if data.get("customer_nama"):
        customer = SimpleNamespace(nama=data["customer_nama"])
    data["customer"] = customer
    data["design_baru"] = bool(data["design_baru"])
    data["created_at"] = _waktu(data["created_at"])
    data["updated_at"] = _waktu(data["updated_at"])
    return SimpleNamespace(**data)


class M_Workshop:
    def __init__(self):
        self.hasil = []

    # ambil satu baris, langsung diubah jadi objek
    def satu(self, sql, pembuat):
        hasil = database().baca_mysqlERP(sql) or []
        if not hasil:
            return None
        return pembuat(hasil[0])

    # susun "kolom='nilai', kolom='nilai'" buat UPDATE
    def susun_set(self, data):
        bagian = []
        for kolom, nilai in data.items():
            if nilai is None:
                bagian.append("%s=NULL" % kolom)
            else:
                bagian.append("%s='%s'" % (kolom, bersih(nilai)))
        return ", ".join(bagian)

    # susun "kolom, kolom" & "'nilai', 'nilai'" buat INSERT
    def susun_insert(self, data):
        kolom = ", ".join(data.keys())
        nilai = ", ".join(
            "NULL" if v is None else "'%s'" % bersih(v) for v in data.values()
        )
        return kolom, nilai

    # ---------------- user & login ----------------

    def get_datauser(self, username):
        sql = "SELECT * FROM users WHERE LOWER(username)=LOWER('%s') LIMIT 1" % bersih(username)
        return self.satu(sql, _user)

    def get_user(self, id):
        sql = "SELECT * FROM users WHERE id=%d LIMIT 1" % int(id)
        return self.satu(sql, _user)

    def get_users(self, role=""):
        sql = "SELECT * FROM users"
        if role != "":
            sql += " WHERE role='%s'" % bersih(role)
        sql += " ORDER BY name"
        return [_user(baris) for baris in database().baca_mysqlERP(sql) or []]

    def cek_username(self, username, id=0):
        sql = "SELECT id FROM users WHERE LOWER(username)=LOWER('%s') AND id<>%d" % (
            bersih(username),
            int(id),
        )
        return len(database().baca_mysqlERP(sql) or []) > 0

    def add_user(self, name, username, role, password_hash):
        sql = "INSERT INTO users (username, name, role, password_hash, active) VALUES ('%s','%s','%s','%s',1)" % (
            bersih(username),
            bersih(name),
            bersih(role),
            bersih(password_hash),
        )
        return database().tulis_mysqlERP(sql)

    def upd_user(self, id, name, username, role, password_hash=""):
        sql = "UPDATE users SET name='%s', username='%s', role='%s'" % (
            bersih(name),
            bersih(username),
            bersih(role),
        )
        if password_hash != "":
            sql += ", password_hash='%s'" % bersih(password_hash)
        sql += " WHERE id=%d" % int(id)
        return database().tulis_mysqlERP(sql)

    def upd_user_aktif(self, id, aktif):
        sql = "UPDATE users SET active=%d WHERE id=%d" % (
            1 if aktif else 0,
            int(id),
        )
        return database().tulis_mysqlERP(sql)

    # ---------------- customer ----------------

    def get_customer(self, id):
        sql = "SELECT * FROM customers WHERE id=%d LIMIT 1" % int(id)
        return self.satu(sql, _customer)

    def get_customers(self, aktif_saja=False):
        sql = "SELECT * FROM customers WHERE dihapus=0"
        if aktif_saja:
            sql += " AND discontinued=0"
        sql += " ORDER BY Nama"
        return [_customer(baris) for baris in database().baca_mysqlERP(sql) or []]

    def cek_kode_customer(self, kode, id=0):
        sql = "SELECT id FROM customers WHERE LOWER(Kode)=LOWER('%s') AND id<>%d" % (
            bersih(kode),
            int(id),
        )
        return len(database().baca_mysqlERP(sql) or []) > 0

    def cek_nama_customer(self, nama, id=0):
        sql = "SELECT id FROM customers WHERE LOWER(Nama)=LOWER('%s') AND id<>%d" % (
            bersih(nama),
            int(id),
        )
        return len(database().baca_mysqlERP(sql) or []) > 0

    def add_customer(self, data):
        kolom, nilai = self.susun_insert(data)
        sql = "INSERT INTO customers (%s) VALUES (%s)" % (kolom, nilai)
        return database().tulis_mysqlERP(sql)

    def upd_customer(self, id, data):
        sql = "UPDATE customers SET %s WHERE id=%d" % (self.susun_set(data), int(id))
        return database().tulis_mysqlERP(sql)

    def upd_customer_nonaktif(self, id, nonaktif):
        sql = "UPDATE customers SET discontinued=%d WHERE id=%d" % (
            1 if nonaktif else 0,
            int(id),
        )
        return database().tulis_mysqlERP(sql)

    def del_customer(self, id):
        sql = "UPDATE customers SET dihapus=1 WHERE id=%d" % int(id)
        return database().tulis_mysqlERP(sql)

    # ---------------- penawaran ----------------

    def get_quotation(self, id):
        sql = (
            "SELECT q.*, c.Nama AS customer_nama FROM quotations q "
            "LEFT JOIN customers c ON c.id=q.customer_id WHERE q.id=%d LIMIT 1" % int(id)
        )
        return self.satu(sql, _quotation)

    def get_quotations(self, kategori=""):
        sql = (
            "SELECT q.*, c.Nama AS customer_nama FROM quotations q "
            "LEFT JOIN customers c ON c.id=q.customer_id"
        )
        if kategori == "draft":
            sql += " WHERE q.status='draft'"
        elif kategori != "":
            sql += " WHERE q.status<>'draft'"
        sql += " ORDER BY q.updated_at DESC"
        return [_quotation(baris) for baris in database().baca_mysqlERP(sql) or []]

    # id & nomor baru: DRF-0001, DRF-0002, ...
    def get_nomor_baru(self):
        sql = "SELECT IFNULL(MAX(id),0)+1 AS id FROM quotations"
        hasil = database().baca_mysqlERP(sql) or [{"id": 1}]
        id = int(hasil[0]["id"])
        return id, "DRF-%04d" % id

    def add_quotation(self, data):
        kolom, nilai = self.susun_insert(data)
        sql = "INSERT INTO quotations (%s) VALUES (%s)" % (kolom, nilai)
        return database().tulis_mysqlERP(sql)

    def upd_quotation(self, id, data):
        sql = "UPDATE quotations SET %s WHERE id=%d" % (self.susun_set(data), int(id))
        return database().tulis_mysqlERP(sql)

    def del_quotation(self, id):
        sql = "DELETE FROM quotations WHERE id=%d" % int(id)
        return database().tulis_mysqlERP(sql)

    def upd_status_quotation(self, id, status, user):
        sql = "UPDATE quotations SET status='%s', updated_by='%s' WHERE id=%d" % (
            bersih(status),
            bersih(user),
            int(id),
        )
        return database().tulis_mysqlERP(sql)

    def get_item_unik(self):
        sql = "SELECT DISTINCT item FROM quotations WHERE item<>'' ORDER BY item"
        return [baris["item"] for baris in database().baca_mysqlERP(sql) or []]

    # ---------------- master ----------------

    def get_master(self, kunci, aktif_saja=False):
        sql = "SELECT * FROM %s" % TABEL[kunci]
        if kunci in ("jenis", "bentuk"):
            sql += " WHERE kategori='%s'" % bersih(kunci)
            if aktif_saja:
                sql += " AND aktif=1"
        elif aktif_saja:
            sql += " WHERE aktif=1"
        if kunci != "biaya":
            sql += " ORDER BY id"
        return [_objek(baris) for baris in database().baca_mysqlERP(sql) or []]

    def get_master_satu(self, kunci, id):
        sql = "SELECT * FROM %s WHERE id=%d LIMIT 1" % (TABEL[kunci], int(id))
        return self.satu(sql, _objek)

    def cek_nama_master(self, kunci, nama, id=0):
        sql = "SELECT id FROM %s WHERE LOWER(nama)=LOWER('%s') AND id<>%d" % (
            TABEL[kunci],
            bersih(nama),
            int(id),
        )
        if kunci in ("jenis", "bentuk"):
            sql += " AND kategori='%s'" % bersih(kunci)
        return len(database().baca_mysqlERP(sql) or []) > 0

    def add_master(self, kunci, data):
        if kunci in ("jenis", "bentuk"):
            data["kategori"] = kunci
        data["aktif"] = 1
        kolom, nilai = self.susun_insert(data)
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (TABEL[kunci], kolom, nilai)
        return database().tulis_mysqlERP(sql)

    def upd_master(self, kunci, id, data):
        sql = "UPDATE %s SET %s WHERE id=%d" % (
            TABEL[kunci],
            self.susun_set(data),
            int(id),
        )
        return database().tulis_mysqlERP(sql)

    def upd_master_aktif(self, kunci, id, aktif):
        sql = "UPDATE %s SET aktif=%d WHERE id=%d" % (
            TABEL[kunci],
            1 if aktif else 0,
            int(id),
        )
        return database().tulis_mysqlERP(sql)

    def del_master(self, kunci, id):
        sql = "DELETE FROM %s WHERE id=%d" % (TABEL[kunci], int(id))
        return database().tulis_mysqlERP(sql)

    # biaya dasar: operator_jam, listrik_kwh, depresiasi_bangunan_jam
    def get_biaya(self):
        sql = "SELECT * FROM master_biaya"
        return {baris["nama"]: baris["nilai"] for baris in database().baca_mysqlERP(sql) or []}

    def add_biaya(self, nama, nilai):
        sql = "INSERT INTO master_biaya (nama, nilai) VALUES ('%s','%s')" % (
            bersih(nama),
            bersih(nilai),
        )
        return database().tulis_mysqlERP(sql)
