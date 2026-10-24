
import os
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

# Load MongoDB connection settings from .env
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "sales_db")
COLLECTION_NAME = os.getenv("MONGODB_COLLECTION", "sales")

# Sample sales records
sales_data = [
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

if not MONGODB_URI:
    raise SystemExit(
        "MONGODB_URI was not found. Check that your .env file is "
        "in the same folder as seed_mongodb.py."
    )

client = None

try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=15000)
    client.admin.command("ping")

    collection = client[DATABASE_NAME][COLLECTION_NAME]

    if collection.count_documents({}) > 0:
        print(
            f"The collection {DATABASE_NAME}.{COLLECTION_NAME} already "
            "contains data. No records were inserted, to avoid duplicates."
        )
    else:
        collection.insert_many(sales_data)
        print(f"Successfully inserted {len(sales_data)} sales records.")
        print(f"Database: {DATABASE_NAME}")
        print(f"Collection: {COLLECTION_NAME}")

except Exception as error:
    print("Could not insert sales data.")
    print("Check your MongoDB URI and Atlas network access settings.")
    print(f"Error: {error}")

finally:
    if client is not None:
        client.close()
