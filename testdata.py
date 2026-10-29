"""Add demo records without deleting existing farmers, products, or orders."""
import json
import secrets
from pathlib import Path
from extensions import db
from models import Farmer, Product


def seed():
    db.create_all()
    credentials_path = Path(__file__).with_name('demo-credentials.json')
    credentials = json.loads(credentials_path.read_text()) if credentials_path.exists() else []
    samples = [
        ('Ramesh Kumar', '9000000001', 'Tandur', 'Vegetables', [('Tomatoes', 30, 100), ('Spinach', 20, 80), ('Carrots', 40, 60)]),
        ('Lakshmi Devi', '9000000002', 'Hyderabad', 'Fruits', [('Apples', 120, 50), ('Mangoes', 90, 40)]),
        ('Anwar Pasha', '9000000003', 'Vikarabad', 'Organic', [('Lettuce', 35, 70), ('Bell Peppers', 65, 45), ('Potatoes', 28, 100)])
    ]
    for name, phone, village, area, products in samples:
        f = Farmer.query.filter_by(phone=phone).first()
        if f:
            continue
        f = Farmer(name=name, phone=phone, village=village, area_farming=area, api_key=secrets.token_urlsafe(32))
        db.session.add(f)
        db.session.flush()
        credentials.append(dict(name=name, api_key=f.api_key))
        for label, price, qty in products:
            db.session.add(Product(farmer_id=f.id, name=label, price=price, quantity=qty,
                                   category='Fruits' if area == 'Fruits' else 'Vegetables',
                                   description=f'Fresh {label.lower()} from {village}. Sold per kilogram.'))
    db.session.commit()
    credentials_path.write_text(json.dumps(credentials, indent=2))
    print('Demo data ready. Private farmer keys saved in demo-credentials.json (not published).')


if __name__ == '__main__':
    from app import app
    with app.app_context():
        seed()
