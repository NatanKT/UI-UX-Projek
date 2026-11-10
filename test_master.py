import os
import tempfile
import unittest

# Arahkan database ke file sementara sebelum app diimpor.
# ini penting biar test ga nembak MySQL asli / sqlite produksi
_tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp.name, "test.db").replace("\\", "/")
os.environ["SECRET_KEY"] = "test"

from app import app  # noqa: E402
from models import Customer, User, db  # noqa: E402


# base class buat semua test: siapkan db kosong + login sebagai admin
class MasterTest(unittest.TestCase):
    def setUp(self):  # dijalankan sebelum tiap test
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()   # bersihkan tabel
        db.create_all() # bikin tabel baru
        admin = User(
            username="testadmin", name="Test Admin", role="admin", active=True
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        self.client = app.test_client()
        self.client.post(  # login sebagai admin dulu
            "/login", data={"username": "testadmin", "password": "admin123"}
        )

    def tearDown(self):  # dijalankan setelah tiap test
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    # helper: submit form tambah customer
    def add_customer(self, kode, nama, **extra):
        data = {"kode": kode, "nama": nama}
        data.update(extra)
        return self.client.post(
            "/master/customers/add", data=data, follow_redirects=True
        )

    # helper: submit form tambah user
    def add_user(self, name, username, role, password):
        return self.client.post(
            "/master/users/add",
            data={
                "name": name,
                "username": username,
                "role": role,
                "password": password,
            },
            follow_redirects=True,
        )


class CustomerMasterTest(MasterTest):
    # test: tambah customer valid -> muncul di daftar & tersimpan lengkap
    def test_tambah_customer(self):
        response = self.add_customer(
            "C-001",
            "PT Maju Jaya",
            sales="Rina",
            telp="021-123",
            limit_kredit="5000000",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PT Maju Jaya", response.data)
        customer = Customer.query.one()
        self.assertEqual(customer.kode, "C-001")
        self.assertEqual(str(customer.limit_kredit), "5000000.00")
        self.assertEqual(customer.created_by, "testadmin")
        self.assertEqual(customer.updated_by, "testadmin")
        self.assertFalse(customer.dihapus)

    # test: kode/nama kosong ditolak + kode/nama dobel (beda huruf besar/kecil) ditolak
    def test_kode_nama_kosong_dan_duplikat_ditolak(self):
        self.add_customer("", "")
        self.add_customer("C-001", "PT Maju Jaya")
        response = self.add_customer("c-001", "PT Maju Jaya")
        self.assertIn(b"Kode customer sudah ada.", response.data)
        self.assertIn(b"Nama customer sudah ada.", response.data)
        self.assertEqual(Customer.query.count(), 1)

    # test: ubah customer, nonaktifkan, lalu soft delete (hilang dari daftar)
    def test_ubah_nonaktifkan_dan_hapus_customer(self):
        self.add_customer("C-001", "PT Lama")
        customer = Customer.query.one()
        self.client.post(
            f"/master/customers/{customer.id}/edit",
            data={"kode": "C-001", "nama": "PT Baru", "limit_kredit": "1000"},
        )
        customer = db.session.get(Customer, customer.id)
        self.assertEqual(customer.nama, "PT Baru")
        self.assertEqual(str(customer.limit_kredit), "1000.00")
        self.assertEqual(customer.updated_by, "testadmin")

        self.client.post(f"/master/customers/{customer.id}/toggle")
        self.assertTrue(db.session.get(Customer, customer.id).discontinued)

        self.client.post(f"/master/customers/{customer.id}/delete")
        self.assertTrue(db.session.get(Customer, customer.id).dihapus)
        response = self.client.get("/master/customers")
        self.assertNotIn(b"PT Baru", response.data)


class UserMasterTest(MasterTest):
    # test: tambah user, pastikan password disimpan sebagai hash (bukan asli)
    def test_tambah_user_dan_password_di_hash(self):
        response = self.add_user("Rina Sales", "rina", "sales", "rahasia")
        self.assertIn(b"Rina Sales", response.data)
        user = User.query.filter_by(username="rina").one()
        self.assertEqual(user.role, "sales")
        self.assertNotEqual(user.password_hash, "rahasia")  # bukan plaintext
        self.assertTrue(user.check_password("rahasia"))

    # test: username dobel (beda huruf besar/kecil) ditolak
    def test_username_duplikat_ditolak(self):
        self.add_user("Rina Sales", "rina", "sales", "rahasia")
        response = self.add_user("Rina Lain", "RINA", "admin", "rahasia")
        self.assertIn(b"Username sudah dipakai.", response.data)
        self.assertEqual(User.query.filter_by(username="rina").count(), 1)

    # test: filter role, ubah user, nonaktifkan user
    def test_filter_role_ubah_dan_nonaktifkan(self):
        self.add_user("Admin Satu", "admin", "admin", "admin123")
        self.add_user("Sales Satu", "sales", "sales", "sales123")

        # filter ?role=admin -> cuma admin yang muncul
        response = self.client.get("/master/users?role=admin")
        self.assertIn(b"Admin Satu", response.data)
        self.assertNotIn(b"Sales Satu", response.data)

        # ubah user sales -> ganti role jadi approver, password dikosongkan (tetap)
        user = User.query.filter_by(role="sales").one()
        self.client.post(
            f"/master/users/{user.id}/edit",
            data={
                "name": "Sales Baru",
                "username": "sales",
                "role": "approver",
                "password": "",
            },
        )
        user = db.session.get(User, user.id)
        self.assertEqual(user.name, "Sales Baru")
        self.assertEqual(user.role, "approver")
        self.assertTrue(user.check_password("sales123"))  # password lama masih berlaku

        self.client.post(f"/master/users/{user.id}/toggle")
        self.assertFalse(db.session.get(User, user.id).active)


class AuthTest(MasterTest):
    # test: belum login -> akses master diarahkan ke /login
    def test_halaman_master_wajib_login(self):
        self.client.post("/logout")
        response = self.client.get("/master/customers")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    # test: login pakai password salah -> ditolak (401)
    def test_login_salah(self):
        self.client.post("/logout")
        response = self.client.post(
            "/login", data={"username": "testadmin", "password": "salah"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Username atau password salah.", response.data)

    # test: user role sales ga boleh buka halaman master
    def test_sales_tidak_boleh_akses_master(self):
        sales = User(username="salesx", name="Sales X", role="sales", active=True)
        sales.set_password("sales123")
        db.session.add(sales)
        db.session.commit()

        self.client.post("/logout")
        response = self.client.post(
            "/login",
            data={"username": "salesx", "password": "sales123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/master/users", follow_redirects=True)
        self.assertIn(b"tidak punya akses", response.data)

    # test: logout -> muncul pesan keluar & master jadi 302 lagi
    def test_logout(self):
        response = self.client.post("/logout", follow_redirects=True)
        self.assertIn(b"Anda sudah keluar.", response.data)
        self.assertEqual(self.client.get("/master/users").status_code, 302)


if __name__ == "__main__":
    unittest.main()
