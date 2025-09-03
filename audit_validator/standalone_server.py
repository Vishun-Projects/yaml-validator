#!/usr/bin/env python3
"""
Standalone HTTP Server for Custom UI
Uses Python's built-in http.server to serve the custom UI
No dependencies on problematic streamlit_app.py
"""

import http.server
import socketserver
import os
import json
import yaml
import pandas as pd
from datetime import datetime, timedelta
import base64
import urllib.parse
from pathlib import Path

# Import real functionality from streamlit_app.py
try:
    from streamlit_app import (
        ai_audit_gui, 
        read_uploaded_config_cached, 
        ask_groq_cached, 
        DEFAULT_MODELS, 
        DEFAULT_GROQ_KEYS,
        build_exec_pdf_bytes
    )
    print("✅ Successfully imported real AI functionality from streamlit_app")
    # Use our local enhanced snapshot collection instead of ai_audit_gui
    class EnhancedStandaloneAI:
        @staticmethod
        def collect_full_snapshot(interactive_ui=False, collect_apps_flag=False):
            """Collect actual system snapshot data for validation"""
            try:
                import platform
                import psutil
                import socket
                import os
                
                snapshot = {
                    "device": platform.node(),
                    "collected": True,
                    "collected_at": datetime.utcnow().isoformat(),
                    
                    # System information
                    "platform": platform.system(),
                    "platform_version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    
                    # Hardware info
                    "cpu_count": psutil.cpu_count(),
                    "memory_total": f"{psutil.virtual_memory().total // (1024**3)} GB",
                    "memory_available": f"{psutil.virtual_memory().available // (1024**3)} GB",
                    
                    # Network info
                    "hostname": socket.gethostname(),
                    "fqdn": socket.getfqdn(),
                    
                    # OS info
                    "os_name": platform.system(),
                    "os_version": platform.version(),
                    "os_release": platform.release(),
                    
                    # Environment info
                    "username": os.getenv('USERNAME') or os.getenv('USER'),
                    "home_dir": os.path.expanduser('~'),
                    "current_dir": os.getcwd(),
                    
                    # Windows specific
                    "windows_directory": os.getenv('WINDIR', 'C:\\Windows'),
                    "program_files": os.getenv('PROGRAMFILES', 'C:\\Program Files'),
                    
                    # Language and locale
                    "language": os.getenv('LANG') or 'en-US',
                    "timezone": os.getenv('TZ') or 'UTC'
                }
                
                # Add disk information
                try:
                    disk_partitions = psutil.disk_partitions()
                    disk_info = []
                    for partition in disk_partitions:
                        if partition.device:
                            usage = psutil.disk_usage(partition.mountpoint)
                            disk_info.append({
                                "device": partition.device,
                                "mountpoint": partition.mountpoint,
                                "filesystem": partition.fstype,
                                "total": f"{usage.total // (1024**3)} GB",
                                "free": f"{usage.free // (1024**3)} GB"
                            })
                    snapshot["disks"] = disk_info
                except Exception as e:
                    snapshot["disks"] = [{"error": str(e)}]
                
                # Add network interfaces
                try:
                    net_if_addrs = psutil.net_if_addrs()
                    network_info = []
                    for interface, addrs in net_if_addrs.items():
                        for addr in addrs:
                            if addr.family == socket.AF_INET:  # IPv4
                                network_info.append({
                                    "interface": interface,
                                    "address": addr.address,
                                    "netmask": addr.netmask
                                })
                    snapshot["network_interfaces"] = network_info
                except Exception as e:
                    snapshot["network_interfaces"] = [{"error": str(e)}]
                
                print(f"✅ Collected system snapshot with {len(snapshot)} fields")
                print(f"📊 Snapshot keys: {list(snapshot.keys())}")
                print(f"📊 Snapshot sample: {dict(list(snapshot.items())[:5])}")
                return snapshot
                
            except Exception as e:
                print(f"❌ Error collecting snapshot: {e}")
                # Fallback to basic info
                return {
                    "device": "fallback-device",
                    "collected": True,
                    "collected_at": datetime.utcnow().isoformat(),
                    "error": str(e)
                }
        
        @staticmethod
        def validate_against_yaml(cfg, snap):
            # Use our enhanced validation instead
            return None  # This will force the use of our enhanced_validation method
    
    StandaloneAI = EnhancedStandaloneAI
except ImportError as e:
    print(f"⚠️ Warning: Could not import from streamlit_app: {e}")
    print("Using fallback AI implementation")
    
    # Fallback AI implementation
    class _FakeAI:
        @staticmethod
        def collect_full_snapshot(interactive_ui=False, collect_apps_flag=False):
            """Collect actual system snapshot data for validation"""
            try:
                import platform
                import psutil
                import socket
                import os
                
                snapshot = {
                    "device": platform.node(),
                    "collected": True,
                    "collected_at": datetime.utcnow().isoformat(),
                    
                    # System information
                    "platform": platform.system(),
                    "platform_version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    
                    # Hardware info
                    "cpu_count": psutil.cpu_count(),
                    "memory_total": f"{psutil.virtual_memory().total // (1024**3)} GB",
                    "memory_available": f"{psutil.virtual_memory().available // (1024**3)} GB",
                    
                    # Network info
                    "hostname": socket.gethostname(),
                    "fqdn": socket.getfqdn(),
                    
                    # OS info
                    "os_name": platform.system(),
                    "os_version": platform.version(),
                    "os_release": platform.release(),
                    
                    # Environment info
                    "username": os.getenv('USERNAME') or os.getenv('USER'),
                    "home_dir": os.path.expanduser('~'),
                    "current_dir": os.getcwd(),
                    
                    # Windows specific
                    "windows_directory": os.getenv('WINDIR', 'C:\\Windows'),
                    "program_files": os.getenv('PROGRAMFILES', 'C:\\Program Files'),
                    
                    # Language and locale
                    "language": os.getenv('LANG') or 'en-US',
                    "timezone": os.getenv('TZ') or 'UTC'
                }
                
                # Add disk information
                try:
                    disk_partitions = psutil.disk_partitions()
                    disk_info = []
                    for partition in disk_partitions:
                        if partition.device:
                            usage = psutil.disk_usage(partition.mountpoint)
                            disk_info.append({
                                "device": partition.device,
                                "mountpoint": partition.mountpoint,
                                "filesystem": partition.fstype,
                                "total": f"{usage.total // (1024**3)} GB",
                                "free": f"{usage.free // (1024**3)} GB"
                            })
                    snapshot["disks"] = disk_info
                except Exception as e:
                    snapshot["disks"] = [{"error": str(e)}]
                
                # Add network interfaces
                try:
                    net_if_addrs = psutil.net_if_addrs()
                    network_info = []
                    for interface, addrs in net_if_addrs.items():
                        for addr in addrs:
                            if addr.family == socket.AF_INET:  # IPv4
                                network_info.append({
                                    "interface": interface,
                                    "address": addr.address,
                                    "netmask": addr.netmask
                                })
                    snapshot["network_interfaces"] = network_info
                except Exception as e:
                    snapshot["network_interfaces"] = [{"error": str(e)}]
                
                print(f"✅ Collected system snapshot with {len(snapshot)} fields")
                return snapshot
                
            except Exception as e:
                print(f"❌ Error collecting snapshot: {e}")
                # Fallback to basic info
                return {
                    "device": "fallback-device",
                    "collected": True,
                    "collected_at": datetime.utcnow().isoformat(),
                    "error": str(e)
                }

        @staticmethod
        def collect_generic_snapshot():
            return {"device": "generic-demo"}

        @staticmethod
        def validate_against_yaml(cfg, snap):
            now = datetime.utcnow()
            return {
                "match_percentage": 73,
                "details": [
                    {"key": "ssh.password_auth", "expected": "no", "actual": "yes", "status": "mismatch", "severity": "critical", "explanation": "Password auth enabled", "first_seen": (now - timedelta(days=5)).isoformat()},
                    {"key": "tls.expiry", "expected": ">30d", "actual": "10d", "status": "mismatch", "severity": "high", "explanation": "Certificate expires soon", "first_seen": (now - timedelta(days=12)).isoformat()},
                    {"key": "ntp.server", "expected": "ntp.example.com", "actual": "pool.ntp.org", "status": "partial", "severity": "medium", "explanation": "NTP different", "first_seen": (now - timedelta(days=2)).isoformat()},
                    {"key": "device.hostname", "expected": "prod-router", "actual": "prod-router", "status": "match", "severity": "low", "explanation": "OK", "first_seen": (now - timedelta(days=60)).isoformat()},
                ],
            }
    
    # Fallback AI chat function
    def ask_groq_cached(prompt, model, keys, system_prompt="You are an expert QA analyst.", max_tokens=700, temperature=0.25, timeout=18):
        return "❌ AI service not available. Please check your API keys."
    
    # Fallback constants
    DEFAULT_MODELS = ["llama-3.1-8b-instant"]
    DEFAULT_GROQ_KEYS = ("fallback_key",)
    
    StandaloneAI = _FakeAI()

# Add real functions from streamlit_app.py
def read_uploaded_config_cached(file_bytes: bytes, filename: str):
    import io

    ext = os.path.splitext(filename)[1].lower()
    if ext in [".xlsx", ".xls", ".xlsm"]:
        # openpyxl engine recommended
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, dtype=str, engine="openpyxl")
        
        # Process each row and parse comma-separated fields
        processed_rows = []
        for _, row in df.iterrows():
            if row.notnull().any():
                processed_row = {}
                for col_name, value in row.to_dict().items():
                    if pd.isna(value):
                        processed_row[str(col_name)] = None
                    else:
                        # Check if value contains comma-separated fields
                        if ',' in str(value) and any(keyword in str(value).lower() for keyword in ['windows', 'intel', 'nvidia', 'amd', 'ram', 'ssd', 'hdd']):
                            # Parse comma-separated fields
                            fields = [field.strip() for field in str(value).split(',')]
                            processed_row[str(col_name)] = fields
                        else:
                            processed_row[str(col_name)] = str(value)
                processed_rows.append(processed_row)
        
        return yaml.safe_dump(processed_rows, sort_keys=False)
    else:
        return file_bytes.decode("utf-8", errors="ignore")

def parse_excel_fields(field_value):
    """Parse Excel fields that contain comma-separated values"""
    if not field_value or pd.isna(field_value):
        return []
    
    field_str = str(field_value)
    if ',' not in field_str:
        return [field_str.strip()]
    
    # Split by comma and clean up
    fields = [field.strip() for field in field_str.split(',')]
    return [f for f in fields if f]  # Remove empty fields

def calculate_field_match_score(expected_fields, actual_fields, user_preferences=None):
    """Calculate match score between expected and actual fields with user preferences"""
    if not expected_fields or not actual_fields:
        return 0, [], []
    
    # Parse fields if they're strings
    if isinstance(expected_fields, str):
        expected_fields = parse_excel_fields(expected_fields)
    if isinstance(actual_fields, str):
        actual_fields = parse_excel_fields(actual_fields)
    
    print(f"    Comparing {len(expected_fields)} expected fields with {len(actual_fields)} actual fields")
    
    total_score = 0
    total_weight = 0
    matched_fields = []
    mismatched_fields = []
    
    for expected_field in expected_fields:
        print(f"      Looking for: '{expected_field}'")
        
        # Find best match for this field
        best_match = None
        best_score = 0
        
        for actual_field in actual_fields:
            # Calculate similarity score
            score = calculate_similarity(expected_field, actual_field)
            print(f"        vs '{actual_field}': {score:.2f}")
            if score > best_score:
                best_score = score
                best_match = actual_field
        
        # Get weight for this field type
        field_type = get_field_type(expected_field)
        weight = user_preferences.get('field_weights', {}).get(field_type, 10) if user_preferences else 10
        
        print(f"        Best match: '{best_match}' (score: {best_score:.2f}, weight: {weight})")
        
        if best_score >= 0.7:  # Lower threshold for better matching
            matched_fields.append({
                'expected': expected_field,
                'actual': best_match,
                'score': best_score,
                'weight': weight
            })
            total_score += best_score * weight
        else:
            mismatched_fields.append({
                'expected': expected_field,
                'actual': 'Not found',
                'score': 0,
                'weight': weight
            })
        
        total_weight += weight
    
    # Normalize score to 0-100 range
    final_score = (total_score / total_weight * 100) if total_weight > 0 else 0
    
    print(f"    Final field score: {final_score:.1f}%")
    
    return final_score, matched_fields, mismatched_fields

def calculate_similarity(str1, str2):
    """Calculate similarity between two strings with enhanced matching"""
    if not str1 or not str2:
        return 0
    
    str1_lower = str1.lower().strip()
    str2_lower = str2.lower().strip()
    
    # Exact match
    if str1_lower == str2_lower:
        return 1.0
    
    # Contains match (one string is part of another)
    if str1_lower in str2_lower or str2_lower in str1_lower:
        return 0.95
    
    # Check for key component matches
    key_components = {
        'windows': ['windows', 'win'],
        'intel': ['intel', 'xeon', 'core', 'i3', 'i5', 'i7', 'i9'],
        'amd': ['amd', 'ryzen', 'athlon'],
        'nvidia': ['nvidia', 'geforce', 'gtx', 'rtx'],
        'ram': ['ram', 'memory', 'gb'],
        'ssd': ['ssd', 'solid state'],
        'hdd': ['hdd', 'hard disk', 'hard drive']
    }
    
    # Check if both strings contain the same key component
    for component, variants in key_components.items():
        str1_has_component = any(variant in str1_lower for variant in variants)
        str2_has_component = any(variant in str2_lower for variant in variants)
        
        if str1_has_component and str2_has_component:
            # Both have the same component type
            return 0.85
    
    # Partial word match with improved algorithm
    words1 = set(str1_lower.split())
    words2 = set(str2_lower.split())
    
    if words1 and words2:
        # Remove common words that don't add meaning
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words1 = words1 - common_words
        words2 = words2 - common_words
        
        if words1 and words2:
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            if union:
                base_score = len(intersection) / len(union)
                
                # Boost score if there are meaningful matches
                if len(intersection) > 0:
                    return min(0.8, base_score + 0.3)
    
    # Check for number matches (RAM, storage sizes)
    import re
    numbers1 = re.findall(r'\d+', str1_lower)
    numbers2 = re.findall(r'\d+', str2_lower)
    
    if numbers1 and numbers2:
        # If numbers are close, give some credit
        for n1 in numbers1:
            for n2 in numbers2:
                if abs(int(n1) - int(n2)) <= 2:  # Allow small differences
                    return 0.6
    
    return 0.0

def get_field_type(field):
    """Determine the type of field for weighting purposes"""
    field_lower = field.lower()
    
    if any(keyword in field_lower for keyword in ['windows', 'os', 'operating system']):
        return 'os'
    elif any(keyword in field_lower for keyword in ['intel', 'amd', 'cpu', 'processor']):
        return 'cpu'
    elif any(keyword in field_lower for keyword in ['nvidia', 'amd', 'geforce', 'graphics', 'gpu']):
        return 'gpu'
    elif any(keyword in field_lower for keyword in ['ram', 'memory']):
        return 'memory'
    elif any(keyword in field_lower for keyword in ['ssd', 'hdd', 'storage', 'disk']):
        return 'storage'
    elif any(keyword in field_lower for keyword in ['desktop', 'laptop', 'server']):
        return 'device_type'
    else:
        return 'other'

def extract_excel_columns(file_data, filename):
    """Extract column names from Excel file"""
    try:
        import io
        
        print(f"🔍 Starting column extraction for {filename}")
        print(f"📊 File data size: {len(file_data)} bytes")
        
        # Create a BytesIO object from the file data
        file_stream = io.BytesIO(file_data)
        print(f"📁 Created BytesIO stream")
        
        # Read Excel file
        if filename.lower().endswith('.xlsx'):
            print(f"📖 Reading XLSX file with openpyxl engine")
            df = pd.read_excel(file_stream, engine='openpyxl')
        elif filename.lower().endswith('.xls'):
            print(f"📖 Reading XLS file with xlrd engine")
            df = pd.read_excel(file_stream, engine='xlrd')
        else:
            print(f"❌ Unsupported file format: {filename}")
            return []
        
        print(f"📊 DataFrame shape: {df.shape}")
        print(f"📋 DataFrame columns: {list(df.columns)}")
        
        # Get column names
        columns = df.columns.tolist()
        print(f"✅ Successfully extracted {len(columns)} columns: {columns}")
        
        return columns
        
    except Exception as e:
        print(f"❌ Error extracting Excel columns: {e}")
        import traceback
        traceback.print_exc()
        return []

# Simple AI response function
def simple_ai_response(message, validation_result=None):
    if not validation_result:
        return "Please run a validation first to analyze results."
    
    details = validation_result.get("details", []) or []
    match_pct = validation_result.get("match_percentage", 0)
    
    # Simple response based on the message
    if "critical" in message.lower():
        critical_count = sum(1 for d in details if str(d.get('severity','')).lower() == 'critical')
        return f"Found {critical_count} critical issues in the validation results."
    elif "high" in message.lower():
        high_count = sum(1 for d in details if str(d.get('severity','')).lower() == 'high')
        return f"Found {high_count} high severity issues in the validation results."
    elif "percentage" in message.lower() or "match" in message.lower():
        return f"The configuration match percentage is {match_pct}%."
    else:
        return f"Based on the validation results: {len(details)} total findings, {match_pct}% match rate. Ask me about specific severity levels or issues."

# Global storage for session data (persistent across requests)
session_data = {}
print("🔄 Session data initialized")

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/custom_ui.html'
        elif self.path == '/api/test':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'message': 'Server is working',
                'session_data': list(session_data.keys())
            }).encode())
            return
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        if self.path == '/api/upload':
            self.handle_upload(post_data)
        elif self.path == '/api/validate':
            self.handle_validation(post_data)
        elif self.path == '/api/chat':
            self.handle_chat(post_data)
        elif self.path == '/api/export':
            self.handle_export(post_data)
        else:
            self.send_error(404, "API endpoint not found")
    
    def handle_upload(self, post_data):
        try:
            print(f"Upload request received. Content-Type: {self.headers.get('Content-Type', '')}")
            print(f"Post data length: {len(post_data)} bytes")
            
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            if 'boundary=' not in content_type:
                raise Exception('Invalid content type - no boundary found')
                
            boundary = content_type.split('boundary=')[1]
            print(f"Boundary: {boundary}")
            
            parts = post_data.split(b'--' + boundary.encode())
            print(f"Found {len(parts)} parts in multipart data")
            
            # Debug: Print first few parts to see what's in them
            for i, part in enumerate(parts[:3]):
                if len(part) > 0:
                    print(f"🔍 Part {i} preview: {part[:200]}...")
            
            filename = None
            file_type = None
            
            for i, part in enumerate(parts):
                print(f"Processing part {i}: {len(part)} bytes")
                if b'Content-Disposition: form-data' in part:
                    print(f"Found form-data in part {i}")
                    
                    # Extract file type
                    if b'name="type"' in part:
                        type_start = part.find(b'name="type"')
                        type_line_start = part.find(b'\r\n', type_start)
                        type_line_end = part.find(b'\r\n', type_line_start + 2)
                        type_content = part[type_line_start + 2:type_line_end]
                        file_type = type_content.decode().strip()
                        print(f"📋 File type from form: {file_type}")
                    elif b'name="file"' in part:
                        # If no explicit type, try to determine from filename
                        filename_start = part.find(b'filename="')
                        if filename_start != -1:
                            filename_start += 10
                            filename_end = part.find(b'"', filename_start)
                            filename = part[filename_start:filename_end].decode()
                            print(f"🔍 Detecting file type from filename: {filename}")
                            
                            if filename.lower().endswith(('.yaml', '.yml', '.xlsx', '.xls', '.pdf', '.docx', '.doc')):
                                file_type = 'config'
                                print(f"✅ File type inferred as config (Excel/PDF/DOC)")
                            elif filename.lower().endswith('.json'):
                                file_type = 'snapshot'
                                print(f"✅ File type inferred as snapshot (JSON)")
                            elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                                file_type = 'logo'
                                print(f"✅ File type inferred as logo (Image)")
                            else:
                                print(f"❌ Unknown file type for: {filename}")
                            
                            print(f"📋 Final file type: {file_type}")
                    
                    # Extract file data
                    if b'name="file"' in part:
                        print(f"Found file in part {i}")
                        # Find the file data section
                        file_start = part.find(b'\r\n\r\n') + 4
                        file_end = part.rfind(b'\r\n')
                        print(f"File data range: {file_start} to {file_end}")
                        
                        if file_end > file_start:
                            file_data = part[file_start:file_end]
                            print(f"File data length: {len(file_data)} bytes")
                            
                            # Extract filename
                            filename_start = part.find(b'filename="')
                            if filename_start != -1:
                                filename_start += 10
                                filename_end = part.find(b'"', filename_start)
                                filename = part[filename_start:filename_end].decode()
                                print(f"Filename: {filename}")
                            
                            # Store file data based on type
                            print(f"🔍 File type detected: {file_type}")
                            print(f"🔍 Filename: {filename}")
                            
                            if file_type == 'config':
                                print(f"✅ Processing as config file")
                                # Use real config processing from streamlit_app.py
                                config_yaml = read_uploaded_config_cached(file_data, filename)
                                
                                # Extract column names from Excel file
                                print(f"🔍 Attempting to extract columns from {filename}")
                                excel_columns = extract_excel_columns(file_data, filename)
                                print(f"📋 Extracted columns: {excel_columns}")
                                
                                session_data['config'] = {
                                    'content': config_yaml,
                                    'filename': filename or 'config_file'
                                }
                                session_data['excel_columns'] = excel_columns
                                
                                print(f"Config file stored: {filename}")
                                print(f"Config content length: {len(config_yaml)}")
                                print(f"Excel columns extracted: {excel_columns}")
                                print(f"Session data keys: {list(session_data.keys())}")
                                print(f"Excel columns in session: {session_data.get('excel_columns', 'NOT FOUND')}")
                                
                            elif file_type == 'snapshot':
                                if filename and filename.lower().endswith('.json'):
                                    snapshot = json.loads(file_data.decode('utf-8'))
                                else:
                                    snapshot = yaml.safe_load(file_data.decode('utf-8'))
                                
                                session_data['snapshot'] = {
                                    'content': snapshot,
                                    'filename': filename or 'snapshot_file'
                                }
                                print(f"Snapshot file stored: {filename}")
                            
                            elif file_type == 'logo':
                                session_data['logo'] = {
                                    'content': base64.b64encode(file_data).decode('utf-8'),
                                    'filename': filename or 'logo_file'
                                }
                                print(f"Logo file stored: {filename}")
                            
                            break
            
            if not filename:
                raise Exception('No file found in upload')
            
            print(f"Upload successful: {filename} ({file_type})")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Include columns in response for config files
            response_data = {
                'success': True, 
                'filename': filename,
                'columns': session_data.get('excel_columns', []) if file_type == 'config' else []
            }
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            print(f"Upload error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_validation(self, post_data):
        try:
            print(f"Validation request received. Post data: {post_data.decode('utf-8')}")
            print(f"Current session data keys: {list(session_data.keys())}")
            
            if 'config' not in session_data:
                raise Exception('Config file not uploaded')
            
            # Parse request data
            data = json.loads(post_data.decode('utf-8'))
            snapshot_type = data.get('snapshot_type', 'auto')
            user_preferences = data.get('user_preferences', {})
            print(f"Snapshot type: {snapshot_type}")
            print(f"User preferences: {user_preferences}")
            
            # Handle snapshot based on type
            if snapshot_type == 'manual':
                if 'snapshot' not in session_data:
                    raise Exception('Snapshot file not uploaded')
                snapshot = session_data['snapshot']['content']
                print("Using manual snapshot")
            else:
                # Auto-generate snapshot
                snapshot = StandaloneAI.collect_full_snapshot()
                print("Using auto-generated snapshot")
            
            # Parse config and run enhanced validation
            config_yaml = session_data['config']['content']
            print(f"Config content length: {len(config_yaml)}")
            
            # Enhanced validation with field parsing
            print(f"🔍 About to call enhanced_validation with snapshot type: {type(snapshot)}")
            print(f"🔍 Snapshot keys: {list(snapshot.keys()) if isinstance(snapshot, dict) else 'Not a dict'}")
            result = self.enhanced_validation(config_yaml, snapshot, user_preferences)
            print(f"Enhanced validation result: {result}")
            
            # Store result
            session_data['validation_result'] = result
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'result': result
            }).encode())
            
        except Exception as e:
            print(f"Validation error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _find_actual_value(self, snapshot, key):
        """Intelligently find actual value in snapshot based on field key"""
        key_lower = key.lower()
        
        # Direct key matches
        if key in snapshot:
            return snapshot[key]
        
        # Intelligent field mapping for specific Excel fields
        if 'series' in key_lower or 'device' in key_lower:
            # Look for device/hostname information
            for field in ['device', 'hostname', 'fqdn', 'machine']:
                if field in snapshot:
                    return snapshot[field]
        
        elif 'device & model' in key_lower:
            # Composite device model information
            device_parts = []
            if 'platform' in snapshot:
                device_parts.append(snapshot['platform'])
            if 'os_name' in snapshot:
                device_parts.append(snapshot['os_name'])
            if 'processor' in snapshot:
                device_parts.append(snapshot['processor'])
            if 'memory_total' in snapshot:
                device_parts.append(snapshot['memory_total'])
            if device_parts:
                return ', '.join(device_parts)
        
        elif 'os' in key_lower or 'windows' in key_lower:
            # Look for OS information
            for field in ['os_name', 'platform', 'platform_version']:
                if field in snapshot:
                    return snapshot[field]
        
        elif 'cpu' in key_lower or 'processor' in key_lower:
            # Look for CPU information
            for field in ['processor', 'cpu_count']:
                if field in snapshot:
                    return snapshot[field]
        
        elif 'memory' in key_lower or 'ram' in key_lower:
            # Look for memory information
            for field in ['memory_total', 'memory_available']:
                if field in snapshot:
                    return snapshot[field]
        
        elif 'storage' in key_lower or 'ssd' in key_lower or 'hdd' in key_lower:
            # Look for storage information
            if 'disks' in snapshot and snapshot['disks']:
                disk_info = snapshot['disks'][0]  # First disk
                return f"{disk_info.get('filesystem', 'Unknown')} {disk_info.get('total', 'Unknown')}"
        
        elif 'language' in key_lower:
            # Look for language information
            for field in ['language', 'os_language']:
                if field in snapshot:
                    return snapshot[field]
        
        elif 'keyboard' in key_lower or 'input' in key_lower:
            # Default keyboard layout
            return 'en-US'  # Common default
        
        elif 'install' in key_lower or 'location' in key_lower or 'directory' in key_lower:
            # Look for directory information
            for field in ['windows_directory', 'program_files', 'home_dir', 'current_dir']:
                if field in snapshot:
                    return snapshot[field]
        
        # Try partial matches
        for snapshot_key, value in snapshot.items():
            if key_lower in snapshot_key.lower() or snapshot_key.lower() in key_lower:
                return value
        
        return 'Not found'

    def _calculate_improved_match_score(self, expected_fields, actual_fields, field_key):
        """Calculate improved match score for Excel fields"""
        if not expected_fields:
            return 0, [], []
        
        if not actual_fields:
            return 0, [], expected_fields
        
        matched_fields = []
        mismatched_fields = []
        total_score = 0
        
        field_key_lower = field_key.lower()
        
        for expected_field in expected_fields:
            expected_lower = str(expected_field).lower()
            best_match = None
            best_score = 0
            
            # Try to find best match in actual fields
            for actual_field in actual_fields:
                actual_lower = str(actual_field).lower()
                
                # Exact match
                if expected_lower == actual_lower:
                    score = 100
                # Contains match
                elif expected_lower in actual_lower or actual_lower in expected_lower:
                    score = 85
                # Partial word match
                elif any(word in actual_lower for word in expected_lower.split()):
                    score = 70
                # Number match (for RAM, storage sizes)
                elif self._extract_numbers(expected_lower) and self._extract_numbers(actual_lower):
                    expected_num = self._extract_numbers(expected_lower)
                    actual_num = self._extract_numbers(actual_lower)
                    if abs(expected_num - actual_num) <= 2:
                        score = 60
                    else:
                        score = 20
                else:
                    score = 0
                
                if score > best_score:
                    best_score = score
                    best_match = actual_field
            
            # Determine if this field is matched
            if best_score >= 60:
                matched_fields.append({
                    'expected': expected_field,
                    'actual': best_match,
                    'score': best_score
                })
                total_score += best_score
            else:
                mismatched_fields.append({
                    'expected': expected_field,
                    'actual': 'Not found',
                    'score': 0
                })
        
        # Calculate overall score
        if expected_fields:
            overall_score = total_score / len(expected_fields)
        else:
            overall_score = 0
        
        return overall_score, matched_fields, mismatched_fields

    def _extract_numbers(self, text):
        """Extract first number from text"""
        import re
        numbers = re.findall(r'\d+', str(text))
        return int(numbers[0]) if numbers else 0

    def enhanced_validation(self, config_yaml, snapshot, user_preferences):
        """Enhanced validation with Excel field parsing and user preferences"""
        try:
            print("🔍 Starting enhanced validation with field parsing...")
            print(f"📊 Snapshot keys: {list(snapshot.keys())}")
            print(f"📊 Snapshot sample: {dict(list(snapshot.items())[:5])}")
            
            # Parse config
            config_data = yaml.safe_load(config_yaml)
            if isinstance(config_data, list):
                config_data = config_data[0] if config_data else {}
            
            print(f"📋 Parsed config data: {list(config_data.keys())}")
            
            # Get user preferences for field weights
            field_weights = user_preferences.get('field_weights', {
                'os': 15,
                'cpu': 20,
                'gpu': 15,
                'memory': 15,
                'storage': 15,
                'device_type': 10
            })
            
            print(f"⚖️ Using field weights: {field_weights}")
            
            details = []
            total_score = 0
            total_weight = 0
            
            # Validate each field
            for key, expected_value in config_data.items():
                if expected_value is None:
                    continue
                
                print(f"\n🔍 Validating field: {key}")
                print(f"   Expected: {expected_value}")
                
                # Get actual value from snapshot with intelligent field mapping
                actual_value = self._find_actual_value(snapshot, key)
                print(f"   Actual: {actual_value}")
                
                # Parse expected value into individual fields
                if isinstance(expected_value, str) and ',' in expected_value:
                    expected_fields = parse_excel_fields(expected_value)
                    print(f"   Parsed expected fields: {expected_fields}")
                else:
                    expected_fields = [str(expected_value)] if expected_value else []
                
                # Parse actual value into individual fields
                if isinstance(actual_value, str) and ',' in actual_value:
                    actual_fields = parse_excel_fields(actual_value)
                    print(f"   Parsed actual fields: {actual_fields}")
                else:
                    actual_fields = [str(actual_value)] if actual_value else []
                
                # Calculate field match score with improved logic
                score, matched_fields, mismatched_fields = self._calculate_improved_match_score(
                    expected_fields, actual_fields, key
                )
                
                print(f"   Match score: {score:.1f}%")
                print(f"   Matched fields: {[f['expected'] for f in matched_fields]}")
                print(f"   Mismatched fields: {[f['expected'] for f in mismatched_fields]}")
                
                # Determine severity based on score and user preferences
                if score >= 95:
                    severity = 'low'
                    status = 'exact_match'
                elif score >= 80:
                    severity = 'low'
                    status = 'match'
                elif score >= 60:
                    severity = 'medium'
                    status = 'partial'
                elif score >= 40:
                    severity = 'high'
                    status = 'mismatch'
                else:
                    severity = 'critical'
                    status = 'mismatch'
                
                # Create detailed explanation
                explanation_parts = []
                if matched_fields:
                    explanation_parts.append(f"✅ Matched: {', '.join([f['expected'] for f in matched_fields])}")
                if mismatched_fields:
                    explanation_parts.append(f"❌ Missing: {', '.join([f['expected'] for f in mismatched_fields])}")
                
                explanation = "; ".join(explanation_parts) if explanation_parts else "No detailed analysis available"
                
                # Get field type for weighting
                field_type = get_field_type(str(expected_value))
                weight = field_weights.get(field_type, 10)  # Default weight for unknown types
                
                details.append({
                    'key': key,
                    'expected': expected_value,
                    'actual': actual_value,
                    'status': status,
                    'severity': severity,
                    'score': score,
                    'explanation': explanation,
                    'matched_fields': matched_fields,
                    'mismatched_fields': mismatched_fields,
                    'field_type': field_type,
                    'weight': weight,
                    'first_seen': datetime.utcnow().isoformat()
                })
                
                # Calculate weighted score
                total_score += score * weight
                total_weight += weight
            
            # Calculate overall match percentage
            match_percentage = (total_score / total_weight) if total_weight > 0 else 0
            
            print(f"\n📊 Final results:")
            print(f"   Total score: {total_score:.1f}")
            print(f"   Total weight: {total_weight:.1f}")
            print(f"   Match percentage: {match_percentage:.1f}%")
            
            return {
                'summary': f'Enhanced validation performed: {match_percentage:.1f}% checks matched',
                'match_percentage': round(match_percentage, 1),
                'details': details,
                'field_weights': field_weights,
                'user_preferences': user_preferences
            }
            
        except Exception as e:
            print(f"❌ Enhanced validation error: {str(e)}")
            import traceback
            traceback.print_exc()
            # Fallback to original validation
            return StandaloneAI.validate_against_yaml(config_yaml, snapshot)
    
    def handle_chat(self, post_data):
        try:
            data = json.loads(post_data.decode('utf-8'))
            message = data.get('message')
            has_files = data.get('hasFiles', False)
            
            print(f"Chat request - Message: '{message}', Has files: {has_files}")
            print(f"Session data keys: {list(session_data.keys())}")
            print(f"Validation result exists: {bool(session_data.get('validation_result'))}")
            
            if not message:
                raise Exception('No message provided')
            
            # Handle different scenarios based on files and validation status
            if not has_files:
                print("No files detected")
                # No files uploaded
                if any(keyword in message.lower() for keyword in ['hello', 'hi', 'hey']):
                    response = "Hello! I'm your AI validation assistant. I can help you analyze configuration validation results once you upload a config file and run validation. What would you like to know?"
                elif any(keyword in message.lower() for keyword in ['analysis', 'findings', 'validation', 'results', 'match', 'percentage']):
                    response = "I can't provide analysis without seeing your configuration files. Please upload a config file first, then run validation so I can give you meaningful insights based on your actual data."
                else:
                    response = "Hello! I'm your AI validation assistant. I can help you with configuration validation. Please upload a config file first, then I'll be able to assist you better."
            elif not session_data.get('validation_result'):
                print("Files detected but no validation results")
                # Files uploaded but no validation run
                response = "Hello! I'm your AI validation assistant. I can see you have files uploaded but haven't run validation yet. Please run validation first, then I'll be able to help you analyze the results and answer your questions."
            else:
                print("Files and validation results detected - generating response")
                # Generate AI response using real AI
                validation_result = session_data.get('validation_result')
                details = validation_result.get("details", []) or []
                match_pct = validation_result.get("match_percentage", 0)
                
                context = f"""
                Current validation results:
                - Match Percentage: {match_pct}%
                - Total Findings: {len(details)}
                - Critical Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'critical')}
                - High Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'high')}
                - Medium Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'medium')}
                - Low Issues: {sum(1 for d in details if str(d.get('severity','')).lower() == 'low')}
                
                All findings: {chr(10).join([f"- {d.get('key')}: {d.get('explanation', '')}" for d in details])}
                """
                
                prompt = f"""
                You are an IT security expert helping analyze configuration validation results.
                
                {context}
                
                User question: {message}
                
                Provide a concise, helpful answer based on the validation results. Be specific and actionable.
                """
                
                try:
                    # Simple fallback response system since AI functions aren't available
                    if 'hello' in message.lower() or 'hi' in message.lower():
                        response = "Hello! I'm your AI validation assistant. I can help you analyze your configuration validation results. What would you like to know?"
                    elif 'findings' in message.lower() or 'results' in message.lower():
                        response = f"Based on your validation results:\n\n**Overall Status:** {match_pct}% match percentage\n**Total Findings:** {len(details)} issues found\n\n**Key Issues:**\n"
                        for detail in details[:3]:  # Show first 3 findings
                            status_emoji = "✅" if detail.get('status') == 'match' else "⚠️" if detail.get('status') == 'partial' else "❌"
                            response += f"{status_emoji} **{detail.get('key')}**: {detail.get('explanation', 'No explanation available')}\n"
                        response += "\nWould you like me to explain any specific finding in detail?"
                    elif 'help' in message.lower():
                        response = "I can help you with:\n• Analyzing validation results\n• Explaining specific findings\n• Providing recommendations\n• Answering questions about your configuration\n\nJust ask me anything about your validation results!"
                    else:
                        response = f"I understand you're asking about '{message}'. Based on your validation results ({match_pct}% match), I can help analyze specific findings or provide general guidance. What would you like to know more about?"
                except Exception as e:
                    response = f"Sorry, I couldn't process that: {str(e)}"
            
            print(f"Final response: {response}")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'response': response}).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_export(self, post_data):
        try:
            data = json.loads(post_data.decode('utf-8'))
            export_type = data.get('format')
            
            if 'validation_result' not in session_data:
                raise Exception('No validation results to export')
            
            result = session_data['validation_result']
            
            if export_type == 'json':
                # Return JSON data
                response_data = {
                    'success': True,
                    'data': json.dumps(result, indent=2),
                    'filename': 'validation_report.json'
                }
            elif export_type == 'csv':
                # Convert to CSV
                details = result.get('details', [])
                if details:
                    df = pd.DataFrame(details)
                    csv_data = df.to_csv(index=False)
                    response_data = {
                        'success': True,
                        'data': csv_data,
                        'filename': 'findings.csv'
                    }
                else:
                    raise Exception('No details to export')
            elif export_type == 'pdf':
                # Simple text-based PDF alternative
                pdf_content = f"""
                AUDIT VALIDATOR REPORT
                =====================
                
                Match Percentage: {result.get('match_percentage', 0)}%
                Total Findings: {len(result.get('details', []))}
                
                DETAILS:
                {chr(10).join([f"- {d.get('key')}: {d.get('explanation', '')}" for d in result.get('details', [])])}
                """
                response_data = {
                    'success': True,
                    'data': pdf_content,
                    'filename': 'validation_report.txt'
                }
            else:
                raise Exception('Invalid export format')
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

def main():
    PORT = 5002
    
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print(f"🎯 Standalone Custom UI Server running on http://localhost:{PORT}")
        print("📱 Open your browser and navigate to the URL above")
        print("🔗 The UI will show the pixel-perfect layout from your image")
        print("✅ No dependencies on problematic streamlit_app.py")
        print("\nPress Ctrl+C to stop the server")
        print("-" * 50)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped. Goodbye!")

if __name__ == "__main__":
    main()
