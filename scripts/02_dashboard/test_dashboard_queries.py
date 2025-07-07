#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Dashboard Queries
Test all dashboard tables and verify data was populated correctly
"""

import sqlite3
from pathlib import Path

def test_dashboard_data():
    """Test dashboard data population"""
    db_path = Path("data/database/cfdi_system_v4.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🧪 Testing Dashboard Data")
    print("=" * 50)
    
    # Test sales weekly summary
    cursor.execute("SELECT COUNT(*) FROM sales_weekly_summary")
    weekly_summary_count = cursor.fetchone()[0]
    print(f"📊 Sales Weekly Summary: {weekly_summary_count} records")
    
    if weekly_summary_count > 0:
        cursor.execute("""
            SELECT week_start_date, total_revenue, total_orders, total_items_sold
            FROM sales_weekly_summary 
            ORDER BY week_start_date DESC 
            LIMIT 3
        """)
        for row in cursor.fetchall():
            print(f"   Week {row[0]}: ${row[1]:,.2f} revenue, {row[2]} orders, {row[3]} items")
    
    # Test product performance
    cursor.execute("SELECT COUNT(*) FROM sales_product_performance")
    product_count = cursor.fetchone()[0]
    print(f"📦 Product Performance: {product_count} records")
    
    if product_count > 0:
        cursor.execute("""
            SELECT product_code, total_revenue, total_quantity
            FROM sales_product_performance 
            ORDER BY total_revenue DESC 
            LIMIT 5
        """)
        print("   Top 5 Products by Revenue:")
        for row in cursor.fetchall():
            print(f"   - {row[0]}: ${row[1]:,.2f} (qty: {row[2]})")
    
    # Test expenses category master
    cursor.execute("SELECT COUNT(*) FROM expenses_category_master")
    category_count = cursor.fetchone()[0]
    print(f"💰 Expense Categories: {category_count} records")
    
    if category_count > 0:
        cursor.execute("""
            SELECT category, subcategory, total_spend
            FROM expenses_category_master 
            ORDER BY total_spend DESC 
            LIMIT 5
        """)
        print("   Top 5 Expense Categories:")
        for row in cursor.fetchall():
            print(f"   - {row[0]} > {row[1]}: ${row[2]:,.2f}")
    
    # Test KPIs
    cursor.execute("SELECT COUNT(*) FROM weekly_kpis")
    kpi_count = cursor.fetchone()[0]
    print(f"🎯 Weekly KPIs: {kpi_count} records")
    
    if kpi_count > 0:
        cursor.execute("""
            SELECT week_start_date, revenue_per_week, orders_per_week, 
                   revenue_per_order, expenses_per_week
            FROM weekly_kpis 
            ORDER BY week_start_date DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            print(f"   Latest Week ({row[0]}):")
            print(f"   - Revenue: ${row[1]:,.2f}")
            print(f"   - Orders: {row[2]}")
            print(f"   - Revenue/Order: ${row[3]:,.2f}")
            print(f"   - Expenses: ${row[4]:,.2f}")
    
    # Test real-time metrics
    cursor.execute("SELECT COUNT(*) FROM real_time_metrics")
    metrics_count = cursor.fetchone()[0]
    print(f"⚡ Real-time Metrics: {metrics_count} records")
    
    if metrics_count > 0:
        cursor.execute("""
            SELECT metric_name, metric_text, last_updated
            FROM real_time_metrics 
            WHERE metric_category = 'sales'
            ORDER BY last_updated DESC
        """)
        print("   Sales Metrics:")
        for row in cursor.fetchall():
            print(f"   - {row[0]}: {row[1]}")
    
    conn.close()
    
    print("\n✅ Dashboard data test complete!")
    print("🎯 Ready for API consumption")

if __name__ == "__main__":
    test_dashboard_data() 