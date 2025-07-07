#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check CFDI Database Schema
Simple script to examine database structure
"""

import sqlite3
from pathlib import Path

def check_schema():
    """Check database schema"""
    db_path = Path("data/database/cfdi_system_v4.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔍 CFDI Database Schema Analysis")
    print("=" * 50)
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print(f"📊 Found {len(tables)} tables:")
    for table in tables:
        table_name = table[0]
        
        # Get column info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        
        print(f"\n✅ {table_name} ({count} records)")
        print("   Columns:")
        for col in columns:
            col_name, col_type = col[1], col[2]
            print(f"   - {col_name}: {col_type}")
    
    conn.close()

if __name__ == "__main__":
    check_schema() 