import json
import os
import sqlite3
import sys
import tempfile
import unittest
from types import SimpleNamespace

os.environ["SECRET_KEY"] = "test"

sys.path.append("./Model")
import model_workshop  # noqa: E402

_tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
_path = os.path.join(_tmp.name, "test.db")

TABEL_UJI = (
    "users",
    "customers",
    "quotations",
    "master_proses",
    "master_material",
    "master_consumable",
    "master_biaya",
    "master_pilihan",
)

SKEMA = """
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  active INTEGER NOT NULL
);
CREATE TABLE customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  Kode TEXT UNIQUE NOT NULL,
  Nama TEXT UNIQUE NOT NULL,
  G_NG TEXT, Sales TEXT, Telp TEXT, NPWP TEXT,
  created_by TEXT, updated_by TEXT,
  dihapus INTEGER NOT NULL DEFAULT 0,
  LimitKredit NUMERIC NOT NULL DEFAULT 0,
  TOP TEXT, Alamat TEXT,
  discontinued INTEGER NOT NULL DEFAULT 0,
  Alamat_Tagihan TEXT, Cara_Bayar TEXT, Other_Bayar TEXT,
  Company TEXT, BU TEXT, Kode_Oracle TEXT
);
CREATE TABLE quotations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nomor TEXT UNIQUE,
  status TEXT NOT NULL,
  customer_id INTEGER,
  sales TEXT, item TEXT,
  qty INTEGER NOT NULL,
  work TEXT, notes TEXT, shape TEXT,
  diameter INTEGER NOT NULL,
  length INTEGER NOT NULL,
  operators INTEGER NOT NULL,
  design_baru INTEGER NOT NULL,
  material TEXT, proses TEXT, consumables TEXT,
  created_by TEXT, updated_by TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  tebal INTEGER NOT NULL DEFAULT 0,
  lebar INTEGER NOT NULL DEFAULT 0,
  ll1 REAL NOT NULL DEFAULT 0.05,
  ll2 REAL NOT NULL DEFAULT 0.01,
  rm REAL NOT NULL DEFAULT 0.1
);
CREATE TABLE master_proses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nama TEXT UNIQUE NOT NULL,
  kwh REAL NOT NULL, depresiasi_jam REAL NOT NULL, aktif INTEGER NOT NULL
);
CREATE TABLE master_material (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nama TEXT UNIQUE NOT NULL,
  bentuk TEXT NOT NULL, density REAL NOT NULL, harga_kg REAL NOT NULL,
  aktif INTEGER NOT NULL
);
CREATE TABLE master_consumable (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nama TEXT UNIQUE NOT NULL, harga REAL NOT NULL, aktif INTEGER NOT NULL
);
CREATE TABLE master_biaya (nama TEXT PRIMARY KEY, nilai REAL NOT NULL);
CREATE TABLE master_pilihan (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kategori TEXT NOT NULL, nama TEXT NOT NULL, aktif INTEGER NOT NULL,
  UNIQUE (kategori, nama)
);
"""


# pengganti connection.database buat test: pakai sqlite, nama method sama
class DBSqlite:
    def __init__(self):
        self.hasil = []

    def koneksi(self):
        basis = sqlite3.connect(_path)
        basis.row_factory = sqlite3.Row
        return basis

    def baca_mysqlERP(self, sql):
        try:
            basis = self.koneksi()
            hasil = [dict(baris) for baris in basis.execute(sql).fetchall()]
            basis.close()
            return hasil
        except Exception as e:
            print(e)

    def tulis_mysqlERP(self, sql):
        try:
            basis = self.koneksi()
            basis.execute(sql)
            basis.commit()
            basis.close()
            return ""
        except Exception as e:
            return str(e)


def reset_db():
    basis = sqlite3.connect(_path)
    for tabel in TABEL_UJI:
        basis.execute("DROP TABLE IF EXISTS %s" % tabel)
    basis.executescript(SKEMA)
    basis.commit()
    basis.close()


# pasang pengganti sebelum app diimport
model_workshop.database = DBSqlite
reset_db()

from app import application  # noqa: E402
import workshop  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

M = model_workshop.M_Workshop


class MasterTest(unittest.TestCase):
    def setUp(self):
        reset_db()
        workshop.seed_master()
        workshop.muat_master()
        M().add_user("Test Admin", "testadmin", "admin", generate_password_hash("admin123"))
        self.client = application.test_client()
        self.client.post("/login", data={"username": "testadmin", "password": "admin123"})

    def add_customer(self, kode, nama, **extra):
        data = {"kode": kode, "nama": nama}
        data.update(extra)
        return self.client.post("/tambahmastercustomer", data=data, follow_redirects=True)

    def add_user(self, name, username, role, password):
        return self.client.post(
            "/tambahmasteruser",
            data={"name": name, "username": username, "role": role, "password": password},
            follow_redirects=True,
        )


class CustomerMasterTest(MasterTest):
    def test_tambah_customer(self):
        response = self.add_customer(
            "C-001", "PT Maju Jaya", sales="Rina", telp="021-123", limit_kredit="5000000"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PT Maju Jaya", response.data)
        customer = M().get_customers()[0]
        self.assertEqual(customer.kode, "C-001")
        self.assertAlmostEqual(float(customer.limit_kredit), 5000000)
        self.assertEqual(customer.created_by, "testadmin")
        self.assertEqual(customer.updated_by, "testadmin")
        self.assertFalse(customer.dihapus)

    def test_kode_nama_kosong_dan_duplikat_ditolak(self):
        self.add_customer("", "")
        self.add_customer("C-001", "PT Maju Jaya")
        response = self.add_customer("c-001", "PT Maju Jaya")
        self.assertIn(b"Kode customer sudah ada.", response.data)
        self.assertIn(b"Nama customer sudah ada.", response.data)
        self.assertEqual(len(M().get_customers()), 1)

    def test_ubah_nonaktifkan_dan_hapus_customer(self):
        self.add_customer("C-001", "PT Lama")
        customer = M().get_customers()[0]
        self.client.post(
            "/ubahmastercustomer/%d" % customer.id,
            data={"kode": "C-001", "nama": "PT Baru", "limit_kredit": "1000"},
        )
        customer = M().get_customer(customer.id)
        self.assertEqual(customer.nama, "PT Baru")
        self.assertAlmostEqual(float(customer.limit_kredit), 1000)
        self.assertEqual(customer.updated_by, "testadmin")

        self.client.post("/aktifmastercustomer/%d" % customer.id)
        self.assertTrue(M().get_customer(customer.id).discontinued)

        self.client.post("/hapusmastercustomer/%d" % customer.id)
        self.assertTrue(M().get_customer(customer.id).dihapus)
        self.assertNotIn(b"PT Baru", self.client.get("/mastercustomer").data)


class MasterDataTest(MasterTest):
    def test_kelola_proses(self):
        response = self.client.post(
            "/tambahmasterproses",
            data={"nama": "EDM", "kwh": "9.5", "depresiasi_jam": "15000"},
            follow_redirects=True,
        )
        self.assertIn(b"EDM", response.data)
        proses = [p for p in M().get_master("proses") if p.nama == "EDM"][0]
        self.assertIn("EDM", workshop.PROSES)

        self.client.post(
            "/ubahmasterproses/%d" % proses.id,
            data={"nama": "EDM Kawat", "kwh": "10", "depresiasi_jam": "16000"},
            follow_redirects=True,
        )
        self.assertNotIn("EDM", workshop.PROSES)
        self.assertEqual(workshop.PROSES["EDM Kawat"], (10, 16000))

        self.client.post("/aktifmasterproses/%d" % proses.id, follow_redirects=True)
        self.assertNotIn("EDM Kawat", workshop.PROSES)

        self.client.post("/hapusmasterproses/%d" % proses.id, follow_redirects=True)
        self.assertEqual(len([p for p in M().get_master("proses") if p.id == proses.id]), 0)

    def test_consumable_dobel_dan_harga(self):
        self.client.post(
            "/tambahmasterconsumable",
            data={"nama": "Coolant X", "harga": "25000"},
            follow_redirects=True,
        )
        self.assertEqual(workshop.CONSUMABLES["Coolant X"], 25000)
        response = self.client.post(
            "/tambahmasterconsumable",
            data={"nama": "coolant x", "harga": "30000"},
            follow_redirects=True,
        )
        self.assertIn(b"Nama sudah ada.", response.data)
        self.assertEqual(len([c for c in M().get_master("consumable") if c.nama == "Coolant X"]), 1)


    def test_material_bentuk_bebas_teks(self):
        response = self.client.post(
            "/tambahmastermaterial",
            data={"nama": "Besi Bulat", "bentuk": "Bulat", "density": "7850", "harga_kg": "20000"},
            follow_redirects=True,
        )
        self.assertIn(b"Besi Bulat", response.data)
        material = [m for m in M().get_master("material") if m.nama == "Besi Bulat"][0]
        self.assertEqual(material.bentuk, "Bulat")

        response = self.client.post(
            "/tambahmastermaterial",
            data={"nama": "Salah Angka", "bentuk": "Bulat", "density": "abc", "harga_kg": "1"},
            follow_redirects=True,
        )
        self.assertIn(b"Density", response.data)
        self.assertEqual(len([m for m in M().get_master("material") if m.nama == "Salah Angka"]), 0)


class UserMasterTest(MasterTest):
    def test_tambah_user_dan_password_di_hash(self):
        response = self.add_user("Rina Sales", "rina", "sales", "rahasia")
        self.assertIn(b"Rina Sales", response.data)
        user = M().get_datauser("rina")
        self.assertEqual(user.role, "sales")
        self.assertNotEqual(user.password_hash, "rahasia")
        from werkzeug.security import check_password_hash

        self.assertTrue(check_password_hash(user.password_hash, "rahasia"))

    def test_username_duplikat_ditolak(self):
        self.add_user("Rina Sales", "rina", "sales", "rahasia")
        response = self.add_user("Rina Lain", "RINA", "admin", "rahasia")
        self.assertIn(b"Username sudah dipakai.", response.data)
        self.assertEqual(len([u for u in M().get_users() if u.username.lower() == "rina"]), 1)

    def test_filter_role_ubah_dan_nonaktifkan(self):
        self.add_user("Admin Satu", "admin", "admin", "admin123")
        self.add_user("Sales Satu", "sales", "sales", "sales123")

        response = self.client.get("/masteruser?role=admin")
        self.assertIn(b"Admin Satu", response.data)
        self.assertNotIn(b"Sales Satu", response.data)

        user = [u for u in M().get_users() if u.role == "sales"][0]
        self.client.post(
            "/ubahmasteruser/%d" % user.id,
            data={"name": "Sales Baru", "username": "sales", "role": "approver", "password": ""},
        )
        user = M().get_user(user.id)
        self.assertEqual(user.name, "Sales Baru")
        self.assertEqual(user.role, "approver")
        from werkzeug.security import check_password_hash

        self.assertTrue(check_password_hash(user.password_hash, "sales123"))

        self.client.post("/aktifmasteruser/%d" % user.id)
        self.assertFalse(M().get_user(user.id).active)


class QuotationDraftTest(MasterTest):
    def draft_data(self, **extra):
        data = {
            "item": "LOCKING BOLT",
            "qty": "5",
            "work": "Spareparts",
            "notes": "catatan",
            "shape": "Rod / Cylinder",
            "diameter": "12",
            "length": "100",
            "tebal": "0",
            "lebar": "0",
            "operators": "2",
            "design_baru": "on",
            "material": "SKD 51 D20",
            "ll1": "5",
            "ll2": "1",
            "rm": "10",
            "proses_nama": ["Bubut", "Milling"],
            "proses_menit": ["30", "15"],
            "consumable_nama": ["Wire D 0.25"],
            "consumable_qty": ["2"],
        }
        data.update(extra)
        return data

    def test_simpan_draft_lalu_ubah_dan_hapus(self):
        self.add_customer("C-001", "PT Maju Jaya")
        customer = M().get_customers()[0]

        response = self.client.post(
            "/formpenawaran",
            data=self.draft_data(customer=str(customer.id)),
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Draft penawaran disimpan.", response.data)

        quotation = M().get_quotations("draft")[0]
        self.assertEqual(quotation.nomor, "DRF-0001")
        self.assertEqual(quotation.status, "draft")
        self.assertEqual(quotation.customer.nama, "PT Maju Jaya")
        self.assertEqual(quotation.qty, 5)
        self.assertTrue(quotation.design_baru)
        self.assertEqual(json.loads(quotation.proses)[1], {"nama": "Milling", "menit": 15})
        self.assertEqual(json.loads(quotation.consumables), [{"nama": "Wire D 0.25", "qty": 2}])
        self.assertEqual(quotation.created_by, "testadmin")

        response = self.client.get("/")
        self.assertIn(b"DRF-0001", response.data)
        self.assertIn(b"LOCKING BOLT", response.data)

        response = self.client.get("/ubahpenawaran/%d" % quotation.id)
        self.assertIn(b"LOCKING BOLT", response.data)

        self.client.post(
            "/ubahpenawaran/%d" % quotation.id,
            data=self.draft_data(item="BOLT BARU", qty="9"),
            follow_redirects=True,
        )
        quotation = M().get_quotation(quotation.id)
        self.assertEqual(quotation.item, "BOLT BARU")
        self.assertEqual(quotation.qty, 9)
        self.assertEqual(quotation.updated_by, "testadmin")

        self.client.post("/hapuspenawaran/%d" % quotation.id, follow_redirects=True)
        self.assertEqual(len(M().get_quotations()), 0)
        self.assertNotIn(b"DRF-0001", self.client.get("/").data)

    def test_draft_boleh_kosong(self):
        response = self.client.post("/formpenawaran", data={}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(M().get_quotations()), 1)

    def test_alur_approval(self):
        self.client.post("/formpenawaran", data=self.draft_data(), follow_redirects=True)
        quotation = M().get_quotations("draft")[0]
        self.client.post("/ajukanpenawaran/%d" % quotation.id, follow_redirects=True)
        self.assertEqual(M().get_quotation(quotation.id).status, "submitted")

        self.client.post(
            "/putuspenawaran/%d" % quotation.id,
            data={"status": "approved"},
            follow_redirects=True,
        )
        self.assertEqual(M().get_quotation(quotation.id).status, "approved")
        self.assertIn(b"Harga jual", self.client.get("/detailpenawaran/%d" % quotation.id).data)


class HitungTest(unittest.TestCase):
    def test_rumus_sesuai_excel(self):
        q = SimpleNamespace(
            shape="Rod / Cylinder",
            diameter=20,
            length=150,
            tebal=0,
            lebar=0,
            qty=24,
            operators=2,
            material="SKD 11 T 20 mm",
            ll1=0.05,
            ll2=0.01,
            rm=0.10,
            proses=json.dumps(
                [
                    {"nama": "Bubut", "menit": 650},
                    {"nama": "Milling", "menit": 775},
                    {"nama": "Wirecut", "menit": 480},
                    {"nama": "Hardening", "menit": 1350},
                ]
            ),
            consumables=json.dumps(
                [
                    {"nama": "Insert Bubut DCMT 25", "qty": 7},
                    {"nama": "Wire D 0.25", "qty": 15000},
                ]
            ),
        )
        h = workshop.hitung(q)
        self.assertAlmostEqual(h["menit"], 3255)
        self.assertAlmostEqual(h["volume"], 0.0011309733552923255, places=12)
        self.assertAlmostEqual(h["total_volume"], 0.0014137166941154068, places=12)
        self.assertAlmostEqual(h["tk"], 3836250, places=2)
        self.assertAlmostEqual(h["listrik"], 632316.33, delta=0.01)
        self.assertAlmostEqual(h["depresiasi"], 572270.26, delta=0.01)
        self.assertAlmostEqual(h["consumables"], 1549500, places=2)
        self.assertAlmostEqual(h["material"], 1741698.97, delta=0.01)
        self.assertAlmostEqual(h["bersih"], 8332035.56, delta=1)
        self.assertAlmostEqual(h["harga"], 9813286.33, delta=1)

    def test_volume_block(self):
        q = SimpleNamespace(
            shape="Block",
            diameter=0,
            length=100,
            lebar=100,
            tebal=20,
            qty=2,
            operators=0,
            material="SKD 11 T 20 mm",
            ll1=0,
            ll2=0,
            rm=0.10,
            proses="[]",
            consumables="[]",
        )
        h = workshop.hitung(q)
        self.assertAlmostEqual(h["volume"], 0.0004, places=12)
        self.assertAlmostEqual(h["total_volume"], 0.00046, places=12)


class AuthTest(MasterTest):
    def test_halaman_master_wajib_login(self):
        self.client.post("/logout")
        response = self.client.get("/mastercustomer")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_login_salah(self):
        self.client.post("/logout")
        response = self.client.post("/login", data={"username": "testadmin", "password": "salah"})
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Username atau password salah.", response.data)

    def test_sales_tidak_boleh_akses_master(self):
        M().add_user("Sales X", "salesx", "sales", generate_password_hash("sales123"))
        self.client.post("/logout")
        self.client.post(
            "/login",
            data={"username": "salesx", "password": "sales123"},
            follow_redirects=True,
        )
        response = self.client.get("/masteruser", follow_redirects=True)
        self.assertIn(b"tidak punya akses", response.data)

    def test_logout(self):
        response = self.client.post("/logout", follow_redirects=True)
        self.assertIn(b"Anda sudah keluar.", response.data)
        self.assertEqual(self.client.get("/masteruser").status_code, 302)


if __name__ == "__main__":
    unittest.main()
