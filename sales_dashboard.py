
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

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "sales_db")
COLLECTION_NAME = os.getenv("MONGODB_COLLECTION", "sales")


# --------------------------------------------------
# 2. SAMPLE SALES DATA
# --------------------------------------------------
SAMPLE_DATA = [
    {"Date": "2026-01-05", "Product": "Laptop", "Category": "Electronics", "Quantity": 2, "UnitPrice": 2500},
    {"Date": "2026-01-12", "Product": "Phone", "Category": "Electronics", "Quantity": 5, "UnitPrice": 800},
    {"Date": "2026-01-20", "Product": "Desk", "Category": "Furniture", "Quantity": 3, "UnitPrice": 300},
    {"Date": "2026-02-03", "Product": "Chair", "Category": "Furniture", "Quantity": 6, "UnitPrice": 150},
    {"Date": "2026-02-11", "Product": "Headphones", "Category": "Electronics", "Quantity": 8, "UnitPrice": 100},
    {"Date": "2026-02-19", "Product": "Notebook", "Category": "Stationery", "Quantity": 10, "UnitPrice": 20},
    {"Date": "2026-03-02", "Product": "Monitor", "Category": "Electronics", "Quantity": 4, "UnitPrice": 400},
    {"Date": "2026-03-10", "Product": "Bookshelf", "Category": "Furniture", "Quantity": 2, "UnitPrice": 500},
    {"Date": "2026-03-18", "Product": "Pen Set", "Category": "Stationery", "Quantity": 12, "UnitPrice": 15},
    {"Date": "2026-04-04", "Product": "Keyboard", "Category": "Electronics", "Quantity": 5, "UnitPrice": 80},
    {"Date": "2026-04-13", "Product": "Table", "Category": "Furniture", "Quantity": 2, "UnitPrice": 600},
    {"Date": "2026-04-22", "Product": "Printer Paper", "Category": "Stationery", "Quantity": 9, "UnitPrice": 25},
]


# --------------------------------------------------
# 3. MONGODB CONNECTION AND DATA LOADING
# --------------------------------------------------
@st.cache_data(ttl=30)
def load_mongodb_sales(uri, database_name, collection_name):
    """Return sales documents and a connection error, if any."""
    client = None

    try:
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=7000,
            connectTimeoutMS=7000,
        )

        # Test the connection.
        client.admin.command("ping")

        collection = client[database_name][collection_name]
        documents = list(collection.find({}, {"_id": 0}))

        return documents, None

    except Exception as exc:
        # Return the error so it can be displayed for troubleshooting.
        return None, str(exc)

    finally:
        if client is not None:
            client.close()


# --------------------------------------------------
# 4. DATA CLEANING AND PREPARATION
# --------------------------------------------------
def prepare_data(documents):
    df = pd.DataFrame(documents)

    if df.empty:
        return df

    # Recognize common variations in column names.
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
        normalized = str(column).strip().replace(" ", "").lower()

        if normalized in aliases:
            rename_columns[column] = aliases[normalized]

    df = df.rename(columns=rename_columns)

    required_columns = [
        "Date",
        "Product",
        "Category",
        "Quantity",
        "UnitPrice",
    ]

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")

    df = df.dropna(subset=required_columns).copy()

    df["Product"] = df["Product"].astype(str)
    df["Category"] = df["Category"].astype(str)
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]

    return df


# --------------------------------------------------
# 5. DASHBOARD HEADER
# --------------------------------------------------
st.title("📊 Big Data Sales Analysis and Visualization System")

st.markdown(
    "Analyze sales performance, revenue trends, product performance, "
    "and category contributions through interactive visualizations."
)


# --------------------------------------------------
# 6. LOAD MONGODB DATA OR USE SAMPLE DATA
# --------------------------------------------------
source = "Sample data"
connection_error = None

if not MONGODB_URI:
    raw_data = SAMPLE_DATA

    st.warning(
        "MongoDB URI was not found. Check that your .env file "
        "is in the project folder and contains MONGODB_URI."
    )

else:
    documents, connection_error = load_mongodb_sales(
        MONGODB_URI,
        DATABASE_NAME,
        COLLECTION_NAME,
    )

    if connection_error:
        raw_data = SAMPLE_DATA

        st.warning(
            "MongoDB connection failed. Showing sample data instead."
        )

        # Display the connection error, not the URI or password.
        st.markdown("**MongoDB diagnostic details:**")
        st.code(connection_error)

    elif documents:
        raw_data = documents
        source = "MongoDB Atlas"

        st.success("Successfully loaded sales records from MongoDB Atlas.")

    else:
        raw_data = SAMPLE_DATA

        st.info(
            f"Connected to MongoDB, but the collection "
            f"'{DATABASE_NAME}.{COLLECTION_NAME}' is empty. "
            "Showing sample data instead."
        )

try:
    df = prepare_data(raw_data)

except (ValueError, TypeError) as exc:
    st.error(f"Could not prepare sales data: {exc}")
    st.stop()

if df.empty:
    st.error("No valid sales records are available.")
    st.stop()

st.caption(f"Data source: {source} | Records loaded: {len(df)}")


# --------------------------------------------------
# 7. SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.header("🔎 Sales Filters")

all_categories = sorted(df["Category"].unique().tolist())

selected_categories = st.sidebar.multiselect(
    "Select categories",
    options=all_categories,
    default=all_categories,
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
# 8. KEY PERFORMANCE INDICATORS
# --------------------------------------------------
st.subheader("📌 Sales Overview")

total_revenue = filtered_df["Revenue"].sum()
units_sold = filtered_df["Quantity"].sum()
sales_records = len(filtered_df)

average_revenue = (
    total_revenue / sales_records if sales_records else 0
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Revenue", f"${total_revenue:,.2f}")
col2.metric("Units Sold", f"{units_sold:,.0f}")
col3.metric("Sales Records", f"{sales_records:,}")
col4.metric("Average Revenue per Record", f"${average_revenue:,.2f}")


# --------------------------------------------------
# 9. HANDLE EMPTY FILTER RESULTS
# --------------------------------------------------
if filtered_df.empty:
    st.warning("No sales records match the selected filters.")
    st.stop()


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
    title="Revenue Trend",
    labels={
        "Revenue": "Revenue ($)",
        "Date": "Date",
    },
)

fig_trend.update_layout(hovermode="x unified")

st.plotly_chart(fig_trend, width="stretch")


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

    st.plotly_chart(fig_product, width="stretch")

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

    st.plotly_chart(fig_category, width="stretch")


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

st.plotly_chart(fig_quantity, width="stretch")


# --------------------------------------------------
# 13. SALES RECORDS TABLE
# --------------------------------------------------
st.subheader("📋 Sales Records")

display_df = filtered_df.copy()
display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")

st.dataframe(
    display_df.sort_values("Date", ascending=False),
    width="stretch",
    hide_index=True,
)


# --------------------------------------------------
# 14. DOWNLOAD FILTERED DATA
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


