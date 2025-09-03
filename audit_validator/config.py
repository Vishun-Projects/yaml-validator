# Configuration file for Audit Validator
import os

# Groq API Configuration
# Get your API key from: https://console.groq.com/
GROQ_API_KEY = os.environ.get('GROQ_API_KEY') or "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"

# Alternative: Set your API key here directly
# GROQ_API_KEY = "gsk_your_actual_api_key_here"

# Groq Model Configuration
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Server Configuration
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True

# AI Chat Configuration
MAX_TOKENS = 800
TEMPERATURE = 0.2
TIMEOUT = 30

# Validation Configuration
SNAPSHOT_INTERACTIVE_UI = False
SNAPSHOT_COLLECT_APPS = False
