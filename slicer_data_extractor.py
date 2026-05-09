"""
3D Slicer Screenshot Data Extractor
Reads screenshots of 3D slicer output (IdeaMaker, BambuStudio) and extracts print time and filament data.
Optimized for Node-based workflows with clear variable exports.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
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
    debug_info: Optional["ExtractionDebugInfo"] = None
    
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


@dataclass
class OCRWordBox:
    text: str
    left: int
    top: int
    width: int
    height: int
    conf: float


@dataclass
class OCRPassDebug:
    variant_label: str
    config: str
    text: str
    word_boxes: List[OCRWordBox] = field(default_factory=list)


@dataclass
class ExtractionDebugInfo:
    passes: List[OCRPassDebug] = field(default_factory=list)
    selected_pass_index: int = 0


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
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def extract_from_file(self, image_path: str, return_debug: bool = False):
        """
        Extract data from a screenshot file
        
        Args:
            image_path: Path to the screenshot image
            
        Returns:
            SlicerExtractionResult with extracted data
        """
        try:
            image = Image.open(image_path)
            return self.extract_from_image(image, return_debug=return_debug)
        except FileNotFoundError:
            raise FileNotFoundError(f"Image file not found: {image_path}")
        except Exception as e:
            raise RuntimeError(f"Error opening image: {str(e)}")
    
    def extract_from_image(self, image, return_debug: bool = False):
        """
        Extract data from a PIL Image
        
        Args:
            image: PIL Image object or file path
            
        Returns:
            SlicerExtractionResult with extracted data
        """
        ocr_passes = self._extract_ocr_passes(image)
        if not ocr_passes:
            fallback_text = pytesseract.image_to_string(image)
            ocr_passes = [OCRPassDebug(variant_label="original", config="default", text=fallback_text, word_boxes=[])]

        best_result: Optional[SlicerExtractionResult] = None
        best_score = -10**9
        best_index = 0

        for index, ocr_pass in enumerate(ocr_passes):
            raw_text = ocr_pass.text
            slicer_type = self._detect_slicer(raw_text)
            time_data = self._parse_time(raw_text)
            filament_data = self._parse_filament(raw_text, slicer_type, time_data)
            filament_length = self._parse_filament_length(raw_text)
            processing_options = self._parse_processing_options(raw_text)
            confidence = self._calculate_confidence(raw_text, time_data, filament_data)

            score = self._score_candidate(raw_text, time_data, filament_data, confidence)
            result = SlicerExtractionResult(
                print_time=time_data,
                filament=filament_data,
                filament_length=filament_length,
                processing_options=processing_options,
                raw_text=raw_text,
                confidence=confidence,
                slicer_detected=slicer_type,
            )

            if best_result is None or score > best_score:
                best_result = result
                best_score = score
                best_index = index

        result = best_result if best_result is not None else SlicerExtractionResult(
            print_time=TimeData(),
            filament=FilamentData(),
            raw_text="",
            confidence=0.0,
            slicer_detected="Unknown",
        )

        if return_debug:
            result.debug_info = ExtractionDebugInfo(passes=ocr_passes, selected_pass_index=best_index)
            return result

        return result

    def _extract_ocr_passes(self, image: Image.Image) -> List[OCRPassDebug]:
        """Run OCR on the original image only; preprocessing variants hurt box placement."""
        base = image.convert("RGB")
        configs = [
            "--oem 3 --psm 6 -c preserve_interword_spaces=1",
            "--oem 3 --psm 11 -c preserve_interword_spaces=1",
        ]

        passes: List[OCRPassDebug] = []
        for config in configs:
            variant_label = "original"
            variant = base
            try:
                candidate = pytesseract.image_to_string(variant, config=config)
            except Exception:
                continue
            if not candidate or not candidate.strip():
                continue

            try:
                ocr_data = pytesseract.image_to_data(variant, output_type=pytesseract.Output.DICT, config=config)
                word_boxes: List[OCRWordBox] = []
                for idx, word in enumerate(ocr_data.get("text", [])):
                    cleaned = str(word).strip()
                    if not cleaned:
                        continue
                    conf_value = ocr_data.get("conf", [])[idx]
                    try:
                        conf = float(conf_value)
                    except Exception:
                        conf = -1.0
                    if conf < 0:
                        continue
                    word_boxes.append(
                        OCRWordBox(
                            text=cleaned,
                            left=int(ocr_data.get("left", [0])[idx]),
                            top=int(ocr_data.get("top", [0])[idx]),
                            width=int(ocr_data.get("width", [0])[idx]),
                            height=int(ocr_data.get("height", [0])[idx]),
                            conf=conf,
                        )
                    )
            except Exception:
                word_boxes = []

            passes.append(OCRPassDebug(variant_label=variant_label, config=config, text=candidate, word_boxes=word_boxes))

        return passes



    def _score_candidate(self, raw_text: str, time_data: TimeData, filament_data: FilamentData, confidence: float) -> float:
        """Heuristic score to pick the best OCR candidate among multiple passes."""
        text_lower = raw_text.lower()
        score = confidence * 100.0

        if re.search(r'\btotal\s*time\b', text_lower):
            score += 25.0
        if re.search(r'\bmaterial\b|\bfilament\b', text_lower):
            score += 10.0
        if re.search(r'(\d+[\.,]\d+)\s*g\b', text_lower):
            score += 15.0

        # Penalize unlikely giant filament values caused by missed decimal points.
        if filament_data.amount_grams >= 500:
            score -= 8.0

        # Prefer candidates where total time likely dominates model printing fragments.
        if "total time" in text_lower and "model printing time" in text_lower and time_data.total_seconds > 0:
            score += 8.0

        return score
    
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
        lines = [line.strip() for line in text_lower.splitlines()]

        def parse_time_expression(value: str) -> Optional[TimeData]:
            value = value.strip().lower()
            if not value:
                return None

            # "12 hours, 51 min, 2 sec" and OCR variants without commas
            match = re.search(r'(\d+)\s*hours?\s*,?\s*(\d+)\s*min(?:utes?)?\s*,?\s*(\d+)\s*sec(?:onds?)?', value)
            if match:
                return TimeData(hours=int(match.group(1)), minutes=int(match.group(2)), seconds=int(match.group(3)))

            # "3h41m46s"
            match = re.search(r'(\d+)\s*h\s*(\d+)\s*m\s*(\d+)\s*s', value)
            if match:
                return TimeData(hours=int(match.group(1)), minutes=int(match.group(2)), seconds=int(match.group(3)))

            # "3h41m"
            match = re.search(r'(\d+)\s*h\s*(\d+)\s*m(?!\w)', value)
            if match:
                return TimeData(hours=int(match.group(1)), minutes=int(match.group(2)), seconds=0)

            # "41m46s"
            match = re.search(r'(\d+)\s*m\s*(\d+)\s*s(?!\w)', value)
            if match:
                return TimeData(hours=0, minutes=int(match.group(1)), seconds=int(match.group(2)))

            # HH:MM:SS
            match = re.search(r'(\d+):(\d+):(\d+)', value)
            if match:
                return TimeData(hours=int(match.group(1)), minutes=int(match.group(2)), seconds=int(match.group(3)))

            return None

        def next_time_value(index: int) -> Optional[TimeData]:
            for next_index in range(index + 1, min(index + 4, len(lines))):
                candidate = parse_time_expression(lines[next_index])
                if candidate and candidate.total_seconds > 0:
                    return candidate
            return None

        # Hard priority: if we can find "total time" label, use that line or its immediate value line.
        for i, line in enumerate(lines):
            if "total" in line and "time" in line:
                candidate = parse_time_expression(line)
                if candidate and candidate.total_seconds > 0:
                    return candidate
                candidate = next_time_value(i)
                if candidate:
                    return candidate

        # Extra BambuStudio heuristic: the "total time" value is often a later line
        # that OCR may not keep next to the label. If both total and model printing
        # values appear in the OCR output, prefer the larger one.
        if any("model printing time" in line for line in lines) and any("total time" in line for line in lines):
            candidates: List[TimeData] = []
            for line in lines:
                if "time" not in line:
                    continue
                parsed = parse_time_expression(line)
                if parsed and parsed.total_seconds > 0:
                    candidates.append(parsed)
            if candidates:
                # Total time should usually be the longest duration on the panel,
                # but ignore obvious prep/timelapse fragments by the earlier penalty.
                return max(candidates, key=lambda td: td.total_seconds)

        # Secondary: a "total" label often appears as just "total:" in OCR.
        for i, line in enumerate(lines):
            if line.startswith("total") and "cost" not in line and "price" not in line:
                candidate = parse_time_expression(line)
                if candidate and candidate.total_seconds > 0:
                    return candidate
                candidate = next_time_value(i)
                if candidate:
                    return candidate

        def line_score(line: str) -> int:
            score = 0
            if "model" in line and "printing" in line and "time" in line:
                score += 70
            elif "print" in line and "time" in line:
                score += 60
            elif "time" in line:
                score += 50

            if "prepare" in line or "timelapse" in line:
                score -= 60

            return score

        best_time: Optional[TimeData] = None
        best_score = -10**9

        for raw_line in lines:
            if not raw_line:
                continue

            parsed = parse_time_expression(raw_line)
            if not parsed or parsed.total_seconds <= 0:
                continue

            score = line_score(raw_line)
            if best_time is None or score > best_score or (score == best_score and parsed.total_seconds > best_time.total_seconds):
                best_time = parsed
                best_score = score

        if best_time:
            return best_time
        
        return TimeData()  # Return empty if no match
    
    def _parse_filament(self, text: str, slicer_type: str, time_data: Optional[TimeData] = None) -> FilamentData:
        """
        Parse filament weight data from extracted text
        Supports: "100g", "1.5kg", "100 g", "1.5 kg", "377.2 g"
        """
        text_lower = text.lower()
        lines = [line.strip() for line in text_lower.splitlines()]

        def parse_decimal(value: str) -> float:
            return float(value.replace(',', '.'))

        def is_reasonable_grams(value: float) -> bool:
            return 0 < value < 10000

        def score_grams_candidate(value: float, had_decimal: bool) -> float:
            score = 0.0
            if not is_reasonable_grams(value):
                return -10**6

            if had_decimal:
                score += 3.0
            if value <= 500:
                score += 2.0
            if value > 500 and not had_decimal:
                score -= 3.0

            if time_data is not None and time_data.total_seconds > 0:
                grams_per_hour = value / (time_data.total_seconds / 3600.0)
                if 0.5 <= grams_per_hour <= 250:
                    score += 4.0
                elif 250 < grams_per_hour <= 500:
                    score += 1.0
                else:
                    score -= 4.0

            return score

        def normalized_grams_from_token(token: str) -> Optional[float]:
            token = token.strip()
            if not token:
                return None

            had_decimal = ("." in token) or ("," in token)
            try:
                raw_value = parse_decimal(token)
            except ValueError:
                return None

            candidates = [raw_value]
            # OCR sometimes drops decimal points, e.g. "6.44" -> "644".
            # Only consider these fixes when the implied print rate is plausible.
            if not had_decimal and raw_value >= 100 and time_data is not None and time_data.total_seconds > 0:
                candidates.append(raw_value / 10.0)
                candidates.append(raw_value / 100.0)

            best_value = None
            best_score = -10**9
            for candidate in candidates:
                candidate_score = score_grams_candidate(candidate, had_decimal)
                if candidate_score > best_score:
                    best_score = candidate_score
                    best_value = candidate

            return best_value

        def extract_kg_candidates(value: str) -> List[float]:
            return [parse_decimal(match) for match in re.findall(r'(\d+[\.,]?\d*)\s*kg\b', value)]

        def extract_g_candidates(value: str) -> List[float]:
            candidates: List[float] = []
            for token in re.findall(r'(\d+[\.,]?\d*)\s*g\b', value):
                try:
                    # Skip meter-like values (> 100)
                    raw = parse_decimal(token)
                    if raw > 100:
                        continue
                except ValueError:
                    pass
                normalized = normalized_grams_from_token(token)
                if normalized is not None:
                    candidates.append(normalized)
            return candidates

        def rightmost_g_value(value: str) -> Optional[float]:
            # Only accept explicit "g" tokens; reject meter values (usually > 100).
            matches = re.findall(r'(\d+[\.,]?\d*)\s*g\b', value)
            if not matches:
                return None
            # Try from rightmost, but skip likely meter values.
            for token in reversed(matches):
                try:
                    candidate = parse_decimal(token)
                except ValueError:
                    continue
                # Skip values that look like meter measurements (> 100 typically)
                if candidate > 100:
                    continue
                return normalized_grams_from_token(token)
            # If all rightmost values look like meters, try the smallest one.
            return normalized_grams_from_token(matches[0])

        def extract_rightmost_numeric_token(value: str) -> Optional[float]:
            tokens = re.findall(r'(\d+[\.,]?\d*)', value)
            if not tokens:
                return None
            try:
                candidate = parse_decimal(tokens[-1])
            except ValueError:
                return None
            if is_reasonable_grams(candidate):
                return candidate
            return None

        def row_matches_total(line: str) -> bool:
            return "total" in line and "price" not in line and "cost" not in line

        def row_matches_material(line: str) -> bool:
            return re.search(r'\b(material|filament|model)\b', line) is not None

        # Priority 1: explicit total/material rows from BambuStudio's table.
        targeted_lines: List[str] = []
        for line in lines:
            if not line:
                continue
            if (row_matches_total(line) or row_matches_material(line)) and "time" not in line and "price" not in line and "cost" not in line:
                targeted_lines.append(line)

        # Prefer a real total row if one exists.
        for line in targeted_lines:
            if not row_matches_total(line):
                continue
            grams = rightmost_g_value(line)
            if grams is None:
                grams = extract_rightmost_numeric_token(line)
            if grams is not None:
                return FilamentData(amount=grams, unit="g")

        # If the total row was split across OCR lines, look for the best line
        # with an explicit grams value near the total row.
        for line in targeted_lines:
            grams = rightmost_g_value(line)
            if grams is None:
                continue

            # Reject suspicious whole-number grams if there are obvious decimals
            # nearby on the same row, because OCR may have dropped the dot.
            if grams >= 100 and re.search(r'\d+[\.,]\d+\s*g\b', line):
                decimals = [parse_decimal(match) for match in re.findall(r'(\d+[\.,]\d*)\s*g\b', line)]
                if decimals:
                    grams = max(decimals)

            return FilamentData(amount=grams, unit="g")

        # BambuStudio total-row fallback: if OCR gives a row like "6.65 m 21.11 g",
        # the grams are usually the rightmost explicit g value on the row.
        for line in lines:
            if "total" in line and "g" in line:
                grams = extract_g_candidates(line)
                if grams:
                    return FilamentData(amount=max(grams), unit="g")

        # Priority 2: explicit kg first, then grams globally.
        kg_candidates = extract_kg_candidates(text_lower)
        if kg_candidates:
            return FilamentData(amount=max(kg_candidates), unit="kg")

        g_candidates = extract_g_candidates(text_lower)
        # Prefer decimal values (5.89 g) over whole numbers, as they're more reliable.
        decimal_g = [c for c in g_candidates if c != int(c)]
        if decimal_g:
            return FilamentData(amount=max(decimal_g), unit="g")
        # Fall back to whole numbers only if no decimals found.
        valid_global_g = [candidate for candidate in g_candidates if is_reasonable_grams(candidate)]
        if valid_global_g:
            best_global_g = max(valid_global_g)
            return FilamentData(amount=best_global_g, unit="g")

        # Priority 3: if OCR dropped unit glyph, use rightmost decimal in targeted line.
        for line in targeted_lines:
            # Skip lines with meter values (they're length, not weight)
            if re.search(r'\d+[\.,]?\d*\s*m\b', line):
                continue
            numeric_values = [parse_decimal(match) for match in re.findall(r'\d+[\.,]?\d*', line)]
            if numeric_values:
                candidate = numeric_values[-1]
                if is_reasonable_grams(candidate):
                    return FilamentData(amount=candidate, unit="g")

        # Last resort: if the time context indicates a short job and the OCR
        # produced a suspiciously large gram value, try the smallest decimal-like
        # candidate from the total row before giving up.
        if time_data is not None and time_data.total_seconds > 0:
            total_like_lines = [line for line in lines if row_matches_total(line)]
            for line in total_like_lines:
                decimal_candidates = [parse_decimal(match) for match in re.findall(r'(\d+[\.,]\d+)\s*g\b', line)]
                if decimal_candidates:
                    best_decimal = min(decimal_candidates)
                    return FilamentData(amount=best_decimal, unit="g")
        
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
