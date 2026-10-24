
import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient

# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="Big Data Sales Analysis",
    page_icon="📊",
    layout="wide",
)

# --------------------------------------------------
# 2. LOAD MONGODB SETTINGS
# --------------------------------------------------
load_dotenv()

try:
    MONGODB_URI = st.secrets["MONGODB_URI"]
except (KeyError, FileNotFoundError):
    MONGODB_URI = os.getenv("MONGODB_URI")

DATABASE_NAME = os.getenv("MONGODB_DATABASE", "sales_db")
COLLECTION_NAME = os.getenv("MONGODB_COLLECTION", "sales")

# Allow database and collection to be configured in Streamlit Secrets.
try:
    DATABASE_NAME = st.secrets.get("MONGODB_DATABASE", DATABASE_NAME)
    COLLECTION_NAME = st.secrets.get("MONGODB_COLLECTION", COLLECTION_NAME)
except (FileNotFoundError, AttributeError):
    pass

# --------------------------------------------------
# 3. SAMPLE DATA (USED IF DATABASE IS UNAVAILABLE)
# --------------------------------------------------
SAMPLE_DATA = [
    {"Date": "2026-01-05", "Product": "Laptop", "Category": "Electronics", "Quantity": 2, "UnitPrice": 75000},
    {"Date": "2026-01-12", "Product": "Mouse", "Category": "Accessories", "Quantity": 5, "UnitPrice": 800},
    {"Date": "2026-01-20", "Product": "Keyboard", "Category": "Accessories", "Quantity": 3, "UnitPrice": 1500},
    {"Date": "2026-02-03", "Product": "Phone", "Category": "Electronics", "Quantity": 2, "UnitPrice": 45000},
    {"Date": "2026-02-10", "Product": "Monitor", "Category": "Electronics", "Quantity": 2, "UnitPrice": 12000},
    {"Date": "2026-02-18", "Product": "Headphones", "Category": "Accessories", "Quantity": 4, "UnitPrice": 2500},
    {"Date": "2026-03-02", "Product": "Tablet", "Category": "Electronics", "Quantity": 1, "UnitPrice": 30000},
    {"Date": "2026-03-09", "Product": "Webcam", "Category": "Accessories", "Quantity": 3, "UnitPrice": 2200},
    {"Date": "2026-03-17", "Product": "Laptop", "Category": "Electronics", "Quantity": 1, "UnitPrice": 75000},
    {"Date": "2026-04-04", "Product": "Phone", "Category": "Electronics", "Quantity": 1, "UnitPrice": 45000},
    {"Date": "2026-04-11", "Product": "Mouse", "Category": "Accessories", "Quantity": 6, "UnitPrice": 800},
    {"Date": "2026-04-20", "Product": "Monitor", "Category": "Electronics", "Quantity": 1, "UnitPrice": 12000},
]

# --------------------------------------------------
# 4. CONNECT TO MONGODB ATLAS
# --------------------------------------------------
@st.cache_data(ttl=30)
def load_sales(uri, database_name, collection_name):
    client = None

    try:
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
        )

        # Verify the database connection.
        client.admin.command("ping")

        collection = client[database_name][collection_name]
        records = list(collection.find({}, {"_id": 0}))

        return records, None

    except Exception as error:
        return None, str(error)

    finally:
        if client is not None:
            client.close()


# --------------------------------------------------
# 5. CLEAN AND PREPARE DATA
# --------------------------------------------------
def prepare_data(records):
    df = pd.DataFrame(records)

    if df.empty:
        return df

    # Support common variations in column names.
    aliases = {
        "date": "Date",
        "salesdate": "Date",
        "orderdate": "Date",
        "product": "Product",
        "productname": "Product",
        "category": "Category",
        "quantity": "Quantity",
        "qty": "Quantity",
        "unitprice": "UnitPrice",
        "unit_price": "UnitPrice",
        "price": "UnitPrice",
    }

    rename_columns = {}

    for column in df.columns:
        normalized = (
            str(column).strip().replace(" ", "").lower()
        )
        if normalized in aliases:
            rename_columns[column] = aliases[normalized]

    df = df.rename(columns=rename_columns)

    required = [
        "Date",
        "Product",
        "Category",
        "Quantity",
        "UnitPrice",
    ]

    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(
            "Required columns missing from MongoDB: "
            + ", ".join(missing)
        )

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")

    df = df.dropna(subset=required).copy()

    df["Product"] = df["Product"].astype(str)
    df["Category"] = df["Category"].astype(str)

    # Calculate revenue for each record.
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]

    return df


# --------------------------------------------------
# 6. DASHBOARD HEADER
# --------------------------------------------------
st.title("📊 Big Data Sales Analysis and Visualization System")

st.markdown(
    """
    Explore sales performance, revenue trends, product performance,
    and category contributions using interactive visualizations.
    """
)

# --------------------------------------------------
# 7. LOAD DATABASE RECORDS
# --------------------------------------------------
if MONGODB_URI:
    records, connection_error = load_sales(
        MONGODB_URI,
        DATABASE_NAME,
        COLLECTION_NAME,
    )

    if connection_error:
        st.error("Could not connect to MongoDB Atlas.")
        st.caption(
            "Check your Streamlit Secrets, database credentials, "
            "Atlas network access, and database user permissions."
        )
        with st.expander("Technical error details"):
            st.code(connection_error)
        st.stop()

    if not records:
        st.warning(
            f"MongoDB is connected, but "
            f"{DATABASE_NAME}.{COLLECTION_NAME} contains no records."
        )
        st.stop()

    raw_data = records
    source = "MongoDB Atlas"
    st.success("Connected to MongoDB Atlas successfully.")

else:
    st.error(
        "MONGODB_URI was not found. Add it under "
        "Streamlit App settings → Secrets."
    )
    st.stop()

try:
    df = prepare_data(raw_data)
except (ValueError, TypeError) as error:
    st.error(f"Could not prepare sales data: {error}")
    st.stop()

if df.empty:
    st.error("No valid sales records were found.")
    st.stop()

st.caption(
    f"Data source: {source} | Total records loaded: {len(df)}"
)

# --------------------------------------------------
# 8. SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.header("🔎 Sales Filters")

categories = sorted(df["Category"].unique().tolist())

selected_categories = st.sidebar.multiselect(
    "Select categories",
    options=categories,
    default=categories,
)

available_products = sorted(
    df.loc[
        df["Category"].isin(selected_categories),
        "Product",
    ].unique().tolist()
)

selected_products = st.sidebar.multiselect(
    "Select products",
    options=available_products,
    default=available_products,
)

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = date_range[0] if isinstance(date_range, (tuple, list)) else date_range
    end_date = start_date

if start_date > end_date:
    st.sidebar.error("Start date cannot be after end date.")
    st.stop()

filtered_df = df[
    df["Category"].isin(selected_categories)
    & df["Product"].isin(selected_products)
    & (df["Date"].dt.date >= start_date)
    & (df["Date"].dt.date <= end_date)
].copy()

# --------------------------------------------------
# 9. KEY PERFORMANCE INDICATORS
# --------------------------------------------------
st.subheader("📌 Sales Overview")

if filtered_df.empty:
    st.warning("No records match your selected filters.")
    st.stop()

total_revenue = filtered_df["Revenue"].sum()
units_sold = filtered_df["Quantity"].sum()
record_count = len(filtered_df)
average_revenue = total_revenue / record_count if record_count else 0

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Revenue", f"${total_revenue:,.2f}")
col2.metric("Units Sold", f"{units_sold:,.0f}")
col3.metric("Sales Records", f"{record_count:,}")
col4.metric("Average Revenue per Record", f"${average_revenue:,.2f}")

# --------------------------------------------------
# 10. REVENUE TREND
# --------------------------------------------------
st.subheader("📈 Revenue Over Time")

daily_revenue = (
    filtered_df.groupby(filtered_df["Date"].dt.date)["Revenue"]
    .sum()
    .reset_index()
)

daily_revenue.columns = ["Date", "Revenue"]

fig_trend = px.line(
    daily_revenue,
    x="Date",
    y="Revenue",
    markers=True,
    title="Daily Revenue Trend",
    labels={"Revenue": "Revenue ($)", "Date": "Date"},
)

fig_trend.update_layout(hovermode="x unified")
st.plotly_chart(fig_trend, use_container_width=True)

# --------------------------------------------------
# 11. REVENUE BY PRODUCT AND CATEGORY
# --------------------------------------------------
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("🛍️ Revenue by Product")

    product_revenue = (
        filtered_df.groupby("Product", as_index=False)["Revenue"]
        .sum()
        .sort_values("Revenue", ascending=False)
    )

    fig_product = px.bar(
        product_revenue,
        x="Product",
        y="Revenue",
        color="Product",
        title="Product Revenue Comparison",
        labels={"Revenue": "Revenue ($)"},
    )

    st.plotly_chart(fig_product, use_container_width=True)

with right_col:
    st.subheader("🍩 Revenue by Category")

    category_revenue = (
        filtered_df.groupby("Category", as_index=False)["Revenue"]
        .sum()
    )

    fig_category = px.pie(
        category_revenue,
        names="Category",
        values="Revenue",
        hole=0.4,
        title="Category Revenue Distribution",
    )

    st.plotly_chart(fig_category, use_container_width=True)

# --------------------------------------------------
# 12. UNITS SOLD BY CATEGORY
# --------------------------------------------------
st.subheader("📦 Units Sold by Category")

category_quantity = (
    filtered_df.groupby("Category", as_index=False)["Quantity"]
    .sum()
    .sort_values("Quantity", ascending=False)
)

fig_quantity = px.bar(
    category_quantity,
    x="Category",
    y="Quantity",
    color="Category",
    title="Quantity Sold by Category",
    labels={"Quantity": "Units Sold"},
)

st.plotly_chart(fig_quantity, use_container_width=True)

# --------------------------------------------------
# 13. SALES RECORDS TABLE
# --------------------------------------------------
st.subheader("📋 Sales Records")

display_df = filtered_df.copy()
display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")

st.dataframe(
    display_df.sort_values("Date", ascending=False),
    use_container_width=True,
    hide_index=True,
)

# --------------------------------------------------
# 14. DOWNLOAD FILTERED SALES DATA
# --------------------------------------------------
csv_data = display_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Filtered Sales as CSV",
    data=csv_data,
    file_name="sales_analysis.csv",
    mime="text/csv",
)

# --------------------------------------------------
# 15. FOOTER
# --------------------------------------------------
st.divider()

st.caption(
    "Big Data Sales Analysis and Visualization System | "
    "Python · Streamlit · Pandas · Plotly · MongoDB Atlas"
)
