import google.generativeai as genai
from .config import settings

# Configure API
genai.configure(api_key=settings.GEMINI_API_KEY)

def simplify_document(file_content: bytes, mime_type: str, language: str = "en") -> str:
    """
    Analyzes an uploaded image/PDF using Gemini Vision and returns a simplified summary.
    """
    # Model List with Fallback Priority
    models_to_try = ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-1.5-flash"]
    
    # Language Handling
    lang_instruction = "English"
    if language == "hi":
        lang_instruction = "Hindi (हिंदी)"
    elif language == "bn":
        lang_instruction = "Bengali (বাংলা)"
    elif language == "te":
        lang_instruction = "Telugu (తెలుగు)"

    prompt = f"""
    You are SamvidhanSetu, a friendly and wise legal assistant who helps ordinary people understand complex official documents.

    Task:
    1. Analyze the attached legal document image/PDF.
    2. **DO NOT simply extract or transcribe text.** Your goal is to EXPLAIN what it means.
    3. Identify what kind of document this is (e.g., "Rent Agreement", "Court Notice", "Traffic Ticket").
    4. Summarize the content in extremely **SIMPLE, EVERYDAY LANGUAGE** (Explain Like I'm 5).
    5. Avoid legal jargon completely. If a legal term is necessary, explain it in brackets.
    6. Provide the output in **{lang_instruction}**.

    Format:
    - **Document Type**: [What is this?]
    - **What it Says (Simply)**: 
        * [Point 1 - The core meaning]
        * [Point 2 - Important detail]
    - **Why it Matters**: [One sentence on the legal implication]
    - **Action Required**: [Exactly what the user needs to do next]

    If the image is not clear or not a document, say "I cannot read this document clearly."
    """

    # Create the Content part
    image_part = {
        "mime_type": mime_type,
        "data": file_content
    }

    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, image_part])
            return response.text
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            continue
            
    return "Error: Could not process document with any available AI models."
