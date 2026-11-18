"""Master data + rumus penawaran.

Angka dari sheet "DATA WORKSHOP" & "Rumus Hitungan WS" (ERP Workshop2.xlsx).
DEFAULT_* cuma buat isi awal tabel master_* di MySQL; yang dipakai app
adalah variabel aktif di bawah, diisi dari database oleh muat_master().
"""

import json

# isi awal tabel master
DEFAULT_JENIS = ("Spareparts", "Project", "Reparasi")
DEFAULT_BENTUK = ("Rod / Cylinder", "Block", "Plate")

# nama proses: (kWh mesin, depresiasi mesin / jam)
DEFAULT_PROSES = {
    "Bubut": (4.25, 7645.54794520548),
    "Milling": (5.5, 12842.465753424658),
    "Wirecut": (13, 22465.753424657534),
    "Las": (5.225, 1917.8082191780823),
    "3D Print": (0.66, 3780.821917808219),
    "Grinding": (3.75, 8219.17808219178),
    "CNC Mill": (15, 31963.470319634704),
    "CNC Turn": (8, 6392.6940639269405),
    "Manual Grind": (0.5, 0),
    "Hardening": (15, 6392.6940639269405),
}

# (nama, bentuk, density kg/m3, harga Rp/kg)
DEFAULT_MATERIALS = (
    ("SKD 51 D20", "Rod / Cylinder", 8140, 350000),
    ("SKD 51 D15", "Rod / Cylinder", 8140, 350000),
    ("SKD 51 D10", "Rod / Cylinder", 8140, 350000),
    ("SS304 D 16", "Rod / Cylinder", 7930, 65000),
    ("SS304 D 18", "Rod / Cylinder", 7930, 65000),
    ("SKD 11 T 20 mm", "Block", 7700, 160000),
    ("SKD 11 T 25 mm", "Block", 7700, 160000),
    ("SKD 11 T 30 mm", "Block", 7700, 160000),
    ("SS304 T 20 mm", "Block", 7930, 65000),
    ("SS304 T 25 mm", "Block", 7930, 65000),
    ("SKD 11 T 2 mm", "Plate", 7700, 160000),
    ("SKD 11 T 3 mm", "Plate", 7700, 160000),
    ("SKD 11 T 4 mm", "Plate", 7700, 160000),
    ("SS304 T 2 mm", "Plate", 7930, 65000),
    ("SS304 T 3 mm", "Plate", 7930, 65000),
)

# nama consumable: harga satuan
DEFAULT_CONSUMABLES = {
    "Wire D 0.25": 83,
    "Wire D 0.30": 87,
    "Wire D 0.5": 83.25,
    "Insert Bubut WNMG 20": 59800,
    "Insert Bubut DCMT 20": 43500,
    "Insert Bubut CNMG 20": 75900,
    "Insert Bubut VNMG 20": 39600,
    "Insert Bubut MRMN 20": 39600,
    "Insert Bubut DGTR 20": 49500,
    "Insert Bubut WNMG 25": 59800,
    "Insert Bubut DCMT 25": 43500,
    "Insert Bubut CNMG 25": 75900,
    "Insert Bubut VNMG 25": 39600,
    "Insert Bubut MRMN 25": 39600,
    "Insert Bubut DGTR 25": 49500,
    "Endmill D16 4 Flute HSS": 650340,
    "Endmill D14 4 Flute HSS": 542250,
    "Endmill D12 4 Flute HSS": 409000,
    "Endmill D10 4 Flute HSS": 346500,
    "Endmill D8 4 Flute HSS": 316000,
    "Endmill D6 4 Flute HSS": 263500,
    "Endmill D5 4 Flute HSS": 293300,
    "Endmill D4 4 Flute HSS": 285000,
    "Endmill D3 4 Flute HSS": 275000,
    "Endmill D2.5 4 Flute HSS": 225000,
    "Endmill D16 4 Flute Carbide": 750000,
    "Endmill D14 4 Flute Carbide": 503100,
    "Endmill D20 4 Flute Carbide": 975000,
    "Endmill D10 4 Flute Carbide": 250000,
    "Endmill D8 4 Flute Carbide": 241960,
    "Endmill D6 4 Flute Carbide": 200000,
    "Endmill D5 4 Flute Carbide": 216000,
    "Endmill D4 4 Flute Carbide": 178000,
    "Endmill D3 4 Flute Carbide": 95000,
    "Endmill D2.5 4 Flute Carbide": 100000,
    "Drill Bit D10 HSS": 77500,
    "Drill Bit D8 HSS": 49600,
    "Drill Bit D6 HSS": 31300,
    "Drill Bit D5 HSS": 24850,
    "Drill Bit D4 HSS": 20500,
    "Drill Bit D3 HSS": 13100,
    "Drill Bit D2.5 HSS": 0,
    "Kawat Las 1.6": 135000,
    "Kawat las SS": 80,
    "Centre Drill D 3 HSS": 149000,
    "Centre Drill D 4 HSS": 277000,
    "Centre Drill D 5 HSS": 299000,
    "Centre Drill D 6 HSS": 1049000,
    "Centre Drill D 8 HSS": 229500,
    "Centre Drill D 10 HSS": 307.854,
    "Hand Tap M3": 70000,
    "Hand Tap M4": 92000,
    "Hand Tap M2.5": 24500,
    "Hand Tap M5": 116000,
    "Hand Tap M6": 120000,
    "Hand Tap M8": 158000,
    "Hand Tap M10": 175000,
    "Cutting wheel": 5500,
}

# biaya dasar
DEFAULT_BIAYA = {
    "operator_jam": 35357.142857142855,
    "listrik_kwh": 1132,
    "depresiasi_bangunan_jam": 14925.79908675799,
}

# versi aktif (diisi dari database)
PROSES = dict(DEFAULT_PROSES)
MATERIALS = list(DEFAULT_MATERIALS)
CONSUMABLES = dict(DEFAULT_CONSUMABLES)
JENIS = list(DEFAULT_JENIS)
BENTUK = list(DEFAULT_BENTUK)
BIAYA_OPERATOR_JAM = DEFAULT_BIAYA["operator_jam"]
BIAYA_LISTRIK_KWH = DEFAULT_BIAYA["listrik_kwh"]
DEPRESI_BANGUNAN_JAM = DEFAULT_BIAYA["depresiasi_bangunan_jam"]
PERSEN_DESIGN = 0.05


# isi tabel master dari DEFAULT_* kalau masih kosong (sekali saja)
def seed_master():
    from model_workshop import M_Workshop

    m = M_Workshop()
    if not m.get_master("proses"):
        for nama, (kwh, depre) in DEFAULT_PROSES.items():
            m.add_master("proses", {"nama": nama, "kwh": kwh, "depresiasi_jam": depre})
    if not m.get_master("material"):
        for n, b, d, h in DEFAULT_MATERIALS:
            m.add_master("material", {"nama": n, "bentuk": b, "density": d, "harga_kg": h})
    if not m.get_master("consumable"):
        for nama, harga in DEFAULT_CONSUMABLES.items():
            m.add_master("consumable", {"nama": nama, "harga": harga})
    biaya = m.get_biaya()
    for nama, nilai in DEFAULT_BIAYA.items():
        if nama not in biaya:
            m.add_biaya(nama, nilai)
    if not m.get_master("jenis") and not m.get_master("bentuk"):
        for nama in DEFAULT_JENIS:
            m.add_master("jenis", {"nama": nama})
        for nama in DEFAULT_BENTUK:
            m.add_master("bentuk", {"nama": nama})


# baca tabel master -> variabel aktif dipakai form & hitung()
def muat_master():
    global BIAYA_OPERATOR_JAM, BIAYA_LISTRIK_KWH, DEPRESI_BANGUNAN_JAM
    from model_workshop import M_Workshop

    m = M_Workshop()
    PROSES.clear()
    PROSES.update(
        {p.nama: (p.kwh, p.depresiasi_jam) for p in m.get_master("proses", True)}
    )
    MATERIALS[:] = [
        (p.nama, p.bentuk, p.density, p.harga_kg) for p in m.get_master("material", True)
    ]
    CONSUMABLES.clear()
    CONSUMABLES.update({p.nama: p.harga for p in m.get_master("consumable", True)})
    JENIS[:] = [p.nama for p in m.get_master("jenis", True)]
    BENTUK[:] = [p.nama for p in m.get_master("bentuk", True)]
    biaya = m.get_biaya()
    BIAYA_OPERATOR_JAM = biaya.get("operator_jam", BIAYA_OPERATOR_JAM)
    BIAYA_LISTRIK_KWH = biaya.get("listrik_kwh", BIAYA_LISTRIK_KWH)
    DEPRESI_BANGUNAN_JAM = biaya.get("depresiasi_bangunan_jam", DEPRESI_BANGUNAN_JAM)


def harga_material(nama):
    """(density, harga/kg) dari nama material, 0 kalau ga ketemu."""
    for n, _, density, harga in MATERIALS:
        if n == nama:
            return density, harga
    return 0, 0


def _baris(teks):
    """JSON kolom 'proses'/'consumables' -> list, aman kalau kosong/rusak."""
    try:
        return json.loads(teks or "[]")
    except (TypeError, ValueError):
        return []


def _volume(q):
    """Volume total (m3) termasuk jumlah item."""
    if (q.shape or "").startswith("Rod"):
        per_item = q.length * 3.141592653589793 * (q.diameter / 2) ** 2
    else:
        per_item = q.length * q.lebar * q.tebal
    return per_item * (q.qty or 0) / 1_000_000_000


def _toleransi(q):
    """Persentase toleransi material sesuai bentuk & ukuran."""
    if (q.shape or "").startswith("Rod"):
        if q.diameter < 10:
            return 0.40
        return 0.25 if q.diameter <= 20 else 0.15
    return 0.15 if q.length * q.lebar * q.tebal > 100_000 else 0.25


def hitung(q):
    """Semua angka estimasi penawaran, mengikuti rumus Excel."""
    rows = [
        (p.get("nama"), p.get("menit") or 0)
        for p in _baris(q.proses)
        if p.get("nama") in PROSES
    ]
    menit = sum(m for _, m in rows)
    rincian = [
        {
            "nama": n,
            "menit": m,
            "listrik": m / 60 * BIAYA_LISTRIK_KWH * PROSES[n][0],
            "depresiasi": m / 60 * PROSES[n][1],
        }
        for n, m in rows
    ]
    listrik = sum(r["listrik"] for r in rincian)
    depresiasi = sum(r["depresiasi"] for r in rincian)

    rincian_c = [
        {
            "nama": c.get("nama"),
            "qty": c.get("qty") or 0,
            "harga": CONSUMABLES.get(c.get("nama"), 0),
        }
        for c in _baris(q.consumables)
        if c.get("nama")
    ]
    for c in rincian_c:
        c["subtotal"] = c["qty"] * c["harga"]
    consumables = sum(c["subtotal"] for c in rincian_c)

    volume = _volume(q)
    total_volume = volume + _toleransi(q) * volume
    density, harga_kg = harga_material(q.material)
    material = total_volume * density * harga_kg

    tk = menit / 60 * BIAYA_OPERATOR_JAM * (q.operators or 0)
    bangunan = menit / 60 * 0.15 * DEPRESI_BANGUNAN_JAM
    bersih = consumables + material + tk + listrik + depresiasi

    qty = q.qty or 0
    harga = bersih * (1 + (q.ll1 or 0) + (q.ll2 or 0)) / (1 - q.rm) if q.rm < 1 else 0
    return {
        "menit": menit,
        "rincian": rincian,
        "rincian_consumables": rincian_c,
        "listrik": listrik,
        "depresiasi": depresiasi,
        "bangunan": bangunan,
        "tk": tk,
        "consumables": consumables,
        "volume": volume,
        "total_volume": total_volume,
        "material": material,
        "design": PERSEN_DESIGN * bersih,
        "bersih": bersih,
        "satuan": bersih / qty if qty else 0,
        "harga": harga,
        "harga_satuan": harga / qty if qty else 0,
    }
