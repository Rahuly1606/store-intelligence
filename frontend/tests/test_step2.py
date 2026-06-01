"""
Test script for Step 2: Routes & Controllers
"""

import sys
import os
from pathlib import Path

frontend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(frontend_dir))
os.chdir(str(frontend_dir))

def test_routes_import():
    """Test that route modules can be imported."""
    print("Testing route imports...")
    
    try:
        from app.routes import upload_bp, dashboard_bp
        print("[PASS] Routes imported successfully")
        
        assert upload_bp.name == 'upload'
        assert dashboard_bp.name == 'dashboard'
        print("[PASS] Blueprints configured correctly")
        
        return True
    except Exception as e:
        print(f"[FAIL] Route import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_creation():
    """Test Flask app creation."""
    print("\nTesting app creation...")
    
    try:
        from app import create_app
        
        app = create_app('testing')
        print("[PASS] App created successfully")
        
        assert app.config['TESTING'] == True
        print("[PASS] Testing config loaded")
        
        # Check blueprints registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        assert 'upload' in blueprint_names
        assert 'dashboard' in blueprint_names
        print("[PASS] Blueprints registered")
        
        # Check services initialized
        assert 'api_client' in app.extensions
        assert 'storage_service' in app.extensions
        assert 'video_processor' in app.extensions
        print("[PASS] Services initialized")
        
        return True
    except Exception as e:
        print(f"[FAIL] App creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_routes_exist():
    """Test that routes are properly defined."""
    print("\nTesting route definitions...")
    
    try:
        from app import create_app
        
        app = create_app('testing')
        
        # Get all routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(str(rule))
        
        # Check key routes exist
        expected_routes = [
            '/',
            '/dashboard',
            '/api/upload',
            '/api/process',
            '/api/upload-and-process',
            '/api/metrics/<store_id>',
            '/api/funnel/<store_id>',
            '/api/heatmap/<store_id>',
            '/api/health',
            '/api/dashboard-data/<store_id>'
        ]
        
        for expected in expected_routes:
            if expected in routes:
                print(f"[PASS] Route exists: {expected}")
            else:
                print(f"[FAIL] Route missing: {expected}")
                return False
        
        return True
    except Exception as e:
        print(f"[FAIL] Route test failed: {e}")
        return False


def test_templates_exist():
    """Test that template files exist."""
    print("\nTesting template files...")
    
    templates_dir = frontend_dir / 'templates'
    
    required_templates = [
        'base.html',
        'upload.html',
        'dashboard.html'
    ]
    
    all_exist = True
    for template in required_templates:
        template_path = templates_dir / template
        if template_path.exists():
            print(f"[PASS] Template exists: {template}")
        else:
            print(f"[FAIL] Template missing: {template}")
            all_exist = False
    
    return all_exist


def test_static_files_exist():
    """Test that static files exist."""
    print("\nTesting static files...")
    
    static_dir = frontend_dir / 'static'
    
    required_files = [
        'css/custom.css',
        'js/upload.js',
        'js/dashboard.js'
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = static_dir / file_path
        if full_path.exists():
            print(f"[PASS] Static file exists: {file_path}")
        else:
            print(f"[FAIL] Static file missing: {file_path}")
            all_exist = False
    
    return all_exist


def main():
    """Run all tests."""
    print("=" * 60)
    print("STEP 2 VERIFICATION: Routes & Controllers")
    print("=" * 60)
    
    tests = [
        ("Route Imports", test_routes_import),
        ("App Creation", test_app_creation),
        ("Route Definitions", test_routes_exist),
        ("Template Files", test_templates_exist),
        ("Static Files", test_static_files_exist)
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nStep 2 completed successfully!")
        print("\nYou can now run the Flask app:")
        print("  cd frontend")
        print("  python run.py")
        print("\nThen visit: http://localhost:5000")
        return 0
    else:
        print("\nSome tests failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
