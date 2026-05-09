"""
Configuration Templates - Ready-to-use configurations for common scenarios
Copy and modify these for your specific use case
"""

import json
from slicer_data_extractor import SlicerDataExtractor, get_exportable_variables_schema


# ============================================================================
# CONFIG 1: Basic Setup (Minimal)
# ============================================================================

class BasicConfig:
    """Minimal configuration - extract and access data"""
    
    @staticmethod
    def setup():
        """Create extractor with default settings"""
        extractor = SlicerDataExtractor(
            tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        )
        return extractor
    
    @staticmethod
    def extract(extractor, image_path):
        """Extract and return dictionary"""
        result = extractor.extract_from_file(image_path)
        return result.to_dict()
    
    @staticmethod
    def example():
        extractor = BasicConfig.setup()
        data = BasicConfig.extract(extractor, 'screenshot.png')
        print(f"Time: {data['print_time']['hours']}h {data['print_time']['minutes']}m")
        print(f"Filament: {data['filament']['amount_grams']}g")


# ============================================================================
# CONFIG 2: Node-RED Integration
# ============================================================================

class NodeREDConfig:
    """Configuration for Node-RED workflows"""
    
    OUTPUT_FORMAT = "json"  # or "dict", "flattened"
    
    @staticmethod
    def setup():
        """Create extractor for Node-RED"""
        extractor = SlicerDataExtractor(
            tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        )
        return extractor
    
    @staticmethod
    def extract_for_node_red(extractor, image_path):
        """Extract and format for Node-RED"""
        result = extractor.extract_from_file(image_path)
        
        if NodeREDConfig.OUTPUT_FORMAT == "json":
            return result.to_json()
        elif NodeREDConfig.OUTPUT_FORMAT == "flattened":
            data = result.to_dict()
            return {
                'time_h': data['print_time']['hours'],
                'time_m': data['print_time']['minutes'],
                'time_s': data['print_time']['seconds'],
                'time_total_s': data['print_time']['total_seconds'],
                'filament_g': data['filament']['amount_grams'],
                'filament_kg': data['filament']['amount_kilograms'],
                'slicer': data['slicer_detected'],
                'confidence': data['confidence']
            }
        else:
            return result.to_dict()
    
    @staticmethod
    def example():
        extractor = NodeREDConfig.setup()
        # Output as JSON string for Node-RED
        json_output = NodeREDConfig.extract_for_node_red(extractor, 'screenshot.png')
        if isinstance(json_output, str):
            print("JSON Output for Node-RED:")
            print(json_output)
        else:
            print("Flattened Output for Node-RED:")
            print(json.dumps(json_output, indent=2))


# ============================================================================
# CONFIG 3: Database Integration
# ============================================================================

class DatabaseConfig:
    """Configuration for storing in database"""
    
    TABLE_SCHEMA = {
        'print_id': 'INTEGER PRIMARY KEY',
        'print_time_seconds': 'REAL',
        'filament_weight_g': 'REAL',
        'filament_weight_kg': 'REAL',
        'slicer_type': 'TEXT',
        'confidence': 'REAL',
        'extraction_status': 'TEXT',
        'processing_travel': 'BOOLEAN',
        'processing_retract': 'BOOLEAN',
        'processing_wipe': 'BOOLEAN',
        'processing_seams': 'BOOLEAN',
        'raw_ocr_text': 'TEXT',
        'timestamp': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
    }
    
    @staticmethod
    def setup():
        """Create extractor for database use"""
        extractor = SlicerDataExtractor(
            tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        )
        return extractor
    
    @staticmethod
    def create_record(extractor, image_path, print_id):
        """Create database record from extraction"""
        result = extractor.extract_from_file(image_path)
        data = result.to_dict()
        
        record = {
            'print_id': print_id,
            'print_time_seconds': int(data['print_time']['total_seconds']),
            'filament_weight_g': round(data['filament']['amount_grams'], 2),
            'filament_weight_kg': round(data['filament']['amount_kilograms'], 4),
            'slicer_type': data['slicer_detected'],
            'confidence': round(data['confidence'], 2),
            'extraction_status': 'success' if data['confidence'] >= 0.7 else 'review',
            'processing_travel': data['processing_options']['travel'],
            'processing_retract': data['processing_options']['retract'],
            'processing_wipe': data['processing_options']['wipe'],
            'processing_seams': data['processing_options']['seams'],
            'raw_ocr_text': data['raw_text']
        }
        
        return record
    
    @staticmethod
    def example():
        extractor = DatabaseConfig.setup()
        record = DatabaseConfig.create_record(extractor, 'screenshot.png', print_id=1)
        print("Database Record:")
        print(json.dumps(record, indent=2, default=str))


# ============================================================================
# CONFIG 4: Quality Assurance (High Confidence Only)
# ============================================================================

class QAConfig:
    """Configuration for quality-assured extractions"""
    
    MIN_CONFIDENCE = 0.8
    RETRY_ON_FAIL = True
    
    @staticmethod
    def setup():
        """Create extractor with QA settings"""
        extractor = SlicerDataExtractor(
            tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        )
        return extractor
    
    @staticmethod
    def extract_with_qa(extractor, image_path):
        """Extract with confidence validation"""
        result = extractor.extract_from_file(image_path)
        data = result.to_dict()
        
        confidence = data['confidence']
        
        if confidence >= QAConfig.MIN_CONFIDENCE:
            return {
                'status': 'approved',
                'confidence': confidence,
                'data': data
            }
        else:
            return {
                'status': 'rejected',
                'confidence': confidence,
                'reason': f'Confidence {confidence} below minimum {QAConfig.MIN_CONFIDENCE}',
                'recommendation': 'Manual review or retake screenshot',
                'raw_text': data['raw_text']
            }
    
    @staticmethod
    def example():
        extractor = QAConfig.setup()
        result = QAConfig.extract_with_qa(extractor, 'screenshot.png')
        print(f"QA Status: {result['status']}")
        print(f"Confidence: {result['confidence']}")
        if result['status'] == 'rejected':
            print(f"Reason: {result['reason']}")


# ============================================================================
# CONFIG 5: Batch Processing
# ============================================================================

class BatchConfig:
    """Configuration for processing multiple images"""
    
    SKIP_ERRORS = True
    MIN_CONFIDENCE = 0.5
    
    @staticmethod
    def setup():
        """Create extractor for batch processing"""
        extractor = SlicerDataExtractor(
            tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        )
        return extractor
    
    @staticmethod
    def process_batch(extractor, image_paths):
        """Process multiple images and return results"""
        results = []
        
        for idx, image_path in enumerate(image_paths, 1):
            try:
                result = extractor.extract_from_file(image_path)
                data = result.to_dict()
                
                if data['confidence'] >= BatchConfig.MIN_CONFIDENCE:
                    results.append({
                        'index': idx,
                        'file': image_path,
                        'status': 'success',
                        'print_time_hours': data['print_time']['hours'],
                        'filament_grams': data['filament']['amount_grams'],
                        'confidence': data['confidence']
                    })
                else:
                    results.append({
                        'index': idx,
                        'file': image_path,
                        'status': 'low_confidence',
                        'confidence': data['confidence']
                    })
            except Exception as e:
                if BatchConfig.SKIP_ERRORS:
                    results.append({
                        'index': idx,
                        'file': image_path,
                        'status': 'error',
                        'error': str(e)
                    })
                else:
                    raise
        
        return results
    
    @staticmethod
    def get_summary(results):
        """Get summary statistics from batch results"""
        successful = [r for r in results if r['status'] == 'success']
        
        summary = {
            'total_files': len(results),
            'successful': len(successful),
            'failed': len([r for r in results if r['status'] in ['error', 'low_confidence']]),
            'statistics': {}
        }
        
        if successful:
            summary['statistics'] = {
                'avg_print_time_hours': sum(r['print_time_hours'] for r in successful) / len(successful),
                'total_filament_grams': sum(r['filament_grams'] for r in successful),
                'avg_confidence': sum(r['confidence'] for r in successful) / len(successful),
                'min_confidence': min(r['confidence'] for r in successful),
                'max_confidence': max(r['confidence'] for r in successful)
            }
        
        return summary
    
    @staticmethod
    def example():
        extractor = BatchConfig.setup()
        image_files = ['screenshot1.png', 'screenshot2.png', 'screenshot3.png']
        results = BatchConfig.process_batch(extractor, image_files)
        summary = BatchConfig.get_summary(results)
        
        print("Batch Processing Results:")
        print(json.dumps(summary, indent=2))


# ============================================================================
# CONFIG 6: API Integration
# ============================================================================

class APIConfig:
    """Configuration for REST API integration"""
    
    API_ENDPOINT = "https://api.example.com/print-jobs"
    INCLUDE_RAW_TEXT = False
    TIMEOUT = 30
    
    @staticmethod
    def setup():
        """Create extractor for API use"""
        extractor = SlicerDataExtractor(
            tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        )
        return extractor
    
    @staticmethod
    def prepare_payload(extractor, image_path, job_id=None):
        """Prepare payload for API"""
        result = extractor.extract_from_file(image_path)
        data = result.to_dict()
        
        payload = {
            'job_id': job_id,
            'print_time': {
                'hours': data['print_time']['hours'],
                'minutes': data['print_time']['minutes'],
                'seconds': data['print_time']['seconds'],
                'total_seconds': data['print_time']['total_seconds']
            },
            'filament': {
                'amount': data['filament']['amount_grams'],
                'unit': 'g'
            },
            'processing_options': data['processing_options'],
            'confidence': data['confidence'],
            'slicer': data['slicer_detected']
        }
        
        if APIConfig.INCLUDE_RAW_TEXT:
            payload['raw_ocr_text'] = data['raw_text']
        
        return payload
    
    @staticmethod
    def example():
        extractor = APIConfig.setup()
        payload = APIConfig.prepare_payload(extractor, 'screenshot.png', job_id=12345)
        
        print("API Payload:")
        print(json.dumps(payload, indent=2))
        
        # Example of how to send:
        # import requests
        # response = requests.post(APIConfig.API_ENDPOINT, json=payload, timeout=APIConfig.TIMEOUT)
        # print(f"API Response: {response.status_code}")


# ============================================================================
# CONFIG 7: Real-time Monitoring
# ============================================================================

class RealtimeConfig:
    """Configuration for continuous monitoring"""
    
    WATCH_FOLDER = r"C:\Screenshots"
    CHECK_INTERVAL = 5  # seconds
    PROCESS_ON_CHANGE = True
    
    @staticmethod
    def setup():
        """Create extractor for real-time monitoring"""
        extractor = SlicerDataExtractor(
            tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        )
        return extractor
    
    @staticmethod
    def process_new_screenshot(extractor, image_path):
        """Process a newly detected screenshot"""
        try:
            result = extractor.extract_from_file(image_path)
            data = result.to_dict()
            
            notification = {
                'timestamp': __import__('datetime').datetime.now().isoformat(),
                'file': image_path,
                'print_time': data['print_time']['formatted'],
                'filament': data['filament']['formatted'],
                'confidence': data['confidence'],
                'slicer': data['slicer_detected']
            }
            
            return notification
        except Exception as e:
            return {
                'timestamp': __import__('datetime').datetime.now().isoformat(),
                'file': image_path,
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def example():
        extractor = RealtimeConfig.setup()
        # This would normally run in a loop watching WATCH_FOLDER
        notification = RealtimeConfig.process_new_screenshot(extractor, 'screenshot.png')
        print("Real-time Notification:")
        print(json.dumps(notification, indent=2, default=str))


# ============================================================================
# CONFIG 8: Mode Selection (Adaptive)
# ============================================================================

class ModeConfig:
    """Configuration for adaptive mode selection based on options"""
    
    MODES = {
        'STANDARD': {
            'description': 'Standard print settings',
            'conditions': lambda opts: opts['travel'] and opts['retract'],
            'settings': {
                'layer_height': 0.2,
                'nozzle_temp': 200,
                'bed_temp': 60
            }
        },
        'FAST': {
            'description': 'Fast print settings',
            'conditions': lambda opts: opts['travel'] and not opts['retract'],
            'settings': {
                'layer_height': 0.3,
                'nozzle_temp': 210,
                'bed_temp': 60
            }
        },
        'QUALITY': {
            'description': 'High quality settings',
            'conditions': lambda opts: opts['wipe'] and opts['seams'],
            'settings': {
                'layer_height': 0.1,
                'nozzle_temp': 190,
                'bed_temp': 50
            }
        },
        'MINIMAL': {
            'description': 'Minimal processing',
            'conditions': lambda opts: not opts['travel'] and not opts['retract'],
            'settings': {
                'layer_height': 0.2,
                'nozzle_temp': 195,
                'bed_temp': 55
            }
        }
    }
    
    @staticmethod
    def setup():
        """Create extractor for mode detection"""
        extractor = SlicerDataExtractor(
            tesseract_path=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        )
        return extractor
    
    @staticmethod
    def determine_mode(extractor, image_path):
        """Determine print mode from processing options"""
        result = extractor.extract_from_file(image_path)
        data = result.to_dict()
        
        options = data['processing_options']
        
        # Check conditions for each mode
        for mode_name, mode_config in ModeConfig.MODES.items():
            if mode_config['conditions'](options):
                return {
                    'mode': mode_name,
                    'description': mode_config['description'],
                    'settings': mode_config['settings'],
                    'confidence': data['confidence']
                }
        
        # Default if no conditions match
        return {
            'mode': 'STANDARD',
            'description': 'Default mode',
            'settings': ModeConfig.MODES['STANDARD']['settings'],
            'confidence': data['confidence']
        }
    
    @staticmethod
    def example():
        extractor = ModeConfig.setup()
        mode_info = ModeConfig.determine_mode(extractor, 'screenshot.png')
        print("Adaptive Mode Selection:")
        print(json.dumps(mode_info, indent=2))


# ============================================================================
# Helper Function - Print All Available Variables
# ============================================================================

def print_available_variables():
    """Print all available variables across all configs"""
    print("\n" + "="*70)
    print("AVAILABLE VARIABLES ACROSS ALL CONFIGS")
    print("="*70)
    
    schema = get_exportable_variables_schema()
    for category, variables in schema.items():
        print(f"\n{category}:")
        for var_path, description in variables.items():
            print(f"  data['{var_path.split('.')[0]}']['{var_path.split('.')[1]}']")


# ============================================================================
# Main - Demo All Configs
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("CONFIGURATION TEMPLATES FOR SLICER DATA EXTRACTOR")
    print("="*70)
    
    print_available_variables()
    
    print("\n" + "="*70)
    print("AVAILABLE CONFIGURATIONS:")
    print("="*70)
    
    configs = [
        ("BasicConfig", "Minimal setup - extract and use data"),
        ("NodeREDConfig", "For Node-RED workflow integration"),
        ("DatabaseConfig", "For database storage"),
        ("QAConfig", "High confidence extractions only"),
        ("BatchConfig", "Process multiple screenshots"),
        ("APIConfig", "REST API integration"),
        ("RealtimeConfig", "Real-time monitoring"),
        ("ModeConfig", "Adaptive mode selection")
    ]
    
    for config_name, description in configs:
        print(f"\n  {config_name}:")
        print(f"    {description}")
        print(f"    Example: {config_name}.example()")
    
    print("\n" + "="*70)
    print("USAGE:")
    print("="*70)
    print("""
Copy the config class you need and modify for your use case:

Example 1 - Basic extraction:
    from config_templates import BasicConfig
    extractor = BasicConfig.setup()
    data = BasicConfig.extract(extractor, 'screenshot.png')

Example 2 - Node-RED:
    from config_templates import NodeREDConfig
    extractor = NodeREDConfig.setup()
    json_output = NodeREDConfig.extract_for_node_red(extractor, 'screenshot.png')

Example 3 - Database:
    from config_templates import DatabaseConfig
    extractor = DatabaseConfig.setup()
    record = DatabaseConfig.create_record(extractor, 'screenshot.png', print_id=1)

Example 4 - Quality Assured:
    from config_templates import QAConfig
    extractor = QAConfig.setup()
    result = QAConfig.extract_with_qa(extractor, 'screenshot.png')

Example 5 - Batch:
    from config_templates import BatchConfig
    extractor = BatchConfig.setup()
    results = BatchConfig.process_batch(extractor, ['img1.png', 'img2.png'])

Example 6 - API:
    from config_templates import APIConfig
    extractor = APIConfig.setup()
    payload = APIConfig.prepare_payload(extractor, 'screenshot.png', job_id=123)

Example 7 - Real-time:
    from config_templates import RealtimeConfig
    extractor = RealtimeConfig.setup()
    notification = RealtimeConfig.process_new_screenshot(extractor, 'screenshot.png')

Example 8 - Adaptive Mode:
    from config_templates import ModeConfig
    extractor = ModeConfig.setup()
    mode = ModeConfig.determine_mode(extractor, 'screenshot.png')
    """)
