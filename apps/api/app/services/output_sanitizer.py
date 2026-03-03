import re

def sanitize_assistant_text(text: str) -> str:
    """
    Ensures that internal IDs like PROJECT_ID_1 or project_id never appear in the final User output.
    """
    # Remove any variants of project_id_#, project_id, PROJECT_ID_1
    text = re.sub(r'(?i)project[_-]?id[_-]?\d*', '', text)
    
    # Remove empty brackets left behind like [], (), or ""
    text = re.sub(r'\[\s*\]|\(\s*\)|""', '', text)
    
    # Clean up double spaces
    text = re.sub(r'\s{2,}', ' ', text).strip()
    return text
