#!/usr/bin/env python3
"""
Simple P62 Categories to Excel Exporter
Reads the P62 categories JSON and exports it to a structured Excel file.

## MAIN FUNCTIONS AVAILABLE:

### Export Functions:
- export_to_excel() -> Creates Excel file with P62 categories
- load_p62_categories() -> Loads JSON data from config file

### Import Functions (for future use):
- import_from_excel(excel_file) -> Will read Excel and update JSON
- update_categories(new_data) -> Will update the P62 categories JSON
- validate_categories(data) -> Will validate category structure

### Usage:
1. Export: python export_p62_to_excel.py
2. Import: Will be implemented for reverse operation

### Output Structure:
- Sheet 1: P62_Categories (Category, Subcategory, Item)
- Sheet 2: Summary (Category overview)
- Sheet 3: Units (Standardized units)
- Sheet 4: Unit_Mappings (Unit code mappings)
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def load_p62_categories():
    """Load P62 categories from JSON file."""
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "config" / "p62_categories.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading P62 categories: {e}")
        return None

def export_to_excel():
    """Export P62 categories to Excel spreadsheet."""
    print("📋 Loading P62 categories...")
    data = load_p62_categories()
    
    if not data:
        return
    
    # Prepare data for Excel export
    rows = []
    categories = data.get('categories', {})
    
    print(f"📊 Processing {len(categories)} categories...")
    
    for category, subcategories in categories.items():
        for subcategory, items in subcategories.items():
            for item in items:
                rows.append({
                    'Category': category,
                    'Subcategory': subcategory,
                    'Item': item
                })
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Output file path
    output_dir = Path(__file__).parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"p62_categories_{timestamp}.xlsx"
    
    # Export to Excel
    print(f"💾 Exporting to: {output_file}")
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Main categories sheet
        df.to_excel(writer, sheet_name='P62_Categories', index=False)
        
        # Summary sheet
        summary_data = []
        for category, subcategories in categories.items():
            total_items = sum(len(items) for items in subcategories.values())
            summary_data.append({
                'Category': category,
                'Subcategories': len(subcategories),
                'Total Items': total_items
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Units and mappings
        if 'standardized_units' in data:
            units_df = pd.DataFrame({
                'Standardized Units': data['standardized_units']
            })
            units_df.to_excel(writer, sheet_name='Units', index=False)
        
        if 'unit_mappings' in data:
            mappings_rows = []
            for unit_type, codes in data['unit_mappings'].items():
                for code in codes:
                    mappings_rows.append({
                        'Unit Type': unit_type,
                        'Code': code
                    })
            mappings_df = pd.DataFrame(mappings_rows)
            mappings_df.to_excel(writer, sheet_name='Unit_Mappings', index=False)
    
    print(f"✅ Excel file created successfully!")
    print(f"   📁 File: {output_file}")
    print(f"   📊 Total rows: {len(rows)}")
    print(f"   📋 Categories: {len(categories)}")
    
    return output_file

def import_from_excel(excel_file):
    """
    Future function: Import categories from Excel back to JSON.
    This will read the Excel file and update the P62 categories.
    """
    # TODO: Implement Excel to JSON import
    print(f"🔄 Import from Excel: {excel_file}")
    print("⚠️  This function will be implemented for reverse operation")
    pass

def update_categories(new_data):
    """
    Future function: Update the P62 categories JSON file.
    This will backup the current file and write new data.
    """
    # TODO: Implement category update with backup
    print("🔄 Update categories function")
    print("⚠️  This function will be implemented for category updates")
    pass

def validate_categories(data):
    """
    Future function: Validate category structure.
    This will ensure data integrity before updates.
    """
    # TODO: Implement validation logic
    print("✅ Validate categories function")
    print("⚠️  This function will be implemented for data validation")
    pass

if __name__ == "__main__":
    print("🚀 P62 Categories Excel Exporter")
    print("=" * 40)
    
    try:
        output_file = export_to_excel()
        if output_file:
            print(f"\n✅ Export completed: {output_file}")
            print("\n📝 Available functions for future use:")
            print("   - import_from_excel(excel_file)")
            print("   - update_categories(new_data)")
            print("   - validate_categories(data)")
    except Exception as e:
        print(f"❌ Export failed: {e}")


