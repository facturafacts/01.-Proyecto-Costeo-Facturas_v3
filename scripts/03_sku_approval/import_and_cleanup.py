#!/usr/bin/env python3
"""
IMPORT APPROVED SKUs AND CLEANUP SCRIPT

This script:
1. Finds the latest Excel approval file
2. Imports approved SKU classifications
3. Cleans up the approval folder automatically
4. Provides detailed feedback on the process
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import glob
from datetime import datetime
import shutil

# Add src to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "src"))

# Import the excel_approval module from the same directory
import sys
sys.path.append(str(Path(__file__).parent))
from excel_approval import ExcelSkuApprovalManager

class ImportAndCleanupManager:
    """Manages the import process and cleanup of approval files."""
    
    def __init__(self):
        """Initialize the manager."""
        self.approval_dir = Path("data/approval")
        self.excel_manager = ExcelSkuApprovalManager()
        
        print("🎯 IMPORT & CLEANUP MANAGER INITIALIZED")
        print(f"   📁 Approval directory: {self.approval_dir}")
    
    def find_latest_excel_file(self) -> Optional[Path]:
        """Find the most recent Excel approval file."""
        try:
            # Look for Excel files with the expected pattern (both .xlsx and .xlsm)
            xlsx_pattern = str(self.approval_dir / "sku_approval_*.xlsx")
            xlsm_pattern = str(self.approval_dir / "sku_approval_*.xlsm")
            
            xlsx_files = glob.glob(xlsx_pattern)
            xlsm_files = glob.glob(xlsm_pattern)
            
            # Combine both file types
            excel_files = xlsx_files + xlsm_files
            
            if not excel_files:
                print("❌ No Excel approval files found in approval directory")
                print("   Looking for: sku_approval_*.xlsx or sku_approval_*.xlsm")
                return None
            
            # Sort by modification time (most recent first)
            excel_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            latest_file = Path(excel_files[0])
            
            print(f"📄 Found latest Excel file: {latest_file.name}")
            print(f"   📅 Modified: {datetime.fromtimestamp(os.path.getmtime(latest_file))}")
            print(f"   📏 Size: {latest_file.stat().st_size / 1024:.1f} KB")
            
            return latest_file
            
        except Exception as e:
            print(f"❌ Error finding Excel files: {e}")
            return None
    
    def import_approvals(self, excel_path: Path) -> Dict[str, Any]:
        """Import approved SKUs from Excel file."""
        print(f"\n📥 IMPORTING APPROVALS FROM: {excel_path.name}")
        print("=" * 60)
        
        try:
            # Use the existing import functionality
            stats = self.excel_manager.import_approved_skus(str(excel_path))
            
            print(f"\n✅ IMPORT SUMMARY:")
            print(f"   📊 Total rows processed: {stats['total_rows']}")
            print(f"   ✅ Successfully imported: {stats['successful_imports']}")
            print(f"   ❌ Errors encountered: {len(stats['errors'])}")
            
            if stats['errors']:
                print(f"\n⚠️  IMPORT ERRORS:")
                for error in stats['errors'][:5]:  # Show first 5 errors
                    print(f"   • {error}")
                if len(stats['errors']) > 5:
                    print(f"   • ... and {len(stats['errors']) - 5} more errors")
            
            return stats
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            raise
    
    def cleanup_approval_folder(self) -> Dict[str, int]:
        """Clean up all files in the approval folder."""
        print(f"\n🧹 CLEANING UP APPROVAL FOLDER")
        print("=" * 40)
        
        cleanup_stats = {
            'files_removed': 0,
            'folders_removed': 0,
            'errors': 0
        }
        
        try:
            if not self.approval_dir.exists():
                print("❌ Approval directory doesn't exist")
                return cleanup_stats
            
            # Remove all files and subdirectories
            for item in self.approval_dir.iterdir():
                try:
                    if item.is_file():
                        print(f"   🗑️  Removing file: {item.name}")
                        item.unlink()
                        cleanup_stats['files_removed'] += 1
                    elif item.is_dir():
                        print(f"   🗑️  Removing folder: {item.name}")
                        shutil.rmtree(item)
                        cleanup_stats['folders_removed'] += 1
                except Exception as e:
                    print(f"   ❌ Error removing {item.name}: {e}")
                    cleanup_stats['errors'] += 1
            
            print(f"\n✅ CLEANUP SUMMARY:")
            print(f"   📄 Files removed: {cleanup_stats['files_removed']}")
            print(f"   📁 Folders removed: {cleanup_stats['folders_removed']}")
            print(f"   ❌ Errors: {cleanup_stats['errors']}")
            
            return cleanup_stats
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            cleanup_stats['errors'] += 1
            return cleanup_stats
    
    def run_full_process(self) -> bool:
        """Run the complete import and cleanup process."""
        print("🚀 STARTING FULL IMPORT & CLEANUP PROCESS")
        print("=" * 50)
        
        try:
            # Step 1: Find the latest Excel file
            excel_file = self.find_latest_excel_file()
            if not excel_file:
                print("❌ No Excel file found to import")
                return False
            
            # Step 2: Import the approvals
            import_stats = self.import_approvals(excel_file)
            
            # Check if import was successful
            if import_stats['successful_imports'] == 0:
                print("⚠️  No SKUs were imported. Skipping cleanup.")
                return False
            
            # Step 3: Clean up the approval folder
            cleanup_stats = self.cleanup_approval_folder()
            
            # Final summary
            print(f"\n🎉 PROCESS COMPLETED SUCCESSFULLY!")
            print(f"   ✅ Imported {import_stats['successful_imports']} approved SKUs")
            print(f"   🧹 Cleaned up {cleanup_stats['files_removed']} files")
            print(f"   📁 Approval folder is now empty and ready for next batch")
            
            return True
            
        except Exception as e:
            print(f"❌ Process failed: {e}")
            return False
    
    def list_approval_files(self):
        """List all files in the approval directory."""
        print("📋 FILES IN APPROVAL DIRECTORY:")
        print("=" * 40)
        
        if not self.approval_dir.exists():
            print("❌ Approval directory doesn't exist")
            return
        
        files = list(self.approval_dir.iterdir())
        
        if not files:
            print("✅ Approval directory is empty")
            return
        
        for item in files:
            if item.is_file():
                size = item.stat().st_size / 1024  # KB
                modified = datetime.fromtimestamp(item.stat().st_mtime)
                print(f"   📄 {item.name}")
                print(f"      📅 Modified: {modified}")
                print(f"      📏 Size: {size:.1f} KB")
            else:
                print(f"   📁 {item.name}/ (directory)")
        
        print(f"\nTotal items: {len(files)}")

def main():
    """CLI for import and cleanup operations."""
    
    manager = ImportAndCleanupManager()
    
    if len(sys.argv) == 1:
        # Default: Run full process
        manager.run_full_process()
    
    elif sys.argv[1] == 'list':
        # List files in approval directory
        manager.list_approval_files()
    
    elif sys.argv[1] == 'import-only':
        # Import without cleanup
        excel_file = manager.find_latest_excel_file()
        if excel_file:
            manager.import_approvals(excel_file)
        else:
            print("❌ No Excel file found to import")
    
    elif sys.argv[1] == 'cleanup-only':
        # Cleanup without import
        manager.cleanup_approval_folder()
    
    elif sys.argv[1] == 'import':
        # Import specific file
        if len(sys.argv) < 3:
            print("❌ Please provide Excel file path")
            return
        
        excel_path = Path(sys.argv[2])
        if not excel_path.exists():
            print(f"❌ File not found: {excel_path}")
            return
        
        manager.import_approvals(excel_path)
    
    else:
        print("📖 USAGE:")
        print("  python scripts/import_and_cleanup.py                    # Full process (import + cleanup)")
        print("  python scripts/import_and_cleanup.py list               # List approval files")
        print("  python scripts/import_and_cleanup.py import-only        # Import latest file only")
        print("  python scripts/import_and_cleanup.py cleanup-only       # Cleanup folder only")
        print("  python scripts/import_and_cleanup.py import <file>      # Import specific file")
        print("")
        print("🎯 RECOMMENDED: Use default command for normal workflow")

if __name__ == "__main__":
    main() 