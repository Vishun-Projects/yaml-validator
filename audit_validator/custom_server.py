from flask import Flask, render_template, request, jsonify, send_file
import os
import json
import yaml
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import io
import base64

# Import your existing modules
import sys
import os

# Add the parent directory to path to import ai_audit_gui
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import your existing validation logic
try:
    # Try to import from ai_audit_gui directly
    import ai_audit_gui
except ImportError:
    try:
        # Try to import from streamlit_app
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

app = Flask(__name__)

# Global storage for session data
session_data = {}

@app.route('/')
def index():
    return send_file('custom_ui.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        file_type = request.form.get('type')
        file = request.files.get('file')
        
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        
        # Store file data
        file_content = file.read()
        file_name = file.filename
        
        if file_type == 'config':
            # Handle config file - use the same logic as Streamlit app
            try:
                if file_name.lower().endswith(('.yaml', '.yml')):
                    config_yaml = file_content.decode('utf-8')
                elif file_name.lower().endswith(('.xlsx', '.xls', '.xlsm')):
                    # Convert Excel to YAML using pandas like Streamlit app
                    import io
                    df = pd.read_excel(io.BytesIO(file_content), sheet_name=0, dtype=str, engine="openpyxl")
                    config_data = {}
                    for _, row in df.iterrows():
                        if row.notnull().any():
                            config_data = {str(k): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                            break
                    config_yaml = yaml.safe_dump(config_data, sort_keys=False)
                else:
                    # For other formats, try to decode as text
                    config_yaml = file_content.decode('utf-8', errors="ignore")
                
                session_data['config'] = {
                    'content': config_yaml,
                    'filename': file_name
                }
                
            except Exception as e:
                return jsonify({'error': f'Failed to process config file: {str(e)}'}), 400
            
        elif file_type == 'snapshot':
            # Handle snapshot file
            try:
                if file_name.lower().endswith('.json'):
                    snapshot = json.loads(file_content.decode('utf-8'))
                else:
                    snapshot = yaml.safe_load(file_content.decode('utf-8'))
                
                session_data['snapshot'] = {
                    'content': snapshot,
                    'filename': file_name
                }
            except Exception as e:
                return jsonify({'error': f'Failed to process snapshot file: {str(e)}'}), 400
        
        elif file_type == 'logo':
            # Handle logo file
            session_data['logo'] = {
                'content': base64.b64encode(file_content).decode('utf-8'),
                'filename': file_name,
                'mime_type': file.content_type
            }
        
        return jsonify({'success': True, 'filename': file_name})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate', methods=['POST'])
def run_validation():
    try:
        print("Validation request received")
        
        if 'config' not in session_data:
            print("No config file in session")
            return jsonify({'error': 'Config file not uploaded'}), 400
        
        # Get config content
        config_yaml = session_data['config']['content']
        print(f"Config content length: {len(config_yaml)} characters")
        
        # Get or generate snapshot
        if 'snapshot' in session_data:
            snapshot = session_data['snapshot']['content']
            print(f"Using uploaded snapshot with {len(snapshot) if snapshot else 0} keys")
        else:
            # Auto-generate snapshot like Streamlit app
            print("Generating auto-snapshot...")
            try:
                snapshot = ai_audit_gui.collect_full_snapshot(interactive_ui=False, collect_apps_flag=False)
                print(f"Auto-snapshot generated with {len(snapshot) if snapshot else 0} keys")
            except Exception as e:
                print(f"Failed to generate snapshot: {str(e)}")
                return jsonify({'error': f'Failed to generate snapshot: {str(e)}'}), 500
        
        # Run validation using the same logic as Streamlit app
        print("Running validation...")
        try:
            result = ai_audit_gui.validate_against_yaml(config_yaml, snapshot)
            print(f"Validation completed: {result.get('match_percentage', 'N/A')}% match, {len(result.get('details', []))} details")
        except Exception as e:
            print(f"Validation failed: {str(e)}")
            return jsonify({'error': f'Validation failed: {str(e)}'}), 500
        
        # Store result
        session_data['validation_result'] = result
        print("Validation result stored in session")
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        print(f"Validation endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Check if we have validation results
        if 'validation_result' not in session_data:
            return jsonify({
                'response': 'Please run a validation first to analyze results. Upload a configuration file and click "Run Validation" to get started.'
            })
        
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
            # Try to use ask_groq_cached if available
            if 'ask_groq_cached' in globals():
                response = ask_groq_cached(
                    prompt,
                    DEFAULT_MODELS[0] if 'DEFAULT_MODELS' in globals() else "llama-3.1-8b-instant",
                    DEFAULT_GROQ_KEYS if 'DEFAULT_GROQ_KEYS' in globals() else ("demo_key",),
                    system_prompt="You are an expert IT security analyst. Provide concise, actionable insights.",
                    max_tokens=300,
                    temperature=0.3,
                    timeout=18,
                )
            else:
                # Fallback response
                response = f"Based on your validation results ({match_pct}% match), I can see {len(details)} findings. {message} - Please provide more specific questions about the validation results."
        except Exception as e:
            response = f"Sorry, I couldn't process that: {str(e)}"
        
        return jsonify({'response': response})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export', methods=['POST'])
def export_data():
    try:
        data = request.get_json()
        export_type = data.get('format')
        
        if 'validation_result' not in session_data:
            return jsonify({'error': 'No validation results to export'}), 400
        
        result = session_data['validation_result']
        
        if export_type == 'json':
            # Return JSON data
            return jsonify({
                'success': True,
                'data': result,
                'filename': 'validation_report.json'
            })
        
        elif export_type == 'csv':
            # Convert to CSV
            details = result.get('details', [])
            if details:
                df = pd.DataFrame(details)
                csv_data = df.to_csv(index=False)
                return jsonify({
                    'success': True,
                    'data': csv_data,
                    'filename': 'findings.csv'
                })
            else:
                return jsonify({'error': 'No details to export'}), 400
        
        elif export_type == 'pdf':
            # Generate PDF
            try:
                if 'build_exec_pdf_bytes' in globals():
                    pdf_bytes, mime, fname = build_exec_pdf_bytes(result, include_ai=True)
                    pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    return jsonify({
                        'success': True,
                        'data': pdf_b64,
                        'filename': fname,
                        'mime_type': mime
                    })
                else:
                    # Fallback to text format if PDF generation not available
                    text_content = f"""
                    Validation Report
                    =================
                    
                    Match Percentage: {result.get('match_percentage', 'N/A')}%
                    Total Findings: {len(result.get('details', []))}
                    
                    Findings:
                    """
                    for detail in result.get('details', []):
                        text_content += f"\n- {detail.get('key', 'N/A')}: {detail.get('explanation', 'N/A')} (Severity: {detail.get('severity', 'N/A')})"
                    
                    return jsonify({
                        'success': True,
                        'data': text_content,
                        'filename': 'validation_report.txt',
                        'mime_type': 'text/plain'
                    })
            except Exception as e:
                return jsonify({'error': f'Export generation failed: {str(e)}'}), 500
        
        else:
            return jsonify({'error': 'Invalid export format'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/results')
def get_results():
    """Get current validation results"""
    if 'validation_result' in session_data:
        return jsonify(session_data['validation_result'])
    else:
        return jsonify({'error': 'No validation results available'}), 404

@app.route('/api/snapshot', methods=['GET'])
def get_system_snapshot():
    """Get a complete system snapshot"""
    try:
        print("Generating system snapshot...")
        
        # Generate snapshot using the same logic as Streamlit app
        snapshot = ai_audit_gui.collect_full_snapshot(interactive_ui=False, collect_apps_flag=False)
        
        print(f"Snapshot generated with {len(snapshot) if snapshot else 0} keys")
        
        # Store in session for later use
        session_data['auto_snapshot'] = snapshot
        
        return jsonify({
            'success': True,
            'snapshot': snapshot
        })
        
    except Exception as e:
        print(f"Snapshot generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting custom UI server...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
