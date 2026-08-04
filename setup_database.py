"""
Sets up a sample e-commerce SQLite database with realistic business data.
Tables: customers, products, categories, orders, order_items, reviews.
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "business.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    category_id   INTEGER PRIMARY KEY,
    category_name TEXT NOT NULL,
    department    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category_id  INTEGER NOT NULL REFERENCES categories(category_id),
    unit_price   REAL NOT NULL,
    stock_qty    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id   INTEGER PRIMARY KEY,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    city          TEXT NOT NULL,
    state         TEXT NOT NULL,
    signup_date   DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id     INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date   DATE NOT NULL,
    status       TEXT NOT NULL CHECK(status IN ('pending','shipped','delivered','cancelled')),
    total_amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id     INTEGER PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(order_id),
    product_id  INTEGER NOT NULL REFERENCES products(product_id),
    quantity    INTEGER NOT NULL,
    unit_price  REAL NOT NULL,
    line_total  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id   INTEGER PRIMARY KEY,
    product_id  INTEGER NOT NULL REFERENCES products(product_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    rating      INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    review_date DATE NOT NULL
);
"""

# ── Seed data ──────────────────────────────────────────────────────

CATEGORIES = [
    ("Electronics", "Tech"),
    ("Computers", "Tech"),
    ("Clothing", "Apparel"),
    ("Footwear", "Apparel"),
    ("Books", "Media"),
    ("Music & Movies", "Media"),
    ("Home & Kitchen", "Home"),
    ("Furniture", "Home"),
    ("Sports", "Outdoors"),
    ("Camping", "Outdoors"),
    ("Toys", "Kids"),
    ("Baby Care", "Kids"),
    ("Beauty", "Lifestyle"),
    ("Health", "Lifestyle"),
    ("Grocery", "Food"),
]

# Each category gets a richer catalog of named products
PRODUCT_TEMPLATES = {
    "Electronics": [
        ("Wireless Headphones", 79.99), ("USB-C Hub", 34.99),
        ("Bluetooth Speaker", 49.99), ("Webcam HD", 59.99),
        ("Mechanical Keyboard", 109.99), ("Portable Charger", 29.99),
        ("Noise Cancelling Earbuds", 129.99), ("4K Action Camera", 199.99),
        ("Smart Watch Basic", 149.99), ("Wireless Mouse", 24.99),
        ("USB Microphone", 69.99), ("HDMI Cable 6ft", 12.99),
        ("Tablet Stand", 22.99), ("Phone Case Clear", 15.99),
        ("LED Desk Lamp", 32.99),
    ],
    "Computers": [
        ("14-inch Laptop", 899.99), ("Gaming Laptop", 1299.99),
        ("Ultrabook 13-inch", 1099.99), ("Desktop Mini PC", 549.99),
        ("27-inch Monitor", 279.99), ("Ultrawide Monitor", 449.99),
        ("External SSD 1TB", 109.99), ("USB Flash Drive 128GB", 18.99),
        ("Laptop Sleeve", 27.99), ("Docking Station", 159.99),
        ("Wireless Router", 89.99), ("Webcam Pro", 99.99),
    ],
    "Clothing": [
        ("Cotton T-Shirt", 19.99), ("Denim Jeans", 49.99),
        ("Winter Jacket", 129.99), ("Baseball Cap", 14.99),
        ("Wool Socks 3-Pack", 12.99), ("Hoodie Classic", 44.99),
        ("Dress Shirt", 39.99), ("Chino Pants", 42.99),
        ("Rain Coat", 79.99), ("Athletic Shorts", 24.99),
        ("Fleece Pullover", 54.99), ("Scarves Set", 21.99),
        ("Belt Leather", 29.99), ("Gloves Touchscreen", 16.99),
    ],
    "Footwear": [
        ("Running Shoes", 89.99), ("Trail Hikers", 119.99),
        ("Casual Sneakers", 64.99), ("Dress Shoes", 99.99),
        ("Sandals", 34.99), ("Winter Boots", 139.99),
        ("Slip-On Loafers", 59.99), ("Kids Sneakers", 39.99),
        ("Soccer Cleats", 74.99), ("House Slippers", 19.99),
    ],
    "Books": [
        ("Python Crash Course", 29.99), ("Data Science Handbook", 39.99),
        ("SQL Cookbook", 34.99), ("Clean Code", 37.99),
        ("Designing Data-Intensive Apps", 44.99), ("The Pragmatic Programmer", 41.99),
        ("System Design Interview", 35.99), ("Deep Learning Basics", 49.99),
        ("Product Management 101", 27.99), ("Startup Playbook", 24.99),
        ("Fiction Bestseller", 16.99), ("Mystery Novel", 14.99),
        ("Cookbook Weeknight", 22.99), ("Travel Guide USA", 19.99),
    ],
    "Music & Movies": [
        ("Vinyl Classic Rock", 24.99), ("Headphones Audiophile", 179.99),
        ("Bluetooth Turntable", 149.99), ("Movie Blu-ray Bundle", 39.99),
        ("Streaming Gift Card", 25.00), ("Karaoke Mic Set", 54.99),
        ("Guitar Beginner", 129.99), ("Piano Stand", 49.99),
        ("Concert Tee", 28.99), ("Soundtrack CD", 12.99),
    ],
    "Home & Kitchen": [
        ("Stainless Steel Pan", 39.99), ("Coffee Maker", 64.99),
        ("Knife Set", 54.99), ("Cutting Board", 19.99),
        ("Blender", 44.99), ("Air Fryer", 89.99),
        ("Toaster Oven", 59.99), ("Electric Kettle", 34.99),
        ("Food Storage Set", 24.99), ("Dish Towel Pack", 14.99),
        ("Vacuum Cleaner", 149.99), ("Robot Vacuum", 249.99),
        ("Bedding Sheet Set", 69.99), ("Pillow Memory Foam", 39.99),
    ],
    "Furniture": [
        ("Office Chair", 189.99), ("Standing Desk", 299.99),
        ("Bookshelf 5-Tier", 119.99), ("Nightstand", 89.99),
        ("Dining Table Set", 499.99), ("Sofa Loveseat", 699.99),
        ("Floor Lamp", 74.99), ("TV Stand", 159.99),
        ("Storage Ottoman", 79.99), ("Wall Shelf Pair", 44.99),
    ],
    "Sports": [
        ("Yoga Mat", 24.99), ("Dumbbells 10lb Pair", 34.99),
        ("Resistance Bands", 14.99), ("Jump Rope", 9.99),
        ("Water Bottle", 12.99), ("Foam Roller", 22.99),
        ("Basketball", 29.99), ("Tennis Racket", 79.99),
        ("Cycling Helmet", 54.99), ("Fitness Tracker Band", 49.99),
        ("Pull-up Bar", 39.99), ("Medicine Ball", 27.99),
    ],
    "Camping": [
        ("2-Person Tent", 129.99), ("Sleeping Bag", 69.99),
        ("Camping Stove", 49.99), ("Headlamp", 24.99),
        ("Hiking Backpack 40L", 89.99), ("Cooler 30qt", 59.99),
        ("Camp Chair", 34.99), ("Portable Grill", 79.99),
        ("Trekking Poles", 44.99), ("First Aid Kit", 19.99),
    ],
    "Toys": [
        ("Building Blocks Set", 29.99), ("Board Game Classic", 24.99),
        ("RC Car", 39.99), ("Puzzle 1000pc", 17.99),
        ("STEM Robot Kit", 59.99), ("Plush Bear", 14.99),
        ("Art Supplies Box", 22.99), ("Drone Mini", 79.99),
        ("Card Game Family", 12.99), ("Action Figure", 18.99),
        ("Lego-Style City Set", 49.99), ("Scooter Kids", 69.99),
    ],
    "Baby Care": [
        ("Diaper Pack Size 3", 32.99), ("Baby Wipes Case", 14.99),
        ("Bottle Set", 24.99), ("Baby Monitor", 99.99),
        ("Stroller Compact", 179.99), ("Car Seat", 149.99),
        ("Pacifier 2-Pack", 8.99), ("Baby Lotion", 11.99),
        ("Crib Sheet", 19.99), ("Teething Toy", 9.99),
    ],
    "Beauty": [
        ("Face Moisturizer", 24.99), ("Sunscreen SPF 50", 16.99),
        ("Shampoo & Conditioner", 18.99), ("Hair Dryer", 49.99),
        ("Electric Toothbrush", 69.99), ("Makeup Brush Set", 29.99),
        ("Lip Balm Pack", 9.99), ("Perfume Sample Set", 34.99),
        ("Nail Care Kit", 14.99), ("Face Mask Pack", 19.99),
    ],
    "Health": [
        ("Vitamin C Gummies", 14.99), ("Multivitamin 90ct", 19.99),
        ("Digital Thermometer", 12.99), ("Blood Pressure Monitor", 44.99),
        ("Resistance Therapy Band", 15.99), ("Massage Gun Mini", 79.99),
        ("Sleep Mask", 11.99), ("Protein Powder 2lb", 39.99),
        ("First Aid Refill", 16.99), ("Hand Sanitizer Pack", 9.99),
    ],
    "Grocery": [
        ("Organic Coffee Beans", 16.99), ("Olive Oil Extra Virgin", 12.99),
        ("Granola Family Pack", 8.99), ("Dark Chocolate Bar", 4.99),
        ("Sparkling Water 12pk", 7.99), ("Pasta Assorted", 5.99),
        ("Trail Mix Bulk", 11.99), ("Green Tea Box", 6.99),
        ("Honey Jar", 9.99), ("Protein Bars 12ct", 18.99),
        ("Rice 5lb Bag", 7.49), ("Almond Butter", 10.99),
    ],
}

FIRST_NAMES = [
    "Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Hank",
    "Ivy", "Jack", "Karen", "Leo", "Mia", "Nick", "Olivia", "Paul",
    "Quinn", "Rachel", "Sam", "Tina", "Uma", "Vince", "Wendy", "Xander",
    "Yara", "Zane", "Ava", "Ben", "Chloe", "Derek", "Elena", "Felix",
    "Gina", "Hugo", "Iris", "Jonah", "Kate", "Liam", "Nora", "Owen",
    "Priya", "Rita", "Sean", "Tara", "Uri", "Vera", "Will", "Zoe",
]
LAST_NAMES = [
    "Smith", "Johnson", "Lee", "Brown", "Davis", "Wilson", "Moore",
    "Taylor", "Anderson", "Thomas", "Martin", "Garcia", "Clark", "Hall",
    "Allen", "Young", "King", "Wright", "Scott", "Green", "Baker",
    "Adams", "Nelson", "Hill", "Ramirez", "Campbell", "Mitchell", "Roberts",
    "Carter", "Phillips", "Evans", "Turner", "Torres", "Parker", "Collins",
]
CITIES_STATES = [
    ("New York", "NY"), ("Los Angeles", "CA"), ("Chicago", "IL"),
    ("Houston", "TX"), ("Phoenix", "AZ"), ("Seattle", "WA"),
    ("Denver", "CO"), ("Boston", "MA"), ("Atlanta", "GA"),
    ("Miami", "FL"), ("Portland", "OR"), ("Austin", "TX"),
    ("San Francisco", "CA"), ("San Diego", "CA"), ("Dallas", "TX"),
    ("Philadelphia", "PA"), ("Detroit", "MI"), ("Minneapolis", "MN"),
    ("Nashville", "TN"), ("Charlotte", "NC"), ("Las Vegas", "NV"),
    ("Salt Lake City", "UT"), ("Columbus", "OH"), ("Indianapolis", "IN"),
]

# Target volumes — large enough for interesting analytics
NUM_CUSTOMERS = 500
NUM_ORDERS = 2500
NUM_REVIEWS = 1800


def _random_date(start: datetime, end: datetime) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).strftime("%Y-%m-%d")


def build_database(db_path: str = DB_PATH, seed: int = 42) -> str:
    """Create and populate the database. Returns the path to the .db file."""
    random.seed(seed)

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)

    # Categories
    for i, (name, dept) in enumerate(CATEGORIES, start=1):
        cur.execute("INSERT INTO categories VALUES (?,?,?)", (i, name, dept))

    # Products — every template entry becomes a row
    pid = 1
    cat_map = {name: i for i, (name, _) in enumerate(CATEGORIES, start=1)}
    for cat_name, products in PRODUCT_TEMPLATES.items():
        for pname, price in products:
            stock = random.randint(5, 800)
            cur.execute(
                "INSERT INTO products VALUES (?,?,?,?,?)",
                (pid, pname, cat_map[cat_name], price, stock),
            )
            pid += 1

    total_products = pid - 1

    # Customers
    emails_seen = set()
    for cid in range(1, NUM_CUSTOMERS + 1):
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        email = f"{fn.lower()}.{ln.lower()}{cid}@example.com"
        while email in emails_seen:
            email = f"{fn.lower()}{random.randint(1, 9999)}.{cid}@example.com"
        emails_seen.add(email)
        city, state = random.choice(CITIES_STATES)
        signup = _random_date(datetime(2022, 1, 1), datetime(2025, 12, 31))
        cur.execute(
            "INSERT INTO customers VALUES (?,?,?,?,?,?,?)",
            (cid, fn, ln, email, city, state, signup),
        )

    # Orders & order_items
    statuses = ["pending", "shipped", "delivered", "delivered", "delivered", "cancelled"]
    # Cache prices to avoid per-item SELECT
    cur.execute("SELECT product_id, unit_price FROM products")
    price_by_pid = dict(cur.fetchall())

    oid = 1
    iid = 1
    order_rows = []
    item_rows = []
    for _ in range(NUM_ORDERS):
        cust = random.randint(1, NUM_CUSTOMERS)
        odate = _random_date(datetime(2023, 1, 1), datetime(2025, 12, 31))
        status = random.choice(statuses)
        n_items = random.randint(1, 6)
        chosen = random.sample(range(1, total_products + 1), k=min(n_items, total_products))
        line_total_sum = 0.0
        for prod in chosen:
            qty = random.randint(1, 5)
            price = price_by_pid[prod]
            line = round(price * qty, 2)
            item_rows.append((iid, oid, prod, qty, price, line))
            line_total_sum += line
            iid += 1
        order_rows.append((oid, cust, odate, status, round(line_total_sum, 2)))
        oid += 1

    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", order_rows)
    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?,?,?)", item_rows)

    # Reviews — unique-ish (customer, product) pairs, positive skew
    review_pairs = set()
    review_rows = []
    rid = 1
    attempts = 0
    while rid <= NUM_REVIEWS and attempts < NUM_REVIEWS * 4:
        attempts += 1
        prod = random.randint(1, total_products)
        cust = random.randint(1, NUM_CUSTOMERS)
        if (cust, prod) in review_pairs:
            continue
        review_pairs.add((cust, prod))
        rating = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 20, 35, 30])[0]
        rdate = _random_date(datetime(2023, 3, 1), datetime(2025, 12, 31))
        review_rows.append((rid, prod, cust, rating, rdate))
        rid += 1

    cur.executemany("INSERT INTO reviews VALUES (?,?,?,?,?)", review_rows)

    conn.commit()
    conn.close()

    n_orders = len(order_rows)
    n_items = len(item_rows)
    n_reviews = len(review_rows)
    print(f"Database created at {db_path}")
    print(f"  {len(CATEGORIES)} categories, {total_products} products, {NUM_CUSTOMERS} customers")
    print(f"  {n_orders} orders, {n_items} order items, {n_reviews} reviews")
    return db_path


if __name__ == "__main__":
    build_database()
