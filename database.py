import sqlite3
import json
from datetime import datetime

DB_NAME = 'restaurant_orders.db'

def init_db():
    """ایجاد دیتابیس و جداول"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            items TEXT,
            total_price INTEGER,
            phone TEXT,
            address TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_order(user_id, username, items, total_price, phone, address):
    """ذخیره سفارش در دیتابیس"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO orders (user_id, username, items, total_price, phone, address, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, json.dumps(items), total_price, phone, address, 'در انتظار تایید'))
    
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    
    return order_id

def get_orders():
    """دریافت تمام سفارش‌ها"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM orders')
    orders = cursor.fetchall()
    conn.close()
    
    return orders
