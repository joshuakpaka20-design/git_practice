import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import random
import os
import plotly.express as px
import hashlib
from pathlib import Path

# -----------------------------
# App configuration
# -----------------------------
st.set_page_config(page_title="Afibuy", layout="wide")
APP_TITLE = "🌍 Afibuy"
DATA_CSV = "Liberia_Global_Trade_Enhanced.csv"
AFIBUY_DB = "afibuy.db"
PRODUCT_IMAGES_DIR = Path("product_images")
PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Helpers: DB, auth, utilities
# -----------------------------

def get_db_connection(db_path: str = AFIBUY_DB):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema():
    """Create DB schema for users, products, cart, orders, etc."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            role TEXT DEFAULT 'buyer'
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_email TEXT,
            product_name TEXT,
            category TEXT,
            price REAL,
            description TEXT,
            image TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cart(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_email TEXT,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_email TEXT,
            total REAL,
            status TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price REAL
        )
        """
    )

    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


# -----------------------------
# Data generation / caching
# -----------------------------

@st.cache_data(show_spinner=False)
def load_or_generate_data(csv_path: str = DATA_CSV, n_records: int = 20000):
    """Load dataset from CSV or generate a representative sample. Uses caching to speed up reloads."""
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            return df
        except Exception:
            # fallback to regenerate if CSV corrupted
            pass

    # generate smaller but realistic dataset
    source_countries = [
        "China", "India", "United States", "Germany", "Turkey",
        "Brazil", "Vietnam", "Netherlands", "Belgium", "Morocco",
        "Nigeria", "Ghana", "Senegal"
    ]

    destination_country = "Liberia"

    categories = {
        "Agriculture": ["Rice", "Palm Oil", "Cassava", "Cocoa", "Coffee"],
        "Electronics": ["Smartphone", "Laptop", "Tablet", "Router", "Printer"],
        "Construction": ["Cement", "Steel Rod", "Roofing Sheet", "Tiles", "Paint"],
        "Automobile": ["Car Battery", "Brake Pad", "Engine Oil", "Tire", "Spark Plug"],
        "Pharmaceutical": ["Paracetamol", "Antibiotics", "Vitamin C", "Malaria Kit", "Syringe"]
    }

    rows = []
    for i in range(n_records):
        category = random.choice(list(categories.keys()))
        product = random.choice(categories[category])
        import_cost = round(random.uniform(5, 5000), 2)
        selling_price = round(import_cost * random.uniform(1.15, 2.50), 2)
        profit = round(selling_price - import_cost, 2)
        margin = round((profit / import_cost) * 100, 2) if import_cost > 0 else 0.0
        rows.append([
            i + 1,
            product,
            category,
            random.choice(source_countries),
            destination_country,
            import_cost,
            selling_price,
            profit,
            margin,
        ])

    df = pd.DataFrame(rows, columns=[
        "ProductID", "ProductName", "Category", "SourceCountry", "DestinationCountry",
        "ImportCostUSD", "SellingPriceUSD", "ProfitUSD", "ProfitMargin"
    ])

    # enhance
    supplier_names = [
        "Liberia Trade Hub", "Monrovia Imports", "Global Trade Africa", "West Africa Commerce",
        "Prime Suppliers Ltd", "Atlantic Trading Group", "Ocean Gate Imports", "Liberty Logistics",
        "Freeport Trading", "World Commerce Inc"
    ]

    ports = ["Freeport of Monrovia", "Buchanan Port", "Greenville Port", "Harper Port"]

    df["HSCode"] = [random.randint(100000, 999999) for _ in range(len(df))]
    df["DemandScore"] = [random.randint(50, 100) for _ in range(len(df))]
    # RiskLevel based on ProfitMargin (more realistic mapping)
    df["RiskLevel"] = [
        "Low Risk" if m >= 30 else ("Medium Risk" if m >= 10 else "High Risk")
        for m in df["ProfitMargin"]
    ]
    df["OpportunityScore"] = [
        int((d + min(int(m), 100)) / 2) for d, m in zip(df["DemandScore"], df["ProfitMargin"])
    ]
    df["SupplierName"] = [random.choice(supplier_names) for _ in range(len(df))]
    df["Port"] = [random.choice(ports) for _ in range(len(df))]

    # persist a CSV so subsequent runs are faster
    try:
        df.to_csv(csv_path, index=False)
    except Exception:
        pass

    # also store a light table into sqlite for product browsing
    try:
        conn = sqlite3.connect(AFIBUY_DB)
        df.head(5000).to_sql("liberia_trade_data", conn, if_exists="replace", index=False)
        conn.commit()
        conn.close()
    except Exception:
        pass

    return df


# load exports sample (cached implicitly by load_or_generate_data)
@st.cache_data(show_spinner=False)
def generate_exports_sample(n_records: int = 5000):
    liberia_exports = ["Rubber", "Iron Ore", "Gold", "Diamonds", "Palm Oil", "Cocoa", "Coffee", "Timber", "Cassava", "Fish"]
    export_rows = []
    for i in range(n_records):
        product = random.choice(liberia_exports)
        destination = random.choice(["China", "United States", "Germany", "Belgium", "India", "Morocco", "Turkey"])
        export_value = round(random.uniform(1000, 100000), 2)
        export_rows.append([i + 1, product, "Liberia", destination, export_value])
    return pd.DataFrame(export_rows, columns=["ExportID", "Product", "Origin", "Destination", "ExportValueUSD"]) 


# -----------------------------
# UI: Authentication
# -----------------------------

ensure_schema()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'email' not in st.session_state:
    st.session_state.email = ""
if 'menu' not in st.session_state:
    st.session_state.menu = "Liberia Trade Overview"


st.title(APP_TITLE)
st.write("Welcome to Afibuy - Liberia Global Trade Intelligence Platform")


def register_user(fullname: str, email: str, password: str) -> tuple[bool, str]:
    if not email or not password:
        return False, "Email and password are required"
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users(fullname, email, password_hash) VALUES (?, ?, ?)",
                       (fullname, email, hash_password(password)))
        conn.commit()
        conn.close()
        return True, "Registered successfully"
    except sqlite3.IntegrityError:
        return False, "A user with this email already exists"
    except Exception as e:
        return False, f"Registration failed: {e}"


def login_user(email: str, password: str) -> tuple[bool, str]:
    if not email or not password:
        return False, "Email and password are required"
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        if row and verify_password(password, row[0]):
            return True, "Logged in"
        else:
            return False, "Invalid email or password"
    except Exception as e:
        return False, f"Login error: {e}"


def show_login():
    st.subheader("Please log in to continue")
    cols = st.columns([1, 1, 1])
    with cols[0]:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            if submit:
                ok, msg = login_user(email.strip().lower(), password)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.email = email.strip().lower()
                    st.success("Logged in")
                else:
                    st.error(msg)

    with cols[1]:
        with st.form("register_form"):
            st.write("Create an account")
            fullname = st.text_input("Full name")
            reg_email = st.text_input("Email (for registration)")
            reg_password = st.text_input("Password", type="password")
            register = st.form_submit_button("Register")
            if register:
                ok, msg = register_user(fullname.strip(), reg_email.strip().lower(), reg_password)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    with cols[2]:
        if st.button("Continue as Guest"):
            st.session_state.logged_in = True
            st.session_state.email = "guest"
            st.success("Continuing as guest")


# -----------------------------
# Page implementations
# -----------------------------

def page_overview(df: pd.DataFrame):
    st.subheader("🇱🇷 Liberia Trade Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Products", f"{len(df):,}")
    with col2:
        st.metric("Total Profit", f"${df['ProfitUSD'].sum():,.0f}")
    with col3:
        st.metric("Average Margin", f"{df['ProfitMargin'].mean():.2f}%")
    with col4:
        st.metric("Suppliers", df['SupplierName'].nunique())

    st.markdown("---")
    # Top countries
    st.subheader("🌍 Top Countries Exporting To Liberia")
    country_df = df.groupby("SourceCountry")["ProductID"].count().reset_index(name="Products")
    fig = px.bar(country_df.sort_values("Products", ascending=False).head(20), x="SourceCountry", y="Products", title="Imports Into Liberia")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("🚢 Liberia Port Analytics")
    port_df = df.groupby("Port").size().reset_index(name="Volume")
    fig2 = px.pie(port_df, names="Port", values="Volume", title="Trade Volume By Port")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("💱 Currency Converter")
    usd = st.number_input("USD", value=100.0)
    lrd_rate = st.number_input("LRD per USD", value=198.0)
    mad_rate = st.number_input("MAD per USD", value=9.2)
    st.metric("Liberian Dollars", f"{usd * lrd_rate:,.2f}")
    st.metric("Moroccan Dirham", f"{usd * mad_rate:,.2f}")


def page_top_countries(df: pd.DataFrame):
    st.subheader("🌍 Top Countries Exporting To Liberia")
    country_df = df.groupby("SourceCountry")["ProductID"].count().reset_index(name="Products")
    fig = px.bar(country_df.sort_values("Products", ascending=False), x="SourceCountry", y="Products", title="Imports Into Liberia")
    st.plotly_chart(fig, use_container_width=True)


def page_port_analytics(df: pd.DataFrame):
    st.subheader("🚢 Liberia Port Analytics")
    port_df = df.groupby("Port")["ProductID"].count().reset_index(name="Volume")
    fig = px.pie(port_df, names="Port", values="Volume", title="Trade Volume By Port")
    st.plotly_chart(fig, use_container_width=True)


def page_opportunities(df: pd.DataFrame):
    st.subheader("🔥 High Opportunity Products")
    min_score = st.slider("Minimum Opportunity Score", 0, 100, 70)
    opportunities = df[df["OpportunityScore"] >= min_score].sort_values("OpportunityScore", ascending=False)
    st.dataframe(opportunities[["ProductName", "SourceCountry", "ProfitUSD", "OpportunityScore", "SupplierName"]].head(200))


def page_export_intel(exports_df: pd.DataFrame):
    st.header("🇱🇷 Liberia Export Intelligence")
    export_summary = exports_df.groupby("Product")["ExportValueUSD"].sum().reset_index()
    fig = px.bar(export_summary.sort_values("ExportValueUSD", ascending=False).head(20), x="Product", y="ExportValueUSD", title="Top Liberian Exports")
    st.plotly_chart(fig, use_container_width=True)


def page_add_product():
    st.subheader("Add Product")
    with st.form("add_product_form"):
        product_name = st.text_input("Product Name")
        category = st.selectbox("Category", ["Agriculture", "Fashion", "Electronics", "Beauty", "Books", "Home", "Automobile"])
        price = st.number_input("Price", min_value=0.0)
        description = st.text_area("Description")
        image = st.file_uploader("Upload Product Image", type=["jpg", "jpeg", "png"]) 
        submitted = st.form_submit_button("Add Product")

        if submitted:
            image_path = None
            if image is not None:
                image_path = str(PRODUCT_IMAGES_DIR / image.name)
                try:
                    with open(image_path, "wb") as f:
                        f.write(image.getbuffer())
                except Exception as e:
                    st.warning(f"Could not save image: {e}")
                    image_path = None

            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO products(seller_email, product_name, category, price, description, image) VALUES(?,?,?,?,?,?)",
                    (st.session_state.email, product_name, category, price, description, image_path),
                )
                conn.commit()
                conn.close()
                st.success("Product added successfully")
            except sqlite3.OperationalError as e:
                st.warning("Database error, attempting recovery and retry")
                ensure_schema()
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO products(seller_email, product_name, category, price, description, image) VALUES(?,?,?,?,?,?)",
                        (st.session_state.email, product_name, category, price, description, image_path),
                    )
                    conn.commit()
                    conn.close()
                    st.success("Product added successfully (after recovery)")
                except Exception as e2:
                    st.error("Failed to add product after recovery")
                    st.exception(e2)
            except Exception as e:
                st.error("Unexpected error while adding product")
                st.exception(e)


def page_products_list():
    st.subheader("Products")
    conn = get_db_connection()
    try:
        products = pd.read_sql("SELECT * FROM products", conn)
        if products.empty:
            st.info("No products available yet. Add a product from the sidebar.")
            return

        # simple filters
        cols = st.columns([3, 1])
        with cols[0]:
            search = st.text_input("Search product name or supplier")
        with cols[1]:
            category_filter = st.selectbox("Category", options=["All"] + sorted(products['category'].dropna().unique().tolist()))

        filtered = products.copy()
        if category_filter and category_filter != "All":
            filtered = filtered[filtered['category'] == category_filter]
        if search:
            q = search.lower()
            filtered = filtered[filtered['product_name'].str.lower().str.contains(q) | filtered['seller_email'].str.lower().str.contains(q)]

        st.dataframe(filtered)

        # show a gallery (first 6)
        st.markdown("---")
        st.write("Product gallery")
        for _, row in filtered.head(6).iterrows():
            cols = st.columns([1, 3])
            with cols[0]:
                if row.get('image') and os.path.exists(row['image']):
                    st.image(row['image'], use_column_width=True)
                else:
                    st.write("(no image)")
            with cols[1]:
                st.markdown(f"**{row['product_name']}**")
                st.write(row.get('description', ''))
                st.write(f"Price: ${row['price']}")
    except Exception as e:
        st.info("No products table found or error while loading products")
        st.exception(e)
    finally:
        conn.close()


# -----------------------------
# Main flow: load data and route pages
# -----------------------------

df = load_or_generate_data()
exports_df = generate_exports_sample()

if not st.session_state.logged_in:
    show_login()
    st.info("After logging in you'll see the Liberia Trade Overview by default. Use the sidebar to navigate to other pages.")
else:
    # sidebar navigation and actions
    st.sidebar.title("Navigation")
    pages = [
        "Liberia Trade Overview",
        "Top Countries Exporting To Liberia",
        "Liberia Port Analytics",
        "High Opportunity Products",
        "Export Intelligence",
        "Add Product",
        "Products List",
    ]

    st.session_state.menu = st.sidebar.selectbox("Choose a section", pages, index=pages.index(st.session_state.menu) if st.session_state.menu in pages else 0)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.email = ""
        st.experimental_rerun()

    # quick product search box in sidebar
    st.sidebar.markdown("---")
    st.sidebar.write("Quick search")
    q = st.sidebar.text_input("Product or supplier")

    # route to pages
    if st.session_state.menu == "Liberia Trade Overview":
        page_overview(df)
    elif st.session_state.menu == "Top Countries Exporting To Liberia":
        page_top_countries(df)
    elif st.session_state.menu == "Liberia Port Analytics":
        page_port_analytics(df)
    elif st.session_state.menu == "High Opportunity Products":
        page_opportunities(df)
    elif st.session_state.menu == "Export Intelligence":
        page_export_intel(exports_df)
    elif st.session_state.menu == "Add Product":
        page_add_product()
    elif st.session_state.menu == "Products List":
        page_products_list()

    st.markdown("---")
    st.caption(f"Logged in as: {st.session_state.email}")
