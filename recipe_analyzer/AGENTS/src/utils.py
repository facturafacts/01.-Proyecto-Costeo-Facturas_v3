# src/utils.py
import json

def extract_json_from_string(text: str) -> dict | None:
    """
    Finds and parses a JSON object from a string that might contain extra text,
    like markdown code fences.
    """
    try:
        # Find the start of the JSON block
        json_start = text.find('{')
        if json_start == -1:
            return None # No JSON object found

        # Find the end of the JSON block
        json_end = text.rfind('}')
        if json_end == -1:
            return None # No JSON object found

        # Extract the potential JSON string
        json_str = text[json_start : json_end + 1]
        
        # Parse and return the JSON object
        return json.loads(json_str)

    except (json.JSONDecodeError, IndexError):
        # If parsing fails or indices are out of bounds, return None
        return None
