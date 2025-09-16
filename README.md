# CFDI Processing System v4

A comprehensive system for processing Mexican CFDI (Comprobante Fiscal Digital por Internet) XML files with AI-powered classification and business intelligence.

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Copy environment configuration
cp config/env.example .env

# Edit .env with your actual credentials
# IMPORTANT: If using Gemini, set GEMINI_API_KEY. For local Ollama, set AI_PROVIDER=ollama
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
python main.py --setup
```

### 4. Process XML Files

```bash
# Process all files in data/inbox/
python main.py

# Process a single file
python main.py --file path/to/invoice.xml
```

## 📁 Directory Structure

```
├── config/           # Configuration files
├── data/
│   ├── inbox/       # XML files to process
│   ├── processed/   # Successfully processed files
│   ├── failed/      # Failed processing files
│   └── database/    # SQLite database
├── logs/            # Application logs
├── src/
│   ├── data/        # Database models and operations
│   ├── processing/  # Core processing logic
│   └── utils/       # Utility functions
├── scripts/         # Setup and maintenance scripts
└── tests/           # Test suite
```

## 🔧 Configuration

Key environment variables in `.env`:

```bash
# AI Provider
# Use Gemini (default) or local Ollama
AI_PROVIDER=ollama

# If AI_PROVIDER=gemini
# GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash

# If AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:1.5b

# Database
DATABASE_URL=sqlite:///data/database/cfdi_system_v4.db

# Processing
LOG_LEVEL=INFO
BATCH_SIZE=10
```

## 🗄️ Database Schema

The system uses 5 main tables:
- `invoices` - Main invoice data
- `invoice_items` - Individual line items
- `invoice_metadata` - Business logic and quick stats
- `approved_skus` - Human-approved classifications
- `processing_logs` - System events and errors

## 🎯 Features

- **XML Parsing**: Complete CFDI field extraction
- **AI Classification**: Gemini or local Ollama-powered product categorization
- **Business Logic**: Currency conversion, payment terms analysis
- **Error Handling**: Comprehensive logging and recovery
- **SKU Management**: Human-approved classification system

- **Ollama**: For local, private classification. The recommended model is `llama3.1:8b-instruct-q4_0` for its balance of speed and accuracy on CPUs.

To switch to Ollama, set the following in your `.env` file:
```
AI_PROVIDER=ollama
OLLAMA_MODEL=llama3.1:8b-instruct-q4_0
```

Make sure to pull the model before running the application:
```bash
ollama pull llama3.1:8b-instruct-q4_0
```

## 🚀 Deployment to DigitalOcean

### Prerequisites
- DigitalOcean account
- Docker (optional, for containerized deployment)
- Domain name (optional, for custom domain)

### Environment Variables for Production

Update your `.env` for production:

```bash
ENVIRONMENT=prod
DEBUG=False
DATABASE_URL=postgresql://user:password@your-db-host:5432/cfdi_db
```

### Deployment Steps

1. **Prepare for deployment**:
```bash
# Test locally first
python main.py --setup
python main.py  # Process any test files
```

2. **Commit your changes**:
```bash
git add .
git commit -m "Restore CFDI processing system functionality"
git push origin feat/cloud-deployment
```

3. **Deploy to DigitalOcean** (follow your specific deployment process)

## 📝 Usage Examples

### Basic Processing
```bash
# Initialize system
python main.py --setup

# Process inbox
python main.py
```

### Database Management
```bash
# Create purchase details table for exports
python main.py --create-purchase-table

# Check system status
python scripts/05_diagnostics/check_tables.py
```

### SKU Approval
```bash
# Review and approve classifications
python scripts/03_sku_approval/excel_approval.py
```

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Issues**: Reinitialize if needed
   ```bash
   python main.py --setup
   ```

3. **Missing API Key**: Check your `.env` file
   ```bash
   # Make sure GEMINI_API_KEY is set
   cat .env | grep GEMINI_API_KEY
   ```

## 📊 Monitoring

Check logs for processing status:
```bash
tail -f logs/cfdi_processing.log
tail -f logs/cfdi_errors.log
```

## 🔄 Updates

To update dependencies:
```bash
pip install -r requirements.txt --upgrade
```

## 📞 Support

For issues or questions:
1. Check the logs in the `logs/` directory
2. Review the error messages
3. Ensure all environment variables are set correctly

---

**Note**: This system processes Mexican tax documents. Ensure compliance with local data protection and tax regulations. 