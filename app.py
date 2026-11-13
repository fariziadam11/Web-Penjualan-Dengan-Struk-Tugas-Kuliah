import sqlite3
from datetime import datetime

from flask import Flask, abort, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["DB"] = "toko.db"

NAMA_TOKO = "Toko Maju Jaya"

PRODUK_AWAL = [
    ("Beras 5 kg", 72000, 20),
    ("Minyak Goreng 1 L", 18000, 30),
    ("Gula Pasir 1 kg", 17500, 25),
    ("Telur 1 kg", 28000, 15),
    ("Mie Instan", 3500, 100),
    ("Kopi Sachet", 1500, 200),
]


def db():
    conn = sqlite3.connect(app.config["DB"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS produk (
                id INTEGER PRIMARY KEY, nama TEXT NOT NULL,
                harga INTEGER NOT NULL, stok INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS transaksi (
                id INTEGER PRIMARY KEY, waktu TEXT NOT NULL,
                total INTEGER NOT NULL, bayar INTEGER NOT NULL, kembali INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS detail (
                transaksi_id INTEGER NOT NULL REFERENCES transaksi(id),
                nama TEXT NOT NULL, harga INTEGER NOT NULL,
                jumlah INTEGER NOT NULL, subtotal INTEGER NOT NULL);
        """)
        if conn.execute("SELECT COUNT(*) FROM produk").fetchone()[0] == 0:
            conn.executemany("INSERT INTO produk (nama, harga, stok) VALUES (?, ?, ?)", PRODUK_AWAL)


@app.template_filter("rp")
def rupiah(n):
    return "Rp " + f"{n:,}".replace(",", ".")


@app.route("/")
def index():
    with db() as conn:
        produk = conn.execute("SELECT * FROM produk ORDER BY nama").fetchall()
    return render_template("index.html", produk=produk, toko=NAMA_TOKO, error=request.args.get("error"))


@app.post("/checkout")
def checkout():
    with db() as conn:
        produk = conn.execute("SELECT * FROM produk").fetchall()
        items, total = [], 0
        for p in produk:
            try:
                jumlah = int(request.form.get(f"qty_{p['id']}") or 0)
            except ValueError:
                return redirect(url_for("index", error="Jumlah harus berupa angka."))
            if jumlah < 0 or jumlah > p["stok"]:
                return redirect(url_for("index", error=f"Jumlah {p['nama']} tidak valid (stok {p['stok']})."))
            if jumlah:
                items.append((p, jumlah, p["harga"] * jumlah))
                total += p["harga"] * jumlah

        if not items:
            return redirect(url_for("index", error="Pilih minimal satu produk."))
        try:
            bayar = int(request.form.get("bayar") or 0)
        except ValueError:
            return redirect(url_for("index", error="Uang bayar harus berupa angka."))
        if bayar < total:
            return redirect(url_for("index", error=f"Uang bayar kurang. Total belanja {rupiah(total)}."))

        waktu = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        cur = conn.execute(
            "INSERT INTO transaksi (waktu, total, bayar, kembali) VALUES (?, ?, ?, ?)",
            (waktu, total, bayar, bayar - total),
        )
        tid = cur.lastrowid
        for p, jumlah, subtotal in items:
            conn.execute(
                "INSERT INTO detail (transaksi_id, nama, harga, jumlah, subtotal) VALUES (?, ?, ?, ?, ?)",
                (tid, p["nama"], p["harga"], jumlah, subtotal),
            )
            conn.execute("UPDATE produk SET stok = stok - ? WHERE id = ?", (jumlah, p["id"]))
    return redirect(url_for("struk", tid=tid))


@app.route("/struk/<int:tid>")
def struk(tid):
    with db() as conn:
        trx = conn.execute("SELECT * FROM transaksi WHERE id = ?", (tid,)).fetchone()
        if trx is None:
            abort(404)
        detail = conn.execute("SELECT * FROM detail WHERE transaksi_id = ?", (tid,)).fetchall()
    return render_template("struk.html", trx=trx, detail=detail, toko=NAMA_TOKO)


@app.route("/riwayat")
def riwayat():
    with db() as conn:
        daftar = conn.execute("SELECT * FROM transaksi ORDER BY id DESC").fetchall()
    return render_template("riwayat.html", daftar=daftar, toko=NAMA_TOKO)


init_db()

if __name__ == "__main__":
    app.run(debug=True)
