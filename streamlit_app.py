import streamlit as st

st.set_page_config(page_title="Afibuy", layout="wide")
st.title("🌍Afibuy🇱🇷")
st.write("Welcome to Afibuy - Liberia Global Trade Intelligence Platform")
# Afibuy Liberia Global Trade Intelligence Platform

import pandas as pd
import numpy as np
import sqlite3
import random

### CREATE COUNTRIES LIST
source_countries = [
    "China",
    "India",
    "United States",
    "Germany",
    "Turkey",
    "Brazil",
    "Vietnam",
    "Netherlands",
    "Belgium",
    "Morocco",
    "Nigeria",
    "Ghana",
    "Senegal"
]

destination_country = "Liberia"

### PRODUCTS CATEGORIES
categories = {
    "Agriculture":[
        "Rice",
        "Palm Oil",
        "Cassava",
        "Cocoa",
        "Coffee"
    ],

    "Electronics":[
        "Smartphone",
        "Laptop",
        "Tablet",
        "Router",
        "Printer"
    ],

    "Construction":[
        "Cement",
        "Steel Rod",
        "Roofing Sheet",
        "Tiles",
        "Paint"
    ],

    "Automobile":[
        "Car Battery",
        "Brake Pad",
        "Engine Oil",
        "Tire",
        "Spark Plug"
    ],

    "Pharmaceutical":[
        "Paracetamol",
        "Antibiotics",
        "Vitamin C",
        "Malaria Kit",
        "Syringe"
    ]
}

### GENERATE 100000 PRODUCTS
rows = []

for i in range(100000):

    category = random.choice(
        list(categories.keys())
    )

    product = random.choice(
        categories[category]
    )

    import_cost = round(
        random.uniform(5,5000),
        2
    )

    selling_price = round(
        import_cost *
        random.uniform(1.15,2.50),
        2
    )

    profit = round(
        selling_price - import_cost,
        2
    )

    margin = round(
        (profit/import_cost)*100,
        2
    )

    rows.append([
        i+1,
        product,
        category,
        random.choice(source_countries),
        destination_country,
        import_cost,
        selling_price,
        profit,
        margin
    ])

### CREATE DATAFRAME
df = pd.DataFrame(
    rows,
    columns=[
        "ProductID",
        "ProductName",
        "Category",
        "SourceCountry",
        "DestinationCountry",
        "ImportCostUSD",
        "SellingPriceUSD",
        "ProfitUSD",
        "ProfitMargin"
    ]
)

df.head()

### SAVE DATASETS
df.to_csv(
    "Liberia_Global_Trade_100K.csv",
    index=False
)

print(
    "100,000 product dataset created successfully."
)

### VERIFY DATASETS
print(df.shape)

### ADD DEMAND SCORE, RISK LEVEL, OPPORTUNITY SCORE, HS CODES & SUPPLIERS
import random

supplier_names = [
    "Liberia Trade Hub",
    "Monrovia Imports",
    "Global Trade Africa",
    "West Africa Commerce",
    "Prime Suppliers Ltd",
    "Atlantic Trading Group",
    "Ocean Gate Imports",
    "Liberty Logistics",
    "Freeport Trading",
    "World Commerce Inc"
]

ports = [
    "Freeport of Monrovia",
    "Buchanan Port",
    "Greenville Port",
    "Harper Port"
]

hs_codes = []

demand_scores = []

risk_levels = []

opportunity_scores = []

suppliers = []

port_list = []

for _, row in df.iterrows():

    hs_codes.append(
        random.randint(100000,999999)
    )

    demand = random.randint(50,100)

    demand_scores.append(demand)

    if row["ProfitMargin"] >= 50:
        risk = "Low Risk"

    elif row["ProfitMargin"] >= 25:
        risk = "Medium Risk"

    else:
        risk = "High Risk"

    risk_levels.append(risk)

    score = (
        demand +
        min(int(row["ProfitMargin"]),100)
    ) // 2

    opportunity_scores.append(score)

    suppliers.append(
        random.choice(supplier_names)
    )

    port_list.append(
        random.choice(ports)
    )

df["HSCode"] = hs_codes

df["DemandScore"] = demand_scores

df["RiskLevel"] = risk_levels

df["OpportunityScore"] = opportunity_scores

df["SupplierName"] = suppliers

df["Port"] = port_list

df.head()

print(df.columns.tolist())

### SAVE AND ENHANCED
df.to_csv(
    "Liberia_Global_Trade_100K_Enhanced.csv",
    index=False
)

print("Enhanced dataset saved.")

### LOAD INTO SQLITE
import sqlite3

conn = sqlite3.connect(
    "afibuy_database.db"
)

df.to_sql(
    "liberia_trade_data",
    conn,
    if_exists="replace",
    index=False
)

conn.commit()

print(
    "100,000 records loaded into SQLite."
)

query = """
SELECT COUNT(*)
FROM liberia_trade_data
"""

import pandas as pd

pd.read_sql(
    query,
    conn
)

### DATABOARD INTEGRATION
top_products = (
    df.groupby("ProductName")
      ["ProfitUSD"]
      .sum()
      .sort_values(
          ascending=False
      )
      .head(20)
)

top_products

df = pd.read_csv(
    "Liberia_Global_Trade_100K_Enhanced.csv"
)

### REPLACE
# ==================================================
# LOAD LIBERIA TRADE DATABASE
# ==================================================

import sqlite3

conn = sqlite3.connect(
    "afibuy_database.db"
)

query = """
SELECT *
FROM liberia_trade_data
"""

df = pd.read_sql(
    query,
    conn
)

print(df.shape)

import streamlit as st

### LIBERIA KPI DASHBOARD
st.subheader("🇱🇷 Liberia Trade Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Products",
        f"{len(df):,}"
    )

with col2:
    st.metric(
        "Total Profit",
        f"${df['ProfitUSD'].sum():,.0f}"
    )

with col3:
    st.metric(
        "Average Margin",
        f"{df['ProfitMargin'].mean():.2f}%"
    )

with col4:
    st.metric(
        "Suppliers",
        df['SupplierName'].nunique()
    )

import plotly.express as px

### TOP IMPORT COUNTRIES CHARTS
st.subheader(
    "🌍 Top Countries Exporting To Liberia"
)

country_df = (
    df.groupby("SourceCountry")
      .size()
      .reset_index(name="Products")
)

fig = px.bar(
    country_df,
    x="SourceCountry",
    y="Products",
    title="Imports Into Liberia"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

### PORT ANALYTICS
st.subheader(
    "🚢 Liberia Port Analytics"
)

port_df = (
    df.groupby("Port")
      .size()
      .reset_index(name="Volume")
)

fig = px.pie(
    port_df,
    names="Port",
    values="Volume",
    title="Trade Volume By Port"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

min_score = st.sidebar.slider(
    "Minimum Opportunity Score",
    0,
    100,
    70
)

opportunities = df[
    df["OpportunityScore"] >= min_score
]

st.subheader(
    "🔥 High Opportunity Products"
)

st.dataframe(
    opportunities[
        [
            "ProductName",
            "SourceCountry",
            "ProfitUSD",
            "OpportunityScore",
            "SupplierName"
        ]
    ].head(100)
)

### LIBERIA TRADE INTELIGENCE
liberia_exports = [
    "Rubber",
    "Iron Ore",
    "Gold",
    "Diamonds",
    "Palm Oil",
    "Cocoa",
    "Coffee",
    "Timber",
    "Cassava",
    "Fish"
]

export_rows = []

for i in range(50000):

    product = random.choice(
        liberia_exports
    )

    destination = random.choice([
        "China",
        "United States",
        "Germany",
        "Belgium",
        "India",
        "Morocco",
        "Turkey"
    ])

    export_value = round(
        random.uniform(1000,100000),
        2
    )

    export_rows.append([
        i + 1,
        product,
        "Liberia",
        destination,
        export_value
    ])

exports_df = pd.DataFrame(
    export_rows,
    columns=[
        "ExportID",
        "Product",
        "Origin",
        "Destination",
        "ExportValueUSD"
    ]
)

exports_df.head()

exports_df.to_sql(
    "liberia_exports",
    conn,
    if_exists="replace",
    index=False
)

conn.commit()

print(
    "Liberia exports loaded."
)

### TOP LIBERIAN EXPORTS
top_exports = (
    exports_df.groupby("Product")
      ["ExportValueUSD"]
      .sum()
      .sort_values(
          ascending=False
      )
)

top_exports

import streamlit as st
import plotly.express as px

# Streamlit page configuration (optional, but good practice for full apps)
st.set_page_config(layout="wide", page_title="Liberia Global Trade Dashboard")

# Sidebar for navigation
st.sidebar.title("Navigation")
menu = st.sidebar.selectbox(
    "Choose a section",
    [
        "Liberia Trade Overview",
        "Top Countries Exporting To Liberia",
        "Liberia Port Analytics",
        "High Opportunity Products",
        "Export Intelligence"
    ]
)

# Content based on menu selection
if menu == "Liberia Trade Overview":
    ### LIBERIA KPI DASHBOARD
    st.subheader("🇱🇷 Liberia Trade Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Products",
            f"{len(df):,}"
        )

    with col2:
        st.metric(
            "Total Profit",
            f"${df['ProfitUSD'].sum():,.0f}"
        )

    with col3:
        st.metric(
            "Average Margin",
            f"{df['ProfitMargin'].mean():.2f}%"
        )

    with col4:
        st.metric(
            "Suppliers",
            df['SupplierName'].nunique()
        )

elif menu == "Top Countries Exporting To Liberia":
    ### TOP IMPORT COUNTRIES CHARTS
    st.subheader(
        "🌍 Top Countries Exporting To Liberia"
    )

    country_df = (
        df.groupby("SourceCountry")
          .size()
          .reset_index(name="Products")
    )

    fig = px.bar(
        country_df,
        x="SourceCountry",
        y="Products",
        title="Imports Into Liberia"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

elif menu == "Liberia Port Analytics":
    ### PORT ANALYTICS
    st.subheader(
        "🚢 Liberia Port Analytics"
    )

    port_df = (
        df.groupby("Port")
          .size()
          .reset_index(name="Volume")
    )

    fig = px.pie(
        port_df,
        names="Port",
        values="Volume",
        title="Trade Volume By Port"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

elif menu == "High Opportunity Products":
    # Note: st.sidebar.slider in the original cell will render in the sidebar
    # alongside the navigation selectbox.
    min_score = st.sidebar.slider(
        "Minimum Opportunity Score",
        0,
        100,
        70
    )

    opportunities = df[
        df["OpportunityScore"] >= min_score
    ]

    st.subheader(
        "🔥 High Opportunity Products"
    )

    st.dataframe(
        opportunities[
            [
                "ProductName",
                "SourceCountry",
                "ProfitUSD",
                "OpportunityScore",
                "SupplierName"
            ]
        ].head(100)
    )

elif menu == "Export Intelligence":
    st.header(
        "🇱🇷 Liberia Export Intelligence"
    )

    export_summary = (
        exports_df.groupby("Product")
          ["ExportValueUSD"]
          .sum()
          .reset_index()
    )

    fig = px.bar(
        export_summary,
        x="Product",
        y="ExportValueUSD",
        title="Top Liberian Exports"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

st.subheader(
    "💱 Currency Converter"
)

usd = st.number_input(
    "USD",
    value=100.0
)

lrd_rate = 198
mad_rate = 9.2

st.metric(
    "Liberian Dollars",
    f"{usd*lrd_rate:,.2f}"
)

st.metric(
    "Moroccan Dirham",
    f"{usd*mad_rate:,.2f}"
)

### NEW DATABASE SCHEMA
import sqlite3

def create_database():

    conn = sqlite3.connect("afibuy.db")
    cursor = conn.cursor()

    # Users

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # Products

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

    conn.commit()
    conn.close()

create_database()

# Migrate Existing Trade Data to afibuy.db
import sqlite3

# Connect to the new database
conn_new_db = sqlite3.connect('afibuy.db')

# Save the main trade data (df) into a new table 'trade_data' in afibuy.db
df.to_sql(
    "trade_data",
    conn_new_db,
    if_exists="replace",
    index=False
)

# Save the exports data (exports_df) into a new table 'exports_data' in afibuy.db
exports_df.to_sql(
    "exports_data",
    conn_new_db,
    if_exists="replace",
    index=False
)

conn_new_db.commit()
conn_new_db.close()

print("Trade data and exports data successfully migrated to 'afibuy.db'.")

import os

if not os.path.exists("product_images"):
    os.makedirs("product_images")

print("Folder Created")

### PRODUCT PAGE
import os

st.title("Add Product")

product_name = st.text_input("Product Name")

category = st.selectbox(
    "Category",
    [
        "Agriculture",
        "Fashion",
        "Electronics",
        "Beauty",
        "Books",
        "Home",
        "Automobile"
    ]
)

price = st.number_input("Price", min_value=0.0)

description = st.text_area("Description")

image = st.file_uploader(
    "Upload Product Image",
    type=["jpg","jpeg","png"]
)

if st.button("Add Product"):

    image_path = ""

    if image:

        image_path = os.path.join(
            "product_images",
            image.name
        )

        with open(image_path, "wb") as f:
            f.write(image.getbuffer())

    cursor.execute(
        """
        INSERT INTO products(
        seller_email,
        product_name,
        category,
        price,
        description,
        image
        )
        VALUES(?,?,?,?,?,?)
        """,
        (
            st.session_state.email,
            product_name,
            category,
            price,
            description,
            image_path
        )
    )

    conn.commit()

    st.success("Product Added Successfully")

import sqlite3

conn = sqlite3.connect("afibuy.db")
cursor = conn.cursor()

sample_products = [

("seller1@gmail.com","Coffee Beans","Agriculture",25,"Premium Liberian coffee",""),

("seller2@gmail.com","African Fabric","Fashion",50,"Traditional fabric",""),

("seller3@gmail.com","Laptop","Electronics",700,"Dell laptop",""),

("seller4@gmail.com","Organic Honey","Agriculture",15,"Pure honey","")

]

cursor.executemany(
"""
INSERT INTO products(
seller_email,
product_name,
category,
price,
description,
image
)
VALUES(?,?,?,?,?,?)
""",
sample_products
)

conn.commit()
conn.close()

import sqlite3

# Re-establish connection to afibuy.db
conn = sqlite3.connect("afibuy.db")
cursor = conn.cursor()

# Cart Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS cart(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_email TEXT,
    product_id INTEGER,
    quantity INTEGER
)
""")

# Orders Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_email TEXT,
    total REAL,
    status TEXT
)
""")

# Order Items
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

import sqlite3

def create_and_populate_database():
    conn = sqlite3.connect("afibuy.db")
    cursor = conn.cursor()

    # Drop tables if they exist to ensure a fresh start
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS products")
    cursor.execute("DROP TABLE IF EXISTS cart")
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("DROP TABLE IF EXISTS order_items")
    cursor.execute("DROP TABLE IF EXISTS trade_data")
    cursor.execute("DROP TABLE IF EXISTS exports_data")

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # Products Table
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

    # Cart Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_email TEXT,
        product_id INTEGER,
        quantity INTEGER
    )
    """)

    # Orders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_email TEXT,
        total REAL,
        status TEXT
    )
    """)

    # Order Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        price REAL
    )
    """)

    # Migrate existing trade data (df) into 'trade_data' table
    # Assuming 'df' and 'exports_df' DataFrames are already in memory from previous steps.
    # If not, you might need to load them first.
    if 'df' in globals():
        df.to_sql(
            "trade_data",
            conn,
            if_exists="replace",
            index=False
        )
    else:
        print("Warning: 'df' DataFrame not found. Trade data not migrated.")

    # Migrate existing exports data (exports_df) into 'exports_data' table
    if 'exports_df' in globals():
        exports_df.to_sql(
            "exports_data",
            conn,
            if_exists="replace",
            index=False
        )
    else:
        print("Warning: 'exports_df' DataFrame not found. Exports data not migrated.")

    # Add sample products
    sample_products = [
        ("seller1@gmail.com","Coffee Beans","Agriculture",25,"Premium Liberian coffee",""),
        ("seller2@gmail.com","African Fabric","Fashion",50,"Traditional fabric",""),
        ("seller3@gmail.com","Laptop","Electronics",700,"Dell laptop",""),
        ("seller4@gmail.com","Organic Honey","Agriculture",15,"Pure honey","")
    ]

    cursor.executemany(
    """
    INSERT INTO products(
    seller_email,
    product_name,
    category,
    price,
    description,
    image
    )
    VALUES(?,?,?,?,?,?)
    """,
    sample_products
    )

    conn.commit()
    conn.close()
    print("Database 'afibuy.db' recreated, schema applied, and data populated successfully.")

create_and_populate_database()
