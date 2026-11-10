import sqlite3

# script buat cek isi database secara manual (debug)
# CATATAN: sekarang app pakai MySQL (lihat instance/config.py), jadi file sqlite ini
# cuma berisi data lama sebelum config.py ditambahkan. Kalau mau cek data live,
# query ke MySQL di server (lihat instance/config.py).

db = sqlite3.connect("instance/ui_ux.db")
# ambil daftar nama tabel yang ada
print("Tabel:", [row[0] for row in db.execute("select name from sqlite_master where type='table'")])
# isi tabel customers
print("Customer:", db.execute("select id, Kode, Nama, LimitKredit, dihapus, discontinued from customers").fetchall())
# isi tabel users (password ga ditampilkan, cuma id/nama/username/role/status)
print("User:", db.execute("select id, name, username, role, active from users").fetchall())
