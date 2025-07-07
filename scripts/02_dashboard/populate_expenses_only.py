#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Populate Expenses Dashboard Data Only
Simplified version to populate just expenses tables
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

class ExpensesDataPopulator:
    """Populates expenses dashboard tables only"""
    
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
    
    def populate_expenses_category_master(self):
        """Populate expenses category master table with 7-column structure"""
        print("💰 Populating expenses_category_master...")
        
        # Get all category combinations from invoice_items joined with approved_skus via sku_key
        self.cursor.execute("""
            SELECT DISTINCT a.category, a.subcategory, a.sub_sub_category
            FROM invoice_items ii
            JOIN approved_skus a ON ii.sku_key = a.sku_key
            WHERE a.category IS NOT NULL 
            AND a.subcategory IS NOT NULL 
            AND a.sub_sub_category IS NOT NULL
        """)
        
        categories = self.cursor.fetchall()
        print(f"   Found {len(categories)} category combinations")
        
        for i, (category, subcategory, sub_sub_category) in enumerate(categories):
            if i % 10 == 0:
                print(f"   Processing category {i+1}/{len(categories)}: {category} > {subcategory}")
            
            # Current week
            week_start, week_end = self.get_week_boundaries()
            
            # Weekly spend
            self.cursor.execute("""
                SELECT 
                    COALESCE(SUM(ii.total_amount), 0) as weekly_spend,
                    COUNT(DISTINCT ii.invoice_id) as invoice_count,
                    COUNT(*) as item_count
                FROM invoice_items ii
                JOIN approved_skus a ON ii.sku_key = a.sku_key
                JOIN invoices i ON ii.invoice_id = i.id
                WHERE a.category = ? AND a.subcategory = ? AND a.sub_sub_category = ?
                AND i.invoice_type = 'I'
                AND DATE(i.issue_date) BETWEEN ? AND ?
            """, (category, subcategory, sub_sub_category, week_start, week_end))
            
            weekly_spend, weekly_invoices, weekly_items = self.cursor.fetchone()
            
            # Monthly spend (last 30 days)
            month_start = datetime.now().date() - timedelta(days=30)
            self.cursor.execute("""
                SELECT COALESCE(SUM(ii.total_amount), 0)
                FROM invoice_items ii
                JOIN approved_skus a ON ii.sku_key = a.sku_key
                JOIN invoices i ON ii.invoice_id = i.id
                WHERE a.category = ? AND a.subcategory = ? AND a.sub_sub_category = ?
                AND i.invoice_type = 'I'
                AND DATE(i.issue_date) >= ?
            """, (category, subcategory, sub_sub_category, month_start))
            
            monthly_spend = self.cursor.fetchone()[0]
            
            # Yearly spend (last 365 days)
            year_start = datetime.now().date() - timedelta(days=365)
            self.cursor.execute("""
                SELECT COALESCE(SUM(ii.total_amount), 0)
                FROM invoice_items ii
                JOIN approved_skus a ON ii.sku_key = a.sku_key
                JOIN invoices i ON ii.invoice_id = i.id
                WHERE a.category = ? AND a.subcategory = ? AND a.sub_sub_category = ?
                AND i.invoice_type = 'I'
                AND DATE(i.issue_date) >= ?
            """, (category, subcategory, sub_sub_category, year_start))
            
            yearly_spend = self.cursor.fetchone()[0]
            
            # Total spend and metrics
            self.cursor.execute("""
                SELECT 
                    COALESCE(SUM(ii.total_amount), 0) as total_spend,
                    COUNT(DISTINCT ii.invoice_id) as invoice_count,
                    COUNT(*) as item_count,
                    AVG(COALESCE(a.confidence_score, 0)) as avg_confidence,
                    MAX(DATE(i.issue_date)) as last_purchase_date
                FROM invoice_items ii
                JOIN approved_skus a ON ii.sku_key = a.sku_key
                JOIN invoices i ON ii.invoice_id = i.id
                WHERE a.category = ? AND a.subcategory = ? AND a.sub_sub_category = ?
                AND i.invoice_type = 'I'
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
        print("   Updating category rankings...")
        self.cursor.execute("""
            UPDATE expenses_category_master 
            SET category_rank = (
                SELECT COUNT(*) + 1 
                FROM expenses_category_master e2 
                WHERE e2.total_spend > expenses_category_master.total_spend
            )
        """)
        
        print(f"   ✅ Processed {len(categories)} expense categories")
    
    def populate_supplier_product_analysis(self):
        """Populate supplier product analysis with price comparison"""
        print("🏪 Populating supplier_product_analysis...")
        
        # Get all supplier-category combinations from invoice_items + approved_skus via sku_key
        self.cursor.execute("""
            SELECT DISTINCT 
                i.issuer_rfc, 
                i.issuer_name,
                a.category,
                a.subcategory,
                a.sub_sub_category
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            JOIN approved_skus a ON ii.sku_key = a.sku_key
            WHERE i.issuer_rfc IS NOT NULL 
            AND i.issuer_name IS NOT NULL
            AND i.invoice_type = 'I'
            AND a.category IS NOT NULL
            AND a.subcategory IS NOT NULL
            AND a.sub_sub_category IS NOT NULL
        """)
        
        combinations = self.cursor.fetchall()
        print(f"   Found {len(combinations)} supplier-category combinations")
        
        for i, (supplier_rfc, supplier_name, category, subcategory, sub_sub_category) in enumerate(combinations):
            if i % 20 == 0:
                print(f"   Processing combination {i+1}/{len(combinations)}: {supplier_rfc}")
            
            # Get supplier metrics for this category using correct table relationships
            self.cursor.execute("""
                SELECT 
                    COALESCE(SUM(ii.total_amount), 0) as total_amount,
                    COUNT(*) as item_count,
                    COUNT(DISTINCT ii.invoice_id) as invoice_count,
                    AVG(COALESCE(ii.unit_price, 0)) as avg_unit_price,
                    MIN(COALESCE(ii.unit_price, 0)) as min_unit_price,
                    MAX(COALESCE(ii.unit_price, 0)) as max_unit_price,
                    MIN(DATE(i.issue_date)) as first_purchase,
                    MAX(DATE(i.issue_date)) as last_purchase,
                    SUM(CASE WHEN im.is_immediate = 1 THEN 1 ELSE 0 END) as pue_count,
                    SUM(CASE WHEN im.is_installments = 1 THEN 1 ELSE 0 END) as ppd_count
                FROM invoice_items ii
                JOIN invoices i ON ii.invoice_id = i.id
                JOIN approved_skus a ON ii.sku_key = a.sku_key
                LEFT JOIN invoice_metadata im ON i.id = im.invoice_id
                WHERE i.issuer_rfc = ? 
                AND i.invoice_type = 'I'
                AND a.category = ?
                AND a.subcategory = ?
                AND a.sub_sub_category = ?
            """, (supplier_rfc, category, subcategory, sub_sub_category))
            
            result = self.cursor.fetchone()
            (total_amount, item_count, invoice_count, avg_unit_price, 
             min_unit_price, max_unit_price, first_purchase, last_purchase,
             pue_count, ppd_count) = result
            
            # Calculate purchase frequency (invoices per month)
            if first_purchase and last_purchase:
                try:
                    first_date = datetime.strptime(first_purchase, '%Y-%m-%d').date()
                    last_date = datetime.strptime(last_purchase, '%Y-%m-%d').date()
                    months_diff = max(1, (last_date - first_date).days / 30)
                    purchase_frequency = int(invoice_count / months_diff)
                except:
                    purchase_frequency = 0
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
    
    def populate_expenses_weekly_summary(self):
        """Populate expenses weekly summary"""
        print("📈 Populating expenses_weekly_summary...")
        
        # Get current week
        week_start, week_end = self.get_week_boundaries()
        print(f"   Processing week {week_start} to {week_end}")
        
        # Weekly expenses metrics
        self.cursor.execute("""
            SELECT 
                COALESCE(SUM(ii.total_amount), 0) as total_expenses,
                COUNT(DISTINCT i.id) as total_invoices,
                COUNT(*) as total_line_items,
                COUNT(DISTINCT i.issuer_rfc) as unique_suppliers,
                SUM(CASE WHEN im.is_immediate = 1 THEN 1 ELSE 0 END) as pue_invoices,
                SUM(CASE WHEN im.is_installments = 1 THEN 1 ELSE 0 END) as ppd_invoices
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            LEFT JOIN invoice_metadata im ON i.id = im.invoice_id
            WHERE i.invoice_type = 'I'
            AND DATE(i.issue_date) BETWEEN ? AND ?
        """, (week_start, week_end))
        
        result = self.cursor.fetchone()
        (total_expenses, total_invoices, total_line_items, unique_suppliers,
         pue_invoices, ppd_invoices) = result
        
        # Get top category for the week
        self.cursor.execute("""
            SELECT 
                a.category,
                SUM(ii.total_amount) as category_amount
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            JOIN approved_skus a ON ii.sku_key = a.sku_key
            WHERE i.invoice_type = 'I'
            AND DATE(i.issue_date) BETWEEN ? AND ?
            AND a.category IS NOT NULL
            GROUP BY a.category
            ORDER BY category_amount DESC
            LIMIT 1
        """, (week_start, week_end))
        
        top_category_result = self.cursor.fetchone()
        top_category = top_category_result[0] if top_category_result else None
        top_category_amount = top_category_result[1] if top_category_result else 0
        
        # Get top supplier for the week
        self.cursor.execute("""
            SELECT i.issuer_rfc, SUM(ii.total_amount) as supplier_amount
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            WHERE i.invoice_type = 'I'
            AND DATE(i.issue_date) BETWEEN ? AND ?
            GROUP BY i.issuer_rfc
            ORDER BY supplier_amount DESC
            LIMIT 1
        """, (week_start, week_end))
        
        top_supplier_result = self.cursor.fetchone()
        top_supplier_rfc = top_supplier_result[0] if top_supplier_result else None
        top_supplier_amount = top_supplier_result[1] if top_supplier_result else 0
        
        # Calculate derived metrics
        avg_invoice_amount = total_expenses / total_invoices if total_invoices > 0 else 0
        
        print(f"     Expenses: ${total_expenses:,.2f}, Invoices: {total_invoices}, Suppliers: {unique_suppliers}")
        
        # Insert weekly summary
        self.cursor.execute("""
            INSERT OR REPLACE INTO expenses_weekly_summary 
            (week_start_date, week_end_date, total_expenses, total_invoices, 
             total_line_items, avg_invoice_amount, unique_suppliers, top_category,
             top_category_amount, top_supplier_rfc, top_supplier_amount, 
             pue_invoices, ppd_invoices, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (week_start, week_end, total_expenses, total_invoices, total_line_items,
              avg_invoice_amount, unique_suppliers, top_category, top_category_amount,
              top_supplier_rfc, top_supplier_amount, pue_invoices, ppd_invoices))
        
        print(f"   ✅ Processed expenses weekly summary")
    
    def populate_expenses_data(self):
        """Populate expenses dashboard tables"""
        print("🚀 Populating Expenses Dashboard Data")
        print("=" * 50)
        
        try:
            self.connect()
            
            # Populate expenses tables
            self.populate_expenses_category_master()
            self.populate_supplier_product_analysis()
            self.populate_expenses_weekly_summary()
            
            # Commit all changes
            self.conn.commit()
            
            print("\n✅ Expenses dashboard data populated successfully!")
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
    populator = ExpensesDataPopulator()
    populator.populate_expenses_data()

if __name__ == "__main__":
    main() 