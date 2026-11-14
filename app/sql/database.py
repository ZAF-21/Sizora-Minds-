"""
Sample SQLite database for the SQL agent (R7).
Tables: sales, employees, and a users table (PII — off-limits to queries).
"""

from __future__ import annotations
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "codeforge_sample.db")

ALLOWED_TABLES = {"sales", "employees"}
BLOCKED_TABLES = {"users"}
MAX_LIMIT = 1000


def init_sample_db(path: str = DB_PATH) -> str:
    conn = sqlite3.connect(path)
    c = conn.cursor()

    c.execute("DROP TABLE IF EXISTS sales")
    c.execute("DROP TABLE IF EXISTS employees")
    c.execute("DROP TABLE IF EXISTS users")

    c.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            salary REAL NOT NULL,
            hire_date TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL,
            product TEXT NOT NULL,
            amount REAL NOT NULL,
            sale_date TEXT NOT NULL,
            region TEXT NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)

    c.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            aadhaar TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    employees = [
        (1, "Aarav Sharma", "Engineering", 85000, "2022-01-15"),
        (2, "Priya Patel", "Sales", 72000, "2021-06-01"),
        (3, "Rohan Mehta", "Marketing", 68000, "2023-03-10"),
        (4, "Ananya Gupta", "Engineering", 92000, "2020-11-20"),
        (5, "Vikram Singh", "Sales", 75000, "2022-08-05"),
    ]
    c.executemany("INSERT INTO employees VALUES (?,?,?,?,?)", employees)

    sales = [
        (1, 2, "Laptop Pro", 89999, "2024-01-10", "North"),
        (2, 2, "Wireless Mouse", 799, "2024-01-12", "North"),
        (3, 5, "USB-C Hub", 1499, "2024-01-15", "South"),
        (4, 2, "Headphones", 4999, "2024-02-01", "North"),
        (5, 5, "Phone Case", 499, "2024-02-10", "South"),
        (6, 3, "Keyboard", 3499, "2024-02-15", "West"),
        (7, 5, "Monitor", 24999, "2024-03-01", "South"),
        (8, 2, "Laptop Stand", 1299, "2024-03-05", "North"),
        (9, 3, "Webcam", 2999, "2024-03-10", "West"),
        (10, 5, "Tablet", 34999, "2024-03-15", "South"),
    ]
    c.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?)", sales)

    users = [
        (1, "aarav@company.com", "9876543210", "234567890123", "hashed_pw_1"),
        (2, "priya@company.com", "9876543211", "345678901234", "hashed_pw_2"),
    ]
    c.executemany("INSERT INTO users VALUES (?,?,?,?,?)", users)

    conn.commit()
    conn.close()
    return path


def run_readonly(sql: str, path: str = DB_PATH) -> list[dict]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    finally:
        conn.close()
