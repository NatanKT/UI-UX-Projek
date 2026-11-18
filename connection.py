import os

import pymysql
import pymysql.cursors

# kredensial database: dari instance/config.py (tidak ikut GitHub) atau env
try:
    from instance.config import DB_HOST, DB_NAME, DB_PASS, DB_USER
except ImportError:
    DB_HOST, DB_USER, DB_PASS, DB_NAME = "", "", "", ""

DB_HOST = os.environ.get("DB_HOST", DB_HOST) or "localhost"
DB_USER = os.environ.get("DB_USER", DB_USER) or "root"
DB_PASS = os.environ.get("DB_PASS", DB_PASS)
DB_NAME = os.environ.get("DB_NAME", DB_NAME) or "erp_workshop"


# bersihkan tanda kutip biar SQL aman
def bersih(teks):
    teks = "" if teks is None else str(teks)
    return teks.replace("\\", "\\\\").replace("'", "''")


# koneksi dipakai ulang biar ga connect ulang tiap query
_basis = None


class database:
    def __init__(self):
        self.hasil = []

    def koneksi(self):
        global _basis
        if _basis is None:
            _basis = pymysql.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
        _basis.ping(reconnect=True)
        return _basis

    def baca_mysqlERP(self, sql):
        try:
            kursor = self.koneksi().cursor()
            kursor.execute(sql)
            hasil = kursor.fetchall()
            kursor.close()
            return hasil
        except Exception as e:
            print(e)

    def tulis_mysqlERP(self, sql):
        try:
            basis = self.koneksi()
            kursor = basis.cursor()
            kursor.execute(sql)
            basis.commit()
            kursor.close()
            return ""
        except Exception as e:
            return str(e)
