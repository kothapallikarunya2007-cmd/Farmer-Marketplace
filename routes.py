import secrets
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify, abort
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import Farmer, Product, Order, OrderItem, Rating

api = Blueprint('api', __name__, url_prefix='/api')


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, 'A JSON object is required.')
    return data


def string(data, key, limit=100):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        abort(400, f'{key} must contain 1 to {limit} characters.')
    return value.strip()


def integer(value, name, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum or value > 1000000:
        abort(400, f'{name} must be a whole number between {minimum} and 1000000.')
    return value


def phone(data):
    value = string(data, 'phone', 10)
    if len(value) != 10 or not value.isascii() or not value.isdigit():
        abort(400, 'Enter a 10-digit phone number.')
    return value


def farmer_auth():
    token = request.headers.get('Authorization', '').removeprefix('Bearer ')
    farmer = Farmer.query.filter_by(api_key=token).first() if len(token) >= 32 else None
    if not farmer:
        abort(401, 'Sign in with your farmer access key.')
    return farmer


def owner(order):
    farmer = farmer_auth()
    if order.farmer_id != farmer.id:
        abort(403, 'This order belongs to another farmer.')


def receipt_auth(order):
    token = request.headers.get('X-Order-Token', '')
    access = db.session.get(OrderAccess, order.id)
    if not access or not secrets.compare_digest(access.token, token):
        abort(403, 'Your private order receipt is required.')


class ReviewClaim(db.Model):
    __tablename__ = 'review_claims'
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), primary_key=True)


class OrderAccess(db.Model):
    __tablename__ = 'order_access'
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), primary_key=True)
    token = db.Column(db.String(64), nullable=False, unique=True)


def public_farmer(f):
    ratings = Rating.query.join(Order).filter(Order.farmer_id == f.id).all()
    return dict(id=f.id, name=f.name, village=f.village, area_farming=f.area_farming,
                product_count=Product.query.filter_by(farmer_id=f.id, active=True).count(),
                rating=round(sum(r.rating for r in ratings)/len(ratings), 1) if ratings else None,
                review_count=len(ratings))


@api.post('/farmers/signup')
def signup():
    data = body()
    f = Farmer(name=string(data, 'name'), phone=phone(data), village=string(data, 'village'),
               area_farming=string(data, 'area_farming', 200) if data.get('area_farming') else 'General',
               api_key=secrets.token_urlsafe(32))
    db.session.add(f)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, 'This phone number is already registered.')
    return jsonify(farmer=public_farmer(f), api_key=f.api_key), 201


@api.get('/farmers/me')
def me():
    return jsonify(public_farmer(farmer_auth()))


@api.get('/farmers')
def farmers():
    return jsonify([public_farmer(f) for f in Farmer.query.all()])


@api.get('/farmers/<int:farmer_id>')
def farmer(farmer_id):
    return jsonify(public_farmer(db.get_or_404(Farmer, farmer_id)))


def product_values(data):
    try:
        price = Decimal(str(data.get('price')))
        if not price.is_finite() or price <= 0 or price > 1000000 or price.as_tuple().exponent < -2:
            raise ValueError()
    except (InvalidOperation, ValueError):
        abort(400, 'Price must be positive with at most two decimal places.')
    description = data.get('description', '')
    if not isinstance(description, str) or len(description) > 500:
        abort(400, 'Description must be at most 500 characters.')
    return dict(name=string(data, 'name'), price=float(price),
                quantity=integer(data.get('quantity'), 'quantity', 0), description=description,
                category=string(data, 'category', 40) if data.get('category') else 'Vegetables',
                unit=string(data, 'unit', 20) if data.get('unit') else 'kg')


@api.get('/products')
def products():
    query = Product.query.filter_by(active=True)
    if request.args.get('farmer_id', type=int):
        query = query.filter_by(farmer_id=request.args.get('farmer_id', type=int))
    if request.args.get('q'):
        query = query.filter(Product.name.ilike('%' + request.args['q'][:100] + '%'))
    return jsonify([p.to_dict() for p in query.order_by(Product.id.desc()).all()])


@api.get('/products/<int:product_id>')
def product(product_id):
    return jsonify(db.get_or_404(Product, product_id).to_dict())


@api.post('/products')
def add_product():
    f = farmer_auth()
    p = Product(farmer_id=f.id, **product_values(body()))
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201


@api.put('/products/<int:product_id>')
def edit_product(product_id):
    f = farmer_auth()
    p = db.get_or_404(Product, product_id)
    if p.farmer_id != f.id:
        abort(403, 'This product belongs to another farmer.')
    for key, value in product_values(body()).items():
        setattr(p, key, value)
    db.session.commit()
    return jsonify(p.to_dict())


@api.post('/orders/create')
def create_order():
    data = body()
    name = string(data, 'customer_name')
    customer_phone = phone({'phone': data.get('customer_phone')})
    location = string(data, 'delivery_location', 300)
    items = data.get('items')
    if not isinstance(items, list) or not 1 <= len(items) <= 50:
        abort(400, 'Choose between 1 and 50 products.')
    quantities = {}
    for item in items:
        if not isinstance(item, dict):
            abort(400, 'Invalid order item.')
        pid = integer(item.get('product_id'), 'product_id')
        quantities[pid] = quantities.get(pid, 0) + integer(item.get('quantity'), 'quantity')
    selected = [db.get_or_404(Product, pid) for pid in sorted(quantities)]
    if len({p.farmer_id for p in selected}) != 1:
        abort(400, 'Place a separate order for each farmer.')
    if any(not p.active for p in selected):
        abort(409, 'A product is no longer available.')
    total = Decimal('0')
    order = Order(customer_name=name, customer_phone=customer_phone, delivery_location=location,
                  farmer_id=selected[0].farmer_id, total_amount=0)
    db.session.add(order)
    for p in selected:
        qty = quantities[p.id]
        result = db.session.execute(update(Product).where(Product.id == p.id, Product.quantity >= qty)
                                    .values(quantity=Product.quantity - qty))
        if result.rowcount != 1:
            db.session.rollback()
            abort(409, f'Not enough stock for {p.name}. Refresh your basket.')
        total += Decimal(str(p.price)) * qty
        order.items.append(OrderItem(product_id=p.id, quantity=qty, price_at_purchase=p.price))
    order.total_amount = float(total.quantize(Decimal('0.01')))
    db.session.flush()
    token = secrets.token_urlsafe(32)
    db.session.add(OrderAccess(order_id=order.id, token=token))
    db.session.commit()
    return jsonify(order=order.to_dict(), order_token=token), 201


@api.get('/orders')
def orders():
    f = farmer_auth()
    return jsonify([o.to_dict() for o in Order.query.filter_by(farmer_id=f.id).order_by(Order.id.desc()).all()])


@api.get('/orders/<int:order_id>')
def order(order_id):
    o = db.get_or_404(Order, order_id)
    receipt_auth(o)
    return jsonify(o.to_dict())


@api.put('/orders/<int:order_id>/status')
def status(order_id):
    o = db.get_or_404(Order, order_id)
    owner(o)
    new = body().get('status')
    transitions = {'pending': ['confirmed', 'declined'], 'confirmed': ['packed'], 'packed': ['in_transit'], 'in_transit': ['delivered']}
    if new not in transitions.get(o.status, []):
        abort(400, 'Move the order to the next delivery stage.')
    previous = o.status
    changed = db.session.execute(update(Order).where(Order.id == o.id, Order.status == previous).values(status=new))
    if changed.rowcount != 1:
        db.session.rollback()
        abort(409, 'The order changed. Refresh and retry.')
    if new == 'declined':
        for item in o.items:
            db.session.execute(update(Product).where(Product.id == item.product_id).values(quantity=Product.quantity + item.quantity))
    db.session.commit()
    return jsonify(o.to_dict())


@api.post('/ratings')
def rate():
    data = body()
    o = db.get_or_404(Order, integer(data.get('order_id'), 'order_id'))
    receipt_auth(o)
    stars = integer(data.get('rating'), 'rating')
    if stars > 5:
        abort(400, 'Rating must be between 1 and 5.')
    if o.status != 'delivered' or o.rating:
        abort(409, 'Only delivered, unreviewed orders can be reviewed.')
    review = data.get('review_text', '')
    if not isinstance(review, str) or len(review) > 500:
        abort(400, 'Review must be at most 500 characters.')
    # Lock the receipt row so concurrent review requests serialize on PostgreSQL.
    db.session.execute(db.select(OrderAccess).filter_by(order_id=o.id).with_for_update())
    if Rating.query.filter_by(order_id=o.id).first():
        abort(409, 'This order has already been reviewed.')
    db.session.add(ReviewClaim(order_id=o.id))
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(409, 'This order has already been reviewed.')
    r = Rating(order_id=o.id, rating=stars, review_text=review)
    db.session.add(r)
    db.session.commit()
    return jsonify(r.to_dict()), 201


@api.get('/ratings')
def ratings():
    return jsonify([dict(rating=r.rating, review_text=r.review_text) for r in Rating.query.all()])


@api.delete('/products/<int:product_id>')
def archive_product(product_id):
    f = farmer_auth()
    p = db.get_or_404(Product, product_id)
    if p.farmer_id != f.id:
        abort(403, 'This product belongs to another farmer.')
    p.active = False
    db.session.commit()
    return '', 204
