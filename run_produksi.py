from app import application

# server produksi: debug dimatikan, bisa diakses dari luar
application.run(host="0.0.0.0", port=8099, debug=False)
