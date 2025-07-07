#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update All Dashboard Data
Master script to update all dashboard tables in the correct order

This script should be run periodically (daily/weekly) to refresh dashboard data
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

def run_script(script_name, description):
    """Run a script and report results"""
    print(f"\n🔄 {description}")
    print("-" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, f"scripts/02_dashboard/{script_name}"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            # Show last few lines of output
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines[-3:]:
                if line.strip():
                    print(f"   {line}")
        else:
            print(f"❌ {description} failed")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False
    
    return True

def main():
    """Update all dashboard data"""
    print("🚀 CFDI Dashboard Data Update")
    print("=" * 60)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # List of scripts to run in order
    update_scripts = [
        ("populate_sales_only.py", "Sales Dashboard Data"),
        ("populate_expenses_simple.py", "Expenses Dashboard Data"),
        ("populate_kpis.py", "KPIs and Final Setup"),
        ("test_dashboard_queries.py", "Dashboard Data Validation")
    ]
    
    success_count = 0
    
    for script_name, description in update_scripts:
        if run_script(script_name, description):
            success_count += 1
        else:
            print(f"\n⚠️  Stopping update process due to failure in {description}")
            break
    
    print(f"\n📊 Update Summary")
    print("=" * 30)
    print(f"✅ Successful: {success_count}/{len(update_scripts)} scripts")
    print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success_count == len(update_scripts):
        print("\n🎯 Dashboard Update Status: SUCCESS")
        print("🚀 All data refreshed and ready for API consumption")
        print("\n📋 Dashboard Tables Updated:")
        print("   • sales_weekly_summary")
        print("   • sales_product_performance")
        print("   • expenses_category_master")
        print("   • supplier_product_analysis")
        print("   • expenses_weekly_summary")
        print("   • weekly_kpis")
        print("   • real_time_metrics")
        
        print("\n🔗 Next Steps:")
        print("   1. API endpoints can now query dashboard tables")
        print("   2. Set up scheduled updates (daily/weekly)")
        print("   3. Monitor dashboard performance")
        
    else:
        print("\n❌ Dashboard Update Status: PARTIAL FAILURE")
        print("   Please check the error messages above")

if __name__ == "__main__":
    main() 