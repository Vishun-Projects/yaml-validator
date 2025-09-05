from flask import Flask, render_template, request, jsonify, send_file
import os
import json
import yaml
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import io
import base64
import requests
import uuid
import time

# Import your existing modules
import sys
import os

# Add the parent directory to path to import ai_audit_gui
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import GDPR database
try:
    from gdpr_database import get_gdpr_db
    GDPR_DB_AVAILABLE = True
except ImportError:
    print("Warning: GDPR database not available. Running without database persistence.")
    GDPR_DB_AVAILABLE = False

# Import configuration
try:
    from config import *
except ImportError:
    # Fallback configuration
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY') or "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"
    GROQ_MODEL = "llama-3.1-8b-instant"
    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
    MAX_TOKENS = 800
    TEMPERATURE = 0.2
    TIMEOUT = 30

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
        print("ERROR: Could not import required modules. Please ensure all dependencies are installed.")
        print("Required: ai_audit_gui, streamlit_app with Groq integration")
        raise ImportError("Missing required modules")

def ask_groq(prompt, system_prompt="You are an expert IT security analyst. Provide concise, actionable insights.", max_tokens=None, temperature=None):
    """Direct Groq API call without caching for the custom server"""
    try:
        # Use configuration values or fallback to defaults
        max_tokens = max_tokens or MAX_TOKENS
        temperature = temperature or TEMPERATURE
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        print(f"Calling Groq API with {len(prompt)} characters, max_tokens={max_tokens}, temperature={temperature}")
        
        start_time = time.time()
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=TIMEOUT)
        response_time = time.time() - start_time
        
        if response.status_code != 200:
            raise Exception(f"Groq API error: HTTP {response.status_code}: {response.text}")
        
        data = response.json()
        choices = data.get("choices", [])
        
        if choices and len(choices) > 0:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if content:
                print(f"Groq API response: {len(content)} characters")
                return content.strip(), response_time, len(prompt), len(content)
        
        raise Exception("No response content from Groq API")
        
    except Exception as e:
        print(f"Groq API call failed: {str(e)}")
        raise e

app = Flask(__name__)

# Global storage for session data (fallback when database is not available)
session_data = {}

# Initialize GDPR database if available
if GDPR_DB_AVAILABLE:
    try:
        gdpr_db = get_gdpr_db(echo=False)
        print("✅ GDPR database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize GDPR database: {e}")
        GDPR_DB_AVAILABLE = False

def get_or_create_session_id():
    """Get or create a session ID for the current request"""
    # Try to get from request headers or create new
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Only create database session if it doesn't already exist
    if GDPR_DB_AVAILABLE:
        try:
            # Check if session already exists in database
            existing_session = gdpr_db.get_session(session_id)
            if not existing_session:
                # Session doesn't exist, create it
                user_agent = request.headers.get('User-Agent')
                ip_address = request.remote_addr
                gdpr_db.create_session(session_id, user_agent, ip_address)
                print(f"✅ Created new database session: {session_id}")
            else:
                print(f"✅ Using existing database session: {session_id}")
        except Exception as e:
            # If it's a duplicate entry error, just log it and continue
            if "Duplicate entry" in str(e):
                print(f"✅ Session already exists (duplicate entry caught): {session_id}")
            else:
                print(f"Warning: Failed to check/create database session: {e}")
    
    return session_id

@app.route('/')
def serve_custom_ui():
    """Serve the custom UI HTML file"""
    return send_file('custom_ui.html')

@app.route('/custom_ui.html')
def serve_custom_ui_alt():
    """Alternative route for custom UI"""
    return send_file('custom_ui.html')

@app.route('/bot.jpg')
def serve_bot_image():
    """Serve the bot image"""
    return send_file('bot.jpg')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        file_type = request.form.get('type')
        file = request.files.get('file')
        
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        
        # Get or create session ID
        session_id = get_or_create_session_id()
        
        # Store file data
        file_content = file.read()
        file_name = file.filename
        
        # Save to database if available
        if GDPR_DB_AVAILABLE:
            try:
                gdpr_db.save_file(session_id, file_type, file_content, file_name, file.content_type)
                print(f"✅ File saved to database: {file_name}")
            except Exception as e:
                print(f"Warning: Failed to save file to database: {e}")
        
        # Store in session data as fallback
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
                    
                    # Process each row and handle comma-separated values
                    for _, row in df.iterrows():
                        if row.notnull().any():
                            row_data = {}
                            for k, v in row.to_dict().items():
                                if pd.notna(v) and v:
                                    # Handle comma-separated values by splitting them
                                    if ',' in str(v):
                                        # Split by comma and create separate entries
                                        values = [val.strip() for val in str(v).split(',') if val.strip()]
                                        for i, val in enumerate(values):
                                            if i == 0:
                                                # First value gets the original key
                                                row_data[str(k)] = val
                                            else:
                                                # Additional values get numbered keys
                                                row_data[f"{k}_{i+1}"] = val
                                    else:
                                        row_data[str(k)] = v
                            
                            if row_data:
                                config_data.update(row_data)
                                break  # Use first non-empty row
                    
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
        
        return jsonify({
            'success': True, 
            'filename': file_name,
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate', methods=['POST'])
def run_validation():
    try:
        print("Validation request received")
        
        # Get or create session ID
        session_id = get_or_create_session_id()
        
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
                snapshot = ai_audit_gui.collect_full_snapshot(interactive_ui=True, collect_apps_flag=False)
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
        
        # Save to database if available
        if GDPR_DB_AVAILABLE:
            try:
                gdpr_db.save_validation_results(session_id, result)
                print(f"✅ Validation results saved to database for session: {session_id}")
            except Exception as e:
                print(f"Warning: Failed to save validation results to database: {e}")
        
        return jsonify({
            'success': True,
            'result': result,
            'session_id': session_id
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
        
        # Get or create session ID
        session_id = get_or_create_session_id()
        
        # Save user message to database if available
        if GDPR_DB_AVAILABLE:
            try:
                gdpr_db.save_chat_message(session_id, 'user', message)
            except Exception as e:
                print(f"Warning: Failed to save user message to database: {e}")
        
        # Check if we have validation results
        if 'validation_result' not in session_data:
            response = 'Please run a validation first to analyze results. Upload a configuration file and click "Run Validation" to get started.'
            
            # Save AI response to database if available
            if GDPR_DB_AVAILABLE:
                try:
                    gdpr_db.save_chat_message(session_id, 'ai', response, 'fallback')
                except Exception as e:
                    print(f"Warning: Failed to save AI response to database: {e}")
            
            return jsonify({'response': response})
        
        # Get validation results for context
        result = session_data['validation_result']
        details = result.get("details", []) or []
        match_pct = result.get("match_percentage", 0)
        
        # Count issues by severity
        critical_count = sum(1 for d in details if str(d.get('severity','')).lower() == 'critical')
        high_count = sum(1 for d in details if str(d.get('severity','')).lower() == 'high')
        medium_count = sum(1 for d in details if str(d.get('severity','')).lower() == 'medium')
        low_count = sum(1 for d in details if str(d.get('severity','')).lower() == 'low')
        
        # Create detailed context for AI analysis
        context = f"""
        Configuration Validation Results:
        - Overall Match: {match_pct}%
        - Total Findings: {len(details)}
        - Critical Issues: {critical_count}
        - High Issues: {high_count}
        - Medium Issues: {medium_count}
        - Low Issues: {low_count}
        
        Detailed Findings:
        {chr(10).join([f"• {d.get('key')}: {d.get('status')} ({d.get('severity')}) - {d.get('explanation', '')}" for d in details])}
        
        Configuration Details:
        {chr(10).join([f"• {d.get('key')}: Expected '{d.get('expected', 'N/A')}', Actual '{d.get('actual', 'N/A')}'" for d in details if d.get('expected') or d.get('actual')])}
        """
        
        # Create intelligent prompt based on user question
        system_prompt = """You are an expert IT security analyst and configuration auditor. You analyze configuration validation results and provide:

1. **Clear Analysis**: Explain what the validation results mean
2. **Risk Assessment**: Identify security and compliance risks
3. **Actionable Recommendations**: Provide specific steps to fix issues
4. **Best Practices**: Suggest security improvements
5. **Priority Guidance**: Help prioritize which issues to fix first

Be specific, technical, and actionable. Use the validation data to give precise advice."""
        
        user_prompt = f"""
        {context}
        
        User Question: {message}
        
        Please provide a comprehensive analysis and answer based on the validation results above. Focus on the specific question asked and provide actionable insights.
        """
        
        try:
            # Use real Groq API for intelligent responses
            ai_response, response_time, prompt_tokens, response_tokens = ask_groq(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            # Save AI response to database if available
            if GDPR_DB_AVAILABLE:
                try:
                    gdpr_db.save_chat_message(
                        session_id, 'ai', ai_response, 'groq', 
                        prompt_tokens, response_tokens, response_time
                    )
                except Exception as e:
                    print(f"Warning: Failed to save AI response to database: {e}")
            
            return jsonify({'response': ai_response})
            
        except Exception as e:
            print(f"Groq API error in chat: {str(e)}")
            # Provide fallback response based on validation data
            fallback_response = generate_intelligent_fallback(message, result, details, match_pct)
            
            # Save fallback response to database if available
            if GDPR_DB_AVAILABLE:
                try:
                    gdpr_db.save_chat_message(session_id, 'ai', fallback_response, 'fallback')
                except Exception as e:
                    print(f"Warning: Failed to save fallback response to database: {e}")
            
            return jsonify({'response': fallback_response})
        
    except Exception as e:
        print(f"Chat endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_intelligent_fallback(message, result, details, match_pct):
    """Generate intelligent fallback response when Groq API fails"""
    message_lower = message.lower()
    
    # Analyze user intent
    if any(word in message_lower for word in ['summary', 'overview', 'summary']):
        return f"""**Validation Summary:**
• **Overall Status**: {match_pct}% configuration match
• **Total Issues**: {len(details)} findings requiring attention
• **Critical Issues**: {sum(1 for d in details if str(d.get('severity','')).lower() == 'critical')} high-priority items
• **Recommendation**: Focus on critical and high-severity issues first for immediate security improvements."""
    
    elif any(word in message_lower for word in ['critical', 'urgent', 'important']):
        critical_issues = [d for d in details if str(d.get('severity','')).lower() == 'critical']
        if critical_issues:
            return f"""**Critical Issues Found ({len(critical_issues)}):**
{chr(10).join([f"• **{d.get('key')}**: {d.get('explanation')} (Expected: {d.get('expected', 'N/A')}, Actual: {d.get('actual', 'N/A')})" for d in critical_issues])}

**Immediate Action Required**: These critical issues pose significant security risks and should be addressed within 24-48 hours."""
        else:
            return "✅ **No Critical Issues Found**: Your configuration shows no critical security vulnerabilities. Continue monitoring medium and low-priority items."
    
    elif any(word in message_lower for word in ['fix', 'resolve', 'remediate', 'solution']):
        mismatches = [d for d in details if d.get('status') != 'match']
        if mismatches:
            return f"""**Remediation Steps for {len(mismatches)} Issues:**
{chr(10).join([f"• **{d.get('key')}**: {d.get('explanation')} → Update configuration to match expected value: '{d.get('expected', 'N/A')}'" for d in mismatches])}

**Next Steps**: Review each finding, update configurations, and re-run validation to confirm fixes."""
        else:
            return "✅ **All Issues Resolved**: Your configuration is fully compliant. No remediation actions needed."
    
    elif any(word in message_lower for word in ['percentage', 'match', 'score']):
        return f"""**Configuration Compliance Score: {match_pct}%**

**Breakdown:**
• **Perfect Matches**: {sum(1 for d in details if d.get('status') == 'match')} configurations
• **Partial Matches**: {sum(1 for d in details if d.get('status') == 'partial')} configurations  
• **Mismatches**: {sum(1 for d in details if d.get('status') == 'mismatch')} configurations

**Target**: Aim for 95%+ compliance for production environments."""
    
    else:
        # General analysis
        return f"""**Configuration Analysis Results:**

**Current Status**: {match_pct}% compliance with {len(details)} total findings

**Priority Breakdown:**
• 🔴 Critical: {sum(1 for d in details if str(d.get('severity','')).lower() == 'critical')} issues
• 🟠 High: {sum(1 for d in details if str(d.get('severity','')).lower() == 'high')} issues  
• 🟡 Medium: {sum(1 for d in details if str(d.get('severity','')).lower() == 'medium')} issues
• 🟢 Low: {sum(1 for d in details if str(d.get('severity','')).lower() == 'low')} issues

**Recommendation**: Address critical and high-severity issues first, then work on medium-priority items. Low-severity issues can be addressed during regular maintenance windows."""

@app.route('/api/export', methods=['POST'])
def export_data():
    try:
        data = request.get_json()
        export_type = data.get('format')
        
        # Get or create session ID
        session_id = get_or_create_session_id()
        
        if 'validation_result' not in session_data:
            return jsonify({'error': 'No validation results to export'}), 400
        
        result = session_data['validation_result']
        
        # Log export action to database if available
        if GDPR_DB_AVAILABLE:
            try:
                gdpr_db._log_audit_action(session_id, "export", {
                    "export_type": export_type,
                    "export_timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                print(f"Warning: Failed to log export action to database: {e}")
        
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
        
        # Get or create session ID
        session_id = get_or_create_session_id()
        
        # Generate snapshot using the same logic as Streamlit app
        snapshot = ai_audit_gui.collect_full_snapshot(interactive_ui=True, collect_apps_flag=False)
        
        print(f"Snapshot generated with {len(snapshot) if snapshot else 0} keys")
        
        # Store in session for later use
        session_data['auto_snapshot'] = snapshot
        
        # Save snapshot to database if available
        if GDPR_DB_AVAILABLE:
            try:
                gdpr_db.save_file(session_id, 'snapshot', json.dumps(snapshot), 'system_snapshot.json', 'application/json')
                print(f"✅ System snapshot saved to database for session: {session_id}")
            except Exception as e:
                print(f"Warning: Failed to save snapshot to database: {e}")
        
        return jsonify({
            'success': True,
            'snapshot': snapshot,
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"Snapshot generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gdpr/export/<session_id>', methods=['GET'])
def export_gdpr_data(session_id):
    """Export all data for a session in GDPR-compliant format"""
    if not GDPR_DB_AVAILABLE:
        return jsonify({'error': 'GDPR database not available'}), 503
    
    try:
        gdpr_export = gdpr_db.export_gdpr_data(session_id)
        if gdpr_export:
            return jsonify(gdpr_export)
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        print(f"GDPR export error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gdpr/cleanup', methods=['POST'])
def cleanup_expired_data():
    """Clean up expired data for GDPR compliance"""
    if not GDPR_DB_AVAILABLE:
        return jsonify({'error': 'GDPR database not available'}), 503
    
    try:
        cleaned_count = gdpr_db.cleanup_expired_data()
        return jsonify({
            'success': True,
            'cleaned_sessions': cleaned_count,
            'message': f'Cleaned up {cleaned_count} expired sessions'
        })
    except Exception as e:
        print(f"GDPR cleanup error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gdpr/sessions', methods=['GET'])
def list_sessions():
    """List all validation sessions"""
    if not GDPR_DB_AVAILABLE:
        return jsonify({'error': 'GDPR database not available'}), 503
    
    try:
        # This would need to be implemented in the GDPR database class
        # For now, return a placeholder
        return jsonify({
            'message': 'Session listing not yet implemented',
            'note': 'Use /api/gdpr/export/<session_id> to export specific session data'
        })
    except Exception as e:
        print(f"Session listing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting custom UI server...")
    print(f"Server will run on: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"Groq API configured: {'Yes' if GROQ_API_KEY and GROQ_API_KEY != 'gsk_your_actual_api_key_here' else 'No (using default)'}")
    print(f"AI Chat: {'Enabled' if GROQ_API_KEY and GROQ_API_KEY != 'gsk_your_actual_api_key_here' else 'Disabled - please set GROQ_API_KEY'}")
    print(f"GDPR Database: {'Enabled' if GDPR_DB_AVAILABLE else 'Disabled'}")
    print("Open your browser and go to the URL above")
    
    app.run(debug=FLASK_DEBUG, host=FLASK_HOST, port=FLASK_PORT)
