import os
import tempfile

import app as toko


def setup():
    toko.app.config["DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
    toko.init_db()
    return toko.app.test_client()


def test_checkout_membuat_struk_dan_mengurangi_stok():
    c = setup()
    r = c.post("/checkout", data={"qty_1": "2", "qty_5": "3", "bayar": "200000"})
    assert r.status_code == 302 and "/struk/1" in r.headers["Location"]
    html = c.get("/struk/1").get_data(as_text=True)
    # Beras 2 x 72.000 + Mie 3 x 3.500 = 154.500, kembali 45.500
    assert "Rp 154.500" in html and "Rp 45.500" in html
    with toko.db() as conn:
        assert conn.execute("SELECT stok FROM produk WHERE id=1").fetchone()[0] == 18


def test_uang_kurang_ditolak():
    c = setup()
    r = c.post("/checkout", data={"qty_1": "1", "bayar": "1000"})
    assert "error" in r.headers["Location"]
    assert c.get("/struk/1").status_code == 404


def test_melebihi_stok_ditolak():
    c = setup()
    r = c.post("/checkout", data={"qty_1": "999", "bayar": "999999999"})
    assert "error" in r.headers["Location"]
