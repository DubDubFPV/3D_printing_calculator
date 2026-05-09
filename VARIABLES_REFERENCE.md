# Quick Reference - Available Variables

This file contains all variables available from the SlicerDataExtractor for connecting to your other code.

## Usage Pattern

```python
result = extractor.extract_from_file('screenshot.png')
data = result.to_dict()

# Access variables like:
value = data['category']['variable_name']
```

---

## PRINT TIME Variables

Access with: `data['print_time'][...]`

| Variable | Type | Example | Description |
|----------|------|---------|-------------|
| `hours` | int | 3 | Hours component (0-23) |
| `minutes` | int | 41 | Minutes component (0-59) |
| `seconds` | int | 0 | Seconds component (0-59) |
| `total_seconds` | float | 13260.0 | Total print time in seconds |
| `formatted` | str | "3h 41m 0s" | Human-readable format |

### Example Usage
```python
hours = data['print_time']['hours']
minutes = data['print_time']['minutes']
seconds = data['print_time']['seconds']
total_seconds = data['print_time']['total_seconds']
time_string = data['print_time']['formatted']

# Use in calculations
hours_decimal = hours + minutes/60 + seconds/3600
```

---

## FILAMENT (Weight) Variables

Access with: `data['filament'][...]`

| Variable | Type | Example | Description |
|----------|------|---------|-------------|
| `amount` | float | 66.11 | Original amount from screenshot |
| `unit` | str | "g" | Original unit: "g" or "kg" |
| `amount_grams` | float | 66.11 | Amount normalized to grams |
| `amount_kilograms` | float | 0.06611 | Amount normalized to kilograms |
| `formatted` | str | "66.11 g" | Human-readable format |

### Example Usage
```python
weight_grams = data['filament']['amount_grams']  # Always in grams
weight_kg = data['filament']['amount_kilograms']  # Always in kg
original_unit = data['filament']['unit']  # What was shown on screen
original_amount = data['filament']['amount']  # Original value

# Use in calculations
if data['filament']['unit'] == 'kg':
    print(f"Heavy print: {weight_kg}kg")
else:
    print(f"Light print: {weight_grams}g")
```

---

## FILAMENT LENGTH Variables

Access with: `data['filament_length'][...]` (may be null)

| Variable | Type | Example | Description |
|----------|------|---------|-------------|
| `amount` | float | 126.48 | Length value |
| `unit` | str | "m" | Always "m" for meters |
| `formatted` | str | "126.48 m" | Human-readable format |

### Example Usage
```python
if data['filament_length'] is not None:
    filament_length_m = data['filament_length']['amount']
    print(f"Filament length: {filament_length_m} meters")
```

---

## PROCESSING OPTIONS Variables

Access with: `data['processing_options'][...]`

All are boolean (True/False)

| Variable | Type | Meaning |
|----------|------|---------|
| `travel` | bool | Travel moves enabled |
| `retract` | bool | Retract moves enabled |
| `unretract` | bool | Unretract moves enabled |
| `wipe` | bool | Wipe moves enabled |
| `seams` | bool | Seam handling enabled |

### Example Usage
```python
# Branch on processing options
if data['processing_options']['retract']:
    mode = "STANDARD"
elif data['processing_options']['travel']:
    mode = "FAST"
else:
    mode = "MINIMAL"

# Use to switch print profile
print_profiles = {
    'STANDARD': {...},
    'FAST': {...},
    'MINIMAL': {...}
}
settings = print_profiles[mode]
```

---

## METADATA Variables

Access with: `data[...]` (top level)

| Variable | Type | Example | Description |
|----------|------|---------|-------------|
| `confidence` | float | 0.95 | Confidence score (0.0-1.0) |
| `slicer_detected` | str | "IdeaMaker" | "IdeaMaker", "BambuStudio", "Unknown" |
| `raw_text` | str | "..." | Raw OCR-extracted text |

### Example Usage
```python
confidence = data['confidence']
slicer = data['slicer_detected']
raw_ocr = data['raw_text']

# Quality check
if confidence >= 0.9:
    print("High confidence extraction")
elif confidence >= 0.5:
    print("Medium confidence - verify manually")
else:
    print("Low confidence - inspection required")

# Slicer-specific handling
if slicer == "IdeaMaker":
    # IdeaMaker-specific code
    pass
elif slicer == "BambuStudio":
    # BambuStudio-specific code
    pass
```

---

## Complete Variable Access Reference

### Access All Variables as Dictionary
```python
result = extractor.extract_from_file('screenshot.png')
data = result.to_dict()
```

### Access as JSON String
```python
result = extractor.extract_from_file('screenshot.png')
json_string = result.to_json()

# Parse if needed
import json
data = json.loads(json_string)
```

### Direct Object Access
```python
result = extractor.extract_from_file('screenshot.png')

print(result.print_time.hours)
print(result.filament.amount_grams)
print(result.processing_options.retract)
print(result.confidence)
print(result.slicer_detected)
```

---

## Common Use Cases & Variable Mapping

### Use Case 1: Send to another Python function
```python
result = extractor.extract_from_file('image.png')
data = result.to_dict()

my_function(
    time_hours=data['print_time']['hours'],
    time_minutes=data['print_time']['minutes'],
    time_seconds=data['print_time']['seconds'],
    filament_grams=data['filament']['amount_grams'],
    filament_kg=data['filament']['amount_kilograms'],
    processing_travel=data['processing_options']['travel'],
    processing_retract=data['processing_options']['retract'],
    slicer=data['slicer_detected'],
    confidence=data['confidence']
)
```

### Use Case 2: Store in database
```python
result = extractor.extract_from_file('image.png')
data = result.to_dict()

db.insert('print_jobs', {
    'print_time_seconds': int(data['print_time']['total_seconds']),
    'filament_weight_g': data['filament']['amount_grams'],
    'filament_weight_kg': data['filament']['amount_kilograms'],
    'slicer': data['slicer_detected'],
    'confidence': data['confidence'],
    'options_travel': data['processing_options']['travel'],
    'options_retract': data['processing_options']['retract']
})
```

### Use Case 3: Send to Node-RED
```python
result = extractor.extract_from_file('image.png')
json_output = result.to_json()

# Node-RED can parse this JSON directly
# Or flatten it for simple nodes:
data = result.to_dict()
flat = {
    'print_time_h': data['print_time']['hours'],
    'print_time_m': data['print_time']['minutes'],
    'print_time_s': data['print_time']['seconds'],
    'print_time_total_s': data['print_time']['total_seconds'],
    'filament_g': data['filament']['amount_grams'],
    'filament_kg': data['filament']['amount_kilograms'],
    'slicer': data['slicer_detected']
}
```

### Use Case 4: Conditional Logic Based on Options
```python
result = extractor.extract_from_file('image.png')
data = result.to_dict()

# Choose action based on processing options
if data['processing_options']['retract']:
    action = "Use standard print settings"
elif data['processing_options']['travel']:
    action = "Use fast print settings"
else:
    action = "Use minimal print settings"

print(action)
```

---

## Data Type Reference

- **int**: Integer number (no decimals) - e.g., `3` hours
- **float**: Decimal number - e.g., `66.11` grams, `13260.0` seconds
- **str**: Text string - e.g., `"IdeaMaker"`, `"3h 41m 0s"`
- **bool**: True or False - e.g., `True` for retract enabled
- **None**: Empty/null value - when filament_length not detected

---

## Node Integration Quick Start

For Node-RED or similar systems, here's the minimal JSON structure:

```json
{
  "time_h": 3,
  "time_m": 41,
  "time_s": 0,
  "time_total_s": 13260,
  "filament_g": 66.11,
  "filament_kg": 0.06611,
  "slicer": "IdeaMaker",
  "confidence": 0.95,
  "options": {
    "travel": true,
    "retract": true,
    "wipe": true,
    "seams": true
  }
}
```

Map these fields to your node inputs.

---

## Troubleshooting Variable Access

### Variables are None/null
- Image quality might be poor
- Check `confidence` score
- Review `raw_text` to see what was detected

### Confidence is low
- Ensure screenshot has good contrast
- Avoid cropped or blurry images
- Check if slicer is IdeaMaker or BambuStudio

### Wrong unit detected
- The code normalizes to both `amount_grams` and `amount_kilograms`
- Always use normalized units for consistency

### Processing options not detected
- They may not be visible in the screenshot
- Defaults to False
- Check `raw_text` to verify OCR captured them

