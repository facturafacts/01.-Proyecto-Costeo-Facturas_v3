#!/usr/bin/env python3
"""
Quick check of approved_skus table contents
"""

import sys
import os
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from data.database import DatabaseManager
from data.models import ApprovedSku

def main():
    """Check approved_skus table contents."""
    print("🔍 CHECKING APPROVED_SKUS TABLE")
    print("=" * 50)
    
    try:
        db_manager = DatabaseManager()
        
        with db_manager.get_session() as session:
            # Count total approved SKUs
            total_count = session.query(ApprovedSku).count()
            print(f"📊 Total Approved SKUs: {total_count}")
            print()
            
            if total_count == 0:
                print("❌ No approved SKUs found in the table")
                return
            
            # Show first 10 entries
            print("📋 First 10 Approved SKUs:")
            print("-" * 80)
            approved_skus = session.query(ApprovedSku).limit(10).all()
            
            for i, sku in enumerate(approved_skus, 1):
                print(f"{i:2d}. SKU Key: {sku.sku_key}")
                print(f"    Description: {sku.normalized_description}")
                print(f"    Category: {sku.category} → {sku.subcategory} → {sku.sub_sub_category}")
                print(f"    Unit: {sku.standardized_unit}")
                print(f"    Approved: {sku.created_at}")
                print()
            
            # Show categories breakdown
            print("📊 BREAKDOWN BY CATEGORY:")
            print("-" * 40)
            from sqlalchemy import func
            category_query = session.query(
                ApprovedSku.category,
                func.count(ApprovedSku.id).label('count')
            ).group_by(ApprovedSku.category).all()
            
            for category, count in category_query:
                print(f"  {category}: {count} SKUs")
            
    except Exception as e:
        print(f"❌ Error checking approved_skus table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main() 