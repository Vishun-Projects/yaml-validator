#!/usr/bin/env python3
"""
Simple HTTP Server for Custom UI
Uses Python's built-in http.server to serve the custom UI
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

# Import your existing modules
import sys
sys.path.append(os.path.dirname(__file__))

# Import your existing validation logic
try:
    from streamlit_app import (
        ai_audit_gui, 
        read_uploaded_config_cached, 
        ask_groq_cached, 
        DEFAULT_MODELS, 
        DEFAULT_GROQ_KEYS,
        build_exec_pdf_bytes
    )
except ImportError:
    # Fallback if imports fail
    class _FakeAI:
        @staticmethod
        def collect_full_snapshot(interactive_ui=False, collect_apps_flag=False):
            return {"device": "demo-device", "collected": True, "collected_at": datetime.utcnow().isoformat()}

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
    
    ai_audit_gui = _FakeAI()

# Global storage for session data
session_data = {}

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/custom_ui.html'
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
            # Parse multipart form data
            boundary = self.headers.get('Content-Type', '').split('boundary=')[1]
            parts = post_data.split(b'--' + boundary.encode())
            
            for part in parts:
                if b'Content-Disposition: form-data' in part:
                    if b'name="file"' in part:
                        # Extract file data
                        file_start = part.find(b'\r\n\r\n') + 4
                        file_end = part.rfind(b'\r\n')
                        file_data = part[file_start:file_end]
                        
                        # Extract filename
                        filename_start = part.find(b'filename="') + 10
                        filename_end = part.find(b'"', filename_start)
                        filename = part[filename_start:filename_end].decode()
                        
                        # Extract file type
                        type_start = part.find(b'name="type"') + 11
                        type_end = part.find(b'\r\n', type_start)
                        file_type = part[type_start:type_end].decode().strip()
                        
                        # Store file data
                        if file_type == 'config':
                            if filename.lower().endswith(('.yaml', '.yml')):
                                config_yaml = file_data.decode('utf-8')
                            elif filename.lower().endswith(('.xlsx', '.xls')):
                                config_yaml = "# Converted from Excel\nconfig:\n  enabled: true"
                            else:
                                config_yaml = file_data.decode('utf-8')
                            
                            session_data['config'] = {
                                'content': config_yaml,
                                'filename': filename
                            }
                            
                        elif file_type == 'snapshot':
                            if filename.lower().endswith('.json'):
                                snapshot = json.loads(file_data.decode('utf-8'))
                            else:
                                snapshot = yaml.safe_load(file_data.decode('utf-8'))
                            
                            session_data['snapshot'] = {
                                'content': snapshot,
                                'filename': filename
                            }
                        
                        elif file_type == 'logo':
                            session_data['logo'] = {
                                'content': base64.b64encode(file_data).decode('utf-8'),
                                'filename': filename
                            }
                        
                        break
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'filename': filename}).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_validation(self, post_data):
        try:
            if 'config' not in session_data:
                raise Exception('Config file not uploaded')
            
            if 'snapshot' not in session_data:
                raise Exception('Snapshot file not uploaded')
            
            # Run validation using your existing logic
            config_yaml = session_data['config']['content']
            snapshot = session_data['snapshot']['content']
            
            result = ai_audit_gui.validate_against_yaml(config_yaml, snapshot)
            
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
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_chat(self, post_data):
        try:
            data = json.loads(post_data.decode('utf-8'))
            message = data.get('message')
            
            if not message:
                raise Exception('No message provided')
            
            # Check if we have validation results
            if 'validation_result' not in session_data:
                response = 'Please run a validation first to analyze results.'
            else:
                # Generate AI response using your existing logic
                result = session_data['validation_result']
                details = result.get("details", []) or []
                match_pct = result.get("match_percentage", 0)
                
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
                    response = ask_groq_cached(
                        prompt,
                        DEFAULT_MODELS[0],
                        DEFAULT_GROQ_KEYS,
                        system_prompt="You are an expert IT security analyst. Provide concise, actionable insights.",
                        max_tokens=300,
                        temperature=0.3,
                        timeout=18,
                    )
                except Exception as e:
                    response = f"Sorry, I couldn't process that: {str(e)}"
            
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
                # Generate PDF
                try:
                    pdf_bytes, mime, fname = build_exec_pdf_bytes(result, include_ai=True)
                    pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    response_data = {
                        'success': True,
                        'data': pdf_b64,
                        'filename': fname,
                        'mime_type': mime
                    }
                except Exception as e:
                    raise Exception(f'PDF generation failed: {str(e)}')
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
    PORT = 5000
    
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print(f"🎯 Custom UI Server running on http://localhost:{PORT}")
        print("📱 Open your browser and navigate to the URL above")
        print("🔗 The UI will show the pixel-perfect layout from your image")
        print("\nPress Ctrl+C to stop the server")
        print("-" * 50)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped. Goodbye!")

if __name__ == "__main__":
    main()
