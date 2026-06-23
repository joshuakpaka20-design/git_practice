import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import random
import os
import plotly.express as px

# Page config
st.set_page_config(page_title="Afibuy", layout="wide")

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'email' not in st.session_state:
    st.session_state.email = ""
if 'menu' not in st.session_state:
    st.session_state.menu = "Liberia Trade Overview"

st.title("🌍Afibuy🇱🇷")
st.write("Welcome to Afibuy - Liberia Global Trade Intelligence Platform")

# --- Data generation / loading (kept from original file) ---
# To keep things simple this example will generate the dataset if it does not exist
CSV_ENHANCED = "Liberia_Global_Trade_100K_Enhanced.csv"
DB_FILE = "afibuy_database.db"

# helper to generate sample dataset (only runs if csv not found)
def generate_datasets():
    source_countries = [
        "China","India","United States","Germany","Turkey",
        "Brazil","Vietnam","Netherlands","Belgium","Morocco",
        "Nigeria","Ghana","Senegal"
    ]

    destination_country = "Liberia"

    categories = {
        "Agriculture":["Rice","Palm Oil","Cassava","Cocoa","Coffee"],
        "Electronics":["Smartphone","Laptop","Tablet","Router","Printer"],
        "Construction":["Cement","Steel Rod","Roofing Sheet","Tiles","Paint"],
        "Automobile":["Car Battery","Brake Pad","Engine Oil","Tire","Spark Plug"],
        "Pharmaceutical":["Paracetamol","Antibiotics","Vitamin C","Malaria Kit","Syringe"]
    }

    rows = []
    for i in range(100000):
        category = random.choice(list(categories.keys()))
        product = random.choice(categories[category])
        import_cost = round(random.uniform(5,5000),2)
        selling_price = round(import_cost * random.uniform(1.15,2.50),2)
        profit = round(selling_price - import_cost,2)
        margin = round((profit/import_cost)*100,2)
        rows.append([i+1, product, category, random.choice(source_countries), destination_country, import_cost, selling_price, profit, margin])

    df = pd.DataFrame(rows, columns=["ProductID","ProductName","Category","SourceCountry","DestinationCountry","ImportCostUSD","SellingPriceUSD","ProfitUSD","ProfitMargin"])

    # enhance
    supplier_names = [
        "Liberia Trade Hub","Monrovia Imports","Global Trade Africa","West Africa Commerce",
        "Prime Suppliers Ltd","Atlantic Trading Group","Ocean Gate Imports","Liberty Logistics",
        "Freeport Trading","World Commerce Inc"
    ]

    ports = ["Freeport of Monrovia","Buchanan Port","Greenville Port","Harper Port"]

    df["HSCode"] = [random.randint(100000,999999) for _ in range(len(df))]
    df["DemandScore"] = [random.randint(50,100) for _ in range(len(df))]
    df["RiskLevel"] = ["Low Risk" if m>=50 else ("Medium Risk" if m>=25 else "High Risk") for m in df["ProfitMargin"]]
    df["OpportunityScore"] = [ (d + min(int(m),100))//2 for d,m in zip(df["DemandScore"], df["ProfitMargin"]) ]
    df["SupplierName"] = [random.choice(supplier_names) for _ in range(len(df))]
    df["Port"] = [random.choice(ports) for _ in range(len(df))]

    df.to_csv(CSV_ENHANCED, index=False)

    # save to sqlite
    conn = sqlite3.connect(DB_FILE)
    df.to_sql("liberia_trade_data", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

    return df

# Load or create dataset
if os.path.exists(CSV_ENHANCED):
    df = pd.read_csv(CSV_ENHANCED)
else:
    with st.spinner("Generating dataset (this may take a moment)..."):
        df = generate_datasets()

# load exports if present or generate small sample
if 'exports_df' not in globals():
    liberia_exports = ["Rubber","Iron Ore","Gold","Diamonds","Palm Oil","Cocoa","Coffee","Timber","Cassava","Fish"]
    export_rows = []
    for i in range(50000):
        product = random.choice(liberia_exports)
        destination = random.choice(["China","United States","Germany","Belgium","India","Morocco","Turkey"])
        export_value = round(random.uniform(1000,100000),2)
        export_rows.append([i+1, product, "Liberia", destination, export_value])
    exports_df = pd.DataFrame(export_rows, columns=["ExportID","Product","Origin","Destination","ExportValueUSD"]) 

# ensure product_images folder exists
if not os.path.exists("product_images"):
    os.makedirs("product_images")

# --- UI: Login flow and navigation ---

def show_login():
    st.subheader("Please log in to continue")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            # NOTE: This is a simple placeholder. Replace with real auth in production.
            if email:
                st.session_state.logged_in = True
                st.session_state.email = email
                st.session_state.menu = "Liberia Trade Overview"
                st.experimental_rerun()
            else:
                st.error("Please enter an email to login (this example uses a simple placeholder auth).")
    with col2:
        if st.button("Continue as Guest"):
            st.session_state.logged_in = True
            st.session_state.email = "guest"
            st.session_state.menu = "Liberia Trade Overview"
            st.experimental_rerun()

# Page implementations

def page_overview():
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

    # Top countries
    st.markdown("---")
    st.subheader("🌍 Top Countries Exporting To Liberia")
    country_df = df.groupby("SourceCountry").size().reset_index(name="Products")
    fig = px.bar(country_df, x="SourceCountry", y="Products", title="Imports Into Liberia")
    st.plotly_chart(fig, use_container_width=True)

    # Ports
    st.markdown("---")
    st.subheader("🚢 Liberia Port Analytics")
    port_df = df.groupby("Port").size().reset_index(name="Volume")
    fig2 = px.pie(port_df, names="Port", values="Volume", title="Trade Volume By Port")
    st.plotly_chart(fig2, use_container_width=True)

    # Currency converter
    st.markdown("---")
    st.subheader("💱 Currency Converter")
    usd = st.number_input("USD", value=100.0)
    lrd_rate = 198
    mad_rate = 9.2
    st.metric("Liberian Dollars", f"{usd*lrd_rate:,.2f}")
    st.metric("Moroccan Dirham", f"{usd*mad_rate:,.2f}")


def page_top_countries():
    st.subheader("🌍 Top Countries Exporting To Liberia")
    country_df = df.groupby("SourceCountry").size().reset_index(name="Products")
    fig = px.bar(country_df, x="SourceCountry", y="Products", title="Imports Into Liberia")
    st.plotly_chart(fig, use_container_width=True)


def page_port_analytics():
    st.subheader("🚢 Liberia Port Analytics")
    port_df = df.groupby("Port").size().reset_index(name="Volume")
    fig = px.pie(port_df, names="Port", values="Volume", title="Trade Volume By Port")
    st.plotly_chart(fig, use_container_width=True)


def page_opportunities():
    st.subheader("🔥 High Opportunity Products")
    min_score = st.slider("Minimum Opportunity Score", 0, 100, 70)
    opportunities = df[df["OpportunityScore"] >= min_score]
    st.dataframe(opportunities[["ProductName","SourceCountry","ProfitUSD","OpportunityScore","SupplierName"]].head(100))


def page_export_intel():
    st.header("🇱🇷 Liberia Export Intelligence")
    export_summary = exports_df.groupby("Product")["ExportValueUSD"].sum().reset_index()
    fig = px.bar(export_summary, x="Product", y="ExportValueUSD", title="Top Liberian Exports")
    st.plotly_chart(fig, use_container_width=True)


def page_add_product():
    st.subheader("Add Product")
    product_name = st.text_input("Product Name")
    category = st.selectbox("Category", ["Agriculture","Fashion","Electronics","Beauty","Books","Home","Automobile"])
    price = st.number_input("Price", min_value=0.0)
    description = st.text_area("Description")
    image = st.file_uploader("Upload Product Image", type=["jpg","jpeg","png"]) 
    if st.button("Add Product"):
        image_path = ""
        if image:
            image_path = os.path.join("product_images", image.name)
            with open(image_path, "wb") as f:
                f.write(image.getbuffer())
        # simple DB insert
        conn = sqlite3.connect("afibuy.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products(seller_email,product_name,category,price,description,image) VALUES(?,?,?,?,?)
        """, (st.session_state.email, product_name, category, price, description, image_path))
        conn.commit()
        conn.close()
        st.success("Product Added Successfully")


def page_products_list():
    st.subheader("Products")
    conn = sqlite3.connect("afibuy.db")
    try:
        products = pd.read_sql("SELECT * FROM products", conn)
        st.dataframe(products)
    except Exception:
        st.info("No products table found in afibuy.db")
    conn.close()

# --- Main flow ---

if not st.session_state.logged_in:
    # show login page only
    show_login()
    st.info("After logging in you'll see the Liberia Trade Overview by default. Use the sidebar to navigate to other pages.")
else:
    # show navigation in sidebar and current selected page
    st.sidebar.title("Navigation")
    pages = [
        "Liberia Trade Overview",
        "Top Countries Exporting To Liberia",
        "Liberia Port Analytics",
        "High Opportunity Products",
        "Export Intelligence",
        "Add Product",
        "Products List"
    ]

    # keep menu selection in session state so we can default to overview after login
    st.session_state.menu = st.sidebar.selectbox("Choose a section", pages, index=pages.index(st.session_state.menu) if st.session_state.menu in pages else 0)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.email = ""
        st.experimental_rerun()

    # route to pages
    if st.session_state.menu == "Liberia Trade Overview":
        page_overview()
    elif st.session_state.menu == "Top Countries Exporting To Liberia":
        page_top_countries()
    elif st.session_state.menu == "Liberia Port Analytics":
        page_port_analytics()
    elif st.session_state.menu == "High Opportunity Products":
        page_opportunities()
    elif st.session_state.menu == "Export Intelligence":
        page_export_intel()
    elif st.session_state.menu == "Add Product":
        page_add_product()
    elif st.session_state.menu == "Products List":
        page_products_list()

    # small footer
    st.markdown("---")
    st.caption(f"Logged in as: {st.session_state.email}")

# ensure afibuy.db schema exists (safe to run)

def ensure_schema():
    conn = sqlite3.connect("afibuy.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_email TEXT,
        product_name TEXT,
        category TEXT,
        price REAL,
        description TEXT,
        image TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_email TEXT,
        product_id INTEGER,
        quantity INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_email TEXT,
        total REAL,
        status TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        price REAL
    )
    """)
    conn.commit()
    conn.close()

ensure_schema()
