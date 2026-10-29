from extensions import db
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# ==================== FARMER MODEL ====================
class Farmer(db.Model):
    __tablename__ = 'farmers'

    id = db.Column(db.Integer, primary_key=True)  # Auto-increment ID
    name = db.Column(db.String(100), nullable=False)  # Cannot be empty
    phone = db.Column(db.String(10), unique=True, nullable=False)  # Must be unique
    village = db.Column(db.String(100), nullable=False)
    area_farming = db.Column(db.String(200))  # "vegetables", "fruits", etc
    api_key = db.Column(db.String(50), unique=True)  # Secret key for API
    created_at = db.Column(db.DateTime, default=_utcnow)  # Auto timestamp

    # Relationship: One farmer has many products
    products = db.relationship('Product', backref='farmer', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        """Convert to JSON"""
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'village': self.village,
            'area_farming': self.area_farming,
            'created_at': self.created_at.isoformat()
        }


# ==================== PRODUCT MODEL ====================
class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id'), nullable=False)  # Links to Farmer
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    price = db.Column(db.Float, nullable=False)  # Price in rupees
    quantity = db.Column(db.Integer, nullable=False)  # Stock available
    image_url = db.Column(db.String(500))  # URL of product image
    created_at = db.Column(db.DateTime, default=_utcnow)

    category = db.Column(db.String(40), default='Vegetables', nullable=False)
    unit = db.Column(db.String(20), default='kg', nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationship: One product can be in many orders
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    def to_dict(self):
        """Convert to JSON"""
        return {
            'id': self.id,
            'farmer_id': self.farmer_id,
            'farmer_name': self.farmer.name if self.farmer else None,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'quantity': self.quantity,
            'category': self.category,
            'unit': self.unit,
            'active': self.active,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat()
        }


# ==================== ORDER MODEL ====================
class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    customer_phone = db.Column(db.String(10), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    delivery_location = db.Column(db.String(300), nullable=False)
    delivery_date = db.Column(db.String(50))
    status = db.Column(db.String(50), default='pending')  # confirmed, packed, in_transit, delivered
    total_amount = db.Column(db.Float, nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id'))
    created_at = db.Column(db.DateTime, default=_utcnow)

    farmer = db.relationship('Farmer', backref='orders')
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    rating = db.relationship('Rating', backref='order', lazy=True, uselist=False, cascade='all, delete-orphan')

    def to_dict(self):
        """Convert to JSON"""
        return {
            'id': self.id,
            'customer_phone': self.customer_phone,
            'customer_name': self.customer_name,
            'delivery_location': self.delivery_location,
            'delivery_date': self.delivery_date,
            'status': self.status,
            'total_amount': self.total_amount,
            'farmer_name': self.farmer.name if self.farmer else None,
            'items': [item.to_dict() for item in self.items],
            'rating': self.rating.to_dict() if self.rating else None,
            'created_at': self.created_at.isoformat()
        }


# ==================== ORDER ITEM MODEL ====================
class OrderItem(db.Model):
    """Links products to orders (many-to-many)"""
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(db.Float, nullable=False)  # Price when ordered

    def to_dict(self):
        """Convert to JSON"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'quantity': self.quantity,
            'price_at_purchase': self.price_at_purchase
        }


# ==================== RATING MODEL ====================
class Rating(db.Model):
    __tablename__ = 'ratings'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    review_text = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=_utcnow)

    def to_dict(self):
        """Convert to JSON"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'rating': self.rating,
            'review_text': self.review_text,
            'created_at': self.created_at.isoformat()
        }
