"""
Flask Inventory Management SaaS — Full-featured web application.
Beautiful UI with dark theme, glassmorphism, and smooth animations.
"""

import os
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

# =============================================================================
# App Configuration
# =============================================================================

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

db = SQLAlchemy(app)


# =============================================================================
# Models
# =============================================================================


class Organization(db.Model):
    __tablename__ = "organizations"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    plan = db.Column(db.String(20), default="free")
    max_users = db.Column(db.Integer, default=5)
    max_warehouses = db.Column(db.Integer, default=2)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = db.relationship("User", backref="organization", lazy=True)
    categories = db.relationship("Category", backref="organization", lazy=True)
    warehouses = db.relationship("Warehouse", backref="organization", lazy=True)
    products = db.relationship("Product", backref="organization", lazy=True)
    transactions = db.relationship("InventoryTransaction", backref="organization", lazy=True)

    def __repr__(self):
        return f"<Organization {self.name}>"


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(150), default="")
    last_name = db.Column(db.String(150), default="")
    phone = db.Column(db.String(20), default="")
    role = db.Column(db.String(10), default="viewer")  # owner, admin, manager, viewer
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)

    performed_transactions = db.relationship("InventoryTransaction", backref="performed_by", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def is_org_admin(self):
        return self.role in ("owner", "admin")

    def __repr__(self):
        return f"<User {self.username}>"


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    parent_id = db.Column(db.String(36), db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = db.relationship("Category", remote_side=[id], backref="children")
    products = db.relationship("Product", backref="category", lazy=True)

    def __repr__(self):
        return f"<Category {self.name}>"


class Warehouse(db.Model):
    __tablename__ = "warehouses"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, default="")
    city = db.Column(db.String(100), default="")
    state = db.Column(db.String(100), default="")
    country = db.Column(db.String(100), default="US")
    postal_code = db.Column(db.String(20), default="")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    products = db.relationship("Product", backref="warehouse", lazy=True)
    transactions = db.relationship("InventoryTransaction", backref="warehouse", lazy=True)

    def __repr__(self):
        return f"<Warehouse {self.name} ({self.code})>"


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    category_id = db.Column(db.String(36), db.ForeignKey("categories.id"), nullable=True)
    warehouse_id = db.Column(db.String(36), db.ForeignKey("warehouses.id"), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(50), nullable=False)
    barcode = db.Column(db.String(100), default="")
    description = db.Column(db.Text, default="")
    unit_price = db.Column(db.Float, default=0)
    cost_price = db.Column(db.Float, default=0)
    quantity = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=10)
    unit = db.Column(db.String(20), default="pcs")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transactions = db.relationship("InventoryTransaction", backref="product", lazy=True)

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    @property
    def stock_value(self):
        return self.quantity * self.cost_price

    def __repr__(self):
        return f"<Product {self.name} [{self.sku}]>"


class InventoryTransaction(db.Model):
    __tablename__ = "inventory_transactions"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey("products.id"), nullable=False)
    warehouse_id = db.Column(db.String(36), db.ForeignKey("warehouses.id"), nullable=True)
    performed_by_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    transaction_type = db.Column(db.String(15), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reference = db.Column(db.String(100), default="")
    notes = db.Column(db.Text, default="")
    quantity_before = db.Column(db.Integer, nullable=False)
    quantity_after = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    TRANSACTION_TYPES = {
        "purchase": "Purchase (Stock In)",
        "sale": "Sale (Stock Out)",
        "transfer_in": "Transfer In",
        "transfer_out": "Transfer Out",
        "adjustment": "Adjustment",
        "return": "Return",
    }

    @property
    def transaction_type_display(self):
        return self.TRANSACTION_TYPES.get(self.transaction_type, self.transaction_type)

    def __repr__(self):
        return f"<Transaction {self.transaction_type} {self.quantity}>"


# =============================================================================
# Auth Decorators
# =============================================================================


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None


def get_current_org():
    user = get_current_user()
    if user and user.organization:
        return user.organization
    return None


@app.context_processor
def inject_user():
    return {"current_user": get_current_user(), "current_org": get_current_org()}


# =============================================================================
# Auth Routes
# =============================================================================


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        org_name = request.form.get("org_name", "").strip()
        org_slug = request.form.get("org_slug", "").strip().lower()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()

        if not all([org_name, org_slug, username, email, password]):
            flash("All required fields must be filled.", "error")
            return render_template("register.html")

        if Organization.query.filter_by(slug=org_slug).first():
            flash("Organization slug already exists.", "error")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "error")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return render_template("register.html")

        org = Organization(name=org_name, slug=org_slug, plan="professional", max_users=20, max_warehouses=5)
        db.session.add(org)
        db.session.flush()

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            organization_id=org.id,
            role="owner",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        session.permanent = True
        flash(f"Welcome to {org_name}! Your account has been created.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            session["user_id"] = user.id
            session.permanent = True
            flash(f"Welcome back, {user.full_name}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials or account disabled.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# =============================================================================
# Dashboard
# =============================================================================


@app.route("/dashboard")
@login_required
def dashboard():
    org = get_current_org()
    if not org:
        flash("No organization found.", "error")
        return redirect(url_for("login"))

    total_products = Product.query.filter_by(organization_id=org.id, is_active=True).count()
    total_categories = Category.query.filter_by(organization_id=org.id).count()
    total_warehouses = Warehouse.query.filter_by(organization_id=org.id, is_active=True).count()
    total_users = User.query.filter_by(organization_id=org.id, is_active=True).count()

    low_stock_products = Product.query.filter(
        Product.organization_id == org.id,
        Product.is_active == True,
        Product.quantity <= Product.low_stock_threshold,
    ).all()

    total_stock_value = sum(p.stock_value for p in Product.query.filter_by(organization_id=org.id, is_active=True).all())

    recent_transactions = (
        InventoryTransaction.query
        .filter_by(organization_id=org.id)
        .order_by(InventoryTransaction.created_at.desc())
        .limit(10)
        .all()
    )

    # Category distribution data
    categories = Category.query.filter_by(organization_id=org.id).all()
    category_data = []
    for cat in categories:
        count = Product.query.filter_by(organization_id=org.id, category_id=cat.id, is_active=True).count()
        if count > 0:
            category_data.append({"name": cat.name, "count": count})

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_categories=total_categories,
        total_warehouses=total_warehouses,
        total_users=total_users,
        low_stock_products=low_stock_products,
        total_stock_value=total_stock_value,
        recent_transactions=recent_transactions,
        category_data=category_data,
    )


# =============================================================================
# Products
# =============================================================================


@app.route("/products")
@login_required
def products():
    org = get_current_org()
    search = request.args.get("search", "")
    category_id = request.args.get("category", "")
    warehouse_id = request.args.get("warehouse", "")
    stock_filter = request.args.get("stock", "")

    query = Product.query.filter_by(organization_id=org.id)

    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%"),
                Product.barcode.ilike(f"%{search}%"),
            )
        )
    if category_id:
        query = query.filter_by(category_id=category_id)
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)
    if stock_filter == "low":
        query = query.filter(Product.quantity <= Product.low_stock_threshold, Product.is_active == True)
    elif stock_filter == "out":
        query = query.filter(Product.quantity <= 0)

    products_list = query.order_by(Product.name).all()
    categories = Category.query.filter_by(organization_id=org.id).order_by(Category.name).all()
    warehouses = Warehouse.query.filter_by(organization_id=org.id, is_active=True).order_by(Warehouse.name).all()

    return render_template(
        "products.html",
        products=products_list,
        categories=categories,
        warehouses=warehouses,
        search=search,
        category_id=category_id,
        warehouse_id=warehouse_id,
        stock_filter=stock_filter,
    )


@app.route("/products/add", methods=["GET", "POST"])
@login_required
def add_product():
    org = get_current_org()
    user = get_current_user()
    if user.role == "viewer":
        flash("You don't have permission to add products.", "error")
        return redirect(url_for("products"))

    if request.method == "POST":
        product = Product(
            organization_id=org.id,
            name=request.form.get("name", "").strip(),
            sku=request.form.get("sku", "").strip(),
            barcode=request.form.get("barcode", "").strip(),
            description=request.form.get("description", "").strip(),
            category_id=request.form.get("category_id") or None,
            warehouse_id=request.form.get("warehouse_id") or None,
            unit_price=float(request.form.get("unit_price", 0)),
            cost_price=float(request.form.get("cost_price", 0)),
            low_stock_threshold=int(request.form.get("low_stock_threshold", 10)),
            unit=request.form.get("unit", "pcs"),
        )

        existing = Product.query.filter_by(organization_id=org.id, sku=product.sku).first()
        if existing:
            flash("A product with this SKU already exists.", "error")
        else:
            db.session.add(product)
            db.session.commit()
            flash(f"Product '{product.name}' created successfully!", "success")
            return redirect(url_for("products"))

    categories = Category.query.filter_by(organization_id=org.id).order_by(Category.name).all()
    warehouses = Warehouse.query.filter_by(organization_id=org.id, is_active=True).order_by(Warehouse.name).all()
    return render_template("product_form.html", product=None, categories=categories, warehouses=warehouses)


@app.route("/products/<product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    org = get_current_org()
    user = get_current_user()
    if user.role == "viewer":
        flash("You don't have permission to edit products.", "error")
        return redirect(url_for("products"))

    product = Product.query.filter_by(id=product_id, organization_id=org.id).first_or_404()

    if request.method == "POST":
        product.name = request.form.get("name", "").strip()
        product.sku = request.form.get("sku", "").strip()
        product.barcode = request.form.get("barcode", "").strip()
        product.description = request.form.get("description", "").strip()
        product.category_id = request.form.get("category_id") or None
        product.warehouse_id = request.form.get("warehouse_id") or None
        product.unit_price = float(request.form.get("unit_price", 0))
        product.cost_price = float(request.form.get("cost_price", 0))
        product.low_stock_threshold = int(request.form.get("low_stock_threshold", 10))
        product.unit = request.form.get("unit", "pcs")
        product.is_active = request.form.get("is_active") == "on"
        product.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f"Product '{product.name}' updated!", "success")
        return redirect(url_for("products"))

    categories = Category.query.filter_by(organization_id=org.id).order_by(Category.name).all()
    warehouses = Warehouse.query.filter_by(organization_id=org.id, is_active=True).order_by(Warehouse.name).all()
    return render_template("product_form.html", product=product, categories=categories, warehouses=warehouses)


@app.route("/products/<product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    org = get_current_org()
    user = get_current_user()
    if user.role == "viewer":
        flash("You don't have permission.", "error")
        return redirect(url_for("products"))

    product = Product.query.filter_by(id=product_id, organization_id=org.id).first_or_404()
    product.is_active = False
    product.updated_at = datetime.utcnow()
    db.session.commit()
    flash(f"Product '{product.name}' deactivated.", "info")
    return redirect(url_for("products"))


# =============================================================================
# Categories
# =============================================================================


@app.route("/categories")
@login_required
def categories():
    org = get_current_org()
    cats = Category.query.filter_by(organization_id=org.id).order_by(Category.name).all()
    return render_template("categories.html", categories=cats)


@app.route("/categories/add", methods=["GET", "POST"])
@login_required
def add_category():
    org = get_current_org()
    user = get_current_user()
    if user.role == "viewer":
        flash("You don't have permission.", "error")
        return redirect(url_for("categories"))

    if request.method == "POST":
        cat = Category(
            organization_id=org.id,
            name=request.form.get("name", "").strip(),
            slug=request.form.get("slug", "").strip().lower(),
            description=request.form.get("description", "").strip(),
            parent_id=request.form.get("parent_id") or None,
        )
        existing = Category.query.filter_by(organization_id=org.id, slug=cat.slug).first()
        if existing:
            flash("A category with this slug already exists.", "error")
        else:
            db.session.add(cat)
            db.session.commit()
            flash(f"Category '{cat.name}' created!", "success")
            return redirect(url_for("categories"))

    parent_cats = Category.query.filter_by(organization_id=org.id).order_by(Category.name).all()
    return render_template("category_form.html", category=None, parent_categories=parent_cats)


@app.route("/categories/<cat_id>/edit", methods=["GET", "POST"])
@login_required
def edit_category(cat_id):
    org = get_current_org()
    user = get_current_user()
    if user.role == "viewer":
        flash("You don't have permission.", "error")
        return redirect(url_for("categories"))

    cat = Category.query.filter_by(id=cat_id, organization_id=org.id).first_or_404()

    if request.method == "POST":
        cat.name = request.form.get("name", "").strip()
        cat.slug = request.form.get("slug", "").strip().lower()
        cat.description = request.form.get("description", "").strip()
        cat.parent_id = request.form.get("parent_id") or None
        cat.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f"Category '{cat.name}' updated!", "success")
        return redirect(url_for("categories"))

    parent_cats = Category.query.filter_by(organization_id=org.id).filter(Category.id != cat_id).order_by(Category.name).all()
    return render_template("category_form.html", category=cat, parent_categories=parent_cats)


@app.route("/categories/<cat_id>/delete", methods=["POST"])
@login_required
def delete_category(cat_id):
    org = get_current_org()
    user = get_current_user()
    if user.role == "viewer":
        flash("You don't have permission.", "error")
        return redirect(url_for("categories"))

    cat = Category.query.filter_by(id=cat_id, organization_id=org.id).first_or_404()
    product_count = Product.query.filter_by(category_id=cat_id).count()
    if product_count > 0:
        flash(f"Cannot delete: {product_count} products are in this category.", "error")
    else:
        name = cat.name
        db.session.delete(cat)
        db.session.commit()
        flash(f"Category '{name}' deleted.", "info")
    return redirect(url_for("categories"))


# =============================================================================
# Warehouses
# =============================================================================


@app.route("/warehouses")
@login_required
def warehouses():
    org = get_current_org()
    whs = Warehouse.query.filter_by(organization_id=org.id).order_by(Warehouse.name).all()
    return render_template("warehouses.html", warehouses=whs)


@app.route("/warehouses/add", methods=["GET", "POST"])
@login_required
def add_warehouse():
    org = get_current_org()
    user = get_current_user()
    if user.role == "viewer":
        flash("You don't have permission.", "error")
        return redirect(url_for("warehouses"))

    if request.method == "POST":
        wh = Warehouse(
            organization_id=org.id,
            name=request.form.get("name", "").strip(),
            code=request.form.get("code", "").strip().upper(),
            address=request.form.get("address", "").strip(),
            city=request.form.get("city", "").strip(),
            state=request.form.get("state", "").strip(),
            country=request.form.get("country", "US").strip(),
            postal_code=request.form.get("postal_code", "").strip(),
        )
        existing = Warehouse.query.filter_by(organization_id=org.id, code=wh.code).first()
        if existing:
            flash("A warehouse with this code already exists.", "error")
        else:
            db.session.add(wh)
            db.session.commit()
            flash(f"Warehouse '{wh.name}' created!", "success")
            return redirect(url_for("warehouses"))

    return render_template("warehouse_form.html", warehouse=None)


@app.route("/warehouses/<wh_id>/edit", methods=["GET", "POST"])
@login_required
def edit_warehouse(wh_id):
    org = get_current_org()
    user = get_current_user()
    if user.role == "viewer":
        flash("You don't have permission.", "error")
        return redirect(url_for("warehouses"))

    wh = Warehouse.query.filter_by(id=wh_id, organization_id=org.id).first_or_404()

    if request.method == "POST":
        wh.name = request.form.get("name", "").strip()
        wh.code = request.form.get("code", "").strip().upper()
        wh.address = request.form.get("address", "").strip()
        wh.city = request.form.get("city", "").strip()
        wh.state = request.form.get("state", "").strip()
        wh.country = request.form.get("country", "US").strip()
        wh.postal_code = request.form.get("postal_code", "").strip()
        wh.is_active = request.form.get("is_active") == "on"
        wh.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f"Warehouse '{wh.name}' updated!", "success")
        return redirect(url_for("warehouses"))

    return render_template("warehouse_form.html", warehouse=wh)


# =============================================================================
# Transactions
# =============================================================================


@app.route("/transactions")
@login_required
def transactions():
    org = get_current_org()
    tx_type = request.args.get("type", "")
    product_id = request.args.get("product", "")

    query = InventoryTransaction.query.filter_by(organization_id=org.id)

    if tx_type:
        query = query.filter_by(transaction_type=tx_type)
    if product_id:
        query = query.filter_by(product_id=product_id)

    txs = query.order_by(InventoryTransaction.created_at.desc()).all()
    products_list = Product.query.filter_by(organization_id=org.id).order_by(Product.name).all()

    return render_template("transactions.html", transactions=txs, products=products_list, tx_type=tx_type, product_id=product_id)


@app.route("/transactions/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    org = get_current_org()
    user = get_current_user()
    if user.role == "viewer":
        flash("You don't have permission.", "error")
        return redirect(url_for("transactions"))

    if request.method == "POST":
        product_id = request.form.get("product_id")
        tx_type = request.form.get("transaction_type")
        quantity = int(request.form.get("quantity", 0))
        warehouse_id = request.form.get("warehouse_id") or None
        reference = request.form.get("reference", "").strip()
        notes = request.form.get("notes", "").strip()

        product = Product.query.filter_by(id=product_id, organization_id=org.id).first()
        if not product:
            flash("Product not found.", "error")
        elif quantity <= 0:
            flash("Quantity must be positive.", "error")
        else:
            outbound = tx_type in ("sale", "transfer_out")
            if outbound and product.quantity < quantity:
                flash(f"Insufficient stock. Available: {product.quantity}, requested: {quantity}.", "error")
            else:
                effective_qty = -abs(quantity) if outbound else abs(quantity)
                qty_before = product.quantity
                product.quantity += effective_qty
                product.updated_at = datetime.utcnow()

                tx = InventoryTransaction(
                    organization_id=org.id,
                    product_id=product.id,
                    warehouse_id=warehouse_id,
                    performed_by_id=user.id,
                    transaction_type=tx_type,
                    quantity=effective_qty,
                    reference=reference,
                    notes=notes,
                    quantity_before=qty_before,
                    quantity_after=product.quantity,
                )
                db.session.add(tx)
                db.session.commit()
                flash(f"Transaction recorded: {tx.transaction_type_display}", "success")
                return redirect(url_for("transactions"))

    products_list = Product.query.filter_by(organization_id=org.id, is_active=True).order_by(Product.name).all()
    warehouses = Warehouse.query.filter_by(organization_id=org.id, is_active=True).order_by(Warehouse.name).all()
    return render_template("transaction_form.html", products=products_list, warehouses=warehouses)


# =============================================================================
# Users Management
# =============================================================================


@app.route("/users")
@login_required
def users():
    org = get_current_org()
    user_list = User.query.filter_by(organization_id=org.id).order_by(User.username).all()
    return render_template("users.html", users=user_list)


@app.route("/users/add", methods=["GET", "POST"])
@login_required
def add_user():
    org = get_current_org()
    user = get_current_user()
    if not user.is_org_admin:
        flash("Only admins can add users.", "error")
        return redirect(url_for("users"))

    if request.method == "POST":
        new_user = User(
            username=request.form.get("username", "").strip(),
            email=request.form.get("email", "").strip(),
            first_name=request.form.get("first_name", "").strip(),
            last_name=request.form.get("last_name", "").strip(),
            phone=request.form.get("phone", "").strip(),
            role=request.form.get("role", "viewer"),
            organization_id=org.id,
        )
        new_user.set_password(request.form.get("password", ""))

        if User.query.filter_by(username=new_user.username).first():
            flash("Username already taken.", "error")
        elif User.query.filter_by(email=new_user.email).first():
            flash("Email already registered.", "error")
        else:
            db.session.add(new_user)
            db.session.commit()
            flash(f"User '{new_user.username}' created!", "success")
            return redirect(url_for("users"))

    return render_template("user_form.html", edit_user=None)


@app.route("/users/<user_id>/edit", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    org = get_current_org()
    user = get_current_user()
    if not user.is_org_admin:
        flash("Only admins can edit users.", "error")
        return redirect(url_for("users"))

    edit_u = User.query.filter_by(id=user_id, organization_id=org.id).first_or_404()

    if request.method == "POST":
        edit_u.first_name = request.form.get("first_name", "").strip()
        edit_u.last_name = request.form.get("last_name", "").strip()
        edit_u.email = request.form.get("email", "").strip()
        edit_u.phone = request.form.get("phone", "").strip()
        edit_u.role = request.form.get("role", edit_u.role)
        edit_u.is_active = request.form.get("is_active") == "on"

        new_pw = request.form.get("password", "").strip()
        if new_pw:
            edit_u.set_password(new_pw)

        db.session.commit()
        flash(f"User '{edit_u.username}' updated!", "success")
        return redirect(url_for("users"))

    return render_template("user_form.html", edit_user=edit_u)


# =============================================================================
# Settings / Organization
# =============================================================================


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    org = get_current_org()
    user = get_current_user()

    if request.method == "POST" and user.is_org_admin:
        org.name = request.form.get("name", org.name).strip()
        org.plan = request.form.get("plan", org.plan)
        org.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Organization settings updated!", "success")

    return render_template("settings.html")


# =============================================================================
# API endpoints for charts (AJAX)
# =============================================================================


@app.route("/api/dashboard-stats")
@login_required
def api_dashboard_stats():
    org = get_current_org()

    # Transaction trend (last 7 days)
    trend = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        count = InventoryTransaction.query.filter(
            InventoryTransaction.organization_id == org.id,
            InventoryTransaction.created_at >= day_start,
            InventoryTransaction.created_at <= day_end,
        ).count()
        trend.append({"date": day.strftime("%b %d"), "count": count})

    # Stock distribution by warehouse
    warehouses = Warehouse.query.filter_by(organization_id=org.id, is_active=True).all()
    warehouse_stock = []
    for wh in warehouses:
        total = db.session.query(db.func.sum(Product.quantity)).filter_by(
            organization_id=org.id, warehouse_id=wh.id, is_active=True
        ).scalar() or 0
        warehouse_stock.append({"name": wh.name, "stock": total})

    return jsonify({"trend": trend, "warehouse_stock": warehouse_stock})


# =============================================================================
# Seed Data
# =============================================================================


def seed_demo_data():
    """Seed database with demo data if empty."""
    if Organization.query.count() > 0:
        return

    org = Organization(name="Demo Corp", slug="demo-corp", plan="professional", max_users=20, max_warehouses=5)
    db.session.add(org)
    db.session.flush()

    admin = User(
        username="admin",
        email="admin@democorp.com",
        first_name="Admin",
        last_name="User",
        role="owner",
        organization_id=org.id,
    )
    admin.set_password("admin123")
    db.session.add(admin)

    # Categories
    electronics = Category(organization_id=org.id, name="Electronics", slug="electronics", description="Electronic devices and components")
    clothing = Category(organization_id=org.id, name="Clothing", slug="clothing", description="Apparel and fashion items")
    food = Category(organization_id=org.id, name="Food & Beverage", slug="food-beverage", description="Food and drink products")
    office = Category(organization_id=org.id, name="Office Supplies", slug="office-supplies", description="Office and stationery items")
    for c in [electronics, clothing, food, office]:
        db.session.add(c)
    db.session.flush()

    # Warehouses
    wh1 = Warehouse(organization_id=org.id, name="Main Warehouse", code="WH-001", address="123 Main St", city="New York", state="NY", country="US", postal_code="10001")
    wh2 = Warehouse(organization_id=org.id, name="West Coast Hub", code="WH-002", address="456 Pacific Ave", city="Los Angeles", state="CA", country="US", postal_code="90001")
    wh3 = Warehouse(organization_id=org.id, name="Distribution Center", code="WH-003", address="789 Commerce Blvd", city="Chicago", state="IL", country="US", postal_code="60601")
    for w in [wh1, wh2, wh3]:
        db.session.add(w)
    db.session.flush()

    # Products
    products_data = [
        ("MacBook Pro 16\"", "ELEC-001", electronics, wh1, 1999.99, 1500.00, 45, 10, "pcs"),
        ("iPhone 15 Pro", "ELEC-002", electronics, wh1, 1199.99, 800.00, 120, 20, "pcs"),
        ("Samsung Galaxy S24", "ELEC-003", electronics, wh2, 899.99, 600.00, 85, 15, "pcs"),
        ("Sony WH-1000XM5", "ELEC-004", electronics, wh1, 349.99, 200.00, 200, 30, "pcs"),
        ("iPad Air", "ELEC-005", electronics, wh2, 599.99, 400.00, 8, 15, "pcs"),
        ("Nike Air Max", "CLT-001", clothing, wh2, 159.99, 80.00, 300, 50, "pcs"),
        ("Levi's 501 Jeans", "CLT-002", clothing, wh1, 69.99, 35.00, 150, 25, "pcs"),
        ("Columbia Jacket", "CLT-003", clothing, wh3, 129.99, 65.00, 5, 10, "pcs"),
        ("Premium Coffee Beans", "FNB-001", food, wh3, 24.99, 12.00, 500, 100, "kg"),
        ("Organic Green Tea", "FNB-002", food, wh3, 18.99, 8.00, 350, 75, "box"),
        ("Printer Paper A4", "OFC-001", office, wh1, 12.99, 6.00, 1000, 200, "box"),
        ("Ballpoint Pens Pack", "OFC-002", office, wh1, 8.99, 3.50, 3, 50, "box"),
        ("Sticky Notes", "OFC-003", office, wh2, 5.99, 2.50, 800, 150, "box"),
        ("USB-C Cable", "ELEC-006", electronics, wh1, 19.99, 5.00, 0, 40, "pcs"),
        ("Wireless Mouse", "ELEC-007", electronics, wh2, 39.99, 15.00, 7, 20, "pcs"),
    ]

    for name, sku, cat, wh, price, cost, qty, threshold, unit in products_data:
        p = Product(
            organization_id=org.id, name=name, sku=sku,
            category_id=cat.id, warehouse_id=wh.id,
            unit_price=price, cost_price=cost, quantity=qty,
            low_stock_threshold=threshold, unit=unit,
        )
        db.session.add(p)
    db.session.flush()

    # Sample transactions
    all_products = Product.query.filter_by(organization_id=org.id).all()
    tx_types = ["purchase", "sale", "purchase", "adjustment", "return", "sale"]
    for i, product in enumerate(all_products[:8]):
        tx_type = tx_types[i % len(tx_types)]
        qty = 10 + (i * 5)
        if tx_type in ("sale",):
            qty = min(qty, product.quantity) if product.quantity > 0 else 0
            if qty == 0:
                continue
            effective = -qty
        else:
            effective = qty

        tx = InventoryTransaction(
            organization_id=org.id,
            product_id=product.id,
            warehouse_id=product.warehouse_id,
            performed_by_id=admin.id,
            transaction_type=tx_type,
            quantity=effective,
            reference=f"REF-{1000 + i}",
            notes=f"Demo transaction #{i+1}",
            quantity_before=product.quantity,
            quantity_after=product.quantity + effective,
            created_at=datetime.utcnow() - timedelta(days=6 - (i % 7), hours=i),
        )
        db.session.add(tx)

    db.session.commit()
    print("✅ Demo data seeded successfully!")
    print("   Login: admin / admin123")


# =============================================================================
# Main
# =============================================================================


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_demo_data()
    app.run(debug=True, port=5000)
