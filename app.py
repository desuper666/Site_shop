from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import os
import random
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clothing_store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.config['DEBUG'] = True

translations = {
    'en': {
        'title': 'Clothing Store',
        'welcome': 'Welcome, {}',
        'cart': 'Cart',
        'orders': 'Orders',
        'logout': 'Logout',
        'login': 'Login',
        'register': 'Register',
        'our_products': 'Our Products',
        'view_details': 'View Details',
        'quantity': 'Quantity',
        'add_to_cart': 'Add to Cart',
        'your_cart': 'Your Cart',
        'remove': 'Remove',
        'total': 'Total',
        'place_order': 'Place Order',
        'your_orders': 'Your Orders',
        'no_orders': 'You have no orders yet.',
        'empty_cart': 'Your cart is empty.',
        'username': 'Username',
        'email': 'Email',
        'password': 'Password',
        'language': 'Русский',
        'theme': 'Dark Mode',
        'out_of_stock': 'Out of stock',
        'insufficient_stock': 'Not enough stock available for {}',
        'stock': 'In Stock: {}',
        'promo_code': 'Promo Code',
        'apply_promo': 'Apply',
        'invalid_promo': 'Invalid or expired promo code',
        'promo_applied': 'Promo code applied! Discount: {}%',
        'delivery_address': 'Delivery Address',
        'address_required': 'Delivery address is required',
        'discount': 'Discount'
    },
    'ru': {
        'title': 'Магазин одежды',
        'welcome': 'Добро пожаловать, {}',
        'cart': 'Корзина',
        'orders': 'Заказы',
        'logout': 'Выйти',
        'login': 'Войти',
        'register': 'Зарегистрироваться',
        'our_products': 'Наши товары',
        'view_details': 'Подробности',
        'quantity': 'Количество',
        'add_to_cart': 'Добавить в корзину',
        'your_cart': 'Ваша корзина',
        'remove': 'Удалить',
        'total': 'Итого',
        'place_order': 'Оформить заказ',
        'your_orders': 'Ваши заказы',
        'no_orders': 'У вас пока нет заказов.',
        'empty_cart': 'Ваша корзина пуста.',
        'username': 'Имя пользователя',
        'email': 'Электронная почта',
        'password': 'Пароль',
        'language': 'English',
        'theme': 'Темный режим',
        'out_of_stock': 'Нет в наличии',
        'insufficient_stock': 'Недостаточно товара для {}',
        'stock': 'В наличии: {}',
        'promo_code': 'Промокод',
        'apply_promo': 'Применить',
        'invalid_promo': 'Недействительный или истекший промокод',
        'promo_applied': 'Промокод применен! Скидка: {}%',
        'delivery_address': 'Адрес доставки',
        'address_required': 'Требуется адрес доставки',
        'discount': 'Скидка'
    }
}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_en = db.Column(db.String(120), nullable=False)
    name_ru = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description_en = db.Column(db.Text, nullable=True)
    description_ru = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(120), nullable=True)
    stock = db.Column(db.Integer, nullable=False, default=0)
    restock_time = db.Column(db.DateTime(timezone=True), nullable=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    user = db.relationship('User', backref='cart_items')
    product = db.relationship('Product', backref='cart_items')

class PromoCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount_percent = db.Column(db.Integer, nullable=False)
    valid_until = db.Column(db.DateTime(timezone=True), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    delivery_address = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    promo_code_id = db.Column(db.Integer, db.ForeignKey('promo_code.id'), nullable=True)
    discount_applied = db.Column(db.Float, nullable=True)
    user = db.relationship('User', backref='orders')
    promo_code = db.relationship('PromoCode')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    order = db.relationship('Order', backref='items')
    product = db.relationship('Product')

def restock_products():
    while True:
        with app.app_context():
            products = Product.query.all()
            current_time = datetime.now(timezone.utc)
            for product in products:
                if product.stock == 0 and product.restock_time:
                    restock_time = product.restock_time
                    if restock_time.tzinfo is None:
                        restock_time = restock_time.replace(tzinfo=timezone.utc)
                    time_elapsed = (current_time - restock_time).total_seconds()
                    if time_elapsed >= 100:
                        product.stock = random.randint(10, 20)
                        product.restock_time = None
                        db.session.commit()
        time.sleep(10)

with app.app_context():
    db.drop_all()
    db.create_all()
    if not Product.query.first():
        products = [
            Product(name_en="Baggy Jeans", name_ru="Свободные джинсы", price=49.99,
                    description_en="Loose fit denim jeans", description_ru="Джинсы свободного кроя",
                    image="Baggy_Jeans.jpg", stock=random.randint(10, 20)),
            Product(name_en="Baggy Pants", name_ru="Свободные штаны", price=44.99,
                    description_en="Relaxed casual pants", description_ru="Повседневные штаны свободного кроя",
                    image="Baggy_pants.jpg", stock=random.randint(10, 20)),
            Product(name_en="Bandana T-shirt", name_ru="Футболка с банданой", price=24.99,
                    description_en="Stylish bandana print tee", description_ru="Футболка с принтом банданы",
                    image="Bandana_T-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="Black T-shirt", name_ru="Черная футболка", price=19.99, description_en="Classic black tee",
                    description_ru="Классическая черная футболка", image="Black_T-shirt.jpg",
                    stock=random.randint(10, 20)),
            Product(name_en="BLG T-shirt", name_ru="Футболка BLG", price=21.99,
                    description_en="Dark green BLG print tee", description_ru="Темно-зеленая футболка с принтом BLG",
                    image="BLG_T-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="Blue T-shirt", name_ru="Голубая футболка", price=18.99,
                    description_en="Soft blue cotton tee", description_ru="Мягкая голубая хлопковая футболка",
                    image="Blue_T-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="Cargo Pants", name_ru="Штаны карго", price=39.99, description_en="Utility cargo pants",
                    description_ru="Функциональные штаны карго", image="Cargo_pants.jpg", stock=random.randint(10, 20)),
            Product(name_en="Fashion Boots", name_ru="Модные ботинки", price=59.99,
                    description_en="Trendy fashion boots", description_ru="Модные ботинки", image="Fashion_boots.jpg",
                    stock=random.randint(10, 20)),
            Product(name_en="Fashion Sneakers", name_ru="Модные кроссовки", price=64.99,
                    description_en="High-top fashion sneakers", description_ru="Модные высокие кроссовки",
                    image="Fashion_sneakers.jpg", stock=random.randint(10, 20)),
            Product(name_en="Fashion T-shirt", name_ru="Модная футболка", price=22.99,
                    description_en="Branded fashion tee", description_ru="Фирменная модная футболка",
                    image="Fashion_t-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="Fashionable T-shirt", name_ru="Фешенебельная футболка", price=27.99,
                    description_en="Trendy logo tee", description_ru="Модная футболка с логотипом",
                    image="Fashionable_T-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="Glitter T-shirt", name_ru="Блестящая футболка", price=23.99,
                    description_en="T-shirt with glitter print", description_ru="Футболка с блестящим принтом",
                    image="Glitter_t-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="Gray Sweater", name_ru="Серый свитер", price=34.99, description_en="Comfy gray sweater",
                    description_ru="Уютный серый свитер", image="Gray_sweater.jpg", stock=random.randint(10, 20)),
            Product(name_en="Green T-shirt", name_ru="Зеленая футболка", price=19.99,
                    description_en="Bright green t-shirt", description_ru="Яркая зеленая футболка",
                    image="Green_T-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="Jeans", name_ru="Джинсы", price=44.99, description_en="Classic straight jeans",
                    description_ru="Классические прямые джинсы", image="Jeans1.jpg", stock=random.randint(10, 20)),
            Product(name_en="Jungle T-shirt", name_ru="Футболка Jungle", price=25.99,
                    description_en="T-shirt with jungle print", description_ru="Футболка с принтом джунглей",
                    image="jungle_t-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="Polo", name_ru="Поло", price=31.99, description_en="Black polo shirt",
                    description_ru="Черная рубашка поло", image="polo.jpg", stock=random.randint(10, 20)),
            Product(name_en="Red Sneakers", name_ru="Красные кроссовки", price=59.99,
                    description_en="Bright red athletic sneakers", description_ru="Яркие красные кроссовки",
                    image="Red_sneakers.jpg", stock=random.randint(10, 20)),
            Product(name_en="Running Sneakers", name_ru="Беговые кроссовки", price=64.99,
                    description_en="Lightweight running sneakers", description_ru="Легкие кроссовки для бега",
                    image="Running_sneakers.jpg", stock=random.randint(10, 20)),
            Product(name_en="Spotted Pants", name_ru="Штаны с пятнами", price=35.99,
                    description_en="Patterned casual pants", description_ru="Повседневные штаны с пятнами",
                    image="Spotted_pants.jpg", stock=random.randint(10, 20)),
            Product(name_en="Sweater", name_ru="Свитер", price=34.99, description_en="Warm pink sweater",
                    description_ru="Теплый розовый свитер", image="Sweater.jpg", stock=random.randint(10, 20)),
            Product(name_en="Torn BT-shirt", name_ru="Рваная футболка (BT)", price=24.99,
                    description_en="Black torn t-shirt", description_ru="Черная рваная футболка",
                    image="Torn_bt-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="Torn T-shirt", name_ru="Рваная футболка", price=24.99,
                    description_en="Givenchy style torn tee", description_ru="Футболка в стиле Givenchy",
                    image="Torn_t-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="Trousers", name_ru="Брюки", price=42.99, description_en="Formal black trousers",
                    description_ru="Классические черные брюки", image="trousers.jpg", stock=random.randint(10, 20)),
            Product(name_en="T-shirt", name_ru="Футболка", price=19.99, description_en="Everyday black tee",
                    description_ru="Повседневная черная футболка", image="T-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="T-shirt with Print", name_ru="Футболка с принтом", price=22.99,
                    description_en="Yellow tee with print", description_ru="Желтая футболка с принтом",
                    image="T-shirt_w_print.jpg", stock=random.randint(10, 20)),
            Product(name_en="Turquoise T-shirt", name_ru="Бирюзовая футболка", price=20.99,
                    description_en="Two-tone turquoise t-shirt", description_ru="Двухцветная бирюзовая футболка",
                    image="turquoise_t-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="W T-shirt", name_ru="Футболка W", price=21.99, description_en="W logo print t-shirt",
                    description_ru="Футболка с принтом W", image="W_T-shirt.jpg", stock=random.randint(10, 20)),
            Product(name_en="White Boots", name_ru="Белые ботинки", price=54.99, description_en="Stylish white boots",
                    description_ru="Стильные белые ботинки", image="White_boots.jpg", stock=random.randint(10, 20)),
        ]
        db.session.bulk_save_objects(products)
        promo_codes = [
            PromoCode(
                code="EASTER20",
                discount_percent=20,
                valid_until=datetime(2025, 12, 31, tzinfo=timezone.utc)
            ),
            PromoCode(
                code="ROMANOVLEXA25",
                discount_percent=25,
                valid_until=datetime(2025, 12, 31, tzinfo=timezone.utc)
            )
        ]
        db.session.bulk_save_objects(promo_codes)
        db.session.commit()

@app.route('/')
def index():
    lang = session.get('lang', 'en')
    products = Product.query.all()
    return render_template('index.html', products=products, t=translations[lang], lang=lang)

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in ['en', 'ru']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    lang = session.get('lang', 'en')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash(translations[lang]['username'] + ' или ' + translations[lang]['email'] + ' уже существует.', 'error')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, email=email)
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрация успешна! Пожалуйста, войдите.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', t=translations[lang], lang=lang)

@app.route('/login', methods=['GET', 'POST'])
def login():
    lang = session.get('lang', 'en')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('index'))
        flash('Неверное ' + translations[lang]['username'] + ' или ' + translations[lang]['password'] + '.', 'error')
    return render_template('login.html', t=translations[lang], lang=lang)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('applied_promo', None)
    lang = session.get('lang', 'en')
    flash('Выход выполнен успешно.', 'success')
    return redirect(url_for('index'))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    lang = session.get('lang', 'en')
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product, t=translations[lang], lang=lang)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    lang = session.get('lang', 'en')
    if 'user_id' not in session:
        flash('Пожалуйста, ' + translations[lang]['login'] + ', чтобы добавить товары в ' + translations[lang]['cart'] + '.', 'error')
        return redirect(url_for('login'))
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    if product.stock == 0:
        flash(translations[lang]['out_of_stock'] + '.', 'error')
        return redirect(url_for('product_detail', product_id=product_id))
    if product.stock < quantity:
        flash(translations[lang]['insufficient_stock'].format(product.name_en if lang == 'en' else product.name_ru), 'error')
        return redirect(url_for('product_detail', product_id=product_id))
    cart_item = CartItem.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    new_quantity = quantity + (cart_item.quantity if cart_item else 0)
    if product.stock < new_quantity:
        flash(translations[lang]['insufficient_stock'].format(product.name_en if lang == 'en' else product.name_ru), 'error')
        return redirect(url_for('product_detail', product_id=product_id))
    if cart_item:
        cart_item.quantity = new_quantity
    else:
        cart_item = CartItem(user_id=session['user_id'], product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    flash(translations[lang]['add_to_cart'] + '!', 'success')
    return redirect(url_for('cart'))

@app.route('/apply_promo', methods=['POST'])
def apply_promo():
    lang = session.get('lang', 'en')
    if 'user_id' not in session:
        flash('Пожалуйста, ' + translations[lang]['login'] + ', чтобы применить промокод.', 'error')
        return redirect(url_for('login'))

    promo_code = request.form.get('promo_code')
    promo = PromoCode.query.filter_by(code=promo_code, is_active=True).first()

    current_time = datetime.now(timezone.utc)
    if promo:
        valid_until = promo.valid_until
        if valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=timezone.utc)

        if valid_until >= current_time:
            session['applied_promo'] = {
                'code': promo.code,
                'discount_percent': promo.discount_percent,
                'id': promo.id
            }
            flash(translations[lang]['promo_applied'].format(promo.discount_percent), 'success')
        else:
            session.pop('applied_promo', None)
            flash(translations[lang]['invalid_promo'], 'error')
    else:
        session.pop('applied_promo', None)
        flash(translations[lang]['invalid_promo'], 'error')

    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    lang = session.get('lang', 'en')
    if 'user_id' not in session:
        flash('Пожалуйста, ' + translations[lang]['login'] + ', чтобы просмотреть ' + translations[lang]['cart'] + '.', 'error')
        return redirect(url_for('login'))
    cart_items = CartItem.query.filter_by(user_id=session['user_id']).all()
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    discount = 0
    applied_promo = session.get('applied_promo')

    if applied_promo:
        discount = subtotal * (applied_promo['discount_percent'] / 100)

    total = subtotal - discount
    return render_template('cart.html', cart_items=cart_items, subtotal=subtotal,
                           total=total, discount=discount, applied_promo=applied_promo,
                           t=translations[lang], lang=lang)

@app.route('/remove_from_cart/<int:item_id>')
def remove_from_cart(item_id):
    lang = session.get('lang', 'en')
    if 'user_id' not in session:
        flash('Пожалуйста, ' + translations[lang]['login'] + ', чтобы изменить ' + translations[lang]['cart'] + '.', 'error')
        return redirect(url_for('login'))
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != session['user_id']:
        flash('Несанкционированное действие.', 'error')
        return redirect(url_for('cart'))
    db.session.delete(cart_item)
    db.session.commit()
    flash(translations[lang]['remove'] + ' из ' + translations[lang]['cart'] + '.', 'success')
    return redirect(url_for('cart'))

@app.route('/place_order', methods=['POST'])
def place_order():
    lang = session.get('lang', 'en')
    if 'user_id' not in session:
        flash('Пожалуйста, ' + translations[lang]['login'] + ', чтобы оформить заказ.', 'error')
        return redirect(url_for('login'))

    delivery_address = request.form.get('delivery_address')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    if not delivery_address:
        flash(translations[lang]['address_required'], 'error')
        return redirect(url_for('cart'))

    cart_items = CartItem.query.filter_by(user_id=session['user_id']).all()
    if not cart_items:
        flash(translations[lang]['empty_cart'] + '.', 'error')
        return redirect(url_for('cart'))

    for item in cart_items:
        if item.product.stock < item.quantity:
            flash(translations[lang]['insufficient_stock'].format(
                item.product.name_en if lang == 'en' else item.product.name_ru), 'error')
            return redirect(url_for('cart'))

    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    discount = 0
    applied_promo = session.get('applied_promo')
    promo_id = None

    if applied_promo:
        promo = PromoCode.query.get(applied_promo['id'])
        if promo:
            valid_until = promo.valid_until
            if valid_until.tzinfo is None:
                valid_until = valid_until.replace(tzinfo=timezone.utc)

            current_time = datetime.now(timezone.utc)
            if valid_until >= current_time and promo.is_active:
                discount = subtotal * (applied_promo['discount_percent'] / 100)
                promo_id = promo.id

    total = subtotal - discount

    order = Order(
        user_id=session['user_id'],
        total=total,
        delivery_address=delivery_address,
        latitude=float(latitude) if latitude else None,
        longitude=float(longitude) if longitude else None,
        promo_code_id=promo_id,
        discount_applied=discount if discount > 0 else None
    )

    db.session.add(order)
    db.session.flush()

    for item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.product.price
        )
        item.product.stock -= item.quantity
        if item.product.stock == 0:
            item.product.restock_time = datetime.now(timezone.utc)
        db.session.add(order_item)
        db.session.delete(item)

    session.pop('applied_promo', None)
    db.session.commit()
    flash('Заказ успешно оформлен!', 'success')
    return redirect(url_for('orders'))

@app.route('/orders')
def orders():
    lang = session.get('lang', 'en')
    if 'user_id' not in session:
        flash('Пожалуйста, ' + translations[lang]['login'] + ', чтобы просмотреть ' + translations[lang]['orders'] + '.', 'error')
        return redirect(url_for('login'))
    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.date.desc()).all()
    return render_template('orders.html', orders=orders, t=translations[lang], lang=lang)

threading.Thread(target=restock_products, daemon=True).start()

os.makedirs('templates', exist_ok=True)
templates = {
    'base.html': '''
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ t.title }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class'
        };
    </script>
    <script>
        const savedTheme = localStorage.getItem('theme');
        if (
            savedTheme === 'dark' ||
            (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)
        ) {
            document.documentElement.classList.add('dark');
        }
    </script>
</head>
<body class="bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 transition-colors duration-300">
    <nav class="bg-blue-600 dark:bg-blue-800 text-white p-4">
        <div class="container mx-auto flex justify-between items-center">
            <a href="{{ url_for('index') }}" class="text-2xl font-bold">{{ t.title }}</a>
            <div class="flex items-center space-x-4">
                {% if session.username %}
                    <span class="mr-4">{{ t.welcome.format(session.username) }}</span>
                    <a href="{{ url_for('cart') }}" class="mr-4 px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded">{{ t.cart }}</a>
                    <a href="{{ url_for('orders') }}" class="mr-4 px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded">{{ t.orders }}</a>
                    <a href="{{ url_for('logout') }}" class="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded">{{ t.logout }}</a>
                {% else %}
                    <a href="{{ url_for('login') }}" class="mr-4 px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded">{{ t.login }}</a>
                    <a href="{{ url_for('register') }}" class="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded">{{ t.register }}</a>
                {% endif %}
                <a href="{{ url_for('set_language', lang='ru' if lang == 'en' else 'en') }}"
                   class="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded">
                   {{ t.language }}
                </a>
                <button id="theme-toggle"
                        onclick="toggleTheme()"
                        class="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded">
                    ☀️
                </button>
            </div>
        </div>
    </nav>
    <div class="container mx-auto p-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="bg-{{ 'green' if category == 'success' else 'red' }}-100 dark:bg-{{ 'green' if category == 'success' else 'red' }}-900 border-{{ 'green' if category == 'success' else 'red' }}-400 dark:border-{{ 'green' if category == 'success' else 'red' }}-600 text-{{ 'green' if category == 'success' else 'red' }}-700 dark:text-{{ 'green' if category == 'success' else 'red' }}-300 px-4 py-3 rounded mb-4">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
    <div class="fixed bottom-4 right-4">
        <button id="easter-egg-button" class="text-gray-100 dark:text-gray-800 hover:text-blue-600 dark:hover:text-blue-400 transition-colors duration-300">
            {{ 'Secret' if lang == 'en' else 'Секрет' }}
        </button>
    </div>
    <div id="easter-egg-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center hidden">
        <div class="bg-white dark:bg-gray-700 p-6 rounded-lg shadow-lg text-center max-w-sm">
            <h2 class="text-2xl font-bold mb-4">{{ 'You Found the Secret!' if lang == 'en' else 'Вы нашли секрет!' }}</h2>
            <p class="text-lg mb-4">{{ 'Use code <strong>EASTER20</strong> for a surprise!' if lang == 'en' else 'Используйте код ROMANOVLEXA25 для сюрприза!' }}</p>
            <div class="flex justify-center mb-4">
                <img src="{{ url_for('static', filename='images/lexa.jpg') if 'lexa.jpg' else 'https://via.placeholder.com/100' }}" alt="T-shirt" class="w-24 h-24 animate-spin-slow">
            </div>
            <button onclick="closeEasterEgg()" class="bg-blue-600 dark:bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600">
                {{ 'Close' if lang == 'en' else 'Закрыть' }}
            </button>
        </div>
    </div>
    <script>
        function toggleTheme() {
            const html = document.documentElement;
            const btn = document.getElementById('theme-toggle');
            const isDark = !html.classList.contains('dark');
            html.classList.toggle('dark', isDark);
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            btn.textContent = isDark ? '🌙' : '☀️';
        }
        document.addEventListener('DOMContentLoaded', () => {
            console.log('DOM loaded, initializing Easter Egg');
            const html = document.documentElement;
            const btn = document.getElementById('theme-toggle');
            if (btn) {
                const isDark = html.classList.contains('dark');
                btn.textContent = isDark ? '🌙' : '☀️';
            }
            const easterButton = document.getElementById('easter-egg-button');
            if (easterButton) {
                console.log('Easter Egg button found');
                easterButton.addEventListener('click', () => {
                    console.log('Easter Egg button clicked, showing modal');
                    const modal = document.getElementById('easter-egg-modal');
                    if (modal) {
                        modal.classList.remove('hidden');
                    } else {
                        console.error('Easter Egg modal not found');
                    }
                });
            } else {
                console.error('Easter Egg button not found');
            }
        });
        function closeEasterEgg() {
            const modal = document.getElementById('easter-egg-modal');
            if (modal) {
                modal.classList.add('hidden');
            } else {
                console.error('Easter Egg modal not found when trying to close');
            }
        }
        const style = document.createElement('style');
        style.innerHTML = `
            .animate-spin-slow {
                animation: spin 3s linear infinite;
            }
            @keyframes spin {
                from {
                    transform: rotate(0deg);
                }
                to {
                    transform: rotate(360deg);
                }
            }
        `;
        document.head.appendChild(style);
    </script>
</body>
</html>
''',
    'index.html': '''
{% extends 'base.html' %}
{% block content %}
    <h1 class="text-3xl font-bold mb-6">{{ t.our_products }}</h1>
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {% for product in products %}
            <div class="bg-white dark:bg-gray-700 rounded-lg shadow-md p-4">
                <div class="relative w-full h-64 flex items-center justify-center">
                    <img src="{{ url_for('static', filename='images/' + product.image) if product.image else 'https://via.placeholder.com/150' }}" alt="{{ product.name_en if lang == 'en' else product.name_ru }}" class="max-h-full max-w-full object-contain rounded">
                </div>
                <h2 class="text-xl font-semibold mt-2">{{ product.name_en if lang == 'en' else product.name_ru }}</h2>
                <p class="text-gray-600 dark:text-gray-300">{{ product.description_en if lang == 'en' else product.description_ru }}</p>
                <p class="text-lg font-bold mt-2">${{ "%.2f" % product.price }}</p>
                <p class="text-gray-600 dark:text-gray-300">{{ t.stock.format(product.stock) }}</p>
                <a href="{{ url_for('product_detail', product_id=product.id) }}" class="mt-4 inline-block bg-blue-600 dark:bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600">{{ t.view_details }}</a>
            </div>
        {% endfor %}
    </div>
{% endblock %}
''',
    'register.html': '''
{% extends 'base.html' %}
{% block content %}
    <h1 class="text-3xl font-bold mb-6">{{ t.register }}</h1>
    <form method="POST" class="max-w-md">
        <div class="mb-4">
            <label for="username" class="block text-gray-700 dark:text-gray-300">{{ t.username }}</label>
            <input type="text" name="username" id="username" class="w-full border rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100" required>
        </div>
        <div class="mb-4">
            <label for="email" class="block text-gray-700 dark:text-gray-300">{{ t.email }}</label>
            <input type="email" name="email" id="email" class="w-full border rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100" required>
        </div>
        <div class="mb-4">
            <label for="password" class="block text-gray-700 dark:text-gray-300">{{ t.password }}</label>
            <input type="password" name="password" id="password" class="w-full border rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100" required>
        </div>
        <button type="submit" class="bg-blue-600 dark:bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600">{{ t.register }}</button>
    </form>
{% endblock %}
''',
    'login.html': '''
{% extends 'base.html' %}
{% block content %}
    <h1 class="text-3xl font-bold mb-6">{{ t.login }}</h1>
    <form method="POST" class="max-w-md">
        <div class="mb-4">
            <label for="username" class="block text-gray-700 dark:text-gray-300">{{ t.username }}</label>
            <input type="text" name="username" id="username" class="w-full border rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100" required>
        </div>
        <div class="mb-4">
            <label for="password" class="block text-gray-700 dark:text-gray-300">{{ t.password }}</label>
            <input type="password" name="password" id="password" class="w-full border rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100" required>
        </div>
        <button type="submit" class="bg-blue-600 dark:bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600">{{ t.login }}</button>
    </form>
{% endblock %}
''',
    'product.html': '''
{% extends 'base.html' %}
{% block content %}
    <div class="flex flex-col md:flex-row gap-6">
        <div class="relative w-full md:w-2/3 h-96 flex items-center justify-center">
            <img src="{{ url_for('static', filename='images/' + product.image) if product.image and product.image in ['Baggy_Jeans.jpg', 'Baggy_pants.jpg', 'Bandana_T-shirt.jpg', 'Black_T-shirt.jpg', 'BLG_T-shirt.jpg', 'Blue_T-shirt.jpg', 'Cargo_pants.jpg', 'Fashion_boots.jpg', 'Fashion_sneakers.jpg', 'Fashion_t-shirt.jpg', 'Fashionable_T-shirt.jpg', 'Glitter_t-shirt.jpg', 'Gray_sweater.jpg', 'Green_T-shirt.jpg', 'Jeans1.jpg', 'jungle_t-shirt.jpg', 'polo.jpg', 'Red_sneakers.jpg', 'Running_sneakers.jpg', 'Spotted_pants.jpg', 'Sweater.jpg', 'Torn_bt-shirt.jpg', 'Torn_t-shirt.jpg', 'trousers.jpg', 'T-shirt.jpg', 'T-shirt_w_print.jpg', 'turquoise_t-shirt.jpg', 'W_T-shirt.jpg', 'White_boots.jpg'] else 'https://via.placeholder.com/300' }}" alt="{{ product.name_en if lang == 'en' else product.name_ru }}" class="max-h-full max-w-full object-contain rounded">
        </div>
        <div>
            <h1 class="text-3xl font-bold mb-4">{{ product.name_en if lang == 'en' else product.name_ru }}</h1>
            <p class="text-gray-600 dark:text-gray-300 mb-4">{{ product.description_en if lang == 'en' else product.description_ru }}</p>
            <p class="text-2xl font-bold mb-4">${{ "%.2f" % product.price }}</p>
            <p class="text-gray-600 dark:text-gray-300 mb-4">{{ t.stock.format(product.stock) }}</p>
            {% if product.stock > 0 %}
                <form method="POST" action="{{ url_for('add_to_cart', product_id=product.id) }}">
                    <label for="quantity" class="block text-gray-700 dark:text-gray-300 mb-2">{{ t.quantity }}</label>
                    <input type="number" name="quantity" id="quantity" value="1" min="1" max="{{ product.stock }}" class="w-20 border rounded px-3 py-2 mb-4 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
                    <button type="submit" class="bg-blue-600 dark:bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600">{{ t.add_to_cart }}</button>
                </form>
            {% else %}
                <p class="text-red-600 dark:text-red-400">{{ t.out_of_stock }}</p>
            {% endif %}
        </div>
    </div>
{% endblock %}
''',
    'cart.html': '''
{% extends 'base.html' %}
{% block content %}
    <h1 class="text-3xl font-bold mb-6">{{ t.your_cart }}</h1>
    {% if cart_items %}
        <div class="bg-white dark:bg-gray-700 rounded-lg shadow-md p-4">
            {% for item in cart_items %}
                <div class="flex items-center justify-between border-b py-4">
                    <div class="flex items-center">
                        <img src="{{ url_for('static', filename='images/' + item.product.image) if item.product.image else 'https://via.placeholder.com/100' }}" alt="{{ item.product.name_en if lang == 'en' else item.product.name_ru }}" class="w-24 h-24 object-cover rounded mr-4">
                        <div>
                            <h2 class="text-lg font-semibold">{{ item.product.name_en if lang == 'en' else item.product.name_ru }}</h2>
                            <p class="text-gray-600 dark:text-gray-300">${{ "%.2f" % item.product.price }} x {{ item.quantity }}</p>
                            <p class="text-gray-600 dark:text-gray-300">{{ t.stock.format(item.product.stock) }}</p>
                        </div>
                    </div>
                    <a href="{{ url_for('remove_from_cart', item_id=item.id) }}" class="text-red-600 dark:text-red-400 hover:underline">{{ t.remove }}</a>
                </div>
            {% endfor %}
            <div class="mt-4">
                <form method="POST" action="{{ url_for('apply_promo') }}" class="mb-4 flex gap-2">
                    <input type="text" name="promo_code" placeholder="{{ t.promo_code }}" class="border rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
                    <button type="submit" class="bg-blue-600 dark:bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600">{{ t.apply_promo }}</button>
                </form>
                {% if applied_promo %}
                    <p class="text-green-600 dark:text-green-400 mb-2">{{ t.promo_applied.format(applied_promo.discount_percent) }}</p>
                {% endif %}
                <p class="text-lg font-bold">Итого без скидки: ${{ "%.2f" % subtotal }}</p>
                {% if discount > 0 %}
                    <p class="text-lg font-bold text-green-600 dark:text-green-400">{{ t.discount }}: -${{ "%.2f" % discount }}</p>
                {% endif %}
                <p class="text-xl font-bold">{{ t.total }}: ${{ "%.2f" % total }}</p>
                <form method="POST" action="{{ url_for('place_order') }}">
                    <div class="mb-4">
                        <label for="delivery_address" class="block text-gray-700 dark:text-gray-300">{{ t.delivery_address }}</label>
                        <input type="text" name="delivery_address" id="delivery_address" class="w-full border rounded px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100" required>
                        <input type="hidden" name="latitude" id="latitude">
                        <input type="hidden" name="longitude" id="longitude">
                    </div>
                    <div class="mb-4">
                        <label class="block text-gray-700 dark:text-gray-300 mb-2">Выберите место доставки</label>
                        <div id="map" class="w-full h-96 rounded"></div>
                    </div>
                    <button type="submit" class="mt-4 bg-blue-600 dark:bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-700 dark:hover:bg-blue-600">{{ t.place_order }}</button>
                </form>
            </div>
        </div>
    {% else %}
        <p>{{ t.empty_cart }}</p>
    {% endif %}
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map').setView([58.538183, 31.288503], 12); // Москва пусть будет в начале
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        const marker = L.marker([58.538183, 31.288503], { draggable: true }).addTo(map);

        marker.on('dragend', function (e) {
            const latlng = marker.getLatLng();
            document.getElementById('latitude').value = latlng.lat;
            document.getElementById('longitude').value = latlng.lng;

            fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latlng.lat}&lon=${latlng.lng}&format=json`)
                .then(response => response.json())
                .then(data => {
                    if (data.display_name) {
                        document.getElementById('delivery_address').value = data.display_name;
                    }
                })
                .catch(error => console.error('Ошибка', error));
        });

        const addressInput = document.getElementById('delivery_address');
        addressInput.addEventListener('input', function () {
            const query = addressInput.value;
            if (query.length < 3) return;

            fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=5`)
                .then(response => response.json())
                .then(data => {
                    if (data.length > 0) {
                        const firstResult = data[0];
                        const lat = parseFloat(firstResult.lat);
                        const lon = parseFloat(firstResult.lon);
                        map.setView([lat, lon], 12);
                        marker.setLatLng([lat, lon]);
                        document.getElementById('latitude').value = lat;
                        document.getElementById('longitude').value = lon;
                        document.getElementById('delivery_address').value = firstResult.display_name;
                    }
                })
                .catch(error => console.error('Ошибка поиска адреса:', error));
        });
    </script>
{% endblock %}
''',
    'orders.html': '''
{% extends 'base.html' %}
{% block content %}
    <h1 class="text-3xl font-bold mb-6">{{ t.your_orders }}</h1>
    {% if orders %}
        <div class="bg-white dark:bg-gray-700 rounded-lg shadow-md p-4">
            {% for order in orders %}
                <div class="border-b py-4">
                    <h2 class="text-xl font-semibold">Заказ #{{ order.id }} - {{ order.date.strftime('%Y-%m-%d %H:%M') }}</h2>
                    <p class="text-gray-600 dark:text-gray-300">{{ t.total }}: ${{ "%.2f" % order.total }}</p>
                    <p class="text-gray-600 dark:text-gray-300">{{ t.delivery_address }}: {{ order.delivery_address }}</p>
                    {% if order.discount_applied %}
                        <p class="text-green-600 dark:text-green-400">{{ t.discount }}: -${{ "%.2f" % order.discount_applied }}</p>
                    {% endif %}
                    <h3 class="text-lg font-semibold mt-2">{{ t.our_products }}</h3>
                    {% for item in order.items %}
                        <div class="flex items-center justify-between mt-2">
                            <div>
                                <p>{{ item.product.name_en if lang == 'en' else item.product.name_ru }} x {{ item.quantity }}</p>
                                <p class="text-gray-600 dark:text-gray-300">${{ "%.2f" % item.price }} x {{ item.quantity }}</p>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            {% endfor %}
        </div>
    {% else %}
        <p>{{ t.no_orders }}</p>
    {% endif %}
{% endblock %}
'''
}

for filename, content in templates.items():
    with open(os.path.join('templates', filename), 'w', encoding='utf-8') as f:
        f.write(content)

os.makedirs('static/images', exist_ok=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
