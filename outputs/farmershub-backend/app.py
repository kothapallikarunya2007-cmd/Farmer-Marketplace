"""FarmersHub marketplace API.

The service deliberately uses SQLite from Python's standard library so it can be
run locally with a single dependency (Flask). Replace SQLite with Postgres and
the notification stub with Twilio before handling real customer data.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from random import randint

from flask import Flask, jsonify, request


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "farmershub.db"))
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def as_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def parse_order(row: sqlite3.Row | None) -> dict | None:
    order = as_dict(row)
    if order:
        order["items"] = json.loads(order.pop("items_json"))
    return order


def api_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@app.after_request
def cors(response):
    allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGIN", "*").split(",") if origin.strip()]
    request_origin = request.headers.get("Origin")
    if "*" in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = "*"
    elif request_origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = request_origin
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PATCH,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.route("/api/<path:_path>", methods=["OPTIONS"])
def options(_path):
    return "", 204


def initialise_database() -> None:
    with closing(connect()) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS farmers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                village TEXT NOT NULL,
                rating REAL NOT NULL DEFAULT 0,
                review_count INTEGER NOT NULL DEFAULT 0,
                photo_url TEXT,
                bio TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_id INTEGER NOT NULL REFERENCES farmers(id),
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0),
                unit TEXT NOT NULL,
                stock INTEGER NOT NULL CHECK(stock >= 0),
                description TEXT DEFAULT '',
                image_url TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT NOT NULL UNIQUE,
                farmer_id INTEGER NOT NULL REFERENCES farmers(id),
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                items_json TEXT NOT NULL,
                total REAL NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending','confirmed','ready','out_for_delivery','delivered','declined')),
                customer_address TEXT NOT NULL,
                delivery_window TEXT NOT NULL,
                special_instructions TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id),
                farmer_id INTEGER NOT NULL REFERENCES farmers(id),
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
        count = db.execute("SELECT COUNT(*) FROM farmers").fetchone()[0]
        if not count:
            seed(db)
        db.commit()


def seed(db: sqlite3.Connection) -> None:
    created_at = now()
    farmer_rows = [
        (1, "Ramesh Kumar", "9000000001", "Tandur, Hyderabad", 4.8, 24,
         "https://images.unsplash.com/photo-1623091410901-00e2d268901f?auto=format&fit=crop&w=300&q=80",
         "Organic vegetables from our family farm, harvested every morning."),
        (2, "Lakshmi Devi", "9000000002", "Shamshabad, Hyderabad", 4.9, 31,
         "https://images.unsplash.com/photo-1606722590583-2b43c6d4e1c7?auto=format&fit=crop&w=300&q=80",
         "Fresh dairy and seasonal produce made with care."),
        (3, "Anwar Pasha", "9000000003", "Vikarabad, Hyderabad", 4.7, 18,
         "https://images.unsplash.com/photo-1551830820-330a71b99659?auto=format&fit=crop&w=300&q=80",
         "Naturally grown grains, pulses and spices."),
    ]
    db.executemany(
        "INSERT INTO farmers VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
        [(*row, created_at) for row in farmer_rows],
    )
    product_rows = [
        (1, "Country Tomatoes", "Vegetables", 50, "kg", 12, "Naturally ripened tomatoes", "https://images.unsplash.com/photo-1546094096-0df4bcaaa337?auto=format&fit=crop&w=500&q=80"),
        (1, "Tender Carrots", "Vegetables", 60, "kg", 8, "Sweet, tender carrots", "https://images.unsplash.com/photo-1447175008436-054170c2e979?auto=format&fit=crop&w=500&q=80"),
        (1, "Fresh Spinach", "Vegetables", 35, "bunch", 16, "Freshly cut leafy spinach", "https://images.unsplash.com/photo-1576045057995-568f588f82fb?auto=format&fit=crop&w=500&q=80"),
        (1, "Farm Eggs", "Dairy", 90, "6 pcs", 20, "Free-range country eggs", "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?auto=format&fit=crop&w=500&q=80"),
        (2, "A2 Cow Milk", "Dairy", 72, "litre", 18, "Morning dairy delivery", "https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=500&q=80"),
        (3, "Red Rice", "Grains", 95, "kg", 25, "Whole-grain native red rice", "https://images.unsplash.com/photo-1586208958839-06c17cacdf08?auto=format&fit=crop&w=500&q=80"),
    ]
    db.executemany(
        """INSERT INTO products (farmer_id,name,category,price,unit,stock,description,image_url,active,created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        [(*row, created_at) for row in product_rows],
    )
    db.execute("INSERT INTO customers (name, phone, created_at) VALUES (?, ?, ?)", ("Priya Sharma", "9876543210", created_at))
    items = [{"product_id": 1, "name": "Country Tomatoes", "quantity": 2, "price": 50, "unit": "kg"}]
    db.execute(
        """INSERT INTO orders (order_number, farmer_id, customer_id, items_json, total, status, customer_address,
           delivery_window, special_instructions, created_at, updated_at)
           VALUES (?, 1, 1, ?, 100, 'pending', '123 Jubilee Hills, Hyderabad', 'Today, 6–8 PM', '', ?, ?)""",
        ("OD-20260916-1234", json.dumps(items), created_at, created_at),
    )


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": now()})


@app.get("/api/farmers")
def list_farmers():
    category = request.args.get("category")
    with closing(connect()) as db:
        query = """
            SELECT f.*, COUNT(p.id) AS product_count FROM farmers f
            LEFT JOIN products p ON p.farmer_id=f.id AND p.active=1
            WHERE f.active=1
        """
        parameters: list[str] = []
        if category and category.lower() != "all":
            query += " AND EXISTS (SELECT 1 FROM products cp WHERE cp.farmer_id=f.id AND cp.active=1 AND cp.category=?)"
            parameters.append(category)
        query += " GROUP BY f.id ORDER BY f.rating DESC, f.name"
        return jsonify([as_dict(row) for row in db.execute(query, parameters)])


@app.get("/api/farmers/<int:farmer_id>")
def farmer_detail(farmer_id: int):
    with closing(connect()) as db:
        farmer = as_dict(db.execute("SELECT * FROM farmers WHERE id=? AND active=1", (farmer_id,)).fetchone())
        if not farmer:
            return api_error("Farmer not found", 404)
        return jsonify(farmer)


@app.get("/api/farmers/<int:farmer_id>/products")
def farmer_products(farmer_id: int):
    with closing(connect()) as db:
        rows = db.execute("SELECT * FROM products WHERE farmer_id=? AND active=1 ORDER BY name", (farmer_id,)).fetchall()
        return jsonify([as_dict(row) for row in rows])


def normalise_order_items(db: sqlite3.Connection, items: list[dict]) -> tuple[int, list[dict], float] | None:
    if not items:
        return None
    normalised, farmer_id, total = [], None, 0.0
    for item in items:
        product_id = item.get("product_id") or item.get("id")
        try:
            quantity = int(item.get("quantity") or item.get("qty") or 0)
        except (TypeError, ValueError):
            return None
        product = db.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
        if not product or quantity < 1 or quantity > product["stock"]:
            return None
        if farmer_id is None:
            farmer_id = product["farmer_id"]
        if farmer_id != product["farmer_id"]:
            return None
        total += product["price"] * quantity
        normalised.append({"product_id": product["id"], "name": product["name"], "quantity": quantity,
                           "price": product["price"], "unit": product["unit"]})
    return farmer_id, normalised, round(total, 2)


@app.post("/api/orders")
def create_order():
    payload = request.get_json(silent=True) or {}
    customer = payload.get("customer") or {}
    name, phone, address = customer.get("name", "").strip(), customer.get("phone", "").strip(), payload.get("address", "").strip()
    if not name or not phone or not address:
        return api_error("Customer name, phone and delivery address are required")
    with closing(connect()) as db:
        parsed = normalise_order_items(db, payload.get("items", []))
        if not parsed:
            return api_error("Cart contains an unavailable item, invalid quantity, or products from multiple farmers")
        farmer_id, items, total = parsed
        existing = db.execute("SELECT id FROM customers WHERE phone=?", (phone,)).fetchone()
        if existing:
            customer_id = existing["id"]
            db.execute("UPDATE customers SET name=? WHERE id=?", (name, customer_id))
        else:
            cursor = db.execute("INSERT INTO customers (name, phone, created_at) VALUES (?, ?, ?)", (name, phone, now()))
            customer_id = cursor.lastrowid
        order_number = f"OD-{datetime.now():%Y%m%d}-{randint(1000, 9999)}"
        while db.execute("SELECT 1 FROM orders WHERE order_number=?", (order_number,)).fetchone():
            order_number = f"OD-{datetime.now():%Y%m%d}-{randint(1000, 9999)}"
        timestamp = now()
        cursor = db.execute(
            """INSERT INTO orders (order_number, farmer_id, customer_id, items_json, total, status, customer_address,
               delivery_window, special_instructions, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)""",
            (order_number, farmer_id, customer_id, json.dumps(items), total, address,
             payload.get("delivery_window", "Today, 6–8 PM"), payload.get("special_instructions", ""), timestamp, timestamp),
        )
        for item in items:
            db.execute("UPDATE products SET stock=stock-? WHERE id=?", (item["quantity"], item["product_id"]))
        db.commit()
        order = db.execute("SELECT * FROM orders WHERE id=?", (cursor.lastrowid,)).fetchone()
    # Hook for Twilio / WhatsApp provider: send_new_order_sms(order_number, farmer_id)
    return jsonify(parse_order(order)), 201


@app.get("/api/orders/<order_number>")
def get_order(order_number: str):
    with closing(connect()) as db:
        row = db.execute(
            """SELECT o.*, f.name AS farmer_name, f.phone AS farmer_phone, f.photo_url AS farmer_photo,
                      c.name AS customer_name, c.phone AS customer_phone
               FROM orders o JOIN farmers f ON f.id=o.farmer_id JOIN customers c ON c.id=o.customer_id
               WHERE o.order_number=?""", (order_number,)
        ).fetchone()
        if not row:
            return api_error("Order not found", 404)
        return jsonify(parse_order(row))


@app.patch("/api/orders/<order_number>/status")
def update_order_status(order_number: str):
    status = (request.get_json(silent=True) or {}).get("status", "").lower()
    allowed = {"pending", "confirmed", "ready", "out_for_delivery", "delivered", "declined"}
    if status not in allowed:
        return api_error("Invalid order status")
    with closing(connect()) as db:
        order = db.execute("SELECT * FROM orders WHERE order_number=?", (order_number,)).fetchone()
        if not order:
            return api_error("Order not found", 404)
        db.execute("UPDATE orders SET status=?, updated_at=? WHERE order_number=?", (status, now(), order_number))
        db.commit()
        updated = db.execute("SELECT * FROM orders WHERE order_number=?", (order_number,)).fetchone()
    # Hook for Twilio: send_customer_status_sms(updated)
    return jsonify(parse_order(updated))


@app.get("/api/farmers/<int:farmer_id>/orders")
def farmer_orders(farmer_id: int):
    status = request.args.get("status")
    with closing(connect()) as db:
        query = """SELECT o.*, c.name AS customer_name, c.phone AS customer_phone
                   FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.farmer_id=?"""
        params: list = [farmer_id]
        if status:
            query += " AND o.status=?"
            params.append(status)
        query += " ORDER BY o.created_at DESC"
        return jsonify([parse_order(row) for row in db.execute(query, params)])


@app.get("/api/farmers/<int:farmer_id>/dashboard")
def farmer_dashboard(farmer_id: int):
    with closing(connect()) as db:
        farmer = db.execute("SELECT * FROM farmers WHERE id=?", (farmer_id,)).fetchone()
        if not farmer:
            return api_error("Farmer not found", 404)
        active = db.execute("SELECT COUNT(*) FROM orders WHERE farmer_id=? AND status NOT IN ('delivered','declined')", (farmer_id,)).fetchone()[0]
        earnings = db.execute("SELECT COALESCE(SUM(total), 0) FROM orders WHERE farmer_id=? AND status='delivered'", (farmer_id,)).fetchone()[0]
        recent = db.execute("SELECT * FROM orders WHERE farmer_id=? ORDER BY created_at DESC LIMIT 10", (farmer_id,)).fetchall()
        return jsonify({"farmer": as_dict(farmer), "active_orders": active, "total_earnings": earnings,
                        "orders": [parse_order(row) for row in recent]})


@app.route("/api/farmers/<int:farmer_id>/products", methods=["POST"])
def create_product(farmer_id: int):
    payload = request.get_json(silent=True) or {}
    required = ["name", "category", "price", "unit", "stock"]
    if any(field not in payload or payload[field] in (None, "") for field in required):
        return api_error("name, category, price, unit and stock are required")
    try:
        price, stock = float(payload["price"]), int(payload["stock"])
    except (TypeError, ValueError):
        return api_error("price and stock must be numbers")
    with closing(connect()) as db:
        if not db.execute("SELECT 1 FROM farmers WHERE id=?", (farmer_id,)).fetchone():
            return api_error("Farmer not found", 404)
        cursor = db.execute(
            """INSERT INTO products (farmer_id,name,category,price,unit,stock,description,image_url,active,created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (farmer_id, payload["name"].strip(), payload["category"], price, payload["unit"], stock,
             payload.get("description", ""), payload.get("image_url", ""), now()),
        )
        db.commit()
        return jsonify(as_dict(db.execute("SELECT * FROM products WHERE id=?", (cursor.lastrowid,)).fetchone())), 201


@app.route("/api/farmers/<int:farmer_id>/products/<int:product_id>", methods=["PATCH", "DELETE"])
def manage_product(farmer_id: int, product_id: int):
    with closing(connect()) as db:
        product = db.execute("SELECT * FROM products WHERE id=? AND farmer_id=?", (product_id, farmer_id)).fetchone()
        if not product:
            return api_error("Product not found", 404)
        if request.method == "DELETE":
            db.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
            db.commit()
            return "", 204
        payload = request.get_json(silent=True) or {}
        editable = {"name", "category", "price", "unit", "stock", "description", "image_url", "active"}
        updates = {key: value for key, value in payload.items() if key in editable}
        if not updates:
            return api_error("No editable fields supplied")
        clause = ", ".join(f"{field}=?" for field in updates)
        db.execute(f"UPDATE products SET {clause} WHERE id=?", [*updates.values(), product_id])
        db.commit()
        return jsonify(as_dict(db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()))


@app.post("/api/reviews")
def create_review():
    payload = request.get_json(silent=True) or {}
    try:
        rating = int(payload.get("rating"))
    except (TypeError, ValueError):
        return api_error("rating must be between 1 and 5")
    if rating not in range(1, 6):
        return api_error("rating must be between 1 and 5")
    with closing(connect()) as db:
        order = db.execute("SELECT * FROM orders WHERE order_number=?", (payload.get("order_number"),)).fetchone()
        if not order:
            return api_error("Order not found", 404)
        if order["status"] != "delivered":
            return api_error("Reviews can be left after delivery")
        try:
            db.execute("INSERT INTO reviews (order_id,farmer_id,rating,comment,created_at) VALUES (?, ?, ?, ?, ?)",
                       (order["id"], order["farmer_id"], rating, payload.get("comment", ""), now()))
        except sqlite3.IntegrityError:
            return api_error("This order has already been reviewed", 409)
        stats = db.execute("SELECT AVG(rating), COUNT(*) FROM reviews WHERE farmer_id=?", (order["farmer_id"],)).fetchone()
        db.execute("UPDATE farmers SET rating=?, review_count=? WHERE id=?", (round(stats[0], 1), stats[1], order["farmer_id"]))
        db.commit()
    return jsonify({"message": "Review recorded"}), 201


if __name__ == "__main__":
    initialise_database()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_ENV") == "development")
else:
    initialise_database()
