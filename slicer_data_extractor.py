"""
3D Slicer Screenshot Data Extractor
Reads screenshots of 3D slicer output (IdeaMaker, BambuStudio) and extracts print time and filament data.
Optimized for Node-based workflows with clear variable exports.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import pytesseract
from PIL import Image
import json


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TimeData:
    """Stores parsed time information with individual components"""
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    total_seconds: float = 0.0
    
    def __post_init__(self):
        """Calculate total seconds"""
        self.total_seconds = self.hours * 3600 + self.minutes * 60 + self.seconds
    
    def __str__(self):
        return f"{self.hours}h {self.minutes}m {self.seconds}s"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for external use"""
        return {
            "hours": self.hours,
            "minutes": self.minutes,
            "seconds": self.seconds,
            "total_seconds": self.total_seconds,
            "formatted": str(self)
        }


@dataclass
class FilamentData:
    """Stores parsed filament information"""
    amount: float = 0.0
    unit: str = ""  # "g", "kg", or "m"
    amount_grams: float = 0.0  # normalized to grams
    amount_kilograms: float = 0.0  # normalized to kg
    
    def __post_init__(self):
        """Normalize amount to both grams and kilograms"""
        if self.unit.lower() == "kg":
            self.amount_grams = self.amount * 1000
            self.amount_kilograms = self.amount
        elif self.unit.lower() == "g":
            self.amount_grams = self.amount
            self.amount_kilograms = self.amount / 1000
        else:  # meters or unknown
            self.amount_grams = self.amount
            self.amount_kilograms = self.amount / 1000
    
    def __str__(self):
        return f"{self.amount} {self.unit}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for external use"""
        return {
            "amount": self.amount,
            "unit": self.unit,
            "amount_grams": self.amount_grams,
            "amount_kilograms": self.amount_kilograms,
            "formatted": str(self)
        }


@dataclass
class ProcessingOptions:
    """Stores processing options found in slicer (Travel, Retract, etc.)"""
    travel: bool = False
    retract: bool = False
    unretract: bool = False
    wipe: bool = False
    seams: bool = False
    custom_options: Dict[str, bool] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "travel": self.travel,
            "retract": self.retract,
            "unretract": self.unretract,
            "wipe": self.wipe,
            "seams": self.seams,
        }
        result.update(self.custom_options)
        return result


@dataclass
class SlicerExtractionResult:
    """Complete data extracted from slicer screenshot"""
    print_time: TimeData
    filament: FilamentData
    filament_length: Optional[FilamentData] = None  # Filament length in meters
    processing_options: ProcessingOptions = field(default_factory=ProcessingOptions)
    raw_text: str = ""
    confidence: float = 0.0  # 0-1 confidence in extraction
    slicer_detected: str = ""  # "IdeaMaker", "BambuStudio", "Unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for external use - optimized for node workflows"""
        return {
            "print_time": self.print_time.to_dict(),
            "filament": self.filament.to_dict(),
            "filament_length": self.filament_length.to_dict() if self.filament_length else None,
            "processing_options": self.processing_options.to_dict(),
            "confidence": self.confidence,
            "slicer_detected": self.slicer_detected,
            "raw_text": self.raw_text
        }
    
    def to_json(self) -> str:
        """Convert to JSON string for easy integration"""
        return json.dumps(self.to_dict(), indent=2)


# ============================================================================
# Main Extractor Class
# ============================================================================

class SlicerDataExtractor:
    """Main class for extracting data from 3D slicer screenshots"""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize the extractor
        
        Args:
            tesseract_path: Optional path to tesseract executable (Windows needs this)
                          e.g., r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
        """
        if tesseract_path:
            pytesseract.pytesseract.pytesseract_cmd = tesseract_path
    
    def extract_from_file(self, image_path: str) -> SlicerExtractionResult:
        """
        Extract data from a screenshot file
        
        Args:
            image_path: Path to the screenshot image
            
        Returns:
            SlicerExtractionResult with extracted data
        """
        try:
            image = Image.open(image_path)
            return self.extract_from_image(image)
        except FileNotFoundError:
            raise FileNotFoundError(f"Image file not found: {image_path}")
        except Exception as e:
            raise RuntimeError(f"Error opening image: {str(e)}")
    
    def extract_from_image(self, image) -> SlicerExtractionResult:
        """
        Extract data from a PIL Image
        
        Args:
            image: PIL Image object or file path
            
        Returns:
            SlicerExtractionResult with extracted data
        """
        # Extract text using OCR
        raw_text = pytesseract.image_to_string(image)
        
        # Detect which slicer this is from
        slicer_type = self._detect_slicer(raw_text)
        
        # Parse time and filament data
        time_data = self._parse_time(raw_text)
        filament_data = self._parse_filament(raw_text, slicer_type)
        filament_length = self._parse_filament_length(raw_text)
        processing_options = self._parse_processing_options(raw_text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(raw_text, time_data, filament_data)
        
        result = SlicerExtractionResult(
            print_time=time_data,
            filament=filament_data,
            filament_length=filament_length,
            processing_options=processing_options,
            raw_text=raw_text,
            confidence=confidence,
            slicer_detected=slicer_type
        )
        
        return result
    
    # ========================================================================
    # Parsing Methods
    # ========================================================================
    
    def _detect_slicer(self, text: str) -> str:
        """Detect which slicer generated this screenshot"""
        text_lower = text.lower()
        
        if "bambu" in text_lower:
            return "BambuStudio"
        elif "ideamaker" in text_lower or "time estimation" in text_lower:
            return "IdeaMaker"
        else:
            return "Unknown"
    
    def _parse_time(self, text: str) -> TimeData:
        """
        Parse print time from extracted text
        Supports multiple formats from different slicers:
        - "12h 34m 56s"
        - "12:34:56"
        - "12h 34m"
        - "1h17m"
        - "25m10s"
        - "11 hours, 48 min, 31 sec"
        - "3h41m", "3h50m"
        """
        text_lower = text.lower()
        hours = 0
        minutes = 0
        seconds = 0
        
        # Pattern 1: "X hours, Y min, Z sec" (IdeaMaker/BambuStudio exact)
        pattern1 = r'(\d+)\s*hours?\s*,\s*(\d+)\s*min(?:utes?)?\s*,\s*(\d+)\s*sec(?:onds?)?'
        match = re.search(pattern1, text_lower)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            return TimeData(hours=hours, minutes=minutes, seconds=seconds)
        
        # Pattern 2: "Xh Ym Zs" or "XhYmZs" format
        pattern2 = r'(\d+)\s*h[\s]*(\d+)\s*m[\s]*(\d+)\s*s'
        match = re.search(pattern2, text_lower)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            return TimeData(hours=hours, minutes=minutes, seconds=seconds)
        
        # Pattern 3: "Xh Ym" or "XhYm" format (no seconds)
        pattern3 = r'(\d+)\s*h[\s]*(\d+)\s*m(?!\w)'
        match = re.search(pattern3, text_lower)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            return TimeData(hours=hours, minutes=minutes, seconds=0)
        
        # Pattern 4: "X:Y:Z" format (HH:MM:SS)
        pattern4 = r'(\d+):(\d+):(\d+)'
        match = re.search(pattern4, text_lower)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            return TimeData(hours=hours, minutes=minutes, seconds=seconds)
        
        # Pattern 5: "XmYs" format (minutes and seconds only)
        pattern5 = r'(\d+)\s*m[\s]*(\d+)\s*s(?!\s*\w)'
        match = re.search(pattern5, text_lower)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            return TimeData(hours=0, minutes=minutes, seconds=seconds)
        
        # Pattern 6: Days + hours/minutes
        pattern6 = r'(\d+)\s*d[\s]*(\d+)\s*h[\s]*(\d+)\s*m'
        match = re.search(pattern6, text_lower)
        if match:
            days = int(match.group(1))
            hours = int(match.group(2))
            minutes = int(match.group(3))
            hours += days * 24
            return TimeData(hours=hours, minutes=minutes, seconds=0)
        
        return TimeData()  # Return empty if no match
    
    def _parse_filament(self, text: str, slicer_type: str) -> FilamentData:
        """
        Parse filament weight data from extracted text
        Supports: "100g", "1.5kg", "100 g", "1.5 kg", "377.2 g"
        """
        text_lower = text.lower()
        
        # Pattern 1: "XXX.X kg" or "XXX kg"
        pattern_kg = r'(\d+\.?\d*)\s*kg(?!\w)'
        match = re.search(pattern_kg, text_lower)
        if match:
            amount = float(match.group(1))
            return FilamentData(amount=amount, unit="kg")
        
        # Pattern 2: "XXX.X g" or "XXX g" (but not part of longer words)
        # Make sure we don't match "kg" or other g-containing words
        pattern_g = r'(\d+\.?\d*)\s*g(?!\w|ram)'
        matches = re.finditer(pattern_g, text_lower)
        
        # Find the highest value that looks like filament (not likely noise)
        best_match = None
        best_amount = 0
        for match in matches:
            amount = float(match.group(1))
            if amount > best_amount and amount < 10000:  # Reasonable filament range
                best_match = match
                best_amount = amount
        
        if best_match:
            return FilamentData(amount=best_amount, unit="g")
        
        return FilamentData()  # Return empty if no match
    
    def _parse_filament_length(self, text: str) -> Optional[FilamentData]:
        """
        Parse filament length data (meters)
        Used by some slicers in addition to weight
        """
        text_lower = text.lower()
        
        # Look for patterns like "126.48 m" or "9.68 m" but avoid matching units
        # Context: usually near actual measurements
        pattern_m = r'(\d+\.?\d*)\s*m(?:\s|$|\n|/)(?![a-z])'
        matches = re.finditer(pattern_m, text_lower)
        
        for match in matches:
            amount = float(match.group(1))
            # Filament length is typically 5-200+ meters, distinguish from time minutes
            if amount > 4:  # Likely filament length, not time
                return FilamentData(amount=amount, unit="m")
        
        return None
    
    def _parse_processing_options(self, text: str) -> ProcessingOptions:
        """
        Parse processing options like Travel, Retract, Wipe, Seams
        Looks for option names and enabled/disabled status
        """
        text_lower = text.lower()
        options = ProcessingOptions()
        
        # Check for common options (case-insensitive)
        if re.search(r'\btravel\b', text_lower):
            options.travel = True
        if re.search(r'\bretract\b', text_lower):
            options.retract = True
        if re.search(r'\bunretract\b', text_lower):
            options.unretract = True
        if re.search(r'\bwipe\b', text_lower):
            options.wipe = True
        if re.search(r'\bseams?\b', text_lower):
            options.seams = True
        
        return options
    
    def _calculate_confidence(self, raw_text: str, time_data: TimeData, filament_data: FilamentData) -> float:
        """
        Calculate confidence score for the extraction (0-1)
        Both time and filament found = 1.0
        Only one found = 0.5
        Neither found = 0.0
        """
        confidence = 0.0
        
        # Time found
        if time_data.total_seconds > 0:
            confidence += 0.5
        
        # Filament found
        if filament_data.amount > 0:
            confidence += 0.5
        
        return confidence


# ============================================================================
# Variable Exports - For Node Integration
# ============================================================================

def get_exportable_variables_schema() -> Dict[str, Dict[str, str]]:
    """
    Returns the schema of all variables that can be exported
    for use in node-based workflows or other integrations
    """
    return {
        "PRINT_TIME": {
            "print_time.hours": "Print time: hours (0-23)",
            "print_time.minutes": "Print time: minutes (0-59)",
            "print_time.seconds": "Print time: seconds (0-59)",
            "print_time.total_seconds": "Print time: total in seconds (float)",
            "print_time.formatted": "Print time: formatted string (e.g., '3h 41m 0s')",
        },
        "FILAMENT_WEIGHT": {
            "filament.amount": "Filament: original amount value (float)",
            "filament.unit": "Filament: unit of original amount ('g' or 'kg')",
            "filament.amount_grams": "Filament: amount in grams (float)",
            "filament.amount_kilograms": "Filament: amount in kilograms (float)",
            "filament.formatted": "Filament: formatted string (e.g., '66.11 g')",
        },
        "FILAMENT_LENGTH": {
            "filament_length.amount": "Filament length: length value (float)",
            "filament_length.unit": "Filament length: unit ('m' for meters)",
            "filament_length.formatted": "Filament length: formatted string",
        },
        "PROCESSING_OPTIONS": {
            "processing_options.travel": "Processing: Travel enabled (bool)",
            "processing_options.retract": "Processing: Retract enabled (bool)",
            "processing_options.unretract": "Processing: Unretract enabled (bool)",
            "processing_options.wipe": "Processing: Wipe enabled (bool)",
            "processing_options.seams": "Processing: Seams enabled (bool)",
        },
        "METADATA": {
            "confidence": "Extraction confidence score (0.0-1.0)",
            "slicer_detected": "Detected slicer type ('IdeaMaker', 'BambuStudio', 'Unknown')",
            "raw_text": "Raw OCR-extracted text from screenshot",
        }
    }


def print_variable_guide():
    """Print a helpful guide for using exported variables"""
    schema = get_exportable_variables_schema()
    print("\n" + "="*70)
    print("EXPORTABLE VARIABLES GUIDE FOR NODE INTEGRATION")
    print("="*70)
    
    for category, variables in schema.items():
        print(f"\n[{category}]")
        for var_path, description in variables.items():
            print(f"  {var_path:<35} → {description}")
    
    print("\n" + "="*70)
    print("USAGE EXAMPLES:")
    print("="*70)
    print("""
Example 1: Access time components
    result = extractor.extract_from_file('screenshot.png')
    data = result.to_dict()
    
    hours = data['print_time']['hours']
    minutes = data['print_time']['minutes']
    seconds = data['print_time']['seconds']
    total_seconds = data['print_time']['total_seconds']

Example 2: Access filament in consistent units
    filament_grams = data['filament']['amount_grams']
    filament_kg = data['filament']['amount_kilograms']
    original_unit = data['filament']['unit']

Example 3: Check processing options to determine mode
    if data['processing_options']['travel']:
        print("Travel mode is enabled")
    if data['processing_options']['retract']:
        print("Retract mode is enabled")

Example 4: Use as JSON for node integration
    json_output = result.to_json()
    # Can be passed directly to Node-RED or other systems

Example 5: Confidence-based error handling
    if result.confidence >= 0.9:
        print(f"High confidence extraction: {result.confidence}")
    elif result.confidence >= 0.5:
        print(f"Medium confidence: {result.confidence}")
    else:
        print(f"Low confidence: {result.confidence} - may need manual verification")
    """)
    print("="*70 + "\n")


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print_variable_guide()
    
    print("\nQUICK START CODE:")
    print("-" * 70)
    print("""
# Initialize the extractor
extractor = SlicerDataExtractor(
    tesseract_path=r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
)

# Extract from image file
result = extractor.extract_from_file('slicer_screenshot.png')

# Get data as dictionary for easy integration
data = result.to_dict()

# Extract specific variables
print(f"Print Time: {data['print_time']['hours']}h {data['print_time']['minutes']}m {data['print_time']['seconds']}s")
print(f"Filament: {data['filament']['amount_grams']}g")
print(f"Confidence: {data['confidence']}")

# Get as JSON for node workflows
json_string = result.to_json()
    """)
    print("-" * 70)
