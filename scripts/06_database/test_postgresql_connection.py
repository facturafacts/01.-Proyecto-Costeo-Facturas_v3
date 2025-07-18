#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL Connection Test and Database Analysis for CFDI Processing System v4

Tests connection and analyzes invoice/purchase details mismatch.
Follows v4 Enhanced Cursor Rules for database operations and error handling.
"""

import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from tabulate import tabulate
import json
from datetime import datetime

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Load the environment variables from the .env file
load_dotenv(dotenv_path=project_root / ".env")

def test_connection():
    """Test the PostgreSQL connection using environment variables."""
    print("🔌 Testing PostgreSQL Connection")
    print("=" * 50)
    
    # Show connection details (without password)
    print(f"Host: {os.getenv('DB_HOST')}")
    print(f"Database: {os.getenv('DB_NAME')}")
    print(f"User: {os.getenv('DB_USER')}")
    print(f"Port: {os.getenv('DB_PORT')}")
    print()
    
    try:
        print("Connecting to the database...")
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT"),
            sslmode='require'  # DigitalOcean requires SSL
        )
        
        # Test basic query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        print("✅ Connection successful!")
        print(f"PostgreSQL Version: {version[0]}")
        print()
        
        return conn, cursor
        
    except Exception as e:
        print("❌ Connection failed.")
        print(f"Error: {e}")
        return None, None

def analyze_tables(cursor):
    """Analyze table structure and relationships."""
    print("📊 Database Table Analysis")
    print("=" * 50)
    
    # Check which tables exist
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    
    tables = cursor.fetchall()
    print("Available tables:")
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  • {table[0]}: {count:,} records")
        except Exception as e:
            print(f"  • {table[0]}: Error - {e}")
    print()
    
    return [table[0] for table in tables]

def analyze_data_relationships(cursor):
    """Analyze relationships between invoices, items, and purchase details."""
    print("🔗 Data Relationship Analysis")
    print("=" * 50)
    
    # Check if required tables exist
    required_tables = ['invoices', 'invoice_items', 'purchase_details']
    
    for table in required_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ {table}: {count:,} records")
        except Exception as e:
            print(f"❌ {table}: Error - {e}")
            return {}
    
    print()
    
    # 1. Check for orphaned purchase_details
    print("🔍 Checking for orphaned purchase_details...")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM purchase_details pd
        LEFT JOIN invoice_items ii ON pd.item_id = ii.id
        WHERE ii.id IS NULL
    """)
    orphaned_purchases = cursor.fetchone()[0]
    print(f"Orphaned purchase_details: {orphaned_purchases}")
    
    # 2. Check for orphaned invoice_items
    print("🔍 Checking for orphaned invoice_items...")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM invoice_items ii
        LEFT JOIN invoices i ON ii.invoice_id = i.id
        WHERE i.id IS NULL
    """)
    orphaned_items = cursor.fetchone()[0]
    print(f"Orphaned invoice_items: {orphaned_items}")
    
    # 3. Check for items without purchase details
    print("🔍 Checking for items without purchase details...")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM invoice_items ii
        LEFT JOIN purchase_details pd ON ii.id = pd.item_id
        WHERE pd.item_id IS NULL
    """)
    items_without_purchases = cursor.fetchone()[0]
    print(f"Items without purchase details: {items_without_purchases}")
    
    # 4. Sample successful join query
    print("🔍 Testing successful joins...")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM purchase_details pd
        INNER JOIN invoice_items ii ON pd.item_id = ii.id
        INNER JOIN invoices i ON ii.invoice_id = i.id
    """)
    successful_joins = cursor.fetchone()[0]
    print(f"Records with complete relationships: {successful_joins}")
    
    print()
    return {
        'orphaned_purchases': orphaned_purchases,
        'orphaned_items': orphaned_items,
        'items_without_purchases': items_without_purchases,
        'successful_joins': successful_joins
    }

def get_sample_data(cursor):
    """Get sample data to understand the structure."""
    print("📝 Sample Data Analysis")
    print("=" * 50)
    
    try:
        # Get sample data with successful joins
        cursor.execute("""
            SELECT 
                pd.id as purchase_id,
                pd.purchase_order,
                pd.purchase_date,
                ii.id as item_id,
                ii.description,
                i.uuid as invoice_uuid,
                i.folio,
                i.issuer_rfc,
                i.total_amount
            FROM purchase_details pd
            INNER JOIN invoice_items ii ON pd.item_id = ii.id
            INNER JOIN invoices i ON ii.invoice_id = i.id
            ORDER BY pd.purchase_date DESC
            LIMIT 10
        """)
        
        sample_data = cursor.fetchall()
        
        if sample_data:
            headers = ["Purchase ID", "PO", "Date", "Item ID", "Description", "Invoice UUID", "Folio", "Issuer RFC", "Total"]
            table_data = []
            
            for row in sample_data:
                desc = row[4][:30] + "..." if len(row[4]) > 30 else row[4]
                table_data.append([
                    row[0], row[1], row[2], row[3], desc, 
                    row[5][:8] + "...", row[6], row[7], f"${row[8]:,.2f}"
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            print("❌ No successful joins found!")
            
    except Exception as e:
        print(f"❌ Error getting sample data: {e}")
    
    print()

def test_api_query_simulation(cursor):
    """Simulate the API queries to identify the exact problem."""
    print("🔌 API Query Simulation")
    print("=" * 50)
    
    # 1. Current (broken) API query - just purchase_details
    print("1. Current API query (purchase_details only):")
    try:
        cursor.execute("SELECT COUNT(*) FROM purchase_details")
        simple_count = cursor.fetchone()[0]
        print(f"   ✅ Returns {simple_count} records")
        
        # Try to get first record to see what fields are available
        cursor.execute("SELECT * FROM purchase_details LIMIT 1")
        if cursor.rowcount > 0:
            columns = [desc[0] for desc in cursor.description]
            print(f"   Available fields: {columns}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # 2. Correct API query - with joins
    print("2. Corrected API query (with joins):")
    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM purchase_details pd
            INNER JOIN invoice_items ii ON pd.item_id = ii.id
            INNER JOIN invoices i ON ii.invoice_id = i.id
        """)
        joined_count = cursor.fetchone()[0]
        print(f"   ✅ Returns {joined_count} records")
        
        # Test actual field availability for API response
        cursor.execute("""
            SELECT 
                i.uuid as invoice_uuid,
                i.folio,
                i.issuer_rfc,
                i.issuer_name,
                i.receiver_rfc,
                i.receiver_name,
                i.currency,
                i.total_amount,
                ii.description,
                ii.quantity,
                ii.unit_price,
                ii.category,
                pd.purchase_order
            FROM purchase_details pd
            INNER JOIN invoice_items ii ON pd.item_id = ii.id
            INNER JOIN invoices i ON ii.invoice_id = i.id
            LIMIT 1
        """)
        
        if cursor.rowcount > 0:
            print("   ✅ All required API fields accessible")
            sample_row = cursor.fetchone()
            print(f"   Sample: Invoice {sample_row[1]}, Item: {sample_row[8][:30]}...")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()

def generate_fix_recommendation(stats):
    """Generate specific fix recommendations based on analysis."""
    print("🎯 Fix Recommendations")
    print("=" * 50)
    
    if stats.get('successful_joins', 0) == 0:
        print("❌ CRITICAL: No successful relationships found!")
        print("   This means:")
        print("   • The purchase_details table is empty, OR")
        print("   • The foreign keys are broken, OR") 
        print("   • The tables are not properly related")
        print()
        print("🔧 Immediate Actions:")
        print("   1. Check if purchase_details has any data")
        print("   2. Verify foreign key constraints")
        print("   3. Check data migration/import process")
        
    elif stats.get('orphaned_purchases', 0) > 0:
        print(f"❌ Found {stats['orphaned_purchases']} orphaned purchase_details")
        print("🔧 Fix: Clean up orphaned records or repair foreign keys")
        
    elif stats.get('items_without_purchases', 0) > 0:
        print(f"⚠️ Found {stats['items_without_purchases']} items without purchase details")
        print("🔧 This is normal if not all items have purchase orders")
        
    else:
        print("✅ Data relationships look good!")
        print("🔧 The issue is likely in the API endpoint code")
    
    print()
    print("📝 API Endpoint Fix Required:")
    print("   File: src/api/endpoints.py")
    print("   Function: get_purchase_details")
    print()
    print("   Replace the simple query:")
    print("   session.query(PurchaseDetails)")
    print()
    print("   With the joined query:")
    print("   session.query(PurchaseDetails, InvoiceItem, Invoice)")
    print("   .join(InvoiceItem, PurchaseDetails.item_id == InvoiceItem.id)")
    print("   .join(Invoice, InvoiceItem.invoice_id == Invoice.id)")

def main():
    """Main execution function following v4 Enhanced error handling standards."""
    print("🚀 PostgreSQL Database Analysis for CFDI System v4")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print()
    
    # Test connection
    conn, cursor = test_connection()
    
    if not conn:
        print("❌ Cannot proceed without database connection")
        print("🔧 Check your .env file has the correct database credentials:")
        print("   DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT")
        return
    
    try:
        # Analyze tables
        tables = analyze_tables(cursor)
        
        # Analyze relationships
        stats = analyze_data_relationships(cursor)
        
        # Get sample data
        get_sample_data(cursor)
        
        # Test API queries
        test_api_query_simulation(cursor)
        
        # Generate recommendations
        generate_fix_recommendation(stats)
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        print("🔧 This may indicate a schema or permission issue")
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("🔐 Database connection closed.")

if __name__ == "__main__":
    main() 