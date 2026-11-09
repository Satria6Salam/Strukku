def _categories(client):
    return {c["key"]: c for c in client.get("/api/v1/categories").json()}


def _scan(client, auth, image_bytes):
    r = client.post("/api/v1/scans", files={"file": ("struk.jpg", image_bytes, "image/jpeg")}, headers=auth)
    assert r.status_code == 200, r.text
    return r.json()


def _payload_from_scan(scan, overrides=None):
    overrides = overrides or {}
    return {
        "scan_id": scan["scan_id"],
        "merchant_name": scan["merchant_name"],
        "transaction_date": scan["transaction_date"],
        "total_amount": scan["total_amount"],
        "items": [
            {
                "item_name": i["item_name"],
                "quantity": i["quantity"],
                "item_price": i["item_price"],
                "category_id": overrides.get(i["item_name"], i["category_id"]),
                "predicted_category_id": i["predicted_category_id"],
                "confidence_score": i["confidence_score"],
                "prediction_source": i["prediction_source"],
            }
            for i in scan["items"]
        ],
    }


def test_categories_synced(client):
    cats = _categories(client)
    assert set(cats) == {"Makanan", "Minuman", "Kebutuhan_Rumah_Tangga", "Perawatan_Diri", "Kesehatan", "Lainnya"}
    assert cats["Kebutuhan_Rumah_Tangga"]["name"] == "Kebutuhan Rumah Tangga"
    assert cats["Makanan"]["icon"]


def test_scan_result(client, auth, image_bytes):
    scan = _scan(client, auth, image_bytes)
    assert scan["merchant_name"] == "INDOMARET"
    assert scan["transaction_date"] == "2026-10-21T14:32:00"
    assert scan["total_amount"] == 60500
    assert scan["total_matches"] is True
    names = [i["item_name"] for i in scan["items"]]
    assert names == ["ROTI TAWAR 500G", "SUSU UHT 1L", "VITAMIN C 10 TABLET", "BARANG ANEH XYZ"]
    susu = scan["items"][1]
    assert susu["quantity"] == 2 and susu["unit_price"] == 9000 and susu["category"]["key"] == "Minuman"
    assert scan["items"][3]["needs_review"] is True  # tidak dikenal -> perlu diperiksa
    assert scan["review_count"] >= 1
    img = client.get(scan["image_url"], headers=auth)
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"


def test_scan_rejects_non_image(client, auth):
    r = client.post("/api/v1/scans", files={"file": ("a.jpg", b"bukan gambar", "image/jpeg")}, headers=auth)
    assert r.status_code == 400
    assert r.json()["code"] == "INVALID_IMAGE"


def test_save_correct_and_learn(client, auth, image_bytes):
    cats = _categories(client)
    scan = _scan(client, auth, image_bytes)
    payload = _payload_from_scan(scan, {"BARANG ANEH XYZ": cats["Lainnya"]["id"]})
    r = client.post("/api/v1/receipts", json=payload, headers=auth)
    assert r.status_code == 201, r.text
    receipt = r.json()
    assert receipt["item_count"] == 4 and receipt["image_url"]
    aneh = [i for i in receipt["items"] if i["item_name"] == "BARANG ANEH XYZ"][0]
    assert aneh["is_user_corrected"] is True
    roti = [i for i in receipt["items"] if i["item_name"] == "ROTI TAWAR 500G"][0]
    assert roti["is_user_corrected"] is False

    # Simpan dua kali dari scan yang sama ditolak (mencegah dobel tap Save).
    assert client.post("/api/v1/receipts", json=payload, headers=auth).status_code == 409

    # Scan berikutnya mengingat koreksi pengguna.
    scan2 = _scan(client, auth, image_bytes)
    aneh2 = [i for i in scan2["items"] if i["item_name"] == "BARANG ANEH XYZ"][0]
    assert aneh2["category"]["key"] == "Lainnya"
    assert aneh2["prediction_source"] == "user_history"
    assert aneh2["needs_review"] is False


def test_manual_receipt_crud_and_isolation(client, auth, other_auth):
    cats = _categories(client)
    r = client.post(
        "/api/v1/receipts",
        json={
            "merchant_name": "Kopi Kenangan",
            "transaction_date": "2026-10-19T08:00:00Z",  # UTC -> 15:00 WIB
            "items": [{"item_name": "Es Kopi Susu", "item_price": 24000, "category_id": cats["Minuman"]["id"]}],
        },
        headers=auth,
    )
    assert r.status_code == 201, r.text
    receipt = r.json()
    assert receipt["total_amount"] == 24000
    assert receipt["transaction_date"] == "2026-10-19T15:00:00"
    rid, item_id = receipt["id"], receipt["items"][0]["id"]

    # Pengguna lain tidak bisa melihat / menghapus.
    assert client.get(f"/api/v1/receipts/{rid}", headers=other_auth).status_code == 404
    assert client.delete(f"/api/v1/receipts/{rid}", headers=other_auth).status_code == 404

    r = client.patch(
        f"/api/v1/receipts/{rid}/items/{item_id}", json={"category_id": cats["Makanan"]["id"]}, headers=auth
    )
    assert r.json()["items"][0]["category"]["key"] == "Makanan"

    r = client.put(
        f"/api/v1/receipts/{rid}",
        json={"merchant_name": "Kopi K", "items": [{"item_name": "A", "item_price": 1000}, {"item_name": "B", "item_price": 2000}]},
        headers=auth,
    )
    assert r.json()["item_count"] == 2 and r.json()["total_amount"] == 3000

    bad = client.post("/api/v1/receipts", json={"items": [{"item_name": "X", "category_id": 9999}]}, headers=auth)
    assert bad.status_code == 400 and bad.json()["code"] == "CATEGORY_NOT_FOUND"

    assert client.delete(f"/api/v1/receipts/{rid}", headers=auth).status_code == 204
    assert client.get(f"/api/v1/receipts/{rid}", headers=auth).status_code == 404


def test_dashboard_and_list(client, auth, image_bytes):
    cats = _categories(client)
    scan = _scan(client, auth, image_bytes)
    client.post("/api/v1/receipts", json=_payload_from_scan(scan), headers=auth)
    client.post(
        "/api/v1/receipts",
        json={"merchant_name": "Grab", "transaction_date": "2026-09-18T10:00:00", "total_amount": 32000,
              "items": [{"item_name": "Ongkos", "item_price": 32000, "category_id": cats["Lainnya"]["id"]}]},
        headers=auth,
    )

    d = client.get("/api/v1/dashboard?month=2026-10", headers=auth).json()
    assert d["month_label"] == "Oktober 2026"
    assert d["total_spent"] == 60500 and d["receipt_count"] == 1
    assert d["previous_month_total"] == 32000
    assert d["change_percent"] == round((60500 - 32000) / 32000 * 100, 1)
    amounts = {c["category"]["key"] if c["category"] else None: c for c in d["categories"]}
    assert amounts["Minuman"]["amount"] == 18000
    assert round(sum(c["percentage"] for c in d["categories"])) == 100
    assert d["recent_receipts"][0]["merchant_name"] == "INDOMARET"

    breakdown = client.get("/api/v1/analytics/categories?month=2026-10", headers=auth).json()
    assert breakdown["total_amount"] == 60500

    trend = client.get("/api/v1/analytics/monthly?month=2026-10&months=3", headers=auth).json()
    assert [p["month"] for p in trend] == ["2026-08", "2026-09", "2026-10"]
    assert trend[1]["total_spent"] == 32000

    page = client.get("/api/v1/receipts?month=2026-10&q=roti", headers=auth).json()
    assert page["total"] == 1 and page["items"][0]["main_category"] is not None
    assert client.get("/api/v1/receipts?month=2026-13", headers=auth).json()["code"] == "INVALID_MONTH"


def test_classify_endpoint(client, auth):
    r = client.post("/api/v1/classify", json={"texts": ["PEPSODENT 190G", "AQUA 600ML"]}, headers=auth)
    keys = [x["category"]["key"] for x in r.json()]
    assert keys == ["Perawatan_Diri", "Minuman"]
