import google.generativeai as genai
from .config import settings

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

def generate_draft(case_type: str, user_details: str, language: str = "en") -> str:
    """
    Generates a structured legal draft based on user input.
    """
    if not settings.GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not found."

    model = genai.GenerativeModel('gemini-2.5-flash')

    lang_map = {
        "en": "English", "hi": "Hindi", "bn": "Bengali", "te": "Telugu"
    }
    target_lang = lang_map.get(language, "English")

    prompt = f"""
    You are an expert legal drafter.
    Task: Draft a formal legal document for a {case_type} case.
    
    User Details:
    {user_details}

    Requirements:
    1. Use standard legal format suitable for Indian Courts.
    2. Include placeholders like [DATE], [PLACE] where necessary.
    3. detailed and professional language.
    4. Cite relevant sections of BNS/BNSS if applicable.
    5. Language: {target_lang}

    Output only the document text. Do not add conversational filler.
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating draft: {str(e)}"
