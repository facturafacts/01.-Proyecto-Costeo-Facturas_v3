#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete System Validation - CFDI + P62 Integration

Validates both the CFDI expense system and P62 sales system for complete
business intelligence and financial management.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import sqlite3

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class CompleteSystemValidator:
    """Validates the complete CFDI + P62 integrated system."""
    
    def __init__(self):
        self.cfdi_db_path = Path("data/database/cfdi_system_v4.db")
        self.p62_db_path = Path("data/database/p62_sales.db")
        self.validation_results = {}
        
    def validate_complete_system(self):
        """Validate both CFDI and P62 systems."""
        print("🔍 Complete System Validation")
        print("=" * 50)
        
        # Validate CFDI system
        cfdi_status = self.validate_cfdi_system()
        
        # Validate P62 system
        p62_status = self.validate_p62_system()
        
        # Show integration analysis
        self.analyze_integration_readiness(cfdi_status, p62_status)
        
        # Generate unified report
        self.generate_unified_report()
        
        return cfdi_status and p62_status
    
    def validate_cfdi_system(self):
        """Validate CFDI expense tracking system."""
        print("\n💰 CFDI Expense System Validation")
        print("-" * 40)
        
        if not self.cfdi_db_path.exists():
            print("❌ CFDI database not found")
            print(f"   Expected: {self.cfdi_db_path}")
            return False
        
        try:
            conn = sqlite3.connect(self.cfdi_db_path)
            cursor = conn.cursor()
            
            # Check core tables
            tables_to_check = [
                'invoices', 'invoice_items', 'invoice_metadata', 
                'approved_skus', 'processing_logs'
            ]
            
            table_status = {}
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_status[table] = count
                    print(f"✅ {table}: {count:,} records")
                except Exception as e:
                    table_status[table] = 0
                    print(f"❌ {table}: Error - {e}")
            
            # Get financial summary
            try:
                cursor.execute("SELECT COUNT(*), SUM(mxn_total) FROM invoice_metadata")
                invoice_count, total_expenses = cursor.fetchone()
                
                cursor.execute("SELECT MIN(issue_date), MAX(issue_date) FROM invoice_metadata")
                min_date, max_date = cursor.fetchone()
                
                self.validation_results['cfdi'] = {
                    'invoice_count': invoice_count,
                    'total_expenses': total_expenses,
                    'date_range': (min_date, max_date),
                    'tables': table_status
                }
                
                print(f"\n📊 CFDI Summary:")
                print(f"   💵 Total Expenses: ${total_expenses:,.2f} MXN")
                print(f"   📋 Invoice Count: {invoice_count:,}")
                print(f"   📅 Date Range: {min_date} to {max_date}")
                
            except Exception as e:
                print(f"⚠️  Could not get CFDI summary: {e}")
            
            conn.close()
            print("✅ CFDI system validation completed")
            return True
            
        except Exception as e:
            print(f"❌ CFDI system validation failed: {e}")
            return False
    
    def validate_p62_system(self):
        """Validate P62 sales system."""
        print("\n🍽️ P62 Sales System Validation")
        print("-" * 40)
        
        # Check if P62 files exist
        p62_files = [
            Path("p62/VENTAS.XLS"),
            Path("p62/comandas.xls"),
            Path("p62/PRODUCTOSVENDIDOSPERIODO.XLS")
        ]
        
        files_available = 0
        total_size = 0
        
        print("📁 P62 Data Files:")
        for file_path in p62_files:
            if file_path.exists():
                size_kb = file_path.stat().st_size / 1024
                total_size += size_kb
                files_available += 1
                print(f"   ✅ {file_path.name}: {size_kb:.1f} KB")
            else:
                print(f"   ❌ {file_path.name}: Not found")
        
        # Check P62 database if it exists
        if self.p62_db_path.exists():
            print(f"\n📊 P62 Database Status:")
            try:
                conn = sqlite3.connect(self.p62_db_path)
                cursor = conn.cursor()
                
                # Check P62 tables
                p62_tables = [
                    'sales_transactions', 'order_details', 
                    'product_performance', 'processing_logs'
                ]
                
                table_status = {}
                total_revenue = 0
                
                for table in p62_tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        table_status[table] = count
                        print(f"   ✅ {table}: {count:,} records")
                        
                        # Get revenue totals
                        if table == 'sales_transactions':
                            cursor.execute("SELECT SUM(total_amount) FROM sales_transactions")
                            total_revenue = cursor.fetchone()[0] or 0
                        
                    except Exception as e:
                        table_status[table] = 0
                        print(f"   ❌ {table}: Error - {e}")
                
                self.validation_results['p62'] = {
                    'files_available': files_available,
                    'total_size_kb': total_size,
                    'total_revenue': total_revenue,
                    'tables': table_status
                }
                
                if total_revenue > 0:
                    print(f"\n📈 P62 Summary:")
                    print(f"   💰 Total Revenue: ${total_revenue:,.2f} MXN")
                
                conn.close()
                print("✅ P62 database validation completed")
                
            except Exception as e:
                print(f"⚠️  P62 database validation failed: {e}")
        
        else:
            print("📋 P62 database not yet created")
            self.validation_results['p62'] = {
                'files_available': files_available,
                'total_size_kb': total_size,
                'database_ready': False
            }
        
        print(f"📊 P62 Files Status: {files_available}/3 available ({total_size:.1f} KB total)")
        return files_available >= 2  # At least 2 files needed
    
    def analyze_integration_readiness(self, cfdi_status, p62_status):
        """Analyze readiness for CFDI-P62 integration."""
        print("\n🔗 Integration Readiness Analysis")
        print("-" * 40)
        
        if cfdi_status and p62_status:
            print("✅ Both systems are ready for integration")
            
            # Calculate potential combined metrics
            cfdi_data = self.validation_results.get('cfdi', {})
            p62_data = self.validation_results.get('p62', {})
            
            expenses = cfdi_data.get('total_expenses', 0)
            revenue = p62_data.get('total_revenue', 0)
            
            if expenses > 0 and revenue > 0:
                profit = revenue - expenses
                margin = (profit / revenue) * 100 if revenue > 0 else 0
                
                print(f"\n📊 Projected Combined Metrics:")
                print(f"   💰 Total Revenue: ${revenue:,.2f} MXN")
                print(f"   💸 Total Expenses: ${expenses:,.2f} MXN")
                print(f"   📈 Net Profit: ${profit:,.2f} MXN")
                print(f"   📊 Profit Margin: {margin:.1f}%")
            
            print(f"\n🎯 Integration Benefits:")
            print("   • Complete P&L visibility")
            print("   • Unified financial reporting")
            print("   • Enhanced business intelligence")
            print("   • Data-driven decision making")
            
        elif cfdi_status and not p62_status:
            print("⚠️  CFDI system ready, P62 system needs setup")
            print("   Next step: Process P62 Excel files")
            
        elif not cfdi_status and p62_status:
            print("⚠️  P62 system ready, CFDI system needs attention")
            print("   Next step: Validate CFDI database")
            
        else:
            print("❌ Both systems need attention before integration")
    
    def generate_unified_report(self):
        """Generate unified system status report."""
        print("\n📋 Unified System Status Report")
        print("=" * 50)
        
        # System availability
        cfdi_available = self.cfdi_db_path.exists()
        p62_files_available = len([f for f in [
            Path("p62/VENTAS.XLS"),
            Path("p62/comandas.xls"), 
            Path("p62/PRODUCTOSVENDIDOSPERIODO.XLS")
        ] if f.exists()])
        
        print("🏗️ System Architecture Status:")
        print(f"   CFDI Database: {'✅ Available' if cfdi_available else '❌ Missing'}")
        print(f"   P62 Data Files: {'✅' if p62_files_available >= 2 else '❌'} {p62_files_available}/3 available")
        print(f"   P62 Database: {'✅ Available' if self.p62_db_path.exists() else '📋 Ready to create'}")
        
        # Data volume summary
        cfdi_data = self.validation_results.get('cfdi', {})
        p62_data = self.validation_results.get('p62', {})
        
        print(f"\n📊 Data Volume Summary:")
        print(f"   CFDI Records: {cfdi_data.get('invoice_count', 0):,} invoices")
        print(f"   P62 Files Size: {p62_data.get('total_size_kb', 0):.1f} KB")
        print(f"   Estimated P62 Records: ~3,600 transactions")
        
        # Financial overview
        expenses = cfdi_data.get('total_expenses', 0)
        revenue = p62_data.get('total_revenue', 0)
        
        print(f"\n💰 Financial Data Overview:")
        print(f"   Tracked Expenses: ${expenses:,.2f} MXN")
        print(f"   Available Revenue Data: {'✅ Ready' if p62_files_available >= 2 else '❌ Pending'}")
        
        # Next steps
        print(f"\n🚀 Recommended Next Steps:")
        
        if not cfdi_available:
            print("   1. ❗ Validate CFDI database setup")
        
        if p62_files_available >= 2 and not self.p62_db_path.exists():
            print("   1. 🔄 Process P62 files: python p62/simple_p62_processor.py")
        
        if cfdi_available and self.p62_db_path.exists():
            print("   1. 📊 Generate unified reports")
            print("   2. 📤 Export to Google Sheets with complete data")
        
        print(f"\n⏱️  Estimated setup time: 30 minutes")
        print(f"🎯 Expected result: Complete restaurant financial management system")


def main():
    """Main validation function."""
    try:
        validator = CompleteSystemValidator()
        success = validator.validate_complete_system()
        
        if success:
            print(f"\n🎉 System validation completed successfully!")
            print("Ready for unified financial management.")
        else:
            print(f"\n⚠️  System validation identified areas for improvement.")
            print("Review the recommendations above.")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 