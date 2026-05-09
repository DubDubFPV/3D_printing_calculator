"""
Test Script - Verify installation and test extraction
Run this to verify Tesseract is installed and the extractor works
"""

import sys
import os
from pathlib import Path


def test_imports():
    """Test that all required packages can be imported"""
    print("="*70)
    print("STEP 1: Testing Python Package Imports")
    print("="*70)
    
    required_packages = ['PIL', 'pytesseract', 'dataclasses', 're', 'json']
    
    for package in required_packages:
        try:
            if package == 'PIL':
                from PIL import Image
            elif package == 'pytesseract':
                import pytesseract
            elif package == 'dataclasses':
                from dataclasses import dataclass
            elif package == 're':
                import re
            elif package == 'json':
                import json
            
            print(f"✓ {package} - OK")
        except ImportError as e:
            print(f"✗ {package} - FAILED: {e}")
            return False
    
    return True


def test_tesseract():
    """Test that Tesseract OCR is installed and working"""
    print("\n" + "="*70)
    print("STEP 2: Testing Tesseract OCR Installation")
    print("="*70)
    
    try:
        import pytesseract
        from PIL import Image
        import subprocess
        
        # Try to find tesseract
        paths_to_try = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            'tesseract'  # System PATH
        ]
        
        tesseract_path = None
        for path in paths_to_try:
            try:
                result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    tesseract_path = path
                    print(f"✓ Found Tesseract at: {path}")
                    print(f"  Version info: {result.stdout.split(chr(10))[0]}")
                    break
            except:
                continue
        
        if not tesseract_path:
            print("✗ Tesseract not found")
            print("\n  Installation instructions:")
            print("  1. Download: https://github.com/UB-Mannheim/tesseract/wiki")
            print("  2. Run installer (default path: C:\\Program Files\\Tesseract-OCR)")
            print("  3. Or install via: choco install tesseract")
            return False, None
        
        return True, tesseract_path
        
    except Exception as e:
        print(f"✗ Error checking Tesseract: {e}")
        return False, None


def test_extractor_import():
    """Test that the extractor module can be imported"""
    print("\n" + "="*70)
    print("STEP 3: Testing Extractor Module Import")
    print("="*70)
    
    try:
        from slicer_data_extractor import SlicerDataExtractor, get_exportable_variables_schema
        print("✓ SlicerDataExtractor module imported successfully")
        
        # Test schema function
        schema = get_exportable_variables_schema()
        print(f"✓ Variables schema loaded ({len(schema)} categories)")
        
        for category in schema.keys():
            var_count = len(schema[category])
            print(f"  - {category}: {var_count} variables")
        
        return True
    except ImportError as e:
        print(f"✗ Failed to import extractor: {e}")
        print(f"  Make sure slicer_data_extractor.py is in the same directory")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_extractor_functionality(tesseract_path):
    """Test extractor with a sample image or OCR text"""
    print("\n" + "="*70)
    print("STEP 4: Testing Extractor Functionality")
    print("="*70)
    
    try:
        from slicer_data_extractor import SlicerDataExtractor, TimeData, FilamentData
        
        # Initialize extractor
        extractor = SlicerDataExtractor(tesseract_path=tesseract_path)
        print("✓ Extractor initialized successfully")
        
        # Test data parsing with mock OCR text
        test_scenarios = [
            {
                'name': 'IdeaMaker Format',
                'text': 'Total time: 3h50m\nTotal: 66.11 g',
                'expected_time_hours': 3,
                'expected_filament_g': 66.11
            },
            {
                'name': 'BambuStudio Format',
                'text': 'Time: 11 hours, 48 min, 31 sec\nMaterial: 377.2 g',
                'expected_time_hours': 11,
                'expected_filament_g': 377.2
            },
            {
                'name': 'Time with seconds',
                'text': '3h41m0s and 28.86 g',
                'expected_time_hours': 3,
                'expected_filament_g': 28.86
            }
        ]
        
        print("\nTesting text parsing:")
        all_passed = True
        for scenario in test_scenarios:
            time_data = extractor._parse_time(scenario['text'])
            filament_data = extractor._parse_filament(scenario['text'], 'Unknown')
            
            time_match = time_data.hours == scenario['expected_time_hours']
            filament_match = filament_data.amount_grams == scenario['expected_filament_g']
            
            status = "✓" if (time_match and filament_match) else "✗"
            print(f"  {status} {scenario['name']}")
            
            if not time_match:
                print(f"     Time mismatch: got {time_data.hours}h, expected {scenario['expected_time_hours']}h")
                all_passed = False
            if not filament_match:
                print(f"     Filament mismatch: got {filament_data.amount_grams}g, expected {scenario['expected_filament_g']}g")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"✗ Error during functionality test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_real_image(tesseract_path):
    """Test with real image if provided"""
    print("\n" + "="*70)
    print("STEP 5: Testing with Real Screenshot (Optional)")
    print("="*70)
    
    # Look for test images in common locations
    test_image_paths = [
        Path.cwd() / 'test.png',
        Path.cwd() / 'test.jpg',
        Path.cwd() / 'screenshot.png',
        Path.cwd() / 'screenshot.jpg',
    ]
    
    test_image = None
    for path in test_image_paths:
        if path.exists():
            test_image = path
            break
    
    if test_image:
        print(f"Found test image: {test_image}")
        try:
            from slicer_data_extractor import SlicerDataExtractor
            extractor = SlicerDataExtractor(tesseract_path=tesseract_path)
            
            result = extractor.extract_from_file(str(test_image))
            data = result.to_dict()
            
            print(f"✓ Successfully extracted from {test_image.name}")
            print(f"\n  Results:")
            print(f"  - Print Time: {data['print_time']['formatted']}")
            print(f"  - Filament: {data['filament']['formatted']}")
            print(f"  - Confidence: {data['confidence']}")
            print(f"  - Slicer: {data['slicer_detected']}")
            
            return True
        except Exception as e:
            print(f"✗ Error processing image: {e}")
            return False
    else:
        print("No test image found (optional - skipping)")
        print("  To test with real image, place a screenshot in:")
        for path in test_image_paths:
            print(f"    - {path}")
        return None  # Optional, not a failure


def print_summary(results):
    """Print test summary"""
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    
    for test_name, result in results.items():
        symbol = "✓" if result is True else ("✗" if result is False else "-")
        status = "PASS" if result is True else ("FAIL" if result is False else "SKIP")
        print(f"  {symbol} {test_name}: {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0:
        print("\n✓ All required tests passed! You're ready to use the extractor.")
        return True
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("SLICER DATA EXTRACTOR - INSTALLATION TEST")
    print("="*70 + "\n")
    
    results = {}
    
    # Test 1: Imports
    results['Package Imports'] = test_imports()
    if not results['Package Imports']:
        print("\n✗ STOPPING: Install missing packages with:")
        print("  pip install pillow pytesseract")
        return False
    
    # Test 2: Tesseract
    tesseract_ok, tesseract_path = test_tesseract()
    results['Tesseract OCR'] = tesseract_ok
    if not tesseract_ok:
        print("\n! WARNING: Tesseract not found. Install it to use real screenshots.")
        tesseract_path = None
    
    # Test 3: Extractor import
    results['Extractor Module'] = test_extractor_import()
    if not results['Extractor Module']:
        print("\n✗ STOPPING: Cannot import extractor module.")
        return False
    
    # Test 4: Functionality (doesn't require tesseract)
    results['Extractor Parsing'] = test_extractor_functionality(tesseract_path)
    
    # Test 5: Real image (optional)
    if tesseract_path:
        image_result = test_with_real_image(tesseract_path)
        if image_result is not None:
            results['Real Screenshot'] = image_result
    
    # Summary
    success = print_summary(results)
    
    if success:
        print("\n" + "="*70)
        print("NEXT STEPS:")
        print("="*70)
        print("""
1. Read the setup guide:
   - Open SETUP.md

2. Review available variables:
   - Open VARIABLES_REFERENCE.md

3. Check integration examples:
   - Open integration_examples.py

4. Use the extractor in your code:
   
   from slicer_data_extractor import SlicerDataExtractor
   
   extractor = SlicerDataExtractor(
       tesseract_path=r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
   )
   
   result = extractor.extract_from_file('screenshot.png')
   data = result.to_dict()
   
   print(f"Time: {data['print_time']['hours']}h {data['print_time']['minutes']}m")
   print(f"Filament: {data['filament']['amount_grams']}g")
        """)
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
