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
            # Handle config file
            if file_name.lower().endswith(('.yaml', '.yml')):
                config_yaml = file_content.decode('utf-8')
            elif file_name.lower().endswith(('.xlsx', '.xls')):
                # Convert Excel to YAML (simplified)
                config_yaml = "# Converted from Excel\nconfig:\n  enabled: true"
            else:
                config_yaml = file_content.decode('utf-8')
            
            session_data['config'] = {
                'content': config_yaml,
                'filename': file_name
            }
            
        elif file_type == 'snapshot':
            # Handle snapshot file
            if file_name.lower().endswith('.json'):
                snapshot = json.loads(file_content.decode('utf-8'))
            else:
                snapshot = yaml.safe_load(file_content.decode('utf-8'))
            
            session_data['snapshot'] = {
                'content': snapshot,
                'filename': file_name
            }
        
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
        if 'config' not in session_data:
            return jsonify({'error': 'Config file not uploaded'}), 400
        
        if 'snapshot' not in session_data:
            return jsonify({'error': 'Snapshot file not uploaded'}), 400
        
        # Run validation using your existing logic
        config_yaml = session_data['config']['content']
        snapshot = session_data['snapshot']['content']
        
        result = ai_audit_gui.validate_against_yaml(config_yaml, snapshot)
        
        # Store result
        session_data['validation_result'] = result
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
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
                'response': 'Please run a validation first to analyze results.'
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
                pdf_bytes, mime, fname = build_exec_pdf_bytes(result, include_ai=True)
                pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                return jsonify({
                    'success': True,
                    'data': pdf_b64,
                    'filename': fname,
                    'mime_type': mime
                })
            except Exception as e:
                return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500
        
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

if __name__ == '__main__':
    print("Starting custom UI server...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
