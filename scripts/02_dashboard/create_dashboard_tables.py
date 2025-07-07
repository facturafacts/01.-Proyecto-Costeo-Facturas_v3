#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create Dashboard Tables for CFDI System
Creates pre-aggregated tables for fast dashboard queries

Tables created:
1. Sales Tables: weekly_summary, product_performance
2. Expense Tables: category_master, supplier_product_analysis, weekly_summary
3. KPI Tables: weekly_kpis, real_time_metrics
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_dashboard_tables():
    """Create all dashboard tables in the CFDI database"""
    
    # Use main CFDI database
    db_path = Path("data/database/cfdi_system_v4.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    print("🏗️  Creating Dashboard Tables")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. SALES WEEKLY SUMMARY
        print("📊 Creating sales_weekly_summary...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_weekly_summary (
                week_start_date DATE PRIMARY KEY,
                week_end_date DATE NOT NULL,
                total_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
                total_orders INTEGER NOT NULL DEFAULT 0,
                total_items_sold INTEGER NOT NULL DEFAULT 0,
                revenue_per_order DECIMAL(15,2) NOT NULL DEFAULT 0,
                avg_order_value DECIMAL(15,2) NOT NULL DEFAULT 0,
                top_product_code VARCHAR(50),
                top_product_revenue DECIMAL(15,2),
                unique_products INTEGER DEFAULT 0,
                growth_rate DECIMAL(5,2),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. SALES PRODUCT PERFORMANCE
        print("📦 Creating sales_product_performance...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_product_performance (
                product_code VARCHAR(50) NOT NULL,
                product_description VARCHAR(255) NOT NULL,
                weekly_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
                weekly_quantity DECIMAL(15,2) NOT NULL DEFAULT 0,
                monthly_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
                monthly_quantity DECIMAL(15,2) NOT NULL DEFAULT 0,
                yearly_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
                yearly_quantity DECIMAL(15,2) NOT NULL DEFAULT 0,
                total_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
                total_quantity DECIMAL(15,2) NOT NULL DEFAULT 0,
                avg_price DECIMAL(15,6) NOT NULL DEFAULT 0,
                order_frequency INTEGER DEFAULT 0,
                revenue_rank INTEGER,
                quantity_rank INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (product_code)
            )
        """)
        
        # 3. EXPENSES CATEGORY MASTER (Enhanced 7-column structure)
        print("💰 Creating expenses_category_master...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses_category_master (
                category VARCHAR(50) NOT NULL,
                subcategory VARCHAR(100) NOT NULL,
                sub_sub_category VARCHAR(150) NOT NULL,
                weekly_spend DECIMAL(15,2) NOT NULL DEFAULT 0,
                monthly_spend DECIMAL(15,2) NOT NULL DEFAULT 0,
                yearly_spend DECIMAL(15,2) NOT NULL DEFAULT 0,
                total_spend DECIMAL(15,2) NOT NULL DEFAULT 0,
                item_count INTEGER DEFAULT 0,
                invoice_count INTEGER DEFAULT 0,
                avg_confidence DECIMAL(5,2),
                last_purchase_date DATE,
                category_rank INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (category, subcategory, sub_sub_category)
            )
        """)
        
        # 4. SUPPLIER PRODUCT ANALYSIS (Enhanced for price comparison)
        print("🏪 Creating supplier_product_analysis...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_product_analysis (
                supplier_rfc VARCHAR(13) NOT NULL,
                supplier_name VARCHAR(100),
                category VARCHAR(50) NOT NULL,
                subcategory VARCHAR(100) NOT NULL,
                sub_sub_category VARCHAR(150) NOT NULL,
                total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                item_count INTEGER DEFAULT 0,
                invoice_count INTEGER DEFAULT 0,
                avg_unit_price DECIMAL(15,6) NOT NULL DEFAULT 0,
                min_unit_price DECIMAL(15,6),
                max_unit_price DECIMAL(15,6),
                last_purchase_date DATE,
                first_purchase_date DATE,
                purchase_frequency INTEGER DEFAULT 0,
                payment_terms_pue INTEGER DEFAULT 0,
                payment_terms_ppd INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (supplier_rfc, category, subcategory, sub_sub_category)
            )
        """)
        
        # 5. EXPENSES WEEKLY SUMMARY
        print("📈 Creating expenses_weekly_summary...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses_weekly_summary (
                week_start_date DATE PRIMARY KEY,
                week_end_date DATE NOT NULL,
                total_expenses DECIMAL(15,2) NOT NULL DEFAULT 0,
                total_invoices INTEGER NOT NULL DEFAULT 0,
                total_line_items INTEGER NOT NULL DEFAULT 0,
                avg_invoice_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                unique_suppliers INTEGER DEFAULT 0,
                top_category VARCHAR(50),
                top_category_amount DECIMAL(15,2),
                top_supplier_rfc VARCHAR(13),
                top_supplier_amount DECIMAL(15,2),
                pue_invoices INTEGER DEFAULT 0,
                ppd_invoices INTEGER DEFAULT 0,
                growth_rate DECIMAL(5,2),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 6. WEEKLY KPIs
        print("🎯 Creating weekly_kpis...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_kpis (
                week_start_date DATE PRIMARY KEY,
                week_end_date DATE NOT NULL,
                revenue_per_week DECIMAL(15,2) NOT NULL DEFAULT 0,
                orders_per_week INTEGER NOT NULL DEFAULT 0,
                revenue_per_order DECIMAL(15,2) NOT NULL DEFAULT 0,
                items_per_order DECIMAL(5,2) NOT NULL DEFAULT 0,
                revenue_per_item DECIMAL(15,6) NOT NULL DEFAULT 0,
                expenses_per_week DECIMAL(15,2) NOT NULL DEFAULT 0,
                invoices_per_week INTEGER NOT NULL DEFAULT 0,
                avg_invoice_size DECIMAL(15,2) NOT NULL DEFAULT 0,
                data_quality_score DECIMAL(5,2),
                classification_confidence DECIMAL(5,2),
                processing_success_rate DECIMAL(5,2),
                revenue_growth_rate DECIMAL(5,2),
                expense_growth_rate DECIMAL(5,2),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 7. REAL-TIME METRICS
        print("⚡ Creating real_time_metrics...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS real_time_metrics (
                metric_name VARCHAR(50) PRIMARY KEY,
                metric_value DECIMAL(15,2),
                metric_text VARCHAR(255),
                metric_date DATE,
                metric_category VARCHAR(20),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 8. TIME PERIOD AGGREGATIONS
        print("📅 Creating time_period_summary...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_period_summary (
                period_type VARCHAR(10) NOT NULL,
                period_value VARCHAR(20) NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                sales_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
                sales_orders INTEGER NOT NULL DEFAULT 0,
                sales_items INTEGER NOT NULL DEFAULT 0,
                expense_total DECIMAL(15,2) NOT NULL DEFAULT 0,
                expense_invoices INTEGER NOT NULL DEFAULT 0,
                unique_products INTEGER DEFAULT 0,
                unique_suppliers INTEGER DEFAULT 0,
                growth_rate DECIMAL(5,2),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (period_type, period_value)
            )
        """)
        
        # Create indexes for performance
        print("🔍 Creating indexes...")
        
        # Sales indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_product_revenue ON sales_product_performance(weekly_revenue DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_product_quantity ON sales_product_performance(weekly_quantity DESC)")
        
        # Expense indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_category_spend ON expenses_category_master(weekly_spend DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_category_total ON expenses_category_master(total_spend DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supplier_analysis_amount ON supplier_product_analysis(total_amount DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supplier_analysis_price ON supplier_product_analysis(avg_unit_price)")
        
        # Time-based indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_weekly_kpis_date ON weekly_kpis(week_start_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_time_period_type ON time_period_summary(period_type, period_start DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_real_time_category ON real_time_metrics(metric_category)")
        
        # Initialize real-time metrics with default values
        print("🎲 Initializing real-time metrics...")
        default_metrics = [
            ('current_week_sales', 0, 'Current week sales revenue', 'sales'),
            ('current_week_expenses', 0, 'Current week expenses', 'expenses'),
            ('current_week_orders', 0, 'Current week order count', 'sales'),
            ('current_week_invoices', 0, 'Current week invoice count', 'expenses'),
            ('last_sale_time', 0, 'Last sale timestamp', 'status'),
            ('last_invoice_time', 0, 'Last invoice processed', 'status'),
            ('data_quality_score', 0, 'Overall data quality percentage', 'quality'),
            ('system_health', 100, 'System health percentage', 'status'),
            ('best_product_week', 0, 'Best selling product this week', 'sales'),
            ('top_expense_category', 0, 'Biggest expense category this week', 'expenses')
        ]
        
        for metric_name, value, description, category in default_metrics:
            cursor.execute("""
                INSERT OR REPLACE INTO real_time_metrics 
                (metric_name, metric_value, metric_text, metric_category, metric_date, last_updated)
                VALUES (?, ?, ?, ?, DATE('now'), CURRENT_TIMESTAMP)
            """, (metric_name, value, description, category))
        
        conn.commit()
        conn.close()
        
        print("\n✅ Dashboard tables created successfully!")
        print("📋 Tables created:")
        print("   • sales_weekly_summary")
        print("   • sales_product_performance") 
        print("   • expenses_category_master (7 columns)")
        print("   • supplier_product_analysis (price comparison)")
        print("   • expenses_weekly_summary")
        print("   • weekly_kpis")
        print("   • real_time_metrics")
        print("   • time_period_summary")
        print("\n🔍 Indexes created for optimal performance")
        print("🎲 Real-time metrics initialized with default values")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating dashboard tables: {e}")
        return False

def verify_tables():
    """Verify that all tables were created successfully"""
    db_path = Path("data/database/cfdi_system_v4.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of dashboard tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND (
                name LIKE '%summary%' 
                OR name LIKE '%performance%' 
                OR name LIKE '%master%'
                OR name LIKE '%analysis%'
                OR name LIKE '%kpis%'
                OR name LIKE '%metrics%'
            )
            ORDER BY name
        """)
        
        tables = cursor.fetchall()
        
        print("\n🔍 Dashboard Tables Verification:")
        print("-" * 40)
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"✅ {table_name}: {count} records")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verifying tables: {e}")
        return False

def main():
    """Main execution function"""
    print("🚀 CFDI Dashboard Tables Setup")
    print("=" * 50)
    
    if create_dashboard_tables():
        verify_tables()
        print("\n🎯 Next Steps:")
        print("   1. Run: python scripts/populate_dashboard_data.py")
        print("   2. Test: python scripts/test_dashboard_queries.py")
        print("   3. Setup: Scheduled updates for real-time data")
    else:
        print("\n❌ Setup failed. Please check the errors above.")

if __name__ == "__main__":
    main() 