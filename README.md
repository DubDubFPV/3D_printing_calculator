# 3D Slicer Data Extractor

Extract print time and filament data from 3D slicer screenshots (IdeaMaker, BambuStudio) using OCR. Get clearly structured variables to integrate with other code.

## Quick Overview

📸 **Input**: Screenshot of slicer output  
🔍 **Process**: OCR + intelligent parsing  
📊 **Output**: Structured variables (hours/minutes/seconds, grams/kilograms, processing options)  
🔗 **Integration**: JSON, dictionaries, or direct variable access

---

## Features

✅ Supports **IdeaMaker** and **BambuStudio** slicers  
✅ Extracts **print time** with individual components (h/m/s)  
✅ Extracts **filament weight** with unit normalization (g/kg)  
✅ Extracts **processing options** (travel, retract, wipe, seams)  
✅ **Node-friendly** - JSON output for Node-RED, databases, APIs  
✅ **Confidence scoring** - Know when extraction is reliable  
✅ **Multiple output formats** - Dictionary, JSON, direct access  

---

## Quick Start

### 1. Install Requirements

```bash
pip install pillow pytesseract
```

**Windows: Install Tesseract OCR**
- Download: https://github.com/UB-Mannheim/tesseract/wiki
- Or: `choco install tesseract`

### 2. Basic Usage

```python
from slicer_data_extractor import SlicerDataExtractor

extractor = SlicerDataExtractor(
    tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
)

result = extractor.extract_from_file('screenshot.png')
data = result.to_dict()

print(f"Time: {data['print_time']['hours']}h {data['print_time']['minutes']}m")
print(f"Filament: {data['filament']['amount_grams']}g")
print(f"Options: Travel={data['processing_options']['travel']}")
```

### GUI Calculator

Launch the desktop calculator to load screenshots, sum total time, sum total filament, and export JSON:

```bash
python gui_calculator.py
```

If you want to start it by double-clicking a file in Windows, open `launch_gui.pyw` instead.

In the GUI you can:
- paste screenshots directly with `Ctrl+V`
- add screenshots from files if you prefer the file picker
- see a live history of jobs created during the current session
- delete the selected job or clear all jobs from the session
- copy the full JSON payload for another node or script

### 3. Test Installation

```bash
python test_installation.py
```

---

## Available Variables

All variables are clearly categorized and easy to access:

### Print Time
```
data['print_time']['hours']         → integer
data['print_time']['minutes']       → integer (0-59)
data['print_time']['seconds']       → integer (0-59)
data['print_time']['total_seconds'] → float
data['print_time']['formatted']     → "3h 41m 0s"
```

### Filament (Weight)
```
data['filament']['amount']             → original value
data['filament']['unit']               → "g" or "kg"
data['filament']['amount_grams']       → normalized to grams
data['filament']['amount_kilograms']   → normalized to kg
data['filament']['formatted']          → "66.11 g"
```

### Processing Options (Boolean)
```
data['processing_options']['travel']    → True/False
data['processing_options']['retract']   → True/False
data['processing_options']['unretract'] → True/False
data['processing_options']['wipe']      → True/False
data['processing_options']['seams']     → True/False
```

### Metadata
```
data['confidence']          → 0.0-1.0 confidence score
data['slicer_detected']     → "IdeaMaker", "BambuStudio", "Unknown"
data['raw_text']            → raw OCR text
```

**➜ See [VARIABLES_REFERENCE.md](VARIABLES_REFERENCE.md) for complete reference**

---

## Integration Examples

### With Node-RED

```python
result = extractor.extract_from_file('screenshot.png')
json_output = result.to_json()  # Send directly to Node-RED
```

### Conditional Processing Based on Options

```python
data = result.to_dict()

if data['processing_options']['retract']:
    mode = "STANDARD"
elif data['processing_options']['travel']:
    mode = "FAST"
else:
    mode = "MINIMAL"
```

### Database Integration

```python
data = result.to_dict()

db.insert({
    'print_time_seconds': int(data['print_time']['total_seconds']),
    'filament_grams': data['filament']['amount_grams'],
    'confidence': data['confidence'],
    'slicer': data['slicer_detected']
})
```

### Quality Assurance

```python
data = result.to_dict()

if data['confidence'] >= 0.8:
    print("✓ Ready for production")
else:
    print(f"✗ Review needed (confidence: {data['confidence']})")
    print(f"Raw text: {data['raw_text']}")
```

**➜ See [integration_examples.py](integration_examples.py) for more patterns**

---

## Files in This Project

| File | Purpose |
|------|---------|
| `slicer_data_extractor.py` | Main extractor class and data structures |
| `SETUP.md` | Installation and troubleshooting guide |
| `VARIABLES_REFERENCE.md` | Complete variable reference and examples |
| `integration_examples.py` | 6 real-world integration patterns |
| `test_installation.py` | Verify your installation |
| `README.md` | This file |

---

## Supported Formats

### IdeaMaker
- Time: `Total time: 3h50m`
- Filament: `Total: 66.11 g`
- Shows processing options (Travel, Retract, etc.)

### BambuStudio
- Time: `11 hours, 48 min, 31 sec`
- Filament: `Material: 377.2 g`
- Multi-color/multi-filament support

---

## Common Use Cases

### 1. Print Time Calculator
Calculate filament usage rate, estimate material cost:
```python
filament_per_hour = data['filament']['amount_grams'] / (data['print_time']['total_seconds'] / 3600)
```

### 2. Mode Selection
Choose print settings based on processing options:
```python
if data['processing_options']['retract']:
    use_profile("standard.profile")
```

### 3. Quality Control
Flag prints with low extraction confidence:
```python
if data['confidence'] < 0.7:
    flag_for_review()
```

### 4. Batch Processing
Process multiple screenshots:
```python
for image in image_list:
    result = extractor.extract_from_file(image)
    # Process result
```

### 5. API/Webhook Integration
Send data to external service:
```python
requests.post('https://api.example.com/jobs', json=result.to_dict())
```

---

## Troubleshooting

### Tesseract not found
1. Install from: https://github.com/UB-Mannheim/tesseract/wiki
2. Or use Chocolatey: `choco install tesseract`
3. Provide path explicitly:
```python
extractor = SlicerDataExtractor(
    tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
)
```

### Low confidence extraction
- Ensure screenshot has good contrast
- Avoid cropped or blurry images
- Check `confidence` score in output
- Review `raw_text` to see what OCR detected

### Variables seem wrong
- Check `raw_text` for actual OCR output
- Verify `confidence >= 0.5` before trusting values
- Use normalized units: `amount_grams` or `amount_kilograms`

**➜ See [SETUP.md](SETUP.md) for detailed troubleshooting**

---

## Data Output Examples

### Example 1: IdeaMaker Screenshot
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
  "processing_options": {
    "travel": true,
    "retract": true,
    "unretract": false,
    "wipe": true,
    "seams": true
  },
  "confidence": 0.95,
  "slicer_detected": "IdeaMaker"
}
```

### Example 2: BambuStudio Screenshot
```json
{
  "print_time": {
    "hours": 11,
    "minutes": 48,
    "seconds": 31,
    "total_seconds": 42511.0,
    "formatted": "11h 48m 31s"
  },
  "filament": {
    "amount": 377.2,
    "unit": "g",
    "amount_grams": 377.2,
    "amount_kilograms": 0.3772,
    "formatted": "377.2 g"
  },
  "confidence": 0.9,
  "slicer_detected": "BambuStudio"
}
```

---

## Getting Help

1. **Installation issues?** → See [SETUP.md](SETUP.md)
2. **Need variable reference?** → See [VARIABLES_REFERENCE.md](VARIABLES_REFERENCE.md)
3. **Integration examples?** → See [integration_examples.py](integration_examples.py)
4. **Test your setup?** → Run `python test_installation.py`

---

## Supported Operating Systems

- ✅ Windows (fully tested)
- ✅ macOS (with Tesseract installed)
- ✅ Linux (with Tesseract installed)

---

## License & Attribution

This tool helps you extract data from 3D slicer screenshots for integration with other systems.

---

## Next Steps

1. **Read the setup guide**: [SETUP.md](SETUP.md)
2. **Review available variables**: [VARIABLES_REFERENCE.md](VARIABLES_REFERENCE.md)
3. **Check integration patterns**: [integration_examples.py](integration_examples.py)
4. **Test your installation**: `python test_installation.py`
5. **Use in your code**:
   ```python
   from slicer_data_extractor import SlicerDataExtractor
   extractor = SlicerDataExtractor(tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe')
   result = extractor.extract_from_file('screenshot.png')
   data = result.to_dict()
   # Use variables: data['print_time']['hours'], data['filament']['amount_grams'], etc.
   ```

---

**Ready to extract data? Start with [SETUP.md](SETUP.md)!** 🚀
