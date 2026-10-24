
import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient

# ==================================================
# 1. PAGE CONFIGURATION
# ==================================================
st.set_page_config(
    page_title="Big Data Sales Analysis",
    page_icon="📊",
    layout="wide",
)

# ==================================================
# 2. LOAD CONFIGURATION
# ==================================================
load_dotenv()


def get_setting(name, default=None):
    """Read a setting from Streamlit Secrets or local .env."""
    try:
        value = st.secrets.get(name)
        if value:
            return value
    except (FileNotFoundError, AttributeError):
        pass

    return os.getenv(name, default)


MONGODB_URI = get_setting("MONGODB_URI")
DATABASE_NAME = get_setting("MONGODB_DATABASE", "sales_db")
COLLECTION_NAME = get_setting("MONGODB_COLLECTION", "sales")

# ==================================================
# 3. MONGODB CONNECTION
# ==================================================
@st.cache_data(ttl=30, show_spinner=False)
def load_sales(uri, database_name, collection_name):
    client = None

    try:
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=15000,
            connectTimeoutMS=15000,
        )

        client.admin.command("ping")

        records = list(
            client[database_name][collection_name].find({}, {"_id": 0})
        )

        return records, None

    except Exception as error:
        return None, str(error)

    finally:
        if client is not None:
            client.close()


# ==================================================
# 4. CLEAN AND PREPARE DATA
# ==================================================
def prepare_data(records):
    df = pd.DataFrame(records)

    if df.empty:
        return df

    # Normalize common column name variations.
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
        "revenue": "Revenue",
        "totalrevenue": "Revenue",
        "sales": "Revenue",
    }

    rename_map = {}

    for column in df.columns:
        normalized = (
            str(column).strip().lower().replace(" ", "").replace("-", "")
        )
        if normalized in aliases:
            rename_map[column] = aliases[normalized]

    df = df.rename(columns=rename_map)

    required = ["Date", "Product", "Category", "Quantity", "UnitPrice"]
    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(
            "Missing required MongoDB columns: " + ", ".join(missing)
        )

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")

    df["Product"] = df["Product"].astype("string").str.strip()
    df["Category"] = df["Category"].astype("string").str.strip()

    df = df.dropna(
        subset=["Date", "Product", "Category", "Quantity", "UnitPrice"]
    ).copy()

    df = df[
        (df["Product"] != "")
        & (df["Category"] != "")
    ].copy()

    # Calculate revenue from quantity and unit price.
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]

    return df


# ==================================================
# 5. DASHBOARD HEADER
# ==================================================
st.title("📊 Big Data Sales Analysis and Visualization System")

st.write(
    "Explore sales performance, revenue trends, product performance, "
    "and category contributions using interactive visualizations."
)

# ==================================================
# 6. CONNECT AND LOAD DATA
# ==================================================
if not MONGODB_URI:
    st.error(
        "MongoDB URI was not found. Add MONGODB_URI in "
        "Streamlit App settings → Secrets."
    )
    st.stop()

with st.spinner("Connecting to MongoDB Atlas and loading sales data..."):
    records, connection_error = load_sales(
        MONGODB_URI,
        DATABASE_NAME,
        COLLECTION_NAME,
    )

if connection_error:
    st.error("Could not connect to MongoDB Atlas.")
    st.caption(
        "Check your connection settings, database user permissions, "
        "Atlas network access, and TLS configuration."
    )

    with st.expander("Technical error details"):
        st.code(connection_error)

    st.stop()

if not records:
    st.warning(
        f"No sales records found in {DATABASE_NAME}.{COLLECTION_NAME}."
    )
    st.stop()

try:
    df = prepare_data(records)
except (ValueError, TypeError) as error:
    st.error(f"Could not prepare sales data: {error}")
    st.stop()

if df.empty:
    st.warning("No valid sales records are available to display.")
    st.stop()

st.success("Connected to MongoDB Atlas successfully.")
st.caption(
    f"Database: {DATABASE_NAME} | Collection: {COLLECTION_NAME} "
    f"| Records loaded: {len(df)}"
)

# ==================================================
# 7. SIDEBAR FILTERS
# ==================================================
st.sidebar.title("🔎 Sales Filters")
st.sidebar.caption("Choose one or more options to update the dashboard.")

# Category filter.
all_categories = sorted(df["Category"].unique().tolist())

selected_categories = st.sidebar.multiselect(
    "Select categories",
    options=all_categories,
    default=all_categories,
    key="category_filter",
    placeholder="Choose categories...",
)

# Use selected categories to determine available products.
if selected_categories:
    category_df = df[
        df["Category"].isin(selected_categories)
    ].copy()
else:
    category_df = df.iloc[0:0].copy()

available_products = sorted(
    category_df["Product"].unique().tolist()
)

# Remove previously selected products that no longer belong
# to the selected categories.
previous_products = st.session_state.get("product_filter", [])
valid_previous_products = [
    product
    for product in previous_products
    if product in available_products
]

# When categories change, include all currently available products.
if (
    set(valid_previous_products) != set(previous_products)
    or "product_filter" not in st.session_state
):
    st.session_state["product_filter"] = available_products

selected_products = st.sidebar.multiselect(
    "Select products",
    options=available_products,
    key="product_filter",
    placeholder="Choose products...",
)

# Date filter.
min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    key="sales_date_range",
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = date_range[0]
    end_date = date_range[0]

# Reset filters button.
if st.sidebar.button("Reset all filters", key="reset_filters"):
    st.session_state["category_filter"] = all_categories
    st.session_state["product_filter"] = sorted(
        category_df["Product"].unique().tolist()
    )
    st.session_state["sales_date_range"] = (min_date, max_date)
    st.rerun()

# ==================================================
# 8. APPLY FILTERS
# ==================================================
filtered_df = df[
    df["Category"].isin(selected_categories)
    & df["Product"].isin(selected_products)
    & (df["Date"].dt.date >= start_date)
    & (df["Date"].dt.date <= end_date)
].copy()

st.sidebar.divider()
st.sidebar.caption(
    f"Showing {len(filtered_df)} of {len(df)} records"
)

if filtered_df.empty:
    st.warning(
        "No sales records match your selected filters. "
        "Choose another category, product, or date range."
    )
    st.stop()

# ==================================================
# 9. KEY PERFORMANCE INDICATORS
# ==================================================
st.subheader("📌 Sales Overview")

total_revenue = filtered_df["Revenue"].sum()
units_sold = filtered_df["Quantity"].sum()
record_count = len(filtered_df)
average_revenue = (
    total_revenue / record_count if record_count else 0
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Revenue", f"${total_revenue:,.2f}")
col2.metric("Units Sold", f"{units_sold:,.0f}")
col3.metric("Sales Records", f"{record_count:,}")
col4.metric("Average Revenue per Record", f"${average_revenue:,.2f}")

# ==================================================
# 10. REVENUE TREND
# ==================================================
st.subheader("📈 Revenue Over Time")

daily_revenue = (
    filtered_df.assign(
        SalesDate=filtered_df["Date"].dt.date
    )
    .groupby("SalesDate", as_index=False)["Revenue"]
    .sum()
)

fig_trend = px.line(
    daily_revenue,
    x="SalesDate",
    y="Revenue",
    markers=True,
    title="Daily Revenue Trend",
    labels={
        "SalesDate": "Date",
        "Revenue": "Revenue ($)",
    },
)

fig_trend.update_layout(hovermode="x unified")
st.plotly_chart(fig_trend, use_container_width=True)

# ==================================================
# 11. PRODUCT AND CATEGORY ANALYSIS
# ==================================================
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

# ==================================================
# 12. UNITS SOLD BY CATEGORY
# ==================================================
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

# ==================================================
# 13. SALES DATA TABLE
# ==================================================
st.subheader("📋 Sales Records")

display_df = filtered_df.copy()
display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")

st.dataframe(
    display_df.sort_values("Date", ascending=False),
    use_container_width=True,
    hide_index=True,
)

# ==================================================
# 14. DOWNLOAD FILTERED DATA
# ==================================================
csv_data = display_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Filtered Sales as CSV",
    data=csv_data,
    file_name="sales_analysis.csv",
    mime="text/csv",
)

# ==================================================
# 15. FOOTER
# ==================================================
st.divider()

st.caption(
    "Big Data Sales Analysis and Visualization System | "
    "Python • Streamlit • Pandas • Plotly • MongoDB Atlas"
)
