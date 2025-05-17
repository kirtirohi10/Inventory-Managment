import streamlit as st
import mysql.connector
import pandas as pd
from datetime import date

# 1. Set page config FIRST thing!
st.set_page_config(page_title="Inventory Manager", page_icon="📦")

# Highlight low stock
def highlight_low_stock(val):
    if isinstance(val, (int, float)):
        return 'color: red; font-weight: bold' if val < 5 else ''
    return ''

# DB Connection with hardcoded credentials
def get_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="SHIVOM@270206",
            database="inventorydb"
        )
    except mysql.connector.Error as err:
        st.error("❌ Could not connect to the database.")
        st.code(str(err))
        return None


# Load table data
def load_data(table):
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")
    data = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()

    if 'ImageURL' in columns:
        columns.remove('ImageURL')
        data = [row[:-1] for row in data]

    return pd.DataFrame(data, columns=columns)

# Add product
def add_product(name, cat_id, sup_id, price, qty):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW COLUMNS FROM Products LIKE 'ImageURL'")
    has_image_col = cursor.fetchone() is not None

    if has_image_col:
        cursor.execute(
            "INSERT INTO Products (ProductName, CategoryID, SupplierID, Price, Quantity, ImageURL) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, cat_id, sup_id, price, qty, None)
        )
    else:
        cursor.execute(
            "INSERT INTO Products (ProductName, CategoryID, SupplierID, Price, Quantity) VALUES (%s, %s, %s, %s, %s)",
            (name, cat_id, sup_id, price, qty)
        )

    conn.commit()
    conn.close()

# Edit Product Record
def edit_product_record(prod_id, new_price, new_qty):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Products SET Price = %s, Quantity = %s WHERE ProductID = %s",
        (new_price, new_qty, prod_id)
    )
    conn.commit()
    conn.close()
    st.success(f"✅ Product {prod_id} updated successfully!")

# Record transaction
def record_transaction(prod_id, cust_id, qty):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Quantity FROM Products WHERE ProductID = %s", (prod_id,))
    available = cursor.fetchone()[0]

    if qty > available:
        st.warning("Not enough stock available!")
        conn.close()
        return

    cursor.execute(
        "INSERT INTO Transactions (ProductID, CustomerID, TransactionDate, QuantitySold) VALUES (%s, %s, %s, %s)",
        (prod_id, cust_id, date.today(), qty)
    )
    cursor.execute(
        "UPDATE Products SET Quantity = Quantity - %s WHERE ProductID = %s",
        (qty, prod_id)
    )

    conn.commit()
    conn.close()
    st.success("Transaction recorded!")

# Delete product
def delete_product(prod_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ProductName FROM Products WHERE ProductID = %s", (prod_id,))
    product = cursor.fetchone()
    if not product:
        st.warning("Product not found!")
        conn.close()
        return

    if st.button(f"❌ Confirm Delete '{product[0]}'"):
        cursor.execute("DELETE FROM Products WHERE ProductID = %s", (prod_id,))
        conn.commit()
        st.success(f"🗑️ Product '{product[0]}' deleted successfully!")
    conn.close()

# Streamlit App UI
st.title("📦 Inventory Management System")

menu = st.sidebar.selectbox("📋 Choose Action", ["View Tables", "Add Product", "Record Sale", "Edit Record", "Delete Product", "Reports"])

if menu == "View Tables":
    st.header("🔍 View Database Tables")
    table = st.selectbox("Select Table", ["Products", "Categories", "Suppliers", "Customers", "Transactions"])
    df = load_data(table)

    if "Quantity" in df.columns:
        styled_df = df.style.applymap(highlight_low_stock, subset=["Quantity"])
    else:
        styled_df = df.style

    st.dataframe(styled_df, use_container_width=True)

elif menu == "Add Product":
    st.header("➕ Add New Product")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT CategoryID, CategoryName FROM Categories")
    categories = cursor.fetchall()
    conn.close()

    category_dict = {category[0]: category[1] for category in categories}
    cat_id = st.selectbox("🏷️ Select Category ID", list(category_dict.keys()), format_func=lambda x: f"{x} - {category_dict[x]}")

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("📝 Product Name")
        price = st.number_input("💲 Price", min_value=0.0, step=0.5)
    with col2:
        sup_id = st.number_input("🚚 Supplier ID", min_value=1, step=1)
        qty = st.number_input("📦 Initial Quantity", min_value=1, step=1)

    if st.button("Add Product"):
        add_product(name, cat_id, sup_id, price, qty)
        st.success(f"✅ Product '{name}' added successfully!")

elif menu == "Record Sale":
    st.header("🛒 Record a Sale")
    st.markdown("Enter sale details to update stock and track transactions.")

    st.subheader("📦 Existing Products")
    st.dataframe(load_data("Products")[["ProductID", "ProductName"]])
    st.subheader("👤 Existing Customers")
    st.dataframe(load_data("Customers")[["CustomerID", "CustomerName"]])

    col1, col2 = st.columns(2)
    with col1:
        prod_id = st.number_input("📦 Product ID", min_value=1, step=1)
        cust_id = st.number_input("👤 Customer ID", min_value=1, step=1)
    with col2:
        qty = st.number_input("🧾 Quantity Sold", min_value=1, step=1)

    if st.button("📤 Record Sale"):
        record_transaction(prod_id, cust_id, qty)

elif menu == "Edit Record":
    st.header("✏️ Edit Product Record")
    st.subheader("📦 Existing Products")
    st.dataframe(load_data("Products")[["ProductID", "ProductName"]])

    prod_id = st.number_input("📦 Product ID", min_value=1, step=1)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ProductName, Price, Quantity FROM Products WHERE ProductID = %s", (prod_id,))
    product = cursor.fetchone()

    if product:
        st.write(f"Editing {product[0]} (ID: {prod_id})")
        new_price = st.number_input("💲 New Price", value=float(product[1]), step=0.5)
        new_qty = st.number_input("📦 New Quantity", value=product[2], step=1)

        if st.button("🔄 Update Record"):
            edit_product_record(prod_id, new_price, new_qty)
    else:
        st.warning("Product not found!")

elif menu == "Delete Product":
    st.header("🗑️ Delete Product")
    st.subheader("📦 Existing Products")
    st.dataframe(load_data("Products")[["ProductID", "ProductName"]])

    prod_id = st.number_input("📦 Enter Product ID to Delete", min_value=1, step=1)
    delete_product(prod_id)

elif menu == "Reports":
    st.header("📊 Reports and Insights")
    conn = get_connection()

    st.subheader("📉 1. Stock Alert (Low Stock < 5)")
    df_low = pd.read_sql("SELECT ProductName, Quantity FROM Products WHERE Quantity < 5", conn)
    if df_low.empty:
        st.success("🎉 All products have sufficient stock!")
    else:
        st.dataframe(df_low.style.applymap(highlight_low_stock, subset=["Quantity"]))

    st.subheader("📈 2. Sales Report")
    query = """
        SELECT P.ProductName, T.QuantitySold, T.TransactionDate, C.CustomerName
        FROM Transactions T
        JOIN Products P ON T.ProductID = P.ProductID
        JOIN Customers C ON T.CustomerID = C.CustomerID
        ORDER BY T.TransactionDate DESC
    """
    df_sales = pd.read_sql(query, conn)
    df_sales["TransactionDate"] = pd.to_datetime(df_sales["TransactionDate"]).dt.strftime('%d %b %Y')

    st.dataframe(
        df_sales.style.set_properties(**{
            'background-color': '#f9f9f9',
            'border-color': 'black',
            'color': '#000',
            'font-size': '14px'
        }),
        use_container_width=True
    )
    conn.close()
