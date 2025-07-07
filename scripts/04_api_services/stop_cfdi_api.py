#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stop CFDI API Server

Simple script to stop the running FastAPI server.
"""

import sys
import psutil
import requests
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def check_api_running():
    """Check if API is responding."""
    try:
        from config.settings import get_settings
        settings = get_settings()
        
        response = requests.get(
            f"http://{settings.API_HOST}:{settings.API_PORT}/api/health", 
            timeout=2
        )
        return response.status_code == 200
    except:
        return False

def find_and_stop_api():
    """Find and stop API server processes."""
    
    print("🛑 Stopping CFDI API Server...")
    print("=" * 40)
    
    # Check if API is responding
    if check_api_running():
        print("✅ API server is currently running")
    else:
        print("⚠️  API server doesn't seem to be responding")
        print("❌ No action needed - server is already stopped")
        return True
    
    stopped_count = 0
    
    # Look for Python processes using port 8000
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                # Check if process is using port 8000
                connections = proc.connections()
                for conn in connections:
                    if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == 8000:
                        print(f"🎯 Found API server process: PID {proc.pid}")
                        
                        # Terminate gracefully
                        proc.terminate()
                        
                        try:
                            proc.wait(timeout=5)
                            print(f"✅ Stopped process {proc.pid}")
                            stopped_count += 1
                        except psutil.TimeoutExpired:
                            # Force kill if needed
                            proc.kill()
                            print(f"⚠️  Force killed process {proc.pid}")
                            stopped_count += 1
                        break
                        
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Verify it's stopped
    if not check_api_running():
        print(f"✅ API server successfully stopped ({stopped_count} processes)")
        return True
    else:
        print("❌ API server might still be running")
        return False

def main():
    """Main function."""
    
    try:
        if find_and_stop_api():
            print("\n🎯 Server stopped successfully!")
            print("\n📋 You can now:")
            print("   • Start the server again with: python scripts/start_cfdi_api.py")
            print("   • Check if it's stopped: python -c \"import requests; requests.get('http://localhost:8000/api/health')\"")
        else:
            print("\n🔧 Manual stop required:")
            print("   • Press CTRL+C in the terminal running the API")
            print("   • Or use Task Manager to end python.exe processes")
            print("   • Or run: taskkill /f /im python.exe")
            
    except Exception as e:
        print(f"❌ Error stopping server: {e}")
        print("\n🔧 Manual alternatives:")
        print("   1. Press CTRL+C in the API terminal")
        print("   2. Close the terminal window")
        print("   3. Use: taskkill /f /im python.exe")

if __name__ == "__main__":
    main() 