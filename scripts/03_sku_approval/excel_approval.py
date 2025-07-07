#!/usr/bin/env python3
"""
EXCEL SKU APPROVAL SYSTEM v4 - Enhanced with VBA-Powered Dependent Dropdowns

Business-Optimized SKU Approval Workflow with VBA macro for robust dependent dropdown menus.
Enhanced with comprehensive file locking detection and Excel process management.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime
import json
import re
import unicodedata
import time
import psutil
import subprocess

# Add src to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "src"))

try:
    import openpyxl
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.styles import Font, Fill, PatternFill, Border, Side, Alignment
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.workbook.defined_name import DefinedName
except ImportError:
    print("❌ openpyxl not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl>=3.1.0"])
    import openpyxl
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.styles import Font, Fill, PatternFill, Border, Side, Alignment

from src.data.database import DatabaseManager
from src.data.models import InvoiceItem, ApprovedSku
from sqlalchemy import text

class ExcelProcessManager:
    """Enhanced Excel process and file lock management."""
    
    @staticmethod
    def is_file_locked(file_path: Path) -> bool:
        """Check if a file is locked by another process."""
        try:
            # Try to open the file in exclusive mode
            with open(file_path, 'r+b') as f:
                pass
            return False
        except (PermissionError, IOError):
            return True
    
    @staticmethod
    def find_excel_processes() -> List[Dict[str, Any]]:
        """Find all running Excel processes."""
        excel_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'excel' in proc.info['name'].lower():
                    excel_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': proc.info['cmdline']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return excel_processes
    
    @staticmethod
    def close_excel_file(file_path: Path, timeout: int = 30) -> bool:
        """Attempt to close a specific Excel file by finding and closing the process."""
        try:
            import win32com.client as win32
            
            # Try to connect to existing Excel application
            try:
                excel_app = win32.GetActiveObject("Excel.Application")
                
                # Find and close the specific workbook
                for wb in excel_app.Workbooks:
                    if Path(wb.FullName) == file_path.absolute():
                        print(f"   🔄 Closing Excel file: {file_path.name}")
                        wb.Close(SaveChanges=False)
                        return True
                        
            except Exception:
                # No active Excel application or file not found
                pass
                
            return False
            
        except ImportError:
            print("   ⚠️  pywin32 not available for Excel automation")
            return False
    
    @staticmethod
    def wait_for_file_unlock(file_path: Path, max_wait: int = 60, check_interval: int = 2) -> bool:
        """Wait for a file to become unlocked."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if not ExcelProcessManager.is_file_locked(file_path):
                return True
            
            print(f"   ⏳ Waiting for file to unlock... ({int(time.time() - start_time)}s)")
            time.sleep(check_interval)
        
        return False
    
    @staticmethod
    def create_unique_filename(base_path: Path) -> Path:
        """Create a unique filename to avoid conflicts."""
        if not base_path.exists():
            return base_path
        
        counter = 1
        while True:
            stem = base_path.stem
            suffix = base_path.suffix
            new_name = f"{stem}_{counter}{suffix}"
            new_path = base_path.parent / new_name
            
            if not new_path.exists() and not ExcelProcessManager.is_file_locked(new_path):
                return new_path
            
            counter += 1
            if counter > 100:  # Prevent infinite loop
                raise RuntimeError("Could not create unique filename after 100 attempts")

class ExcelSkuApprovalManager:
    """Advanced Excel-based SKU approval workflow with VBA-powered dependent dropdowns."""
    
    def __init__(self):
        """Initialize database connection and settings."""
        self.db_manager = DatabaseManager()
        self.approval_dir = Path("data/approval")
        self.approval_dir.mkdir(exist_ok=True)
        self.process_manager = ExcelProcessManager()
        
        # Load P62 categories for dropdowns
        self.p62_categories = self._load_p62_categories()
        
        # Standardized units (the 3 main types)
        self.standardized_units = ["Litros", "Kilogramos", "Piezas"]
        
        # Sub-subcategories (specific product types)
        self.sub_subcategories = self._generate_sub_subcategories()
        
        print("🎯 Excel SKU Approval Manager initialized (VBA-powered)")
        print(f"   📁 Approval directory: {self.approval_dir}")
        
        # Count the actual taxonomy structure
        categories = self.p62_categories.get('categories', {})
        total_subcategories = sum(len(subcats) for subcats in categories.values())
        total_sub_subcategories = sum(len(sub_sub_list) for subcats in categories.values() for sub_sub_list in subcats.values())
        
        print(f"   📋 P62 Taxonomy loaded:")
        print(f"       • Categories (Tier 1): {len(categories)}")
        print(f"       • SubCategories (Tier 2): {total_subcategories}")
        print(f"       • Sub-SubCategories (Tier 3): {total_sub_subcategories}")
        
    def _load_p62_categories(self) -> Dict[str, Any]:
        """Load P62 categories from configuration."""
        try:
            with open("config/p62_categories.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading P62 categories: {e}")
            return {"categories": {}}
    
    def _generate_sub_subcategories(self) -> Dict[str, List[str]]:
        """Extract the actual sub-subcategories from P62 taxonomy (3rd tier)."""
        sub_subcategories = {}
        
        # Use the REAL 3-tier taxonomy from P62 configuration
        for category, subcategories in self.p62_categories.get("categories", {}).items():
            for subcategory, sub_sub_list in subcategories.items():
                # Store the actual sub-subcategories from the P62 file
                sub_subcategories[subcategory] = sub_sub_list
        
        return sub_subcategories
    
    def export_pending_skus(self, min_frequency: int = 1, min_value: float = 0.0) -> str:
        """Export pending SKUs to Excel with VBA-powered dependent dropdowns."""
        print("🔄 EXPORTING PENDING SKUs WITH VBA-POWERED DEPENDENT DROPDOWNS")
        print("=" * 60)
        
        try:
            with self.db_manager.get_session() as session:
                # Query pending classifications
                query = """
                SELECT 
                    ii.sku_key as ID,
                    ii.description as Description,
                    inv.issuer_name as Supplier,
                    ii.category as AI_Proposed_Category,
                    ii.subcategory as AI_Proposed_SubCategory,
                    ii.sub_sub_category as AI_Proposed_SubSubCategory,
                    ii.unit_code as Original_Unit_Of_Measure,
                    ii.standardized_unit as AI_Proposed_Unit_Of_Measure,
                    COALESCE(ii.conversion_factor, 1.0) as AI_Proposed_Units_Per_Package,
                    'FALSE' as Is_General_Expense,
                    COUNT(*) as Frequency,
                    SUM(ii.total_amount) as Total_Value_MXN,
                    AVG(ii.total_amount) as Avg_Value_MXN,
                    AVG(ii.category_confidence) as Avg_Confidence
                FROM invoice_items ii
                JOIN invoices inv ON ii.invoice_id = inv.id
                LEFT JOIN approved_skus aps ON ii.sku_key = aps.sku_key
                WHERE ii.approval_status = 'pending' 
                  AND aps.sku_key IS NULL
                  AND ii.sku_key IS NOT NULL
                GROUP BY ii.sku_key, ii.description, inv.issuer_name, ii.category, ii.subcategory, 
                         ii.sub_sub_category, ii.unit_code, ii.standardized_unit, 
                         ii.conversion_factor
                HAVING COUNT(*) >= :min_frequency AND SUM(ii.total_amount) >= :min_value
                ORDER BY SUM(ii.total_amount) DESC, COUNT(*) DESC
                """
                
                # Execute query
                result = session.execute(text(query), {"min_frequency": min_frequency, "min_value": min_value})
                rows = result.fetchall()
                
                if not rows:
                    print("❌ No pending SKUs found matching criteria")
                    return None
                
                # Create DataFrame
                columns = [
                    'ID', 'Description', 'Supplier', 'AI_Proposed_Category', 'AI_Proposed_SubCategory',
                    'AI_Proposed_SubSubCategory', 'Original_Unit_Of_Measure', 
                    'AI_Proposed_Unit_Of_Measure', 'AI_Proposed_Units_Per_Package',
                    'Is_General_Expense', 'Frequency', 'Total_Value_MXN', 'Avg_Value_MXN',
                    'Avg_Confidence'
                ]
                
                df = pd.DataFrame([dict(zip(columns, row)) for row in rows])
                
                # Calculate priority score
                df['Priority_Score'] = (df['Frequency'] * df['Total_Value_MXN']).round(2)
                
                # Create Excel file with enhanced file management
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = f"sku_approval_{timestamp}.xlsx"
                excel_path = self.process_manager.create_unique_filename(self.approval_dir / base_filename)
                
                self._create_excel_with_vba_dropdowns(df, excel_path)
                
                print(f"✅ Successfully exported {len(df)} pending SKUs")
                print(f"📄 Excel file: {excel_path}")
                print(f"💰 Total business impact: ${df['Total_Value_MXN'].sum():,.2f} MXN")
                
                return str(excel_path)
                
        except Exception as e:
            print(f"❌ Export failed: {e}")
            raise
    
    def _create_excel_with_vba_dropdowns(self, df: pd.DataFrame, excel_path: Path) -> None:
        """Create Excel file with VBA macro for dependent dropdown functionality."""
        
        print("🔧 Creating Excel file with VBA-powered dependent dropdowns...")
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws_main = wb.active
        ws_main.title = "SKU_Approval"
        
        # Create reference sheets (simplified - no named ranges needed for VBA)
        self._create_reference_sheets_for_vba(wb)
        
        # Set up main sheet
        self._setup_main_sheet(ws_main, df)
        
        # Add basic dropdowns (non-dependent ones)
        self._add_basic_dropdowns(ws_main, len(df))
        
        # Format sheet
        self._format_sheet(ws_main)
        
        # First save as regular Excel file (.xlsx)
        wb.save(excel_path)
        print(f"   💾 Base Excel file created: {excel_path}")
        
        # Convert to macro-enabled and add VBA with enhanced error handling
        excel_path_xlsm = self._convert_to_macro_enabled_enhanced(excel_path)
        
        if excel_path_xlsm:
            print(f"   ✅ Macro-enabled Excel file ready: {excel_path_xlsm}")
            # Update the path for return value
            excel_path = excel_path_xlsm
        else:
            print(f"   📝 Regular Excel file created: {excel_path}")
            print("   ⚠️  For dependent dropdowns, manually add VBA code (see instructions below)")
        
    def _create_reference_sheets_for_vba(self, wb) -> None:
        """Create simplified reference sheets for VBA macro."""
        
        # Categories sheet (for main category dropdown)
        ws_categories = wb.create_sheet("Categories")
        categories = list(self.p62_categories.get("categories", {}).keys())
        
        for i, category in enumerate(categories, 1):
            ws_categories[f'A{i}'] = category
        
        # Create named range for main categories
        wb.defined_names["MainCategories"] = DefinedName("MainCategories", attr_text=f"Categories!$A$1:$A${len(categories)}")
        
        # Units sheet
        ws_units = wb.create_sheet("Units")
        for i, unit in enumerate(self.standardized_units, 1):
            ws_units[f'A{i}'] = unit
        
        wb.defined_names["StandardizedUnits"] = DefinedName("StandardizedUnits", attr_text=f"Units!$A$1:$A${len(self.standardized_units)}")
        
        # Expense options
        ws_expense = wb.create_sheet("ExpenseOptions")
        ws_expense['A1'] = 'TRUE'
        ws_expense['A2'] = 'FALSE'
        wb.defined_names["ExpenseOptions"] = DefinedName("ExpenseOptions", attr_text="ExpenseOptions!$A$1:$A$2")
    
    def _setup_main_sheet(self, ws, df: pd.DataFrame) -> None:
        """Set up the main approval sheet."""
        
        # Title
        ws['A1'] = "SKU APPROVAL SYSTEM - VBA-Powered Dependent Dropdowns"
        ws['A1'].font = Font(size=14, bold=True, color="FFFFFF")
        ws['A1'].fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        ws.merge_cells('A1:J1')
        
        # Headers
        headers = [
            "Priority Score", "ID", "Description", "Supplier", "Category ▼", 
            "SubCategory ▼", "SubSubCategory", "Original Unit", 
            "Standardized Unit ▼", "Units Per Package", "General Expense ▼"
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
        
        # Add data
        approval_columns = [
            'Priority_Score', 'ID', 'Description', 'Supplier', 'AI_Proposed_Category', 
            'AI_Proposed_SubCategory', 'AI_Proposed_SubSubCategory',
            'Original_Unit_Of_Measure', 'AI_Proposed_Unit_Of_Measure', 
            'AI_Proposed_Units_Per_Package', 'Is_General_Expense'
        ]
        
        for row_idx, (_, row_data) in enumerate(df.iterrows(), 3):
            for col_idx, column in enumerate(approval_columns, 1):
                value = row_data.get(column, '')
                if pd.isna(value):
                    value = ''
                ws.cell(row=row_idx, column=col_idx, value=value)
    
    def _add_basic_dropdowns(self, ws, data_rows: int) -> None:
        """Add basic dropdown validations (non-dependent ones)."""
        
        last_row = data_rows + 2
        
        # Category dropdown (Column E) - This will trigger the VBA macro
        category_validation = DataValidation(
            type="list",
            formula1="MainCategories",
            showDropDown=True
        )
        category_validation.add(f'E3:E{last_row}')
        ws.add_data_validation(category_validation)
        
        # Unit dropdown (Column I)
        unit_validation = DataValidation(
            type="list",
            formula1="StandardizedUnits",
            showDropDown=True
        )
        unit_validation.add(f'I3:I{last_row}')
        ws.add_data_validation(unit_validation)
        
        # Expense dropdown (Column K)
        expense_validation = DataValidation(
            type="list",
            formula1="ExpenseOptions",
            showDropDown=True
        )
        expense_validation.add(f'K3:K{last_row}')
        ws.add_data_validation(expense_validation)
        
        # Note: SubCategory dropdown (Column F) will be handled by VBA macro
    
    def _convert_to_macro_enabled_enhanced(self, excel_path: Path) -> Optional[Path]:
        """Enhanced conversion to macro-enabled Excel with comprehensive error handling."""
        
        try:
            import win32com.client as win32
            
            print("   🔧 Converting to macro-enabled Excel file...")
            
            # Step 1: Check for existing Excel processes and warn user
            excel_processes = self.process_manager.find_excel_processes()
            if excel_processes:
                print(f"   ⚠️  Found {len(excel_processes)} running Excel process(es)")
                print("   💡 For best results, close Excel applications before running this script")
            
            # Step 2: Enhanced file lock detection and resolution
            if self.process_manager.is_file_locked(excel_path):
                print("   🔒 File is currently locked")
                
                # Try to close the specific file
                if self.process_manager.close_excel_file(excel_path):
                    print("   ✅ Successfully closed Excel file")
                else:
                    print("   ⏳ Waiting for file to become available...")
                    if not self.process_manager.wait_for_file_unlock(excel_path, max_wait=30):
                        print("   ❌ File remains locked. Please close Excel and try again.")
                        self._save_vba_to_file()
                        return None
            
            # Step 3: Create Excel application with error handling
            excel_app = None
            wb = None
            
            try:
                # Try to get existing Excel application first
                try:
                    excel_app = win32.GetActiveObject("Excel.Application")
                    print("   📎 Connected to existing Excel application")
                except:
                    # Create new Excel application
                    excel_app = win32.Dispatch("Excel.Application")
                    print("   🆕 Created new Excel application")
                
                excel_app.Visible = False
                excel_app.DisplayAlerts = False
                excel_app.ScreenUpdating = False
                
                # Check if VBA access is enabled
                try:
                    vba_enabled = excel_app.VBE.VBProjects.Count >= 0
                    print("   ✅ VBA access is enabled")
                except:
                    print("   ⚠️  VBA access is restricted. Enable 'Trust access to the VBA project object model' in Excel settings.")
                    raise Exception("VBA access is restricted")
                
                # Step 4: Open the workbook with retry logic
                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        wb = excel_app.Workbooks.Open(str(excel_path.absolute()))
                        break
                    except Exception as e:
                        if attempt < max_attempts - 1:
                            print(f"   ⏳ Retry opening file (attempt {attempt + 1}/{max_attempts})")
                            time.sleep(2)
                        else:
                            raise e
                
                # Step 5: Add VBA code
                vba_code = self._generate_vba_code()
                
                # Find the correct worksheet and add VBA code
                try:
                    # Method 1: Try by name
                    ws = wb.Worksheets("SKU_Approval")
                    ws_module = wb.VBProject.VBComponents(ws.CodeName).CodeModule
                    ws_module.AddFromString(vba_code)
                    print("   ✅ VBA code added to SKU_Approval worksheet")
                except:
                    try:
                        # Method 2: Try first worksheet by index
                        ws = wb.Worksheets(1)
                        ws_module = wb.VBProject.VBComponents(ws.CodeName).CodeModule
                        ws_module.AddFromString(vba_code)
                        print(f"   ✅ VBA code added to worksheet: {ws.Name}")
                    except:
                        try:
                            # Method 3: Try to find worksheet component by iterating
                            for component in wb.VBProject.VBComponents:
                                if component.Type == 100:  # vbext_ct_Document (worksheet)
                                    component.CodeModule.AddFromString(vba_code)
                                    print(f"   ✅ VBA code added to component: {component.Name}")
                                    break
                            else:
                                raise Exception("No worksheet component found")
                        except Exception as e:
                            raise Exception(f"All VBA insertion methods failed: {e}")
                
                # Step 6: Save as macro-enabled workbook
                excel_path_xlsm = excel_path.with_suffix('.xlsm')
                
                # Ensure target file is not locked
                if excel_path_xlsm.exists() and self.process_manager.is_file_locked(excel_path_xlsm):
                    excel_path_xlsm = self.process_manager.create_unique_filename(excel_path_xlsm)
                
                wb.SaveAs(str(excel_path_xlsm.absolute()), FileFormat=52)  # 52 = xlOpenXMLWorkbookMacroEnabled
                print("   💾 Saved as macro-enabled workbook")
                
                # Step 7: Clean up
                wb.Close(SaveChanges=False)
                
                # Only quit if we created the Excel application
                try:
                    if len(excel_app.Workbooks) == 0:
                        excel_app.Quit()
                        print("   🔄 Excel application closed")
                except:
                    pass  # Excel might have been closed already
                
                # Step 8: Remove original file
                try:
                    if excel_path.exists():
                        excel_path.unlink()
                        print("   🗑️  Removed original .xlsx file")
                except PermissionError:
                    print(f"   ⚠️  Could not delete original file {excel_path} (file may be in use)")
                
                print("   ✅ VBA macro added successfully")
                return excel_path_xlsm
                
            except Exception as e:
                # Clean up on error
                try:
                    if wb:
                        wb.Close(SaveChanges=False)
                    if excel_app and len(excel_app.Workbooks) == 0:
                        excel_app.Quit()
                except:
                    pass
                raise e
                
        except ImportError:
            print("   ⚠️  pywin32 not available. Install with: pip install pywin32")
            self._save_vba_to_file()
            return None
        except Exception as e:
            print(f"   ⚠️  Could not add VBA macro automatically: {e}")
            self._save_vba_to_file()
            return None
    
    def _save_vba_to_file(self) -> None:
        """Save VBA code to a text file for manual installation."""
        vba_file = Path("scripts/VBA_Dependant_Script.txt")
        try:
            with open(vba_file, 'w', encoding='utf-8') as f:
                f.write("VBA CODE FOR DEPENDENT DROPDOWNS - SKU APPROVAL SYSTEM v4\n")
                f.write("=" * 70 + "\n\n")
                f.write("INSTRUCTIONS:\n")
                f.write("1. Open your Excel file\n")
                f.write("2. Press Alt+F11 to open VBA editor\n")
                f.write("3. Double-click on 'SKU_Approval' sheet in project explorer\n")
                f.write("4. Copy and paste the VBA code below\n")
                f.write("5. Save as .xlsm file (Excel Macro-Enabled Workbook)\n")
                f.write("6. Close VBA editor and test dependent dropdowns\n\n")
                f.write("VBA CODE:\n")
                f.write("-" * 70 + "\n")
                f.write(self._generate_vba_code())
                f.write("\n" + "-" * 70 + "\n")
            
            print(f"   📝 VBA code saved to: {vba_file}")
            print("   💡 Follow the instructions in the file to manually add VBA code")
        except Exception as e:
            print(f"   ❌ Could not save VBA code to file: {e}")
    
    def _generate_vba_code(self) -> str:
        """Generate enhanced VBA code for 3-tier dependent dropdowns that prevents data loss."""
        
        # Create category to subcategory mapping
        category_mappings = []
        for category, subcategories in self.p62_categories.get("categories", {}).items():
            subcats_str = '","'.join(subcategories.keys())
            category_mappings.append(f'                Case "{category}": arr = Array("{subcats_str}")')
        
        # Create subcategory to sub-subcategory mapping
        subcategory_mappings = []
        for category, subcategories in self.p62_categories.get("categories", {}).items():
            for subcategory, sub_sub_list in subcategories.items():
                sub_sub_str = '","'.join(sub_sub_list)
                subcategory_mappings.append(f'                Case "{subcategory}": arr = Array("{sub_sub_str}")')
        
        vba_code = f'''
' VBA Macro for 3-Tier Dependent Dropdowns in SKU Approval System v4
' ENHANCED VERSION - Prevents data loss and handles single-cell changes only

Private Sub Worksheet_Change(ByVal Target As Range)
    ' Only process single cell changes to avoid cascading issues
    If Target.Cells.Count > 1 Then Exit Sub
    
    Dim categoryRange As Range, subCategoryRange As Range
    Dim subCategoryCell As Range, subSubCategoryCell As Range
    Dim category As String, subCategory As String
    Dim arr As Variant
    Dim i As Integer
    Dim validationList As String
    Dim targetRow As Long
    
    ' Get the row of the changed cell
    targetRow = Target.Row
    
    ' Only process rows 3 and onwards (data rows)
    If targetRow < 3 Then Exit Sub
    
    ' Handle Category selection (Column E) - ONLY for the specific changed cell
    If Target.Column = 5 Then
        ' Get the corresponding subcategory and sub-subcategory cells for THIS ROW ONLY
        Set subCategoryCell = Cells(targetRow, 6)      ' Column F, same row
        Set subSubCategoryCell = Cells(targetRow, 7)   ' Column G, same row
        category = Target.Value
        
        ' Disable events to prevent cascading
        Application.EnableEvents = False
        
        ' Only clear and reset THIS ROW's dependent cells
        subCategoryCell.Value = ""
        subSubCategoryCell.Value = ""
        
        ' Remove existing validation from THIS ROW only
        On Error Resume Next
        subCategoryCell.Validation.Delete
        subSubCategoryCell.Validation.Delete
        On Error GoTo 0
        
        ' Set up subcategory dropdown based on selected category
        If category <> "" Then
            Select Case category
{chr(10).join(category_mappings)}
                Case Else
                    arr = Array("No subcategories available")
            End Select
            
            ' Create validation list string for subcategories
            validationList = ""
            For i = 0 To UBound(arr)
                If i > 0 Then validationList = validationList & ","
                validationList = validationList & arr(i)
            Next i
            
            ' Apply validation to subcategory cell (THIS ROW ONLY)
            With subCategoryCell.Validation
                .Delete
                .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, _
                     Operator:=xlBetween, Formula1:=validationList
                .IgnoreBlank = True
                .InCellDropdown = True
                .ShowInput = True
                .ShowError = True
            End With
        End If
        
        ' Re-enable events
        Application.EnableEvents = True
    
    ' Handle SubCategory selection (Column F) - ONLY for the specific changed cell
    ElseIf Target.Column = 6 Then
        ' Get the corresponding sub-subcategory cell for THIS ROW ONLY
        Set subSubCategoryCell = Cells(targetRow, 7)   ' Column G, same row
        subCategory = Target.Value
        
        ' Disable events to prevent cascading
        Application.EnableEvents = False
        
        ' Only clear THIS ROW's sub-subcategory
        subSubCategoryCell.Value = ""
        
        ' Remove existing validation from THIS ROW only
        On Error Resume Next
        subSubCategoryCell.Validation.Delete
        On Error GoTo 0
        
        ' Set up sub-subcategory dropdown based on selected subcategory
        If subCategory <> "" Then
            Select Case subCategory
{chr(10).join(subcategory_mappings)}
                Case Else
                    arr = Array("No sub-subcategories available")
            End Select
            
            ' Create validation list string for sub-subcategories
            validationList = ""
            For i = 0 To UBound(arr)
                If i > 0 Then validationList = validationList & ","
                validationList = validationList & arr(i)
            Next i
            
            ' Apply validation to sub-subcategory cell (THIS ROW ONLY)
            With subSubCategoryCell.Validation
                .Delete
                .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, _
                     Operator:=xlBetween, Formula1:=validationList
                .IgnoreBlank = True
                .InCellDropdown = True
                .ShowInput = True
                .ShowError = True
            End With
        End If
        
        ' Re-enable events
        Application.EnableEvents = True
    End If
End Sub

' Helper function to initialize dropdowns when file is opened
Private Sub Worksheet_Activate()
    ' Disable events during initialization to prevent cascading
    Application.EnableEvents = False
    
    Dim cell As Range
    Dim lastRow As Long
    
    ' Find the last row with data
    lastRow = Cells(Rows.Count, 2).End(xlUp).Row  ' Column B (ID column)
    
    ' First refresh category dropdowns (only for rows with data)
    For Each cell In Range("E3:E" & lastRow)
        If cell.Value <> "" And Cells(cell.Row, 2).Value <> "" Then
            ' Manually trigger subcategory setup for this row
            Call SetupSubCategoryDropdown(cell.Row, cell.Value)
        End If
    Next cell
    
    ' Then refresh subcategory dropdowns (only for rows with data)
    For Each cell In Range("F3:F" & lastRow)
        If cell.Value <> "" And Cells(cell.Row, 2).Value <> "" Then
            ' Manually trigger sub-subcategory setup for this row
            Call SetupSubSubCategoryDropdown(cell.Row, cell.Value)
        End If
    Next cell
    
    ' Re-enable events
    Application.EnableEvents = True
End Sub

' Helper subroutine to set up subcategory dropdown for a specific row
Private Sub SetupSubCategoryDropdown(targetRow As Long, category As String)
    Dim arr As Variant
    Dim validationList As String
    Dim i As Integer
    Dim subCategoryCell As Range
    
    Set subCategoryCell = Cells(targetRow, 6)  ' Column F
    
    Select Case category
{chr(10).join(category_mappings)}
        Case Else
            arr = Array("No subcategories available")
    End Select
    
    ' Create validation list
    validationList = ""
    For i = 0 To UBound(arr)
        If i > 0 Then validationList = validationList & ","
        validationList = validationList & arr(i)
    Next i
    
    ' Apply validation
    With subCategoryCell.Validation
        .Delete
        .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, _
             Operator:=xlBetween, Formula1:=validationList
        .IgnoreBlank = True
        .InCellDropdown = True
    End With
End Sub

' Helper subroutine to set up sub-subcategory dropdown for a specific row
Private Sub SetupSubSubCategoryDropdown(targetRow As Long, subCategory As String)
    Dim arr As Variant
    Dim validationList As String
    Dim i As Integer
    Dim subSubCategoryCell As Range
    
    Set subSubCategoryCell = Cells(targetRow, 7)  ' Column G
    
    Select Case subCategory
{chr(10).join(subcategory_mappings)}
        Case Else
            arr = Array("No sub-subcategories available")
    End Select
    
    ' Create validation list
    validationList = ""
    For i = 0 To UBound(arr)
        If i > 0 Then validationList = validationList & ","
        validationList = validationList & arr(i)
    Next i
    
    ' Apply validation
    With subSubCategoryCell.Validation
        .Delete
        .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, _
             Operator:=xlBetween, Formula1:=validationList
        .IgnoreBlank = True
        .InCellDropdown = True
    End With
End Sub
'''
        
        return vba_code
    
    def _format_sheet(self, ws) -> None:
        """Format the approval sheet."""
        
        # Column widths
        column_widths = [15, 25, 40, 18, 22, 25, 15, 20, 18, 18]
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[chr(64 + col)].width = width
        
        # Freeze panes
        ws.freeze_panes = 'A3'
    
    def import_approved_skus(self, excel_path: str) -> Dict[str, Any]:
        """Import approved SKU classifications from Excel with enhanced file handling."""
        print("📥 IMPORTING APPROVED SKUs FROM EXCEL")
        print("=" * 50)
        
        excel_file_path = Path(excel_path)
        
        # Check if file exists
        if not excel_file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")
        
        # Check if file is locked and wait if necessary
        if self.process_manager.is_file_locked(excel_file_path):
            print("   🔒 File is currently locked, waiting...")
            if not self.process_manager.wait_for_file_unlock(excel_file_path, max_wait=30):
                raise RuntimeError("File remains locked. Please close Excel and try again.")
        
        try:
            # Handle both .xlsx and .xlsm files
            if excel_path.endswith('.xlsm'):
                print("   📋 Detected macro-enabled file (.xlsm)")
            
            # Read Excel file with error handling
            try:
                df = pd.read_excel(excel_path, sheet_name='SKU_Approval', skiprows=1)
            except Exception as e:
                print(f"   ❌ Error reading Excel file: {e}")
                raise
            
            # Clean column names
            df.columns = [
                'Priority_Score', 'ID', 'Description', 'Supplier', 'Category', 
                'SubCategory', 'SubSubCategory', 'Original_Unit',
                'Standardized_Unit', 'Units_Per_Package', 'General_Expense'
            ]
            
            # Remove empty rows
            df = df.dropna(subset=['ID'])
            
            stats = {
                'total_rows': len(df),
                'successful_imports': 0,
                'errors': []
            }
            
            # Track which SKU keys we've seen in this Excel file to handle duplicates
            seen_sku_keys = set()
            
            # Process each row individually with its own transaction for error resilience
            for idx, row in df.iterrows():
                try:
                    sku_key = str(row['ID']).strip()
                    
                    # Skip if we've already seen this SKU key in this Excel file
                    if sku_key in seen_sku_keys:
                        stats['errors'].append(f"Row {idx + 3}: Duplicate SKU key '{sku_key}' within Excel file - skipped")
                        continue
                    
                    seen_sku_keys.add(sku_key)
                    
                    with self.db_manager.get_session() as session:
                        # Check if already exists in database
                        existing = session.query(ApprovedSku).filter_by(sku_key=sku_key).first()
                        
                        if existing:
                            stats['errors'].append(f"Row {idx + 3}: SKU key '{sku_key}' already exists in database - skipped")
                            continue
                        
                        # Create new approved SKU
                        approved_sku = ApprovedSku(
                            sku_key=sku_key,
                            normalized_description=str(row['Description']).strip(),
                            category=str(row['Category']).strip(),
                            subcategory=str(row['SubCategory']).strip(),
                            sub_sub_category=str(row['SubSubCategory']).strip(),
                            standardized_unit=str(row['Standardized_Unit']).strip(),
                            units_per_package=float(row['Units_Per_Package']),
                            approved_by='excel_import',
                            approval_date=datetime.utcnow(),
                            confidence_score=1.0
                        )
                        
                        session.add(approved_sku)
                        
                        # Update invoice items
                        session.query(InvoiceItem).filter_by(
                            sku_key=sku_key
                        ).update({
                            'approval_status': 'approved',
                            'category': str(row['Category']).strip(),
                            'subcategory': str(row['SubCategory']).strip(),
                            'sub_sub_category': str(row['SubSubCategory']).strip(),
                            'standardized_unit': str(row['Standardized_Unit']).strip(),
                            'conversion_factor': float(row['Units_Per_Package']),
                            'units_per_package': float(row['Units_Per_Package'])
                        })
                        
                        session.commit()
                        stats['successful_imports'] += 1
                        
                        if stats['successful_imports'] % 10 == 0:
                            print(f"   ✅ Imported {stats['successful_imports']} SKUs...")
                        
                except Exception as e:
                    stats['errors'].append(f"Row {idx + 3}: {str(e)}")
                    print(f"   ⚠️  Row {idx + 3} error: {str(e)}")
            
            print(f"✅ Import completed:")
            print(f"   📊 Total rows: {stats['total_rows']}")
            print(f"   ✅ Imported: {stats['successful_imports']}")
            print(f"   ❌ Errors: {len(stats['errors'])}")
            
            return stats
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            raise

    def sanitize_name(self, name: str) -> str:
        """Sanitize a string to be a valid Excel named range (alphanumeric and underscores only)."""
        # Remove accents and special characters
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('ASCII', 'ignore').decode('ASCII')
        # Replace non-alphanumeric with _
        return re.sub(r'[^A-Za-z0-9]', '_', name)

def main():
    """CLI for Excel SKU approval with VBA-powered dependent dropdowns."""
    
    print("🎯 EXCEL SKU APPROVAL SYSTEM v4 - VBA-POWERED (Enhanced)")
    print("=" * 60)
    
    manager = ExcelSkuApprovalManager()
    
    if len(sys.argv) == 1:
        # Export
        excel_path = manager.export_pending_skus()
        if excel_path:
            print(f"\n🎯 NEXT STEPS:")
            print(f"1. Open: {excel_path}")
            print(f"2. Enable macros when prompted")
            print(f"3. Edit using dependent dropdowns")
            print(f"4. Import: python scripts/excel_approval.py import \"{excel_path}\"")
    
    elif sys.argv[1] == 'export':
        min_freq = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        min_value = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        manager.export_pending_skus(min_freq, min_value)
    
    elif sys.argv[1] == 'import':
        if len(sys.argv) < 3:
            print("❌ Please provide Excel file path")
            return
        
        excel_path = sys.argv[2]
        if not Path(excel_path).exists():
            print(f"❌ File not found: {excel_path}")
            return
        
        manager.import_approved_skus(excel_path)
    
    else:
        print("Usage:")
        print("  python scripts/excel_approval.py                    # Export pending SKUs")
        print("  python scripts/excel_approval.py export [freq] [value]  # Export with filters")
        print("  python scripts/excel_approval.py import <excel_file>    # Import approved SKUs")

if __name__ == "__main__":
    main() 