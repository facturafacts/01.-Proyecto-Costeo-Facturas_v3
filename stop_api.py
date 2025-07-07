#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Stopper - Stop the CFDI Dashboard API
Run this from anywhere: python stop_api.py
"""

import subprocess
import sys
import platform

def stop_api():
    """Stop the running API server."""
    
    print(" Stopping CFDI Dashboard API Server")
    print("=" * 50)
    
    try:
        system = platform.system()
        
        if system == "Windows":
            # Find Python processes running uvicorn or run_api.py
            cmd = ['tasklist', '/fi', 'imagename eq python.exe', '/fo', 'csv']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse the output to find API processes
                lines = result.stdout.strip().split('\n')
                api_pids = []
                
                for line in lines[1:]:  # Skip header
                    if 'python.exe' in line:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            pid = parts[1].strip('"')
                            # Check if this is our API process
                            try:
                                detail_cmd = ['tasklist', '/fi', f'pid eq {pid}', '/v', '/fo', 'csv']
                                detail_result = subprocess.run(detail_cmd, capture_output=True, text=True)
                                if 'uvicorn' in detail_result.stdout or 'run_api' in detail_result.stdout:
                                    api_pids.append(pid)
                            except:
                                pass
                
                if api_pids:
                    for pid in api_pids:
                        try:
                            subprocess.run(['taskkill', '/f', '/pid', pid], 
                                         check=True, capture_output=True)
                            print(f" Stopped API process (PID: {pid})")
                        except subprocess.CalledProcessError:
                            print(f"  Could not stop process {pid}")
                else:
                    print(" No running API processes found")
            else:
                print(" Could not check running processes")
                
        else:
            # Unix-like systems (Linux, macOS)
            try:
                # Find processes running uvicorn or containing run_api
                cmd = ['pgrep', '-f', '(uvicorn|run_api)']
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            try:
                                subprocess.run(['kill', '-TERM', pid], check=True)
                                print(f" Stopped API process (PID: {pid})")
                            except subprocess.CalledProcessError:
                                print(f"  Could not stop process {pid}")
                else:
                    print(" No running API processes found")
                    
            except FileNotFoundError:
                print(" pgrep command not found. Trying alternative method...")
                # Alternative: use ps and grep
                try:
                    cmd = ['ps', 'aux']
                    ps_result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if ps_result.returncode == 0:
                        lines = ps_result.stdout.split('\n')
                        for line in lines:
                            if 'uvicorn' in line or 'run_api' in line:
                                parts = line.split()
                                if len(parts) >= 2:
                                    pid = parts[1]
                                    try:
                                        subprocess.run(['kill', '-TERM', pid], check=True)
                                        print(f" Stopped API process (PID: {pid})")
                                    except subprocess.CalledProcessError:
                                        print(f"  Could not stop process {pid}")
                    else:
                        print(" Could not list processes")
                        
                except FileNotFoundError:
                    print(" Could not find process management tools")
    
    except Exception as e:
        print(f" Error stopping API: {e}")
        return
    
    print("=" * 50)
    print(" API stop completed")
    print(" To start again, run: python run_api.py")

if __name__ == "__main__":
    stop_api()
