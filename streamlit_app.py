import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import random
import os
import plotly.express as px
import plotly.graph_objects as go
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Machine Learning imports
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import joblib

# NLP for recommendations
from sklearn.feature_extraction.text import TfidfVectorizer

# Statistics
from scipy import stats

# Caching for ML models
from functools import lru_cache

# -----------------------------
# App configuration
# -----------------------------
st.set_page_config(page_title="Afibuy", layout="wide")
APP_TITLE = "🌍 Afibuy"
DATA_CSV = "Liberia_Global_Trade_Enhanced.csv"
AFIBUY_DB = "afibuy.db"
PRODUCT_IMAGES_DIR = Path("product_images")
PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

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
    
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'password_hash' not in columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        except sqlite3.OperationalError:
            pass

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


# =============================
# MACHINE LEARNING & AI TOOLS
# =============================

class MLPipeline:
    """Unified ML pipeline for predictions and recommendations"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.scaler = StandardScaler()
        self.price_model = None
        self.demand_model = None
        self.clusters = None
        self.pca = None
        
    def train_price_predictor(self):
        """Train RandomForest to predict selling price based on features"""
        try:
            # Prepare features
            X = self.df[['ImportCostUSD', 'ProfitMargin', 'DemandScore']].fillna(0)
            y = self.df['SellingPriceUSD'].fillna(0)
            
            self.price_model = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42)
            self.price_model.fit(X, y)
            return True
        except Exception as e:
            st.warning(f"Price predictor training failed: {e}")
            return False
    
    def train_demand_predictor(self):
        """Train RandomForest to predict product demand"""
        try:
            X = self.df[['ImportCostUSD', 'ProfitMargin', 'OpportunityScore']].fillna(0)
            y = self.df['DemandScore'].fillna(0)
            
            self.demand_model = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42)
            self.demand_model.fit(X, y)
            return True
        except Exception as e:
            st.warning(f"Demand predictor training failed: {e}")
            return False
    
    def predict_price(self, import_cost: float, profit_margin: float, demand_score: float) -> float:
        """Predict selling price for a new product"""
        if self.price_model is None:
            self.train_price_predictor()
        
        X = np.array([[import_cost, profit_margin, demand_score]])
        return max(0, self.price_model.predict(X)[0])
    
    def predict_demand(self, import_cost: float, profit_margin: float, opportunity_score: float) -> float:
        """Predict demand score"""
        if self.demand_model is None:
            self.train_demand_predictor()
        
        X = np.array([[import_cost, profit_margin, opportunity_score]])
        return max(0, min(100, self.demand_model.predict(X)[0]))
    
    def segment_products(self, n_clusters: int = 5):
        """Cluster products into market segments"""
        try:
            X = self.df[['ImportCostUSD', 'ProfitMargin', 'DemandScore', 'OpportunityScore']].fillna(0)
            X_scaled = self.scaler.fit_transform(X)
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            self.clusters = kmeans.fit_predict(X_scaled)
            
            self.df['Segment'] = self.clusters
            return self.df
        except Exception as e:
            st.warning(f"Segmentation failed: {e}")
            return self.df
    
    def get_product_recommendations(self, product_id: int, n_recommendations: int = 5):
        """Recommend similar products using content-based filtering"""
        try:
            # Create features from product metadata
            features = self.df[['ProfitMargin', 'DemandScore', 'OpportunityScore', 'ProfitUSD']].fillna(0)
            features_scaled = self.scaler.fit_transform(features)
            
            # Calculate similarity
            similarities = cosine_similarity([features_scaled[product_id]], features_scaled)[0]
            
            # Get top recommendations (excluding the product itself)
            top_indices = np.argsort(similarities)[::-1][1:n_recommendations+1]
            return self.df.iloc[top_indices]
        except Exception as e:
            st.warning(f"Recommendation failed: {e}")
            return pd.DataFrame()
    
    def detect_anomalies(self):
        """Detect unusual products (outliers) using statistical methods"""
        df_copy = self.df.copy()
        anomalies = []
        
        for col in ['ProfitMargin', 'DemandScore', 'ProfitUSD']:
            z_scores = np.abs(stats.zscore(df_copy[col].fillna(0)))
            anomaly_mask = z_scores > 3
            anomalies.append(anomaly_mask)
        
        combined_anomaly = np.any(anomalies, axis=0)
        df_copy['IsAnomaly'] = combined_anomaly
        return df_copy[df_copy['IsAnomaly'] == True]
    
    def forecast_trends(self, category: str = None):
        """Simple trend analysis and forecasting"""
        try:
            if category:
                data = self.df[self.df['Category'] == category].copy()
            else:
                data = self.df.copy()
            
            # Sort by profit and calculate trend
            data = data.sort_values('ProfitUSD')
            trend_data = []
            
            for idx, row in data.iterrows():
                trend_data.append({
                    'ProductName': row['ProductName'],
                    'Category': row['Category'],
                    'CurrentProfit': row['ProfitUSD'],
                    'PredictedGrowth': row['OpportunityScore'] * (row['DemandScore'] / 100),
                    'RiskLevel': row['RiskLevel']
                })
            
            return pd.DataFrame(trend_data)
        except Exception as e:
            st.warning(f"Trend forecasting failed: {e}")
            return pd.DataFrame()
    
    def optimize_supplier_mix(self, budget: float):
        """Recommend optimal supplier mix based on profit & risk"""
        try:
            # Score products on efficiency (profit per cost unit)
            df_copy = self.df.copy()
            df_copy['Efficiency'] = df_copy['ProfitUSD'] / (df_copy['ImportCostUSD'] + 1)
            df_copy = df_copy.sort_values('Efficiency', ascending=False)
            
            selected = []
            remaining_budget = budget
            
            for _, row in df_copy.iterrows():
                if remaining_budget >= row['ImportCostUSD']:
                    selected.append(row)
                    remaining_budget -= row['ImportCostUSD']
            
            if selected:
                return pd.DataFrame(selected)[['ProductName', 'Category', 'ImportCostUSD', 'ProfitUSD', 'Efficiency']]
            return pd.DataFrame()
        except Exception as e:
            st.warning(f"Optimization failed: {e}")
            return pd.DataFrame()


def get_ml_pipeline(df: pd.DataFrame) -> MLPipeline:
    """Get or create ML pipeline (with caching)"""
    if 'ml_pipeline' not in st.session_state:
        pipeline = MLPipeline(df)
        pipeline.train_price_predictor()
        pipeline.train_demand_predictor()
        st.session_state.ml_pipeline = pipeline
    return st.session_state.ml_pipeline


# =============================
# DATA GENERATION / CACHING
# =============================

@st.cache_data(show_spinner=False)
def load_or_generate_data(csv_path: str = DATA_CSV, n_records: int = 20000):
    """Load dataset from CSV or generate a representative sample. Uses caching to speed up reloads."""
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            return df
        except Exception:
            pass

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

    supplier_names = [
        "Liberia Trade Hub", "Monrovia Imports", "Global Trade Africa", "West Africa Commerce",
        "Prime Suppliers Ltd", "Atlantic Trading Group", "Ocean Gate Imports", "Liberty Logistics",
        "Freeport Trading", "World Commerce Inc"
    ]

    ports = ["Freeport of Monrovia", "Buchanan Port", "Greenville Port", "Harper Port"]

    df["HSCode"] = [random.randint(100000, 999999) for _ in range(len(df))]
    df["DemandScore"] = [random.randint(50, 100) for _ in range(len(df))]
    df["RiskLevel"] = [
        "Low Risk" if m >= 30 else ("Medium Risk" if m >= 10 else "High Risk")
        for m in df["ProfitMargin"]
    ]
    df["OpportunityScore"] = [
        int((d + min(int(m), 100)) / 2) for d, m in zip(df["DemandScore"], df["ProfitMargin"])
    ]
    df["SupplierName"] = [random.choice(supplier_names) for _ in range(len(df))]
    df["Port"] = [random.choice(ports) for _ in range(len(df))]

    try:
        df.to_csv(csv_path, index=False)
    except Exception:
        pass

    try:
        conn = sqlite3.connect(AFIBUY_DB)
        df.head(5000).to_sql("liberia_trade_data", conn, if_exists="replace", index=False)
        conn.commit()
        conn.close()
    except Exception:
        pass

    return df


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


# =============================
# UI: Authentication
# =============================

ensure_schema()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'email' not in st.session_state:
    st.session_state.email = ""
if 'menu' not in st.session_state:
    st.session_state.menu = "Liberia Trade Overview"


st.title(APP_TITLE)
st.write("Welcome to Afibuy - Liberia Global Trade Intelligence Platform with AI-Powered Recommendations")


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


# =============================
# PAGE IMPLEMENTATIONS
# =============================

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


# =============================
# ML-POWERED PAGES
# =============================

def page_price_predictor(df: pd.DataFrame):
    """Predict product pricing using ML"""
    st.subheader("🤖 AI Price Predictor")
    st.write("Predict optimal selling price based on import cost and market demand")
    
    pipeline = get_ml_pipeline(df)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        import_cost = st.number_input("Import Cost (USD)", min_value=0.0, value=100.0)
    with col2:
        profit_margin = st.number_input("Target Profit Margin (%)", min_value=0.0, max_value=200.0, value=50.0)
    with col3:
        demand_score = st.number_input("Demand Score (0-100)", min_value=0, max_value=100, value=70)
    
    if st.button("Predict Price"):
        predicted_price = pipeline.predict_price(import_cost, profit_margin, demand_score)
        st.success(f"💰 Predicted Selling Price: **${predicted_price:,.2f}**")
        
        # Show analysis
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Expected Profit", f"${predicted_price - import_cost:,.2f}")
        with col_b:
            actual_margin = ((predicted_price - import_cost) / import_cost * 100) if import_cost > 0 else 0
            st.metric("Actual Margin", f"{actual_margin:.2f}%")


def page_product_segmentation(df: pd.DataFrame):
    """View ML-based product segments"""
    st.subheader("📊 Market Segmentation Analysis")
    st.write("Products grouped into market segments using AI clustering")
    
    pipeline = get_ml_pipeline(df)
    n_clusters = st.slider("Number of Segments", 3, 10, 5)
    
    if st.button("Segment Products"):
        segmented_df = pipeline.segment_products(n_clusters=n_clusters)
        
        # Visualize segments
        fig = px.scatter(segmented_df, 
                        x='ImportCostUSD', 
                        y='ProfitUSD',
                        color='Segment',
                        size='OpportunityScore',
                        hover_name='ProductName',
                        title='Product Market Segments')
        st.plotly_chart(fig, use_container_width=True)
        
        # Show segment statistics
        st.subheader("Segment Statistics")
        segment_stats = segmented_df.groupby('Segment').agg({
            'ProductID': 'count',
            'ProfitMargin': 'mean',
            'DemandScore': 'mean',
            'ProfitUSD': 'mean'
        }).round(2)
        segment_stats.columns = ['Product Count', 'Avg Margin %', 'Avg Demand', 'Avg Profit']
        st.dataframe(segment_stats)


def page_recommendations(df: pd.DataFrame):
    """Get ML-powered recommendations"""
    st.subheader("✨ Smart Product Recommendations")
    st.write("Find similar products based on AI analysis")
    
    pipeline = get_ml_pipeline(df)
    
    selected_product = st.selectbox(
        "Select a product",
        options=df['ProductName'].unique(),
        key="rec_product"
    )
    
    if selected_product:
        product_idx = df[df['ProductName'] == selected_product].index[0]
        recommendations = pipeline.get_product_recommendations(product_idx, n_recommendations=5)
        
        if not recommendations.empty:
            st.subheader(f"Products Similar to '{selected_product}':")
            rec_display = recommendations[['ProductName', 'Category', 'SourceCountry', 'ProfitMargin', 'OpportunityScore']]
            st.dataframe(rec_display)
        else:
            st.info("No recommendations found")


def page_trend_forecasting(df: pd.DataFrame):
    """Forecast market trends"""
    st.subheader("📈 Market Trend Forecasting")
    st.write("AI-powered predictions of market movements and growth potential")
    
    pipeline = get_ml_pipeline(df)
    
    col1, col2 = st.columns(2)
    with col1:
        category_filter = st.selectbox("Category", options=["All"] + df['Category'].unique().tolist())
    with col2:
        show_anomalies = st.checkbox("Show Anomalies", value=False)
    
    if category_filter == "All":
        forecast_df = pipeline.forecast_trends()
    else:
        forecast_df = pipeline.forecast_trends(category=category_filter)
    
    if not forecast_df.empty:
        forecast_df = forecast_df.sort_values('PredictedGrowth', ascending=False).head(20)
        st.dataframe(forecast_df)
        
        # Visualize predictions
        fig = px.bar(forecast_df, 
                    x='ProductName', 
                    y='PredictedGrowth',
                    color='RiskLevel',
                    title='Predicted Growth Potential by Product')
        st.plotly_chart(fig, use_container_width=True)
    
    if show_anomalies:
        st.subheader("🚨 Anomalous Products Detected")
        anomalies = pipeline.detect_anomalies()
        if not anomalies.empty:
            st.warning(f"Found {len(anomalies)} unusual products")
            st.dataframe(anomalies[['ProductName', 'Category', 'ProfitMargin', 'DemandScore']].head(10))


def page_budget_optimizer(df: pd.DataFrame):
    """Budget optimization tool"""
    st.subheader("💼 Smart Budget Optimizer")
    st.write("Get AI recommendations for optimal product selection given your budget")
    
    pipeline = get_ml_pipeline(df)
    
    budget = st.number_input("Your Budget (USD)", min_value=100.0, value=10000.0)
    
    if st.button("Optimize Budget"):
        optimized = pipeline.optimize_supplier_mix(budget)
        
        if not optimized.empty:
            st.success(f"✅ Recommended {len(optimized)} products")
            
            total_cost = optimized['ImportCostUSD'].sum()
            total_profit = optimized['ProfitUSD'].sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Products Selected", len(optimized))
            with col2:
                st.metric("Total Cost", f"${total_cost:,.2f}")
            with col3:
                st.metric("Expected Profit", f"${total_profit:,.2f}")
            
            st.subheader("Recommended Products")
            st.dataframe(optimized)
            
            # Visualization
            fig = px.scatter(optimized,
                           x='ImportCostUSD',
                           y='ProfitUSD',
                           size='Efficiency',
                           hover_name='ProductName',
                           color='Category',
                           title='Budget Optimization Results')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No valid products found for optimization")


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


# =============================
# MAIN FLOW
# =============================

df = load_or_generate_data()
exports_df = generate_exports_sample()

if not st.session_state.logged_in:
    show_login()
    st.info("After logging in you'll see the Liberia Trade Overview by default. Use the sidebar to navigate to other pages.")
else:
    st.sidebar.title("Navigation")
    
    # Organize pages by category
    pages_dict = {
        "📊 Trade Analytics": [
            "Liberia Trade Overview",
            "Top Countries Exporting To Liberia",
            "Liberia Port Analytics",
            "High Opportunity Products",
            "Export Intelligence",
        ],
        "🤖 AI & ML Tools": [
            "Price Predictor",
            "Market Segmentation",
            "Product Recommendations",
            "Trend Forecasting",
            "Budget Optimizer",
        ],
        "🛍️ E-Commerce": [
            "Add Product",
            "Products List",
        ],
    }
    
    # Create select menu
    page_category = st.sidebar.radio("Category", pages_dict.keys())
    st.session_state.menu = st.sidebar.selectbox("Choose a section", pages_dict[page_category])

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.email = ""
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.write("Quick search")
    q = st.sidebar.text_input("Product or supplier")

    # Route to pages
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
    elif st.session_state.menu == "Price Predictor":
        page_price_predictor(df)
    elif st.session_state.menu == "Market Segmentation":
        page_product_segmentation(df)
    elif st.session_state.menu == "Product Recommendations":
        page_recommendations(df)
    elif st.session_state.menu == "Trend Forecasting":
        page_trend_forecasting(df)
    elif st.session_state.menu == "Budget Optimizer":
        page_budget_optimizer(df)
    elif st.session_state.menu == "Add Product":
        page_add_product()
    elif st.session_state.menu == "Products List":
        page_products_list()

    st.markdown("---")
    st.caption(f"Logged in as: {st.session_state.email}")
