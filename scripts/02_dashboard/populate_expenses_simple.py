#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Populate Expenses Dashboard Data - Simplified Version
Works with actual database structure without complex joins
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

class SimpleExpensesPopulator:
    """Populates expenses dashboard tables - simplified version"""
    
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
    
    def populate_basic_categories(self):
        """Populate basic category data from approved_skus"""
        print("💰 Populating expenses_category_master (basic version)...")
        
        # Get all categories from approved_skus
        self.cursor.execute("""
            SELECT DISTINCT category, subcategory, sub_sub_category
            FROM approved_skus
            WHERE category IS NOT NULL 
            AND subcategory IS NOT NULL 
            AND sub_sub_category IS NOT NULL
        """)
        
        categories = self.cursor.fetchall()
        print(f"   Found {len(categories)} category combinations in approved_skus")
        
        for i, (category, subcategory, sub_sub_category) in enumerate(categories):
            if i % 10 == 0:
                print(f"   Processing category {i+1}/{len(categories)}: {category}")
            
            # For now, just populate with basic structure and zero values
            # In the future, this will be enhanced with actual spend calculations
            
            # Insert basic category structure
            self.cursor.execute("""
                INSERT OR REPLACE INTO expenses_category_master 
                (category, subcategory, sub_sub_category, weekly_spend, monthly_spend,
                 yearly_spend, total_spend, item_count, invoice_count, updated_at)
                VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, CURRENT_TIMESTAMP)
            """, (category, subcategory, sub_sub_category))
        
        print(f"   ✅ Created structure for {len(categories)} expense categories")
    
    def populate_basic_suppliers(self):
        """Populate basic supplier data"""
        print("🏪 Populating supplier_product_analysis (basic version)...")
        
        # Get unique suppliers from invoices
        self.cursor.execute("""
            SELECT DISTINCT issuer_rfc, issuer_name
            FROM invoices
            WHERE issuer_rfc IS NOT NULL
        """)
        
        suppliers = self.cursor.fetchall()
        print(f"   Found {len(suppliers)} suppliers")
        
        # Get basic categories
        self.cursor.execute("""
            SELECT DISTINCT category, subcategory, sub_sub_category
            FROM approved_skus
            LIMIT 5
        """)
        
        categories = self.cursor.fetchall()
        
        # Create basic supplier-category combinations (sample)
        for supplier_rfc, supplier_name in suppliers[:10]:  # Limit to first 10 suppliers
            for category, subcategory, sub_sub_category in categories[:3]:  # First 3 categories
                self.cursor.execute("""
                    INSERT OR REPLACE INTO supplier_product_analysis 
                    (supplier_rfc, supplier_name, category, subcategory, sub_sub_category,
                     total_amount, item_count, invoice_count, avg_unit_price, updated_at)
                    VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, CURRENT_TIMESTAMP)
                """, (supplier_rfc, supplier_name, category, subcategory, sub_sub_category))
        
        print(f"   ✅ Created basic supplier analysis structure")
    
    def populate_expenses_weekly_summary(self):
        """Populate expenses weekly summary with actual invoice data"""
        print("📈 Populating expenses_weekly_summary...")
        
        # Get current week
        week_start, week_end = self.get_week_boundaries()
        print(f"   Processing week {week_start} to {week_end}")
        
        # Get basic invoice metrics for the week
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_invoices,
                COUNT(DISTINCT issuer_rfc) as unique_suppliers,
                COALESCE(AVG(total_amount), 0) as avg_invoice_amount,
                COALESCE(SUM(total_amount), 0) as total_expenses
            FROM invoices
            WHERE DATE(issue_date) BETWEEN ? AND ?
        """, (week_start, week_end))
        
        result = self.cursor.fetchone()
        total_invoices, unique_suppliers, avg_invoice_amount, total_expenses = result
        
        # Get line items count
        self.cursor.execute("""
            SELECT COUNT(*) 
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            WHERE DATE(i.issue_date) BETWEEN ? AND ?
        """, (week_start, week_end))
        
        total_line_items = self.cursor.fetchone()[0]
        
        # Get top supplier for the week
        self.cursor.execute("""
            SELECT issuer_rfc, SUM(total_amount) as supplier_total
            FROM invoices
            WHERE DATE(issue_date) BETWEEN ? AND ?
            GROUP BY issuer_rfc
            ORDER BY supplier_total DESC
            LIMIT 1
        """, (week_start, week_end))
        
        top_supplier_result = self.cursor.fetchone()
        top_supplier_rfc = top_supplier_result[0] if top_supplier_result else None
        top_supplier_amount = top_supplier_result[1] if top_supplier_result else 0
        
        print(f"     Expenses: ${total_expenses:,.2f}, Invoices: {total_invoices}, Suppliers: {unique_suppliers}")
        
        # Insert weekly summary
        self.cursor.execute("""
            INSERT OR REPLACE INTO expenses_weekly_summary 
            (week_start_date, week_end_date, total_expenses, total_invoices, 
             total_line_items, avg_invoice_amount, unique_suppliers, 
             top_supplier_rfc, top_supplier_amount, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (week_start, week_end, total_expenses, total_invoices, total_line_items,
              avg_invoice_amount, unique_suppliers, top_supplier_rfc, top_supplier_amount))
        
        print(f"   ✅ Processed expenses weekly summary")
    
    def update_real_time_metrics(self):
        """Update real-time metrics with expense data"""
        print("⚡ Updating real-time metrics...")
        
        # Current week expenses
        week_start, week_end = self.get_week_boundaries()
        
        self.cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0), COUNT(*)
            FROM invoices
            WHERE DATE(issue_date) BETWEEN ? AND ?
        """, (week_start, week_end))
        
        current_expenses, current_invoices = self.cursor.fetchone()
        
        # Update metrics
        self.cursor.execute("""
            UPDATE real_time_metrics 
            SET metric_value = ?, metric_text = ?, last_updated = CURRENT_TIMESTAMP
            WHERE metric_name = 'current_week_expenses'
        """, (current_expenses, f"${current_expenses:,.2f}"))
        
        self.cursor.execute("""
            UPDATE real_time_metrics 
            SET metric_value = ?, metric_text = ?, last_updated = CURRENT_TIMESTAMP
            WHERE metric_name = 'current_week_invoices'
        """, (current_invoices, f"{current_invoices} invoices"))
        
        print(f"   ✅ Updated real-time expense metrics")
    
    def populate_expenses_data(self):
        """Populate expenses dashboard tables - simplified version"""
        print("🚀 Populating Expenses Dashboard Data (Simplified)")
        print("=" * 60)
        
        try:
            self.connect()
            
            # Populate basic expense structure
            self.populate_basic_categories()
            self.populate_basic_suppliers()
            self.populate_expenses_weekly_summary()
            self.update_real_time_metrics()
            
            # Commit all changes
            self.conn.commit()
            
            print("\n✅ Expenses dashboard data populated successfully!")
            print("📋 Note: This is a simplified version with basic structure")
            print("🎯 Expenses data ready for API consumption")
            
        except Exception as e:
            print(f"❌ Error populating expenses data: {e}")
            import traceback
            traceback.print_exc()
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.disconnect()

def main():
    """Main execution function"""
    populator = SimpleExpensesPopulator()
    populator.populate_expenses_data()

if __name__ == "__main__":
    main() 