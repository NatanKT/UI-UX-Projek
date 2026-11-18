-- Struktur database ERP Workshop (MySQL).
-- Import sekali di database kosong: mysql -u user -p erp_workshop < erp_workshop.sql
-- Isi master (proses/material/consumable) otomatis diisi aplikasi saat pertama jalan.

CREATE TABLE IF NOT EXISTS users (
  id int(11) NOT NULL AUTO_INCREMENT,
  username varchar(50) NOT NULL,
  name varchar(120) NOT NULL,
  role varchar(20) NOT NULL,
  password_hash varchar(255) NOT NULL,
  active tinyint(1) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS customers (
  id int(11) NOT NULL AUTO_INCREMENT,
  Kode varchar(30) NOT NULL,
  Nama varchar(150) NOT NULL,
  G_NG varchar(10) DEFAULT NULL,
  Sales varchar(100) DEFAULT NULL,
  Telp varchar(40) DEFAULT NULL,
  NPWP varchar(40) DEFAULT NULL,
  created_by varchar(50) DEFAULT NULL,
  updated_by varchar(50) DEFAULT NULL,
  dihapus tinyint(1) NOT NULL DEFAULT 0,
  LimitKredit decimal(15,2) NOT NULL DEFAULT 0.00,
  TOP varchar(30) DEFAULT NULL,
  Alamat text DEFAULT NULL,
  discontinued tinyint(1) NOT NULL DEFAULT 0,
  Alamat_Tagihan text DEFAULT NULL,
  Cara_Bayar varchar(50) DEFAULT NULL,
  Other_Bayar varchar(100) DEFAULT NULL,
  Company varchar(100) DEFAULT NULL,
  BU varchar(50) DEFAULT NULL,
  Kode_Oracle varchar(50) DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_customers_kode (Kode),
  UNIQUE KEY uq_customers_nama (Nama)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quotations (
  id int(11) NOT NULL AUTO_INCREMENT,
  nomor varchar(30) DEFAULT NULL,
  status varchar(20) NOT NULL,
  customer_id int(11) DEFAULT NULL,
  sales varchar(100) DEFAULT NULL,
  item varchar(150) DEFAULT NULL,
  qty int(11) NOT NULL,
  work varchar(50) DEFAULT NULL,
  notes text DEFAULT NULL,
  shape varchar(30) DEFAULT NULL,
  diameter int(11) NOT NULL,
  length int(11) NOT NULL,
  operators int(11) NOT NULL,
  design_baru tinyint(1) NOT NULL,
  material varchar(100) DEFAULT NULL,
  proses text DEFAULT NULL,
  consumables text DEFAULT NULL,
  created_by varchar(50) DEFAULT NULL,
  updated_by varchar(50) DEFAULT NULL,
  created_at datetime NOT NULL,
  updated_at datetime NOT NULL,
  tebal int(11) NOT NULL DEFAULT 0,
  lebar int(11) NOT NULL DEFAULT 0,
  ll1 float NOT NULL DEFAULT 0.05,
  ll2 float NOT NULL DEFAULT 0.01,
  rm float NOT NULL DEFAULT 0.1,
  PRIMARY KEY (id),
  UNIQUE KEY nomor (nomor),
  KEY customer_id (customer_id),
  CONSTRAINT quotations_ibfk_1 FOREIGN KEY (customer_id) REFERENCES customers (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS master_proses (
  id int(11) NOT NULL AUTO_INCREMENT,
  nama varchar(50) NOT NULL,
  kwh float NOT NULL,
  depresiasi_jam float NOT NULL,
  aktif tinyint(1) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY nama (nama)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS master_material (
  id int(11) NOT NULL AUTO_INCREMENT,
  nama varchar(100) NOT NULL,
  bentuk varchar(30) NOT NULL,
  density float NOT NULL,
  harga_kg float NOT NULL,
  aktif tinyint(1) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY nama (nama)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS master_consumable (
  id int(11) NOT NULL AUTO_INCREMENT,
  nama varchar(150) NOT NULL,
  harga float NOT NULL,
  aktif tinyint(1) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY nama (nama)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS master_biaya (
  nama varchar(50) NOT NULL,
  nilai float NOT NULL,
  PRIMARY KEY (nama)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS master_pilihan (
  id int(11) NOT NULL AUTO_INCREMENT,
  kategori varchar(20) NOT NULL,
  nama varchar(50) NOT NULL,
  aktif tinyint(1) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY kategori (kategori, nama)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
