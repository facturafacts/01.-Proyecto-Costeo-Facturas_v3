#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Runner - Permanent solution for CFDI Dashboard API
Run this from project root: python run_api.py
"""

import sys
import os
import socket
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Change to project directory to ensure relative paths work
os.chdir(project_root)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_free_port(start_port=8000, max_attempts=10):
    """Find a free port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    
    raise RuntimeError(f"No free ports found in range {start_port}-{start_port + max_attempts}")

def test_dashboard_data():
    """Test if dashboard data exists"""
    try:
        import sqlite3
        
        # Use direct SQLite connection for reliability
        conn = sqlite3.connect('data/database/cfdi_system_v4.db')
        cursor = conn.cursor()
        
        # Test if dashboard tables exist and have data
        tables_to_check = [
            'sales_weekly_summary',
            'sales_product_performance', 
            'real_time_metrics',
            'weekly_kpis'
        ]
        
        results = {}
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                results[table] = count
            except Exception:
                results[table] = 0
        
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Error checking dashboard data: {e}")
        return {}

def main():
    """Start the CFDI Dashboard API server with full error handling."""
    
    print(" Starting CFDI Dashboard API Server")
    print("=" * 60)
    
    # Check dashboard data first
    print(" Checking dashboard data availability...")
    data_status = test_dashboard_data()
    
    if data_status:
        for table, count in data_status.items():
            status = "" if count > 0 else " "
            print(f"   {status} {table}: {count} records")
    else:
        print("     Unable to check dashboard data")
    
    print()  # Empty line for readability
    
    if not any(data_status.values()):
        print(" No dashboard data found. To populate data, run:")
        print("   python scripts/02_dashboard/populate_sales_only.py")
        print("   python scripts/02_dashboard/populate_kpis.py")
        print("\n Continue anyway? (y/n): ", end="")
        if input().lower() != 'y':
            return
    
    # Import after path setup
    try:
        import uvicorn
        from src.api import app  # This uses your __init__.py!
        print(" API modules loaded successfully")
    except ImportError as e:
        print(f" Error importing API modules: {e}")
        print(" Make sure you're running from the project root directory")
        return
    except Exception as e:
        print(f" Unexpected error: {e}")
        return
    
    # Find available port
    try:
        api_port = find_free_port(8000)
        print(f" Using port {api_port}")
    except RuntimeError as e:
        print(f" {e}")
        return
    
    # Show available endpoints
    print(f"\n API Documentation: http://127.0.0.1:{api_port}/docs")
    print(f" Health Check: http://127.0.0.1:{api_port}/api/health")
    print(f"\n Dashboard Endpoints:")
    print(f"    Sales: http://127.0.0.1:{api_port}/api/dashboard/sales")
    print(f"    Expenses: http://127.0.0.1:{api_port}/api/dashboard/expenses")
    print(f"    KPIs: http://127.0.0.1:{api_port}/api/dashboard/kpis")
    print(f"\n Legacy Endpoints:")
    print(f"    Metadata: http://127.0.0.1:{api_port}/api/invoices/metadata")
    print(f"\n Ready for ngrok tunnel!")
    print(f" In another terminal, run: ngrok http {api_port}")
    print("=" * 60)
    
    try:
        # Use your existing app from __init__.py
        uvicorn.run(
            app,
            host="127.0.0.1", 
            port=api_port,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n Server stopped by user")
    except Exception as e:
        print(f" Failed to start server: {e}")
        print(" Try running as administrator or check firewall settings")

if __name__ == "__main__":
    main()
