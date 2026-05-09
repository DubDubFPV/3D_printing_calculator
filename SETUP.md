# 3D Slicer Data Extractor - Setup Guide

## Overview
This tool extracts print time and filament data from 3D slicer screenshots (IdeaMaker, BambuStudio). It uses OCR to read the screenshots and returns structured, node-friendly data.

## Installation

### 1. Install Tesseract OCR

**Windows (RECOMMENDED - Manual Installer):**
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
   - Look for: `tesseract-ocr-w64-setup-v5.x.exe` (latest version)
2. Run the installer
3. Choose installation path: `C:\Program Files\Tesseract-OCR` (default is fine)
4. Complete the installation
5. Verify by opening PowerShell and typing: `tesseract --version`

**If Chocolatey install fails:**
The Chocolatey method may not properly add Tesseract to PATH. Use the manual installer above instead.

**If you already tried Chocolatey:**
- Uninstall: `choco uninstall tesseract`
- Use manual installer instead (recommended)

### 2. Install Python Dependencies

```bash
pip install pillow pytesseract
```

## Quick Start

```python
from slicer_data_extractor import SlicerDataExtractor

# Initialize with Tesseract path (Windows)
extractor = SlicerDataExtractor(
    tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
)

# Extract from screenshot
result = extractor.extract_from_file('screenshot.png')

# Get dictionary with all variables
data = result.to_dict()

# Access variables
print(f"Time: {data['print_time']['hours']}h {data['print_time']['minutes']}m {data['print_time']['seconds']}s")
print(f"Filament: {data['filament']['amount_grams']}g")
print(f"Confidence: {data['confidence']}")
```

## Available Variables (for node integration)

### Print Time Variables
- `print_time.hours` - Hours (integer)
- `print_time.minutes` - Minutes (0-59)
- `print_time.seconds` - Seconds (0-59)
- `print_time.total_seconds` - Total seconds (float)
- `print_time.formatted` - Formatted string like "3h 41m 0s"

### Filament Variables
- `filament.amount` - Original amount value
- `filament.unit` - Original unit ('g' or 'kg')
- `filament.amount_grams` - Amount in grams (normalized)
- `filament.amount_kilograms` - Amount in kilograms (normalized)
- `filament.formatted` - Formatted string

### Filament Length Variables (if available)
- `filament_length.amount` - Length value (float)
- `filament_length.unit` - 'm' for meters
- `filament_length.formatted` - Formatted string

### Processing Options Variables (boolean flags)
- `processing_options.travel`
- `processing_options.retract`
- `processing_options.unretract`
- `processing_options.wipe`
- `processing_options.seams`

### Metadata Variables
- `confidence` - 0.0-1.0 confidence score
- `slicer_detected` - "IdeaMaker", "BambuStudio", or "Unknown"
- `raw_text` - Raw OCR text

## JSON Output Format

The extractor can output results as JSON for easy integration with other systems:

```python
result = extractor.extract_from_file('screenshot.png')
json_output = result.to_json()

# Or get dictionary
data = result.to_dict()
```

Example JSON structure:
```json
{
  "print_time": {
    "hours": 3,
    "minutes": 41,
    "seconds": 0,
    "total_seconds": 13260.0,
    "formatted": "3h 41m 0s"
  },
  "filament": {
    "amount": 66.11,
    "unit": "g",
    "amount_grams": 66.11,
    "amount_kilograms": 0.06611,
    "formatted": "66.11 g"
  },
  "filament_length": null,
  "processing_options": {
    "travel": true,
    "retract": true,
    "unretract": false,
    "wipe": true,
    "seams": true
  },
  "confidence": 1.0,
  "slicer_detected": "IdeaMaker",
  "raw_text": "..."
}
```

## Supported Screenshot Formats

### IdeaMaker
- Shows time as: "Total time: Xh Ym" or variations
- Shows filament as: "Total: XXg" or "XXg"
- Includes processing options display

### BambuStudio
- Shows time in various formats
- Shows filament weight
- May include multiple filament entries for multi-color prints

## Troubleshooting

### Tesseract not found
**Error:** `FileNotFoundError: tesseract is not installed or it's not in your PATH`

**Solution:**
1. Install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
2. Or, specify the path explicitly:
```python
extractor = SlicerDataExtractor(
    tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
)
```

### Poor OCR recognition
- Ensure screenshot has good contrast
- Avoid cropped or blurry images
- Check confidence score (`data['confidence']`)

### Incorrect extraction
- Check `raw_text` field to see what OCR detected
- Verify slicer is supported (IdeaMaker or BambuStudio)
- Low confidence may indicate unclear screenshot

## Integration Examples

### Example 1: Node-RED Integration
```python
# Export as JSON for Node-RED
result = extractor.extract_from_file('screenshot.png')
json_data = result.to_json()
# Pass json_data to Node-RED input
```

### Example 2: Custom Processing Mode Based on Options
```python
result = extractor.extract_from_file('screenshot.png')
data = result.to_dict()

if data['processing_options']['retract']:
    print("Retract mode active - use retract settings")
elif data['processing_options']['travel']:
    print("Travel mode active - use travel settings")
```

### Example 3: Error Handling with Confidence
```python
result = extractor.extract_from_file('screenshot.png')
data = result.to_dict()

if data['confidence'] >= 0.9:
    # Use extracted data
    process_print_job(data)
else:
    # Request manual verification
    print(f"Low confidence ({data['confidence']}) - manual review needed")
```

## File Format Support
- PNG ✓
- JPG/JPEG ✓
- BMP ✓
- Other PIL-supported formats ✓
