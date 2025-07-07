#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Populate Sales Dashboard Data Only
Simplified version to populate just sales tables first
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

class SalesDataPopulator:
    """Populates sales dashboard tables only"""
    
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
                DATE(fecha_cierre, 'weekday 0', '-6 days') as week_start,
                DATE(fecha_cierre, 'weekday 0') as week_end
            FROM sales_orders 
            WHERE fecha_cierre IS NOT NULL
            ORDER BY week_start DESC
        """)
        
        weeks = self.cursor.fetchall()
        print(f"   Found {len(weeks)} weeks of data")
        
        for week_start, week_end in weeks:
            print(f"   Processing week {week_start} to {week_end}")
            
            # Calculate weekly metrics
            self.cursor.execute("""
                SELECT 
                    COUNT(DISTINCT folio_cuenta) as total_orders,
                    COALESCE(SUM(ventas_total), 0) as total_revenue
                FROM sales_orders 
                WHERE DATE(fecha_cierre) BETWEEN ? AND ?
            """, (week_start, week_end))
            
            orders, revenue = self.cursor.fetchone()
            
            # Get total items sold from sales_items table
            self.cursor.execute("""
                SELECT COALESCE(SUM(si.cantidad), 0) as total_items_sold
                FROM sales_items si
                JOIN sales_orders so ON si.folio_cuenta = so.folio_cuenta
                WHERE DATE(so.fecha_cierre) BETWEEN ? AND ?
            """, (week_start, week_end))
            
            items = self.cursor.fetchone()[0]
            
            # Get top product for the week
            self.cursor.execute("""
                SELECT si.clave_producto, SUM(si.importe) as product_revenue
                FROM sales_items si
                JOIN sales_orders so ON si.folio_cuenta = so.folio_cuenta
                WHERE DATE(so.fecha_cierre) BETWEEN ? AND ?
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
                WHERE DATE(so.fecha_cierre) BETWEEN ? AND ?
            """, (week_start, week_end))
            
            unique_products = self.cursor.fetchone()[0]
            
            # Calculate derived metrics
            revenue_per_order = revenue / orders if orders > 0 else 0
            avg_order_value = revenue_per_order  # Same as revenue_per_order
            
            print(f"     Revenue: ${revenue:,.2f}, Orders: {orders}, Items: {items}")
            
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
            ORDER BY clave_producto
        """)
        
        products = self.cursor.fetchall()
        print(f"   Found {len(products)} products")
        
        for i, (product_code, description) in enumerate(products):
            if i % 50 == 0:
                print(f"   Processing product {i+1}/{len(products)}: {product_code}")
            
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
                AND DATE(so.fecha_cierre) BETWEEN ? AND ?
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
                AND DATE(so.fecha_cierre) >= ?
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
                AND DATE(so.fecha_cierre) >= ?
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
        print("   Updating rankings...")
        self.cursor.execute("""
            UPDATE sales_product_performance 
            SET revenue_rank = (
                SELECT COUNT(*) + 1 
                FROM sales_product_performance p2 
                WHERE p2.total_revenue > sales_product_performance.total_revenue
            )
        """)
        
        self.cursor.execute("""
            UPDATE sales_product_performance 
            SET quantity_rank = (
                SELECT COUNT(*) + 1 
                FROM sales_product_performance p2 
                WHERE p2.total_quantity > sales_product_performance.total_quantity
            )
        """)
        
        print(f"   ✅ Processed {len(products)} products")
    
    def populate_sales_data(self):
        """Populate sales dashboard tables"""
        print("🚀 Populating Sales Dashboard Data")
        print("=" * 50)
        
        try:
            self.connect()
            
            # Populate sales tables
            self.populate_sales_weekly_summary()
            self.populate_sales_product_performance()
            
            # Commit all changes
            self.conn.commit()
            
            print("\n✅ Sales dashboard data populated successfully!")
            print("🎯 Sales data ready for API consumption")
            
        except Exception as e:
            print(f"❌ Error populating sales data: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.disconnect()

def main():
    """Main execution function"""
    populator = SalesDataPopulator()
    populator.populate_sales_data()

if __name__ == "__main__":
    main() 