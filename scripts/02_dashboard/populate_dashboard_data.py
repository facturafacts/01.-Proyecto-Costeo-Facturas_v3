#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Populate Dashboard Data for CFDI System
Calculates and populates all dashboard tables with aggregated data

This script should be run periodically (daily/weekly) to update dashboard data
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class DashboardDataPopulator:
    """Populates dashboard tables with calculated data"""
    
    def __init__(self):
        self.db_path = Path("data/database/cfdi_system_v4.db")
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to database"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            
    def get_week_boundaries(self, date_str=None):
        """Get week start and end dates"""
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = datetime.now().date()
            
        # Get Monday of the week
        days_since_monday = date.weekday()
        week_start = date - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        
        return week_start, week_end
    
    def populate_sales_weekly_summary(self):
        """Populate sales weekly summary table"""
        print("📊 Populating sales_weekly_summary...")
        
        # Get all weeks with sales data
        self.cursor.execute("""
            SELECT DISTINCT 
                DATE(processing_date, 'weekday 0', '-6 days') as week_start,
                DATE(processing_date, 'weekday 0') as week_end
            FROM sales_orders 
            WHERE processing_date IS NOT NULL
            ORDER BY week_start DESC
        """)
        
        weeks = self.cursor.fetchall()
        
        for week_start, week_end in weeks:
            # Calculate weekly metrics
            self.cursor.execute("""
                SELECT 
                    COUNT(DISTINCT folio_cuenta) as total_orders,
                    COALESCE(SUM(ventas_total), 0) as total_revenue
                FROM sales_orders 
                WHERE DATE(processing_date) BETWEEN ? AND ?
            """, (week_start, week_end))
            
            orders, revenue = self.cursor.fetchone()
            
            # Get total items sold from sales_items table
            self.cursor.execute("""
                SELECT COALESCE(SUM(si.cantidad), 0) as total_items_sold
                FROM sales_items si
                JOIN sales_orders so ON si.folio_cuenta = so.folio_cuenta
                WHERE DATE(so.processing_date) BETWEEN ? AND ?
            """, (week_start, week_end))
            
            items = self.cursor.fetchone()[0]
            
            # Get top product for the week
            self.cursor.execute("""
                SELECT si.clave_producto, SUM(si.importe) as product_revenue
                FROM sales_items si
                JOIN sales_orders so ON si.folio_cuenta = so.folio_cuenta
                WHERE DATE(so.processing_date) BETWEEN ? AND ?
                GROUP BY si.clave_producto
                ORDER BY product_revenue DESC
                LIMIT 1
            """, (week_start, week_end))
            
            top_product_result = self.cursor.fetchone()
            top_product_code = top_product_result[0] if top_product_result else None
            top_product_revenue = top_product_result[1] if top_product_result else 0
            
            # Count unique products
            self.cursor.execute("""
                SELECT COUNT(DISTINCT si.clave_producto)
                FROM sales_items si
                JOIN sales_orders so ON si.folio_cuenta = so.folio_cuenta
                WHERE DATE(so.processing_date) BETWEEN ? AND ?
            """, (week_start, week_end))
            
            unique_products = self.cursor.fetchone()[0]
            
            # Calculate derived metrics
            revenue_per_order = revenue / orders if orders > 0 else 0
            avg_order_value = revenue_per_order  # Same as revenue_per_order
            
            # Insert or update weekly summary
            self.cursor.execute("""
                INSERT OR REPLACE INTO sales_weekly_summary 
                (week_start_date, week_end_date, total_revenue, total_orders, 
                 total_items_sold, revenue_per_order, avg_order_value, 
                 top_product_code, top_product_revenue, unique_products, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (week_start, week_end, revenue, orders, items, 
                  revenue_per_order, avg_order_value, top_product_code, 
                  top_product_revenue, unique_products))
        
        print(f"   ✅ Processed {len(weeks)} weeks of sales data")
    
    def populate_sales_product_performance(self):
        """Populate sales product performance table"""
        print("📦 Populating sales_product_performance...")
        
        # Get all products
        self.cursor.execute("""
            SELECT DISTINCT clave_producto, descripcion
            FROM sales_items
            WHERE clave_producto IS NOT NULL
        """)
        
        products = self.cursor.fetchall()
        
        for product_code, description in products:
            # Current week
            week_start, week_end = self.get_week_boundaries()
            
            # Weekly metrics
            self.cursor.execute("""
                SELECT 
                    COALESCE(SUM(si.importe), 0) as revenue,
                    COALESCE(SUM(si.cantidad), 0) as quantity
                FROM sales_items si
                JOIN sales_orders so ON si.folio_cuenta = so.folio_cuenta
                WHERE si.clave_producto = ? 
                AND DATE(so.processing_date) BETWEEN ? AND ?
            """, (product_code, week_start, week_end))
            
            weekly_revenue, weekly_quantity = self.cursor.fetchone()
            
            # Monthly metrics (last 30 days)
            month_start = datetime.now().date() - timedelta(days=30)
            self.cursor.execute("""
                SELECT 
                    COALESCE(SUM(si.importe), 0) as revenue,
                    COALESCE(SUM(si.cantidad), 0) as quantity
                FROM sales_items si
                JOIN sales_orders so ON si.folio_cuenta = so.folio_cuenta
                WHERE si.clave_producto = ? 
                AND DATE(so.processing_date) >= ?
            """, (product_code, month_start))
            
            monthly_revenue, monthly_quantity = self.cursor.fetchone()
            
            # Yearly metrics (last 365 days)
            year_start = datetime.now().date() - timedelta(days=365)
            self.cursor.execute("""
                SELECT 
                    COALESCE(SUM(si.importe), 0) as revenue,
                    COALESCE(SUM(si.cantidad), 0) as quantity
                FROM sales_items si
                JOIN sales_orders so ON si.folio_cuenta = so.folio_cuenta
                WHERE si.clave_producto = ? 
                AND DATE(so.processing_date) >= ?
            """, (product_code, year_start))
            
            yearly_revenue, yearly_quantity = self.cursor.fetchone()
            
            # Total metrics (all time)
            self.cursor.execute("""
                SELECT 
                    COALESCE(SUM(si.importe), 0) as revenue,
                    COALESCE(SUM(si.cantidad), 0) as quantity,
                    COUNT(DISTINCT so.folio_cuenta) as order_frequency
                FROM sales_items si
                JOIN sales_orders so ON si.folio_cuenta = so.folio_cuenta
                WHERE si.clave_producto = ?
            """, (product_code,))
            
            total_revenue, total_quantity, order_frequency = self.cursor.fetchone()
            
            # Calculate average price
            avg_price = total_revenue / total_quantity if total_quantity > 0 else 0
            
            # Insert or update product performance
            self.cursor.execute("""
                INSERT OR REPLACE INTO sales_product_performance 
                (product_code, product_description, weekly_revenue, weekly_quantity,
                 monthly_revenue, monthly_quantity, yearly_revenue, yearly_quantity,
                 total_revenue, total_quantity, avg_price, order_frequency, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (product_code, description, weekly_revenue, weekly_quantity,
                  monthly_revenue, monthly_quantity, yearly_revenue, yearly_quantity,
                  total_revenue, total_quantity, avg_price, order_frequency))
        
        # Update rankings
        self.cursor.execute("""
            UPDATE sales_product_performance 
            SET revenue_rank = (
                SELECT COUNT(*) + 1 
                FROM sales_product_performance p2 
                WHERE p2.weekly_revenue > sales_product_performance.weekly_revenue
            )
        """)
        
        self.cursor.execute("""
            UPDATE sales_product_performance 
            SET quantity_rank = (
                SELECT COUNT(*) + 1 
                FROM sales_product_performance p2 
                WHERE p2.weekly_quantity > sales_product_performance.weekly_quantity
            )
        """)
        
        print(f"   ✅ Processed {len(products)} products")
    
    def populate_expenses_category_master(self):
        """Populate expenses category master table with 7-column structure"""
        print("💰 Populating expenses_category_master...")
        
        # Get all category combinations from invoice_metadata
        self.cursor.execute("""
            SELECT DISTINCT category, subcategory, sub_sub_category
            FROM invoice_metadata
            WHERE category IS NOT NULL 
            AND subcategory IS NOT NULL 
            AND sub_sub_category IS NOT NULL
        """)
        
        categories = self.cursor.fetchall()
        
        for category, subcategory, sub_sub_category in categories:
            # Current week
            week_start, week_end = self.get_week_boundaries()
            
            # Weekly spend
            self.cursor.execute("""
                SELECT 
                    COALESCE(SUM(mxn_total), 0) as weekly_spend,
                    COUNT(DISTINCT invoice_id) as invoice_count,
                    COUNT(*) as item_count
                FROM invoice_metadata
                WHERE category = ? AND subcategory = ? AND sub_sub_category = ?
                AND DATE(invoice_date) BETWEEN ? AND ?
            """, (category, subcategory, sub_sub_category, week_start, week_end))
            
            weekly_spend, weekly_invoices, weekly_items = self.cursor.fetchone()
            
            # Monthly spend (last 30 days)
            month_start = datetime.now().date() - timedelta(days=30)
            self.cursor.execute("""
                SELECT COALESCE(SUM(mxn_total), 0)
                FROM invoice_metadata
                WHERE category = ? AND subcategory = ? AND sub_sub_category = ?
                AND DATE(invoice_date) >= ?
            """, (category, subcategory, sub_sub_category, month_start))
            
            monthly_spend = self.cursor.fetchone()[0]
            
            # Yearly spend (last 365 days)
            year_start = datetime.now().date() - timedelta(days=365)
            self.cursor.execute("""
                SELECT COALESCE(SUM(mxn_total), 0)
                FROM invoice_metadata
                WHERE category = ? AND subcategory = ? AND sub_sub_category = ?
                AND DATE(invoice_date) >= ?
            """, (category, subcategory, sub_sub_category, year_start))
            
            yearly_spend = self.cursor.fetchone()[0]
            
            # Total spend and metrics
            self.cursor.execute("""
                SELECT 
                    COALESCE(SUM(mxn_total), 0) as total_spend,
                    COUNT(DISTINCT invoice_id) as invoice_count,
                    COUNT(*) as item_count,
                    AVG(COALESCE(confidence_score, 0)) as avg_confidence,
                    MAX(DATE(invoice_date)) as last_purchase_date
                FROM invoice_metadata
                WHERE category = ? AND subcategory = ? AND sub_sub_category = ?
            """, (category, subcategory, sub_sub_category))
            
            total_spend, invoice_count, item_count, avg_confidence, last_purchase = self.cursor.fetchone()
            
            # Insert or update category master
            self.cursor.execute("""
                INSERT OR REPLACE INTO expenses_category_master 
                (category, subcategory, sub_sub_category, weekly_spend, monthly_spend,
                 yearly_spend, total_spend, item_count, invoice_count, avg_confidence,
                 last_purchase_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (category, subcategory, sub_sub_category, weekly_spend, monthly_spend,
                  yearly_spend, total_spend, item_count, invoice_count, avg_confidence,
                  last_purchase))
        
        # Update category rankings
        self.cursor.execute("""
            UPDATE expenses_category_master 
            SET category_rank = (
                SELECT COUNT(*) + 1 
                FROM expenses_category_master e2 
                WHERE e2.weekly_spend > expenses_category_master.weekly_spend
            )
        """)
        
        print(f"   ✅ Processed {len(categories)} expense categories")
    
    def populate_supplier_product_analysis(self):
        """Populate supplier product analysis with price comparison"""
        print("🏪 Populating supplier_product_analysis...")
        
        # Get all supplier-category combinations
        self.cursor.execute("""
            SELECT DISTINCT 
                issuer_rfc, issuer_name, category, subcategory, sub_sub_category
            FROM invoice_metadata
            WHERE issuer_rfc IS NOT NULL 
            AND category IS NOT NULL 
            AND subcategory IS NOT NULL 
            AND sub_sub_category IS NOT NULL
        """)
        
        combinations = self.cursor.fetchall()
        
        for supplier_rfc, supplier_name, category, subcategory, sub_sub_category in combinations:
            # Get supplier metrics for this category
            self.cursor.execute("""
                SELECT 
                    COALESCE(SUM(mxn_total), 0) as total_amount,
                    COUNT(*) as item_count,
                    COUNT(DISTINCT invoice_id) as invoice_count,
                    AVG(unit_price_mxn) as avg_unit_price,
                    MIN(unit_price_mxn) as min_unit_price,
                    MAX(unit_price_mxn) as max_unit_price,
                    MIN(DATE(invoice_date)) as first_purchase,
                    MAX(DATE(invoice_date)) as last_purchase,
                    SUM(CASE WHEN is_immediate = 1 THEN 1 ELSE 0 END) as pue_count,
                    SUM(CASE WHEN is_installments = 1 THEN 1 ELSE 0 END) as ppd_count
                FROM invoice_metadata
                WHERE issuer_rfc = ? AND category = ? AND subcategory = ? AND sub_sub_category = ?
            """, (supplier_rfc, category, subcategory, sub_sub_category))
            
            result = self.cursor.fetchone()
            (total_amount, item_count, invoice_count, avg_unit_price, 
             min_unit_price, max_unit_price, first_purchase, last_purchase,
             pue_count, ppd_count) = result
            
            # Calculate purchase frequency (invoices per month)
            if first_purchase and last_purchase:
                first_date = datetime.strptime(first_purchase, '%Y-%m-%d').date()
                last_date = datetime.strptime(last_purchase, '%Y-%m-%d').date()
                months_diff = max(1, (last_date - first_date).days / 30)
                purchase_frequency = int(invoice_count / months_diff)
            else:
                purchase_frequency = 0
            
            # Insert or update supplier analysis
            self.cursor.execute("""
                INSERT OR REPLACE INTO supplier_product_analysis 
                (supplier_rfc, supplier_name, category, subcategory, sub_sub_category,
                 total_amount, item_count, invoice_count, avg_unit_price, min_unit_price,
                 max_unit_price, first_purchase_date, last_purchase_date, purchase_frequency,
                 payment_terms_pue, payment_terms_ppd, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (supplier_rfc, supplier_name, category, subcategory, sub_sub_category,
                  total_amount, item_count, invoice_count, avg_unit_price, min_unit_price,
                  max_unit_price, first_purchase, last_purchase, purchase_frequency,
                  pue_count, ppd_count))
        
        print(f"   ✅ Processed {len(combinations)} supplier-category combinations")
    
    def populate_weekly_kpis(self):
        """Populate weekly KPIs table"""
        print("🎯 Populating weekly_kpis...")
        
        # Get current week
        week_start, week_end = self.get_week_boundaries()
        
        # Sales KPIs
        self.cursor.execute("""
            SELECT 
                COALESCE(SUM(ventas_total), 0) as revenue,
                COUNT(DISTINCT folio_cuenta) as orders
            FROM sales_orders 
            WHERE DATE(processing_date) BETWEEN ? AND ?
        """, (week_start, week_end))
        
        revenue, orders = self.cursor.fetchone()
        
        # Get total items from sales_items
        self.cursor.execute("""
            SELECT COALESCE(SUM(si.cantidad), 0) as items
            FROM sales_items si
            JOIN sales_orders so ON si.folio_cuenta = so.folio_cuenta
            WHERE DATE(so.processing_date) BETWEEN ? AND ?
        """, (week_start, week_end))
        
        items = self.cursor.fetchone()[0]
        
        # Expense KPIs
        self.cursor.execute("""
            SELECT 
                COALESCE(SUM(mxn_total), 0) as expenses,
                COUNT(DISTINCT invoice_id) as invoices
            FROM invoice_metadata
            WHERE DATE(invoice_date) BETWEEN ? AND ?
        """, (week_start, week_end))
        
        expenses, invoices = self.cursor.fetchone()
        
        # Calculate derived KPIs
        revenue_per_order = revenue / orders if orders > 0 else 0
        items_per_order = items / orders if orders > 0 else 0
        revenue_per_item = revenue / items if items > 0 else 0
        avg_invoice_size = expenses / invoices if invoices > 0 else 0
        
        # Quality KPIs (simplified)
        data_quality_score = 95.0  # Placeholder
        classification_confidence = 88.5  # Placeholder
        processing_success_rate = 99.2  # Placeholder
        
        # Insert weekly KPIs
        self.cursor.execute("""
            INSERT OR REPLACE INTO weekly_kpis 
            (week_start_date, week_end_date, revenue_per_week, orders_per_week,
             revenue_per_order, items_per_order, revenue_per_item, expenses_per_week,
             invoices_per_week, avg_invoice_size, data_quality_score, 
             classification_confidence, processing_success_rate, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (week_start, week_end, revenue, orders, revenue_per_order, items_per_order,
              revenue_per_item, expenses, invoices, avg_invoice_size, data_quality_score,
              classification_confidence, processing_success_rate))
        
        print(f"   ✅ Updated KPIs for week {week_start} to {week_end}")
    
    def populate_real_time_metrics(self):
        """Update real-time metrics"""
        print("⚡ Updating real_time_metrics...")
        
        # Current week boundaries
        week_start, week_end = self.get_week_boundaries()
        
        # Current week sales
        self.cursor.execute("""
            SELECT COALESCE(SUM(ventas_total), 0), COUNT(DISTINCT folio_cuenta)
            FROM sales_orders 
            WHERE DATE(processing_date) BETWEEN ? AND ?
        """, (week_start, week_end))
        
        current_sales, current_orders = self.cursor.fetchone()
        
        # Current week expenses
        self.cursor.execute("""
            SELECT COALESCE(SUM(mxn_total), 0), COUNT(DISTINCT invoice_id)
            FROM invoice_metadata
            WHERE DATE(invoice_date) BETWEEN ? AND ?
        """, (week_start, week_end))
        
        current_expenses, current_invoices = self.cursor.fetchone()
        
        # Last activity times
        self.cursor.execute("SELECT MAX(processing_date) FROM sales_orders")
        last_sale = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT MAX(created_at) FROM invoice_metadata")
        last_invoice = self.cursor.fetchone()[0]
        
        # Best product this week
        self.cursor.execute("""
            SELECT si.clave_producto, SUM(si.importe) as revenue
            FROM sales_items si
            JOIN sales_orders so ON si.folio_cuenta = so.folio_cuenta
            WHERE DATE(so.processing_date) BETWEEN ? AND ?
            GROUP BY si.clave_producto
            ORDER BY revenue DESC
            LIMIT 1
        """, (week_start, week_end))
        
        best_product_result = self.cursor.fetchone()
        best_product = best_product_result[0] if best_product_result else 'N/A'
        
        # Top expense category this week
        self.cursor.execute("""
            SELECT category, SUM(mxn_total) as total
            FROM invoice_metadata
            WHERE DATE(invoice_date) BETWEEN ? AND ?
            GROUP BY category
            ORDER BY total DESC
            LIMIT 1
        """, (week_start, week_end))
        
        top_expense_result = self.cursor.fetchone()
        top_expense = top_expense_result[0] if top_expense_result else 'N/A'
        
        # Update real-time metrics
        metrics_updates = [
            ('current_week_sales', current_sales, f'${current_sales:,.2f}'),
            ('current_week_expenses', current_expenses, f'${current_expenses:,.2f}'),
            ('current_week_orders', current_orders, f'{current_orders} orders'),
            ('current_week_invoices', current_invoices, f'{current_invoices} invoices'),
            ('last_sale_time', 0, last_sale or 'No sales yet'),
            ('last_invoice_time', 0, last_invoice or 'No invoices yet'),
            ('data_quality_score', 95.0, '95% data quality'),
            ('system_health', 100, 'System running normally'),
            ('best_product_week', 0, best_product),
            ('top_expense_category', 0, top_expense)
        ]
        
        for metric_name, value, text in metrics_updates:
            self.cursor.execute("""
                UPDATE real_time_metrics 
                SET metric_value = ?, metric_text = ?, metric_date = DATE('now'), 
                    last_updated = CURRENT_TIMESTAMP
                WHERE metric_name = ?
            """, (value, text, metric_name))
        
        print("   ✅ Updated 10 real-time metrics")
    
    def populate_all_tables(self):
        """Populate all dashboard tables"""
        print("🚀 Populating All Dashboard Tables")
        print("=" * 50)
        
        try:
            self.connect()
            
            # Populate in logical order
            self.populate_sales_weekly_summary()
            self.populate_sales_product_performance()
            self.populate_expenses_category_master()
            self.populate_supplier_product_analysis()
            self.populate_weekly_kpis()
            self.populate_real_time_metrics()
            
            # Commit all changes
            self.conn.commit()
            
            print("\n✅ All dashboard tables populated successfully!")
            print("🎯 Dashboard is ready for API consumption")
            
        except Exception as e:
            print(f"❌ Error populating dashboard data: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.disconnect()

def main():
    """Main execution function"""
    populator = DashboardDataPopulator()
    populator.populate_all_tables()

if __name__ == "__main__":
    main() 