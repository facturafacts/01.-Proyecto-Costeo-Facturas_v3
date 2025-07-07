# Scripts Folder - CFDI Processing System v4

## Organized Workflow Structure

This folder contains all automation scripts organized by function and workflow stage.

## Folder Structure

### 01_setup/ - Initial System Setup (Run Once)
**Purpose**: First-time system initialization and validation
**When to use**: Setting up the system for the first time

- `setup_directories.py` - Creates all folders, .env file, sample XML
- `setup_database.py` - Initializes database tables and schema  
- `validate_complete_system.py` - Validates entire CFDI + P62 system

### 02_dashboard/ - Dashboard Data Management (Run Regularly)
**Purpose**: Business intelligence and reporting data management
**When to use**: Daily/weekly to refresh dashboard data for Google Sheets

- `create_dashboard_tables.py` - Create dashboard database tables (one-time)
- `update_dashboard_all.py` - **MASTER SCRIPT** - Updates all dashboard data
- `populate_sales_only.py` - Populate only sales dashboard data
- `populate_expenses_simple.py` - Populate expenses data (basic structure)
- `populate_expenses_only.py` - Populate expenses data (advanced with joins)
- `populate_kpis.py` - Calculate KPIs and real-time metrics
- `populate_dashboard_data.py` - Populate ALL dashboard data at once
- `test_dashboard_queries.py` - Test and validate dashboard data
- `dashboard_summary.py` - Show current dashboard status report

### 03_sku_approval/ - SKU Classification Workflow (As Needed)
**Purpose**: Manage product classification approvals via Excel workflow
**When to use**: When new products need classification or review

- `excel_approval.py` - Export pending SKUs to Excel with VBA dropdowns
- `import_and_cleanup.py` - Import approved SKUs and cleanup folder
- `check_approved_skus.py` - Verify approved SKU data and categories

**SKU Approval Workflow:**
1. `excel_approval.py` - Export pending SKUs to Excel
2. **Manual**: Edit Excel file with proper classifications
3. `import_and_cleanup.py` - Import approved classifications back

### 04_api_services/ - API and External Services (As Needed)
**Purpose**: External integrations and API services for Google Sheets
**When to use**: For Google Sheets integration or external data access

- `start_cfdi_api.py` - Start FastAPI server for Google Sheets
- `stop_cfdi_api.py` - Stop running FastAPI server
- `start_ngrok.py` - Create public tunnel for external access

### 05_diagnostics/ - System Diagnostics (Troubleshooting)
**Purpose**: System monitoring, validation, and problem diagnosis
**When to use**: When troubleshooting or monitoring system health

- `check_db_schema.py` - Validate database structure and tables
- `check_tables.py` - Quick table counts and basic checks
- `validate_data_integrity.py.bak` - Comprehensive data integrity validation

### temp_data/ - Temporary Script Data
**Purpose**: Store temporary files and logs from script execution
- `data/` - Script-specific temporary data
- `logs/` - Script execution logs

## Quick Start Workflows

### First Time Setup
```bash
# 1. Create directories and configuration
python scripts/01_setup/setup_directories.py

# 2. Initialize database
python scripts/01_setup/setup_database.py

# 3. Create dashboard tables
python scripts/02_dashboard/create_dashboard_tables.py

# 4. Validate system
python scripts/01_setup/validate_complete_system.py
```

### Daily Dashboard Update
```bash
# Update all dashboard data (recommended)
python scripts/02_dashboard/update_dashboard_all.py

# OR update specific components
python scripts/02_dashboard/populate_sales_only.py
python scripts/02_dashboard/populate_expenses_simple.py
python scripts/02_dashboard/populate_kpis.py
```

### SKU Classification Workflow
```bash
# 1. Export pending SKUs for review
python scripts/03_sku_approval/excel_approval.py

# 2. Edit the generated Excel file manually

# 3. Import approved classifications
python scripts/03_sku_approval/import_and_cleanup.py
```

### API Services for Google Sheets
```bash
# Start API server
python scripts/04_api_services/start_cfdi_api.py

# In separate terminal: Create public tunnel
python scripts/04_api_services/start_ngrok.py

# Stop API when done
python scripts/04_api_services/stop_cfdi_api.py
```

### System Health Check
```bash
# Quick status check
python scripts/02_dashboard/dashboard_summary.py

# Database validation
python scripts/05_diagnostics/check_db_schema.py

# Table counts
python scripts/05_diagnostics/check_tables.py

# Complete system validation
python scripts/01_setup/validate_complete_system.py
```

## Recommended Usage Patterns

### Daily Operations Team
```bash
python scripts/02_dashboard/update_dashboard_all.py
python scripts/02_dashboard/dashboard_summary.py
```

### Weekly Management Review
```bash
python scripts/05_diagnostics/check_db_schema.py
python scripts/03_sku_approval/check_approved_skus.py
python scripts/02_dashboard/test_dashboard_queries.py
```

### New Product Classification
```bash
python scripts/03_sku_approval/excel_approval.py
# Manual Excel editing
python scripts/03_sku_approval/import_and_cleanup.py
```

### Google Sheets Integration
```bash
python scripts/04_api_services/start_cfdi_api.py
python scripts/04_api_services/start_ngrok.py
```

## Emergency Troubleshooting

1. **Dashboard not updating**: `python scripts/05_diagnostics/check_tables.py`
2. **API not working**: `python scripts/04_api_services/stop_cfdi_api.py` then restart
3. **Data integrity issues**: `python scripts/05_diagnostics/check_db_schema.py`
4. **Complete system check**: `python scripts/01_setup/validate_complete_system.py`

## Notes

- **Master Script**: `02_dashboard/update_dashboard_all.py` is your daily go-to script
- **First Time**: Always start with `01_setup/` scripts in order
- **Regular Use**: Focus on `02_dashboard/` for daily operations
- **Troubleshooting**: Use `05_diagnostics/` when things go wrong
- **External Access**: Use `04_api_services/` for Google Sheets integration

## Success Indicators

- Dashboard updates without errors
- API serves data to Google Sheets  
- SKU classifications are up to date
- All diagnostic checks pass
- Business reports are accurate 