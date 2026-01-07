#!/usr/bin/env python3
"""Test script to verify cutscene imports work correctly."""

import sys
import os

# Add parent directory to path (the repository root), same as main.py does
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(SCRIPT_DIR)  # code directory
ROOT_DIR = os.path.dirname(CODE_DIR)  # repository root
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Add code directory to path so we can import from cutscenes
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

def test_cutscene_imports():
    """Test that cutscene imports work without errors."""
    print("Testing cutscene imports...")
    
    try:
        # Test import from cutscenes package
        from cutscenes.registry import get_cutscene
        print("✓ Successfully imported get_cutscene from cutscenes.registry")
        
        # Test that we can retrieve cutscenes
        opening = get_cutscene("opening_raya_demo")
        print(f"✓ Retrieved 'opening_raya_demo' cutscene: {opening.get('time_label')}")
        
        hospital = get_cutscene("test_raya_enters_hospital")
        print(f"✓ Retrieved 'test_raya_enters_hospital' cutscene: {hospital.get('time_label')}")
        
        # Test CutSceneManager import (requires pygame, may fail in test environment)
        try:
            from cutscenes.runner import CutSceneManager
            print("✓ Successfully imported CutSceneManager from cutscenes.runner")
        except ImportError as e:
            if 'pygame' in str(e).lower():
                print("⚠ Skipping CutSceneManager import (pygame not available in test environment)")
            else:
                raise
        
        print("\n✅ All critical cutscene imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except KeyError as e:
        print(f"❌ Missing cutscene: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cutscene_imports()
    sys.exit(0 if success else 1)
