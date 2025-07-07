#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Summary Report
Shows the current status of all dashboard tables and data
"""

import sqlite3
from pathlib import Path
from datetime import datetime

def create_dashboard_summary():
    """Create comprehensive dashboard summary"""
    
    db_path = Path("data/database/cfdi_system_v4.db")
    
    if not db_path.exists():
        print("❌ Database not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("📊 CFDI DASHBOARD SUMMARY REPORT")
    print("=" * 60)
    print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Dashboard Tables Status
    print("🏗️  DASHBOARD TABLES STATUS")
    print("-" * 40)
    
    dashboard_tables = [
        ('sales_weekly_summary', 'Sales weekly aggregations'),
        ('sales_product_performance', 'Product performance metrics'),
        ('expenses_category_master', 'Expense category breakdown'),
        ('supplier_product_analysis', 'Supplier analysis'),
        ('expenses_weekly_summary', 'Expenses weekly aggregations'),
        ('weekly_kpis', 'Key performance indicators'),
        ('real_time_metrics', 'Real-time dashboard metrics')
    ]
    
    for table_name, description in dashboard_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        status = "✅ READY" if count > 0 else "⚠️  EMPTY"
        print(f"{status} {table_name}: {count} records")
        print(f"     {description}")
    
    print()
    
    # Key Metrics
    print("🎯 KEY DASHBOARD METRICS")
    print("-" * 40)
    
    # Sales metrics
    cursor.execute("""
        SELECT total_revenue, total_orders, total_items_sold, week_start_date
        FROM sales_weekly_summary 
        ORDER BY week_start_date DESC LIMIT 1
    """)
    
    sales_data = cursor.fetchone()
    if sales_data:
        revenue, orders, items, week = sales_data
        print(f"📈 Current Week Sales ({week}):")
        print(f"   💰 Revenue: ${revenue:,.2f}")
        print(f"   📦 Orders: {orders:,}")
        print(f"   🛍️  Items: {items:,.1f}")
        print(f"   💵 Avg Order: ${revenue/orders:,.2f}" if orders > 0 else "   💵 Avg Order: $0.00")
    
    # Top products
    cursor.execute("""
        SELECT product_code, total_revenue, total_quantity
        FROM sales_product_performance 
        ORDER BY total_revenue DESC LIMIT 5
    """)
    
    top_products = cursor.fetchall()
    if top_products:
        print(f"\n🏆 TOP 5 PRODUCTS (All Time):")
        for i, (code, revenue, qty) in enumerate(top_products, 1):
            print(f"   {i}. {code}: ${revenue:,.2f} (qty: {qty:,.0f})")
    
    # Expense categories
    cursor.execute("SELECT COUNT(DISTINCT category) FROM expenses_category_master")
    category_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT supplier_rfc) FROM supplier_product_analysis")
    supplier_count = cursor.fetchone()[0]
    
    print(f"\n💰 EXPENSE TRACKING:")
    print(f"   📊 Categories: {category_count}")
    print(f"   🏪 Suppliers: {supplier_count}")
    
    # Real-time metrics
    cursor.execute("""
        SELECT metric_name, metric_text, last_updated
        FROM real_time_metrics 
        WHERE metric_category = 'sales'
        ORDER BY last_updated DESC
    """)
    
    metrics = cursor.fetchall()
    if metrics:
        print(f"\n⚡ REAL-TIME METRICS:")
        for name, text, updated in metrics[:3]:
            print(f"   {name}: {text}")
    
    print()
    
    # API Readiness
    print("🚀 API READINESS STATUS")
    print("-" * 40)
    
    # Check if all required tables have data
    required_tables = ['sales_weekly_summary', 'sales_product_performance', 'real_time_metrics']
    all_ready = True
    
    for table in required_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count == 0:
            all_ready = False
    
    if all_ready:
        print("✅ DASHBOARD READY FOR API CONSUMPTION")
        print("🎯 All core tables populated with data")
        print("📊 Sales analytics: READY")
        print("💰 Expense analytics: BASIC STRUCTURE READY")
        print("⚡ Real-time metrics: READY")
        
        print("\n📋 AVAILABLE API ENDPOINTS:")
        print("   GET /api/sales/weekly-summary")
        print("   GET /api/sales/product-performance")
        print("   GET /api/expenses/categories")
        print("   GET /api/expenses/suppliers")
        print("   GET /api/kpis/weekly")
        print("   GET /api/metrics/real-time")
        
    else:
        print("⚠️  DASHBOARD PARTIALLY READY")
        print("   Some tables need data population")
    
    print("\n🔄 NEXT STEPS:")
    print("   1. Set up scheduled data updates (daily/weekly)")
    print("   2. Enhance expense classification logic")
    print("   3. Add more KPI calculations")
    print("   4. Monitor API performance")
    
    conn.close()

if __name__ == "__main__":
    create_dashboard_summary() 