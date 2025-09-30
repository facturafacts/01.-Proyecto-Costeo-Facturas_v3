# src/gemini_connector.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables from a .env file at the project root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# It's recommended to have GEMINI_API_KEY in your .env file
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = 'gemini-2.0-flash'

# --- Global State ---
_model = None

def _get_gemini_model():
    """Initializes and returns the Gemini Pro model client, caching it for reuse."""
    global _model
    if _model is None:
        if not API_KEY:
            raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")
        
        try:
            genai.configure(api_key=API_KEY)
            _model = genai.GenerativeModel(MODEL_NAME)
            print(f"✅ Gemini model '{MODEL_NAME}' initialized successfully.")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini model: {e}")
            
    return _model

def call_gemini_api(prompt: str) -> str:
    """Sends a prompt to the Gemini API and returns the text response."""
    try:
        model = _get_gemini_model()
        print("Submitting prompt to Gemini API...")
        response = model.generate_content(prompt)
        print("✅ Received response from API.")
        return response.text
    except Exception as e:
        print(f"❌ ERROR: An error occurred while calling the Gemini API: {e}")
        # Return a string that looks like a JSON error to be caught downstream
        return '{"error": "API call failed", "details": "' + str(e) + '"}'


