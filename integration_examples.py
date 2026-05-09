"""
Example Integration - How to use SlicerDataExtractor with other code
Shows multiple integration patterns for different use cases
"""

import json
from slicer_data_extractor import SlicerDataExtractor, get_exportable_variables_schema


# ============================================================================
# Pattern 1: Direct Variable Integration (Most Common)
# ============================================================================

class PrintJobCalculator:
    """Example: Calculate print job details using extracted data"""
    
    def __init__(self, extractor):
        self.extractor = extractor
    
    def process_screenshot(self, image_path):
        """Extract data and calculate job metrics"""
        result = self.extractor.extract_from_file(image_path)
        data = result.to_dict()
        
        # Extract individual variables (what you'd use in your other code)
        print_time_hours = data['print_time']['hours']
        print_time_minutes = data['print_time']['minutes']
        print_time_seconds = data['print_time']['seconds']
        total_seconds = data['print_time']['total_seconds']
        
        filament_grams = data['filament']['amount_grams']
        filament_kg = data['filament']['amount_kilograms']
        
        confidence = data['confidence']
        slicer_type = data['slicer_detected']
        
        # Now use these variables in your calculations
        print(f"\n=== Print Job Analysis ===")
        print(f"Slicer: {slicer_type}")
        print(f"Confidence: {confidence}")
        print(f"\nPrint Time:")
        print(f"  {print_time_hours}h {print_time_minutes}m {print_time_seconds}s")
        print(f"  Total: {total_seconds} seconds")
        print(f"\nFilament:")
        print(f"  {filament_grams}g ({filament_kg:.2f}kg)")
        
        # Calculate example metrics
        filament_per_hour = filament_grams / (total_seconds / 3600) if total_seconds > 0 else 0
        print(f"  Usage rate: {filament_per_hour:.2f}g/hour")
        
        return {
            'print_time_hours': print_time_hours,
            'print_time_minutes': print_time_minutes,
            'print_time_seconds': print_time_seconds,
            'total_seconds': total_seconds,
            'filament_grams': filament_grams,
            'filament_kg': filament_kg,
            'confidence': confidence,
            'filament_per_hour': filament_per_hour
        }


# ============================================================================
# Pattern 2: Node/Workflow Output (JSON-based)
# ============================================================================

class NodeRedIntegration:
    """Example: Format data for Node-RED or similar workflow systems"""
    
    def __init__(self, extractor):
        self.extractor = extractor
    
    def export_for_node_red(self, image_path):
        """Export as JSON string for Node-RED input"""
        result = self.extractor.extract_from_file(image_path)
        
        # Method 1: Direct JSON export
        json_output = result.to_json()
        print("\n=== Node-RED JSON Export ===")
        print(json_output)
        
        # Method 2: Dictionary for programmatic access
        data = result.to_dict()
        
        # Create a flattened structure if needed by your node
        flat_output = {
            'print_time_h': data['print_time']['hours'],
            'print_time_m': data['print_time']['minutes'],
            'print_time_s': data['print_time']['seconds'],
            'print_time_total_s': data['print_time']['total_seconds'],
            'filament_g': data['filament']['amount_grams'],
            'filament_kg': data['filament']['amount_kilograms'],
            'processing_travel': data['processing_options']['travel'],
            'processing_retract': data['processing_options']['retract'],
            'processing_wipe': data['processing_options']['wipe'],
            'slicer': data['slicer_detected'],
            'confidence': data['confidence']
        }
        
        print("\n=== Flattened Format (for simple nodes) ===")
        print(json.dumps(flat_output, indent=2))
        
        return flat_output


# ============================================================================
# Pattern 3: Processing Mode Selection (Conditional Logic)
# ============================================================================

class PrintSettingsManager:
    """Example: Select processing mode based on extracted options"""
    
    def __init__(self, extractor):
        self.extractor = extractor
    
    def determine_print_mode(self, image_path):
        """Use processing options to determine print mode"""
        result = self.extractor.extract_from_file(image_path)
        data = result.to_dict()
        
        options = data['processing_options']
        time_data = data['print_time']
        filament_data = data['filament']
        
        print(f"\n=== Determining Print Mode ===")
        print(f"Processing Options Detected:")
        for option, enabled in options.items():
            print(f"  {option}: {enabled}")
        
        # Determine mode based on options
        if options['travel'] and options['retract']:
            mode = "STANDARD"
        elif options['travel'] and not options['retract']:
            mode = "FAST"
        elif not options['travel']:
            mode = "MINIMAL"
        else:
            mode = "CUSTOM"
        
        print(f"\nRecommended Mode: {mode}")
        
        # Build mode-specific settings
        settings = self._build_mode_settings(
            mode=mode,
            print_time_hours=time_data['hours'],
            filament_grams=filament_data['amount_grams'],
            options=options
        )
        
        return mode, settings
    
    def _build_mode_settings(self, mode, print_time_hours, filament_grams, options):
        """Build print settings based on detected mode"""
        settings = {
            'mode': mode,
            'print_time_hours': print_time_hours,
            'filament_grams': filament_grams,
        }
        
        if mode == "STANDARD":
            settings['layer_height'] = 0.2
            settings['nozzle_temp'] = 200
            settings['bed_temp'] = 60
        elif mode == "FAST":
            settings['layer_height'] = 0.3
            settings['nozzle_temp'] = 210
            settings['bed_temp'] = 60
        elif mode == "MINIMAL":
            settings['layer_height'] = 0.1
            settings['nozzle_temp'] = 190
            settings['bed_temp'] = 50
        
        return settings


# ============================================================================
# Pattern 4: Error Handling with Confidence Scoring
# ============================================================================

class ReliableDataExtractor:
    """Example: Extract with quality assurance"""
    
    def __init__(self, extractor, min_confidence=0.7):
        self.extractor = extractor
        self.min_confidence = min_confidence
    
    def extract_with_validation(self, image_path):
        """Extract with confidence-based validation"""
        result = self.extractor.extract_from_file(image_path)
        data = result.to_dict()
        
        confidence = data['confidence']
        
        print(f"\n=== Extraction Validation ===")
        print(f"Confidence Score: {confidence}")
        print(f"Minimum Required: {self.min_confidence}")
        
        if confidence >= self.min_confidence:
            print(f"✓ Extraction accepted")
            return {
                'status': 'success',
                'confidence': confidence,
                'data': data
            }
        else:
            print(f"✗ Extraction rejected - confidence too low")
            print(f"Raw text detected:")
            print(data['raw_text'][:200] + "..." if len(data['raw_text']) > 200 else data['raw_text'])
            return {
                'status': 'rejected',
                'confidence': confidence,
                'reason': f'Confidence {confidence} below minimum {self.min_confidence}',
                'raw_text': data['raw_text']
            }


# ============================================================================
# Pattern 5: Database Storage Format
# ============================================================================

class PrintJobDatabase:
    """Example: Format data for database storage"""
    
    def __init__(self, extractor):
        self.extractor = extractor
    
    def create_db_record(self, image_path, job_id):
        """Create a database record from extracted data"""
        result = self.extractor.extract_from_file(image_path)
        data = result.to_dict()
        
        # Format for database insertion
        record = {
            'job_id': job_id,
            'slicer_type': data['slicer_detected'],
            'print_time_seconds': int(data['print_time']['total_seconds']),
            'filament_weight_grams': round(data['filament']['amount_grams'], 2),
            'confidence_score': round(data['confidence'], 2),
            'extraction_status': 'success' if data['confidence'] >= 0.7 else 'manual_review',
            'raw_ocr_text': data['raw_text'],
            'processing_options': json.dumps(data['processing_options'])
        }
        
        print(f"\n=== Database Record ===")
        for key, value in record.items():
            if key == 'raw_ocr_text':
                print(f"  {key}: (OCR text - {len(str(value))} chars)")
            else:
                print(f"  {key}: {value}")
        
        return record


# ============================================================================
# Pattern 6: Multi-File Batch Processing
# ============================================================================

class BatchProcessor:
    """Example: Process multiple screenshots"""
    
    def __init__(self, extractor):
        self.extractor = extractor
    
    def process_batch(self, image_paths):
        """Process multiple images and aggregate results"""
        results = []
        
        for idx, image_path in enumerate(image_paths, 1):
            try:
                result = self.extractor.extract_from_file(image_path)
                data = result.to_dict()
                
                results.append({
                    'image': image_path,
                    'print_time_hours': data['print_time']['hours'],
                    'filament_grams': data['filament']['amount_grams'],
                    'confidence': data['confidence'],
                    'status': 'success'
                })
            except Exception as e:
                results.append({
                    'image': image_path,
                    'status': 'error',
                    'error': str(e)
                })
        
        # Print summary
        print(f"\n=== Batch Processing Summary ===")
        print(f"Total files: {len(image_paths)}")
        print(f"Successful: {sum(1 for r in results if r['status'] == 'success')}")
        print(f"Failed: {sum(1 for r in results if r['status'] == 'error')}")
        
        # Calculate aggregates
        successful = [r for r in results if r['status'] == 'success']
        if successful:
            avg_time = sum(r['print_time_hours'] for r in successful) / len(successful)
            total_filament = sum(r['filament_grams'] for r in successful)
            avg_confidence = sum(r['confidence'] for r in successful) / len(successful)
            
            print(f"\nAverages (successful extractions):")
            print(f"  Avg print time: {avg_time:.1f} hours")
            print(f"  Total filament: {total_filament:.1f}g")
            print(f"  Avg confidence: {avg_confidence:.2f}")
        
        return results


# ============================================================================
# Main Demo
# ============================================================================

def main():
    """Demonstrate all integration patterns"""
    
    # Initialize extractor (set your Tesseract path)
    extractor = SlicerDataExtractor(
        tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    )
    
    # Example image path (replace with your actual screenshot)
    image_path = 'screenshot.png'
    
    print("\n" + "="*70)
    print("SLICER DATA EXTRACTOR - INTEGRATION EXAMPLES")
    print("="*70)
    
    # Print available variables
    schema = get_exportable_variables_schema()
    print("\nAll Available Variables:")
    for category, variables in schema.items():
        print(f"\n{category}:")
        for var_path in variables.keys():
            print(f"  - {var_path}")
    
    # Note: The following examples require an actual screenshot file
    print("\n" + "="*70)
    print("INTEGRATION PATTERNS (require valid screenshot):")
    print("="*70)
    print("""
Pattern 1: PrintJobCalculator
    calculator = PrintJobCalculator(extractor)
    metrics = calculator.process_screenshot('screenshot.png')

Pattern 2: NodeRedIntegration
    node_integration = NodeRedIntegration(extractor)
    flat_data = node_integration.export_for_node_red('screenshot.png')

Pattern 3: PrintSettingsManager
    settings_mgr = PrintSettingsManager(extractor)
    mode, settings = settings_mgr.determine_print_mode('screenshot.png')

Pattern 4: ReliableDataExtractor
    qa_extractor = ReliableDataExtractor(extractor, min_confidence=0.8)
    result = qa_extractor.extract_with_validation('screenshot.png')

Pattern 5: PrintJobDatabase
    db = PrintJobDatabase(extractor)
    record = db.create_db_record('screenshot.png', job_id=123)

Pattern 6: BatchProcessor
    processor = BatchProcessor(extractor)
    results = processor.process_batch(['img1.png', 'img2.png', 'img3.png'])
    """)


if __name__ == "__main__":
    main()
