# Google Sheets Integration Setup Guide

## 🎯 Overview

This guide walks you through setting up the complete integration to export CFDI invoice metadata from your local database to Google Sheets.

**Architecture**: Database → FastAPI → Ngrok → Google Apps Script → Google Sheets

## 📋 Prerequisites

1. **Python Dependencies**: All packages from `requirements.txt` installed
2. **Ngrok Account**: Free account at [ngrok.com](https://ngrok.com)
3. **Google Account**: Access to Google Sheets
4. **Database**: CFDI data already processed and stored

## 🚀 Step-by-Step Setup

### Step 1: Install Dependencies

```bash
# Install the new dependencies
pip install fastapi uvicorn pyngrok

# Or install all requirements
pip install -r requirements.txt
```

### Step 2: Configure Ngrok

1. **Sign up** at [ngrok.com](https://ngrok.com) (free account)
2. **Get your auth token** from the dashboard
3. **Set environment variable**:

```bash
# Windows
set NGROK_AUTH_TOKEN=your_auth_token_here

# Linux/Mac
export NGROK_AUTH_TOKEN=your_auth_token_here
```

4. **Optional**: Set custom domain (paid feature):

```bash
# Windows
set NGROK_DOMAIN=your-custom-domain.ngrok.io

# Linux/Mac
export NGROK_DOMAIN=your-custom-domain.ngrok.io
```

### Step 3: Start the API Server

Open **Terminal 1** and run:

```bash
python scripts/start_api.py
```

You should see:
```
🚀 Starting CFDI Invoice Metadata API Server
==================================================
API Title: CFDI Invoice Metadata API
Host: 127.0.0.1
Port: 8000
📖 API Documentation: http://127.0.0.1:8000/docs
```

**Keep this terminal running**

### Step 4: Start Ngrok Tunnel

Open **Terminal 2** and run:

```bash
python scripts/start_ngrok.py
```

You should see:
```
✅ Ngrok tunnel created successfully!
🌐 Public URL: https://abc123.ngrok.io
📊 API Endpoint: https://abc123.ngrok.io/api/invoices/metadata
📝 For Google Apps Script, use this URL:
   const API_URL = 'https://abc123.ngrok.io/api/invoices/metadata';
```

**Copy the public URL** - you'll need it for Google Sheets.

**Keep this terminal running**

### Step 5: Test the API

Open **Terminal 3** and run:

```bash
python scripts/test_api.py
```

Verify all tests pass:
```
🧪 Testing CFDI Invoice Metadata API
✅ Root endpoint OK
✅ Health check OK - Status: healthy
✅ Invoice metadata OK - Returned X records
✅ API docs OK
```

### Step 6: Set Up Google Apps Script

1. **Open Google Sheets** in your browser
2. **Create a new spreadsheet** or open existing one
3. **Go to Extensions > Apps Script**
4. **Delete** the default `Code.gs` content
5. **Copy and paste** the code from `docs/google_apps_script.js`
6. **Update the API_URL** with your ngrok URL:

```javascript
// Replace this line:
const API_URL = 'https://your-domain.ngrok.io/api/invoices/metadata';

// With your actual ngrok URL:
const API_URL = 'https://abc123.ngrok.io/api/invoices/metadata';
```

7. **Save** the script (Ctrl+S)
8. **Authorize** the script when prompted

### Step 7: Import Data to Google Sheets

1. **Go back to your Google Sheet**
2. **Refresh the page** (to load the custom menu)
3. **Look for "CFDI Import" menu** in the menu bar
4. **Click "CFDI Import" > "Test API Connection"** first
5. If test passes, **click "CFDI Import" > "Import Invoice Metadata"**

You should see your invoice data populate the sheet with formatted columns!

## 📊 What Gets Imported

The Google Sheet will contain these columns:

| Column | Description |
|--------|-------------|
| Invoice UUID | Unique invoice identifier |
| Folio | Invoice folio number |
| Issue Date | When invoice was issued |
| Issuer RFC | Company that issued the invoice |
| Issuer Name | Company name |
| Receiver RFC | Company that received the invoice |
| Receiver Name | Company name |
| Currency | Original currency (MXN, USD, etc.) |
| Original Total | Amount in original currency |
| MXN Total | Amount converted to Mexican Pesos |
| Exchange Rate | Conversion rate used |
| Payment Method | SAT payment method code |
| Installments (PPD) | Yes/No for installment payments |
| Immediate (PUE) | Yes/No for immediate payments |

## 🔧 Customization Options

### API Filters

In Google Apps Script, you can modify the `API_FILTERS` object:

```javascript
const API_FILTERS = {
  limit: 1000,                    // Maximum records
  issuer_rfc: 'RFC123456789',     // Specific issuer
  currency: 'MXN',                // Currency filter
  date_from: '2024-01-01',        // Start date
  date_to: '2024-12-31',          // End date
  payment_immediate: true,        // Only immediate payments
  payment_installments: false     // Exclude installments
};
```

### API Configuration

In `config/settings.py` or environment variables:

```python
API_HOST = "127.0.0.1"          # API server host
API_PORT = 8000                 # API server port
API_TITLE = "Custom API Name"   # API title
```

## 🔍 Troubleshooting

### API Server Issues

**Problem**: "Connection refused" or "API not responding"
```bash
# Check if API is running
curl http://127.0.0.1:8000/api/health

# Restart API server
python scripts/start_api.py
```

### Ngrok Issues

**Problem**: "Tunnel connection failed" or "ngrok not found"
```bash
# Check ngrok installation
ngrok --version

# Check auth token
echo $NGROK_AUTH_TOKEN

# Restart ngrok
python scripts/start_ngrok.py
```

### Google Sheets Issues

**Problem**: "Could not connect to API" in Google Sheets

1. **Verify ngrok URL** is correct in Apps Script
2. **Check CORS** - API should allow Google domains
3. **Test direct access** - open ngrok URL in browser
4. **Check API logs** in Terminal 1

**Problem**: "Script authorization failed"

1. **Go to Apps Script editor**
2. **Click "Review Permissions"**
3. **Follow authorization flow**
4. **Accept all permissions**

### Database Issues

**Problem**: "No invoice records found"

```bash
# Check database has data
python -c "
from src.data.database import DatabaseManager
from src.data.models import InvoiceMetadata
db = DatabaseManager()
with db.get_session() as session:
    count = session.query(InvoiceMetadata).count()
    print(f'Invoice metadata records: {count}')
"
```

## 📈 Usage Tips

1. **Start both servers** (API + ngrok) before importing
2. **Test API connection** before importing data
3. **Use filters** to limit data for large datasets
4. **Schedule imports** by running the import function periodically
5. **Monitor ngrok dashboard** at http://127.0.0.1:4040

## 🔒 Security Notes

- **Ngrok URLs are public** - don't share them unnecessarily
- **API has no authentication** - consider adding API keys for production
- **Use HTTPS ngrok tunnels** for data security
- **Monitor ngrok usage** to avoid hitting free tier limits

## 🎉 Success!

Once set up, you can:
- **Refresh data** by running the import again
- **Filter data** by modifying API filters
- **Schedule imports** using Google Apps Script triggers
- **Share sheets** with team members for analysis

Your CFDI invoice metadata is now accessible in Google Sheets for business analysis!

---

## 🆘 Getting Help

If you encounter issues:

1. **Check logs** in all three terminals
2. **Test each component** individually
3. **Verify URLs** and configuration
4. **Review error messages** carefully

For additional support, check the API documentation at your ngrok URL + `/docs` 