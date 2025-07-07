# 🚀 CFDI Dashboard System - Quick Start Guide

## ✨ **New Simplified Workflow**

### 1. Start the API Server
```bash
python run_api.py
```
✅ **Permanent solution** - No more import errors!
✅ **All 6 endpoints** including 3 dashboard endpoints  
✅ **Automatic port detection** and data validation
✅ **Clear user feedback** and error handling

### 2. Start ngrok Tunnel
```bash
python scripts/04_api_services/start_ngrok.py
```

### 3. Update Google Apps Script
1. Copy the ngrok URL (e.g., `https://abc123.ngrok-free.app`)
2. Update `BASE_URL` in Google Apps Script
3. Save the script

### 4. Create Dashboards
In Google Sheets: **Extensions > CFDI System > 📊 Create Dashboards**

Creates 3 professional sheets:
- **📈 Sales Dashboard** - Weekly summaries + top products
- **💰 Expenses Dashboard** - Category breakdown + suppliers  
- **📊 KPIs Dashboard** - Real-time metrics + performance

## 🛑 Stop the API
```bash
python stop_api.py
```

## 📊 **Available API Endpoints**

### Dashboard Endpoints (NEW)
- `GET /api/dashboard/sales` - Complete sales analytics
- `GET /api/dashboard/expenses` - Expense breakdown
- `GET /api/dashboard/kpis` - Key performance indicators

### Legacy Endpoints  
- `GET /api/health` - Server health check
- `GET /api/invoices/metadata` - Invoice metadata
- `GET /` - API documentation

## ✅ **What's Fixed**

### ❌ Before (Problems):
- Import path errors when closing/reopening Cursor
- Outdated `start_cfdi_api.py` with only 3 endpoints
- Manual setup required each time
- Complex troubleshooting

### ✅ After (Solutions):
- **Permanent `run_api.py`** - Works from anywhere
- **All 6 endpoints** including dashboards
- **Automatic validation** and clear feedback
- **One-click dashboard creation** in Google Sheets

## 🎯 **Business Value**

Transform raw CFDI data into actionable insights:
- **📈 Sales Trends** - Weekly performance tracking
- **💰 Expense Management** - Category and supplier analysis
- **📊 KPI Monitoring** - Real-time business metrics
- **🎨 Professional Formatting** - Executive-ready dashboards

## 🔧 **Troubleshooting**

### API Won't Start?
```bash
python -c "import sys; sys.path.insert(0, '.'); from src.api import app; print('✅ API OK!')"
```

### Port Already in Use?
The script automatically finds a free port (8000-8010)

### No Data in Dashboards?
Run data population scripts:
```bash
python scripts/02_dashboard/populate_sales_only.py
python scripts/02_dashboard/populate_kpis.py
```

### Google Sheets Connection Issues?
1. Check ngrok URL is updated in script
2. Verify API is running (`http://localhost:8000/docs`)
3. Test health endpoint first

---

**🎉 Ready to go!** Your CFDI system now has permanent, professional dashboard capabilities. 