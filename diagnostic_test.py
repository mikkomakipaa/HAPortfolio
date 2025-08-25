#!/usr/bin/env python3
"""
Diagnostic script for Portfolio Tracker integration.
Run this script to identify potential issues preventing the integration from loading.
"""

import json
import sys
from pathlib import Path

def test_imports():
    """Test critical imports."""
    print("Testing critical imports...")
    
    # Test zoneinfo
    try:
        from zoneinfo import ZoneInfo
        print("✅ zoneinfo available")
    except ImportError:
        try:
            from backports.zoneinfo import ZoneInfo
            print("✅ backports.zoneinfo available")
        except ImportError:
            print("⚠️  zoneinfo not available - will use UTC fallback")
    
    # Test voluptuous
    try:
        import voluptuous as vol
        print("✅ voluptuous available")
    except ImportError:
        print("❌ voluptuous not available - service registration will fail")
    
    # Test InfluxDB
    try:
        from influxdb import InfluxDBClient
        print("✅ influxdb client available")
    except ImportError:
        print("❌ influxdb client not available - core functionality will fail")
    
    # Test Google API
    try:
        from googleapiclient.discovery import build
        from google.oauth2.service_account import Credentials
        print("✅ Google API client available")
    except ImportError:
        print("❌ Google API client not available - Google Sheets functionality will fail")

def test_manifest():
    """Test manifest.json validity."""
    print("\nTesting manifest.json...")
    
    manifest_path = Path("custom_components/portfolio_tracker/manifest.json")
    if not manifest_path.exists():
        print("❌ manifest.json not found")
        return False
    
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        required_fields = ["domain", "name", "version", "requirements"]
        for field in required_fields:
            if field not in manifest:
                print(f"❌ Missing required field: {field}")
                return False
        
        print("✅ manifest.json is valid")
        print(f"   Domain: {manifest['domain']}")
        print(f"   Version: {manifest['version']}")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in manifest: {e}")
        return False

def test_file_structure():
    """Test required file structure."""
    print("\nTesting file structure...")
    
    base_path = Path("custom_components/portfolio_tracker")
    required_files = [
        "__init__.py",
        "manifest.json", 
        "config_flow.py",
        "const.py",
        "portfolio_manager.py",
        "sensor.py",
        "binary_sensor.py"
    ]
    
    all_present = True
    for file in required_files:
        file_path = base_path / file
        if file_path.exists():
            print(f"✅ {file}")
        else:
            print(f"❌ Missing: {file}")
            all_present = False
    
    return all_present

def test_syntax():
    """Test Python syntax in key files."""
    print("\nTesting Python syntax...")
    
    base_path = Path("custom_components/portfolio_tracker")
    python_files = ["__init__.py", "config_flow.py", "portfolio_manager.py"]
    
    all_valid = True
    for file in python_files:
        file_path = base_path / file
        if not file_path.exists():
            continue
            
        try:
            with open(file_path) as f:
                compile(f.read(), str(file_path), 'exec')
            print(f"✅ {file}")
        except SyntaxError as e:
            print(f"❌ Syntax error in {file}: {e}")
            all_valid = False
        except Exception as e:
            print(f"❌ Error compiling {file}: {e}")
            all_valid = False
    
    return all_valid

def main():
    """Run all diagnostic tests."""
    print("Portfolio Tracker Integration Diagnostic")
    print("=" * 45)
    
    # Change to the correct directory
    import os
    if not os.path.exists("custom_components"):
        print("❌ Run this script from the HAPortfolio repository root")
        sys.exit(1)
    
    test_imports()
    manifest_ok = test_manifest()
    files_ok = test_file_structure()
    syntax_ok = test_syntax()
    
    print("\n" + "=" * 45)
    if manifest_ok and files_ok and syntax_ok:
        print("✅ All basic checks passed!")
        print("\nIf the integration is still failing silently:")
        print("1. Check Home Assistant logs: Settings > System > Logs")
        print("2. Look for Portfolio Tracker entries")
        print("3. Check that dependencies are installed in HA environment")
        print("4. Verify InfluxDB and Google Sheets configuration")
    else:
        print("❌ Some checks failed - fix these issues first")

if __name__ == "__main__":
    main()