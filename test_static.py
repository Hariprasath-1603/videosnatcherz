#!/usr/bin/env python3
"""
Static Files Test Script
Run this to verify static files are configured correctly
"""

import sys
import os
from pathlib import Path

def test_static_files():
    """Test that all static files exist and are readable"""
    
    print("Testing Static Files Configuration...")
    print("=" * 50)
    
    # Expected static files
    static_files = [
        "static/style.css",
        "static/app.js",
        "static/nav.js",
        "static/favicon.svg"
    ]
    
    # Expected template files
    template_files = [
        "templates/base.html",
        "templates/home.html",
        "templates/downloader.html",
        "templates/features.html",
        "templates/about.html",
        "templates/faq.html",
        "templates/contact.html",
        "templates/privacy.html"
    ]
    
    passed = 0
    failed = 0
    
    # Test static files exist
    print("\n1. Checking static files...")
    for file_path in static_files:
        if Path(file_path).exists():
            size = Path(file_path).stat().st_size
            print(f"  ✓ {file_path} ({size:,} bytes)")
            passed += 1
        else:
            print(f"  ✗ {file_path} NOT FOUND")
            failed += 1
    
    # Test template files exist
    print("\n2. Checking template files...")
    for file_path in template_files:
        if Path(file_path).exists():
            print(f"  ✓ {file_path}")
            passed += 1
        else:
            print(f"  ✗ {file_path} NOT FOUND")
            failed += 1
    
    # Test template paths
    print("\n3. Checking template paths...")
    base_template = Path("templates/base.html")
    if base_template.exists():
        content = base_template.read_text(encoding='utf-8')
        
        # Check for absolute paths
        if 'href="/static/' in content and 'src="/static/' in content:
            print("  ✓ Templates use absolute paths (/static/)")
            passed += 1
        else:
            print("  ✗ Templates may not use absolute paths")
            failed += 1
        
        # Check for version parameters
        if '?v=' in content:
            print("  ✓ Cache busting version parameters found")
            passed += 1
        else:
            print("  ⚠ Version parameters not found (optional)")
    else:
        print("  ✗ base.html not found")
        failed += 1
    
    # Test main.py configuration
    print("\n4. Checking main.py configuration...")
    main_py = Path("main.py")
    if main_py.exists():
        content = main_py.read_text(encoding='utf-8')
        
        if 'StaticFiles' in content:
            print("  ✓ StaticFiles imported")
            passed += 1
        else:
            print("  ✗ StaticFiles not imported")
            failed += 1
        
        if 'app.mount("/static"' in content or 'app.mount(\'/static\'' in content:
            print("  ✓ Static files mounted at /static")
            passed += 1
        else:
            print("  ✗ Static files not mounted correctly")
            failed += 1
        
        if 'GZipMiddleware' in content:
            print("  ✓ GZip compression enabled")
            passed += 1
        else:
            print("  ✗ GZip compression not enabled")
            failed += 1
    else:
        print("  ✗ main.py not found")
        failed += 1
    
    # Test Python imports
    print("\n5. Testing Python imports...")
    try:
        import fastapi
        print(f"  ✓ FastAPI {fastapi.__version__} installed")
        passed += 1
    except ImportError:
        print("  ✗ FastAPI not installed")
        failed += 1
    
    try:
        import uvicorn
        print(f"  ✓ Uvicorn installed")
        passed += 1
    except ImportError:
        print("  ✗ Uvicorn not installed")
        failed += 1
    
    try:
        import yt_dlp
        print(f"  ✓ yt-dlp installed")
        passed += 1
    except ImportError:
        print("  ✗ yt-dlp not installed")
        failed += 1
    
    try:
        import jinja2
        print(f"  ✓ Jinja2 {jinja2.__version__} installed")
        passed += 1
    except ImportError:
        print("  ✗ Jinja2 not installed")
        failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    if failed == 0:
        print("\n✓ All checks passed! Ready for deployment.")
        return 0
    else:
        print(f"\n✗ {failed} check(s) failed. Please fix before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(test_static_files())
