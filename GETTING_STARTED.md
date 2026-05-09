# Getting Started Guide

## What You Got

A complete system for extracting print time and filament data from 3D slicer screenshots (IdeaMaker, BambuStudio) with clear, usable variables for integration with other code.

---

## Files Overview

| File | Purpose |
|------|---------|
| **README.md** | Start here - Overview and quick start |
| **SETUP.md** | Installation and troubleshooting guide |
| **VARIABLES_REFERENCE.md** | Complete variable reference (bookmark this!) |
| **slicer_data_extractor.py** | Main extractor code (don't edit unless you know what you're doing) |
| **config_templates.py** | 8 ready-to-use configuration patterns |
| **integration_examples.py** | 6 real-world integration patterns |
| **test_installation.py** | Verify everything is set up correctly |
| **GETTING_STARTED.md** | This file |

---

## Step-by-Step Setup

### Step 1: Install Dependencies (5 minutes)

**Install Python packages:**
```bash
pip install pillow pytesseract
```

**Install Tesseract OCR (Windows):**
- Option A: Download installer from https://github.com/UB-Mannheim/tesseract/wiki
- Option B: Use Chocolatey: `choco install tesseract`
- Default path: `C:\Program Files\Tesseract-OCR`

### Step 2: Verify Installation (5 minutes)

```bash
python test_installation.py
```

If all tests pass ✓, you're ready to go!

### Step 3: Test with Your First Screenshot (5 minutes)

```python
from slicer_data_extractor import SlicerDataExtractor

extractor = SlicerDataExtractor(
    tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
)

result = extractor.extract_from_file('your_screenshot.png')
data = result.to_dict()

print(f"Print Time: {data['print_time']['hours']}h {data['print_time']['minutes']}m {data['print_time']['seconds']}s")
print(f"Filament: {data['filament']['amount_grams']}g")
print(f"Confidence: {data['confidence']}")
```

---

## How to Use in Your Code

### Option A: Simple Dictionary Access (Most Common)
```python
from slicer_data_extractor import SlicerDataExtractor

extractor = SlicerDataExtractor(tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe')
result = extractor.extract_from_file('screenshot.png')
data = result.to_dict()

# Access any variable:
hours = data['print_time']['hours']
filament_grams = data['filament']['amount_grams']
confidence = data['confidence']
```

### Option B: JSON Output (For APIs/Node-RED)
```python
result = extractor.extract_from_file('screenshot.png')
json_string = result.to_json()
# Send to Node-RED, API, etc.
```

### Option C: Use Ready-Made Configuration
```python
from config_templates import NodeREDConfig  # or DatabaseConfig, APIConfig, etc.

extractor = NodeREDConfig.setup()
output = NodeREDConfig.extract_for_node_red(extractor, 'screenshot.png')
```

---

## What Variables You Can Access

All these are available from the extracted data:

**Print Time:**
- `hours`, `minutes`, `seconds`, `total_seconds`, `formatted`

**Filament Weight:**
- `amount`, `unit`, `amount_grams`, `amount_kilograms`, `formatted`

**Processing Options:**
- `travel`, `retract`, `unretract`, `wipe`, `seams` (all boolean)

**Metadata:**
- `confidence`, `slicer_detected`, `raw_text`

**➜ See VARIABLES_REFERENCE.md for the complete list and examples**

---

## Common Use Cases

### Use Case 1: Connect to Node-RED
```python
from config_templates import NodeREDConfig
extractor = NodeREDConfig.setup()
json_output = NodeREDConfig.extract_for_node_red(extractor, 'screenshot.png')
# Send json_output to Node-RED
```

### Use Case 2: Store in Database
```python
from config_templates import DatabaseConfig
extractor = DatabaseConfig.setup()
record = DatabaseConfig.create_record(extractor, 'screenshot.png', print_id=123)
# Insert record into database
```

### Use Case 3: Choose Mode Based on Options
```python
data = result.to_dict()
if data['processing_options']['retract']:
    mode = "STANDARD"
elif data['processing_options']['travel']:
    mode = "FAST"
else:
    mode = "MINIMAL"
# Use mode in your code
```

### Use Case 4: Batch Process Multiple Screenshots
```python
from config_templates import BatchConfig
extractor = BatchConfig.setup()
results = BatchConfig.process_batch(extractor, ['img1.png', 'img2.png', 'img3.png'])
summary = BatchConfig.get_summary(results)
```

### Use Case 5: Quality Check Before Using Data
```python
data = result.to_dict()
if data['confidence'] >= 0.8:
    # Use with confidence
else:
    # Manual review recommended
```

---

## Integration Examples

### With Your Existing Python Code
```python
# Your existing code
my_function(
    time_hours=data['print_time']['hours'],
    time_minutes=data['print_time']['minutes'],
    filament_grams=data['filament']['amount_grams'],
    mode_retract_enabled=data['processing_options']['retract']
)
```

### With HTTP/REST API
```python
from config_templates import APIConfig
payload = APIConfig.prepare_payload(extractor, 'screenshot.png', job_id=123)
requests.post('https://api.example.com/jobs', json=payload)
```

### With Databases
```python
from config_templates import DatabaseConfig
record = DatabaseConfig.create_record(extractor, 'screenshot.png', print_id=1)
db.insert('print_jobs', record)
```

**➜ See integration_examples.py for more patterns**

---

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| "tesseract is not installed" | Install from https://github.com/UB-Mannheim/tesseract/wiki |
| "No module named 'PIL'" | Run `pip install pillow` |
| "No module named 'pytesseract'" | Run `pip install pytesseract` |
| Extraction seems wrong | Check `data['confidence']` - low confidence = low reliability |
| Can't find variables | See VARIABLES_REFERENCE.md - all variables are there |
| Need different output format | Try config_templates.py - 8 different patterns |

**➜ See SETUP.md for detailed troubleshooting**

---

## Complete Variable List (Quick Reference)

```
data['print_time']['hours']              → integer hours
data['print_time']['minutes']            → integer minutes (0-59)
data['print_time']['seconds']            → integer seconds (0-59)
data['print_time']['total_seconds']      → float total seconds
data['print_time']['formatted']          → string "3h 41m 0s"

data['filament']['amount']               → original amount
data['filament']['unit']                 → "g" or "kg"
data['filament']['amount_grams']         → float grams (normalized)
data['filament']['amount_kilograms']     → float kg (normalized)
data['filament']['formatted']            → string "66.11 g"

data['filament_length']['amount']        → float (if detected)
data['filament_length']['unit']          → "m" (meters)
data['filament_length']['formatted']     → string "126.48 m"

data['processing_options']['travel']     → boolean
data['processing_options']['retract']    → boolean
data['processing_options']['unretract']  → boolean
data['processing_options']['wipe']       → boolean
data['processing_options']['seams']      → boolean

data['confidence']                       → float 0.0-1.0
data['slicer_detected']                  → "IdeaMaker" or "BambuStudio"
data['raw_text']                         → string (raw OCR output)
```

---

## Next Steps

1. **Read the full README.md** - Understand what the tool does
2. **Run test_installation.py** - Verify everything works
3. **Follow SETUP.md** - Get fully set up
4. **Check VARIABLES_REFERENCE.md** - See all available variables
5. **Pick a config from config_templates.py** - Use as starting point
6. **Integrate into your code** - Replace with your actual screenshot paths

---

## Key Points to Remember

✅ **All variables are clearly named** - Easy to understand what each one means

✅ **Multiple output formats** - Dictionary, JSON, direct object access

✅ **Confidence scoring** - Know when to trust the data

✅ **Node-friendly** - Works with Node-RED, APIs, databases, etc.

✅ **Well documented** - Every variable explained with examples

✅ **Ready-made patterns** - 8 configurations for common use cases

✅ **Real integration examples** - 6 complete working patterns

---

## Support

**Issue?** → Check SETUP.md first (Troubleshooting section)

**Need variable reference?** → See VARIABLES_REFERENCE.md

**Want integration example?** → Check config_templates.py or integration_examples.py

**Installation test?** → Run `python test_installation.py`

---

## Example: Complete Integration Flow

```python
# 1. Import
from slicer_data_extractor import SlicerDataExtractor

# 2. Initialize
extractor = SlicerDataExtractor(
    tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
)

# 3. Extract
result = extractor.extract_from_file('slicer_screenshot.png')
data = result.to_dict()

# 4. Use variables
print(f"Print time: {data['print_time']['total_seconds']} seconds")
print(f"Filament: {data['filament']['amount_grams']} grams")
print(f"Quality: {data['confidence']}")

# 5. Conditional logic
if data['processing_options']['retract']:
    use_profile("standard")
else:
    use_profile("fast")

# 6. Send to other system
if data['confidence'] >= 0.8:
    send_to_api(data)
else:
    flag_for_manual_review(data)
```

---

## You're All Set! 🚀

You now have a complete, production-ready system for extracting 3D slicer data. Start with README.md and SETUP.md, then jump into the integration patterns that fit your workflow.

**Happy printing! 🖨️**
