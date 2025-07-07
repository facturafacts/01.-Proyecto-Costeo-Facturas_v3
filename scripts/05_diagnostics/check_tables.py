#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/database/cfdi_system_v4.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("All tables in database:")
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
    count = cursor.fetchone()[0]
    print(f"  - {table[0]}: {count} records")

conn.close() 