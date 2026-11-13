import sqlite3
from logging import exception

import pandas as pd

def create_tables(conn):
    cursor = conn.cursor()
    #删除已有表
    cursor.execute("DROP TABLE IF EXISTS order_items;")
    cursor.execute("DROP TABLE IF EXISTS payments;")
    cursor.execute("DROP TABLE IF EXISTS orders;")
    cursor.execute("DROP TABLE IF EXISTS products;")
    cursor.execute("DROP TABLE IF EXISTS sellers;")
    cursor.execute("DROP TABLE IF EXISTS customers;")
    # 1. 客户表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers(
        customer_id TEXT PRIMARY KEY,
        customer_unique_id TEXT,
        customer_zip_code_prefix INTEGER,
        customer_city TEXT,
        customer_state TEXT
    );
    """)

    # 2. 卖家表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sellers (
        seller_id TEXT PRIMARY KEY,
        seller_zip_code_prefix INTEGER,
        seller_city TEXT,
        seller_state TEXT
    );
    """)

    # 3. 商品表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,
        product_category_name TEXT,
        product_name_lenght INTEGER,
        product_description_lenght INTEGER,
        product_photos_qty INTEGER,
        product_weight_g INTEGER,
        product_length_cm INTEGER,
        product_height_cm INTEGER,
        product_width_cm INTEGER
    );
    """)

    # 4. 订单主表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        customer_id TEXT,
        order_status TEXT,
        order_purchase_timestamp TEXT,
        order_approved_at TEXT,
        order_delivered_carrier_date TEXT,
        order_delivered_customer_date TEXT,
        order_estimated_delivery_date TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );
    """)

    # 5. 订单明细表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        order_id TEXT,
        order_item_id INTEGER,
        product_id TEXT,
        seller_id TEXT,
        shipping_limit_date TEXT,
        price INTEGER, 
        freight_value INTEGER, 
        PRIMARY KEY (order_id, order_item_id),
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id),
        FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
    );
    """)

    # 6. 支付表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        order_id TEXT,
        payment_sequential INTEGER,
        payment_type TEXT,
        payment_installments INTEGER,
        payment_value INTEGER, 
        PRIMARY KEY (order_id, payment_sequential),
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
    );
    """)

    conn.commit()
    print("✅ 6 张核心表建表成功！")

def import_data(conn):


    df_customers = pd.read_csv("data/olist_customers_dataset.csv")
    df_customers.to_sql("customers", con=conn, if_exists='append', index=False)
    print("customers 导入完成")
    # 2. 卖家表 (无外键)
    df_sellers = pd.read_csv("data/olist_sellers_dataset.csv")
    df_sellers.to_sql("sellers", conn, if_exists="append", index=False)

    # 3. 商品表 (无外键)
    df_products = pd.read_csv("data/olist_products_dataset.csv")
    df_products.to_sql("products", conn, if_exists="append", index=False)

    # 4. 订单主表
    df_orders = pd.read_csv("data/olist_orders_dataset.csv")
    df_orders.to_sql("orders", conn, if_exists="append", index=False)

    # 5. 订单明细表
    df_items=pd.read_csv("data/olist_order_items_dataset.csv")
    df_items["price"]=(df_items["price"]*100).round().astype("Int64")
    df_items["freight_value"]=(df_items["freight_value"]*100).round().astype("Int64")
    df_items.to_sql("order_items", conn, if_exists="append", index=False)

    # 6. 支付表
    df_payments = pd.read_csv("data/olist_order_payments_dataset.csv")
    df_payments["payment_value"] = (df_payments["payment_value"] * 100).round().astype("Int64")
    df_payments.to_sql("payments", conn, if_exists="append", index=False)
    print("✅ 所有数据导入完成！")


if __name__ == "__main__":
    conn = sqlite3.connect("olist.db")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        print("开始重建表结构...")
        create_tables(conn)

        print("开始导入数据...")
        import_data(conn)

        conn.commit()
        print("✅ 所有任务执行成功！")
    except exception as e:
        conn.rollback()
        print(f"发生错误，已回滚！错误信息：{e}")
    finally:
        conn.close()