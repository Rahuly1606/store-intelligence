"""
Test script for Step 1: Project Setup & Configuration
"""

import sys
import os
from pathlib import Path

# Add frontend directory to path
frontend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(frontend_dir))
os.chdir(str(frontend_dir))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from app.config import get_config, DevelopmentConfig
        print("[PASS] Config module imported")
        
        from app.models import Video, CameraType, StoreMetrics
        print("[PASS] Models module imported")
        
        from app.utils import ValidationError, FileValidator, MetricsFormatter
        print("[PASS] Utils module imported")
        
        from app.services import APIClient, StorageService, VideoProcessorService
        print("[PASS] Services module imported")
        
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """Test configuration system."""
    print("\nTesting configuration...")
    
    try:
        from app.config import get_config
        
        dev_config = get_config('development')
        assert dev_config.DEBUG == True
        print("[PASS] Development config works")
        
        prod_config = get_config('production')
        assert prod_config.DEBUG == False
        print("[PASS] Production config works")
        
        default_config = get_config()
        assert default_config.DEBUG == True
        print("[PASS] Default config works")
        
        return True
    except Exception as e:
        print(f"[FAIL] Config test failed: {e}")
        return False


def test_models():
    """Test domain models."""
    print("\nTesting domain models...")
    
    try:
        from app.models import Video, CameraType, ProcessingStatus
        from datetime import datetime
        from pathlib import Path
        
        video = Video(
            filename="test.mp4",
            camera_type=CameraType.ENTRY,
            store_id="STORE_TEST_001",
            file_path=Path("/tmp/test.mp4"),
            uploaded_at=datetime.utcnow()
        )
        
        assert video.camera_id == "CAM_ENTRY_01"
        assert video.status == ProcessingStatus.PENDING
        print("[PASS] Video model works")
        
        processing_video = video.mark_processing()
        assert processing_video.is_processing
        print("[PASS] Video state transitions work")
        
        return True
    except Exception as e:
        print(f"[FAIL] Model test failed: {e}")
        return False


def test_validators():
    """Test validation utilities."""
    print("\nTesting validators...")
    
    try:
        from app.utils import CameraTypeValidator, StoreIdValidator
        
        is_valid, error = CameraTypeValidator.validate("entry")
        assert is_valid == True
        print("[PASS] Camera type validator works")
        
        is_valid, error = StoreIdValidator.validate("STORE_BLR_002")
        assert is_valid == True
        print("[PASS] Store ID validator works")
        
        is_valid, error = StoreIdValidator.validate("")
        assert is_valid == False
        assert error is not None
        print("[PASS] Validation error handling works")
        
        return True
    except Exception as e:
        print(f"[FAIL] Validator test failed: {e}")
        return False


def test_formatters():
    """Test formatting utilities."""
    print("\nTesting formatters...")
    
    try:
        from app.utils import TimeFormatter, PercentageFormatter
        
        formatted = TimeFormatter.format_duration(5000)
        assert formatted == "5.0s"
        print("[PASS] Time formatter works")
        
        formatted = PercentageFormatter.format(0.75)
        assert formatted == "75.0%"
        print("[PASS] Percentage formatter works")
        
        return True
    except Exception as e:
        print(f"[FAIL] Formatter test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("STEP 1 VERIFICATION: Project Setup & Configuration")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Domain Models", test_models),
        ("Validators", test_validators),
        ("Formatters", test_formatters)
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
        print("\nStep 1 completed successfully!")
        print("\nNext: Step 2 - Routes & Controllers")
        return 0
    else:
        print("\nSome tests failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
