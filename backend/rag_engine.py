import os
# Fix for "Could not find a suitable TLS CA certificate bundle" error
# attempting to use a non-existent PostgreSQL certificate.
os.environ.pop('CURL_CA_BUNDLE', None)

import google.generativeai as genai
import chromadb
from .config import settings
from .prompt_templates import SYSTEM_PROMPT
import time
import logging



# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Memory Bank Removed - History is now passed per request


# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

# Initialize Chroma Client
chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
collection = chroma_client.get_or_create_collection(name="legal_docs")


def transcribe_audio(audio_bytes, mime_type="audio/webm"):
    """
    Transcribes audio using Gemini's multimodal capabilities.
    Auto-detects language (Hindi, Bengali, Telugu, English, etc).
    """
    if not settings.GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not found."

    models_to_try = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-1.5-flash']
    
    for model_name in models_to_try:
        try:
            # We need to use a model that supports audio
            audio_model = genai.GenerativeModel(model_name)
            
            response = audio_model.generate_content([
                "Please transcribe this audio accurately. Return only the text. If it is in an Indian language, use the native script (Devanagari/Bengali/Telugu) mixed with English if necessary, or just the script. Do not translate, just transcribe.",
                {
                    "mime_type": mime_type,
                    "data": audio_bytes
                }
            ])
            
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Transcription failed with {model_name}: {e}")
            continue

    return "Error: Transcription failed with all available models."

def get_query_embedding(text):
    """Fetch query embeddings using Gemini API with retry logic"""
    retries = 3
    for attempt in range(retries):
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait_time = 2 * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                logger.warning(f"Rate limit hit (429). Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Error generating embedding: {e}")
                return None

def query_rag(query_text: str, history: list = None, language: str = "en"):
    if not settings.GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not found in .env settings."

    # 1. Embed the query
    try:
        query_embedding = get_query_embedding(query_text) # Using existing get_query_embedding
    except Exception as e:
        return f"Error generating embedding: {str(e)}"

    # 2. Retrieve from ChromaDB
    context_text = ""
    if query_embedding:
        try:
            results = collection.query(
                query_embeddings=[query_embedding], # get_query_embedding returns a single embedding, so wrap in list
                n_results=3,  # Top 3 chunks
                include=['documents', 'metadatas']
            )
            
            # Determine if we found valid results
            if results['documents'] and results['documents'][0]:
                docs = results['documents'][0]
                metas = results['metadatas'][0]
                
                # Format context with source citations
                formatted_snippets = []
                for i, doc in enumerate(docs):
                    source = metas[i].get('source', 'Unknown')
                    page = metas[i].get('page', '?')
                    formatted_snippets.append(f"[Source: {source}, Page: {page}]\n{doc}")
                context_text = "\n---\n".join(formatted_snippets)
            else:
                context_text = "No specific relevant legal documents found in database."
        except Exception as e:
            return f"Error retrieving documents: {str(e)}"
    else:
        context_text = "Could not retrieve documents due to embedding error."

    # 2. Augment Prompt with History
    history_text = ""
    if history:
        history_text = "\nRECENT CONVERSATION HISTORY:\n"
        for msg in history:
            role = "User" if msg.get("role") == "user" else "NyayaSetu"
            history_text += f"{role}: {msg.get('content')}\n"
    
    # Map language code to full name
    lang_map = {
        "en": "English", "hi": "Hindi", "bn": "Bengali", "te": "Telugu", 
        "ta": "Tamil", "mr": "Marathi", "kn": "Kannada", "ml": "Malayalam"
    }
    target_lang = lang_map.get(language, "English")

    full_prompt = f"""{SYSTEM_PROMPT}

CONTEXT FROM LEGAL DOCUMENTS:
{context_text}

{history_text}
USER QUERY:
{query_text}

IMPORTANT INSTRUCTION:
Answer the above query in **{target_lang}** language.

ANSWER:
"""

    # 3. Generate Response (Structured Mode)
    # Inject JSON formatting instruction
    json_instruction = """
    
    IMPORTANT: Provide your response in JSON format.
    Return a list of objects, where each object has a 'title' (optional) and a 'content' (the explanation).
    Structure:
    [
      { "title": "Right to Equality", "content": "You are treated equally..." },
      { "title": "Next Point", "content": "..." }
    ]
    Do not wrap in markdown code blocks. Just valid JSON.
    """
    final_prompt = full_prompt + json_instruction

    retries = 3
    final_response_text = ""
    
    # Configure for JSON
    generation_config = genai.types.GenerationConfig(
        candidate_count=1,
        max_output_tokens=2048,
        temperature=0.7,
        response_mime_type="application/json",
    )
    
    # Model Priority List
    # Try gemini-3-flash-preview first, then fallback to gemini-2.5-flash
    # Note: Using known valid model names. If user specified custom names, we use them.
    # Assuming 'gemini-1.5-flash' is the actual stable one, but user asked for 2.5/3.
    # I will use the user's requested names, but if they fail, I'll keep 1.5-flash as a safety net.
    # User Request: ['gemini-2.5-flash', 'gemini-3-flash-preview']
    
    # NOTE: 'gemini-3-flash-preview' and 'gemini-2.5-flash' are likely hypothetical or experimental names 
    # that might not exist yet in the public API. 
    # However, to strictly follow user instructions, I will put their requested strings.
    # BUT, to ensure the app doesn't crash if they are invalid, I will keep 1.5-flash as final fallback.
    
    models_to_try = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-1.5-flash']

    import json

    final_response_text = ""
    success = False

    for model_name in models_to_try:
        if success: break
        
        try:
            current_model = genai.GenerativeModel(model_name)
            # print(f"Trying model: {model_name}") # Debug
            
            response = current_model.generate_content(final_prompt, generation_config=generation_config)
            
            # Parse JSON
            try:
                # Clean up the response text
                text_to_parse = response.text.strip()
                
                # Remove markdown code blocks if present
                if text_to_parse.startswith("```"):
                    # Find first newline
                    first_newline = text_to_parse.find('\n')
                    if first_newline != -1:
                        text_to_parse = text_to_parse[first_newline+1:]
                    # Find last code block marker
                    last_backticks = text_to_parse.rfind("```")
                    if last_backticks != -1:
                        text_to_parse = text_to_parse[:last_backticks]
                
                text_to_parse = text_to_parse.strip()
                
                json_data = json.loads(text_to_parse)
                
                # Convert to Markdown bullets
                markdown_output = ""
                items = json_data
                if isinstance(json_data, dict):
                     for key, val in json_data.items():
                        if isinstance(val, list):
                            items = val
                            break
                            
                if isinstance(items, list):
                    for item in items:
                        title = item.get('title', '').strip()
                        content = item.get('content', '').strip()
                        if title and title.lower() != "none":
                            markdown_output += f"\n* **{title}**: {content}\n"
                        else:
                            markdown_output += f"\n* {content}\n"
                    final_response_text = markdown_output
                    success = True # Success!
                else:
                    # If it parses but isn't a list/dict-list, treat as text
                    final_response_text = str(items)  # Or keep response.text? Better to use parsed content.
                    success = True
            except json.JSONDecodeError:
                # Fallback: Try to use regex to find the JSON list part
                # Sometimes model says "Here is the JSON: [...]"
                import re
                match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if match:
                    try:
                        json_data = json.loads(match.group(0))
                        # Reuse the list formatting logic? For now, recursive call or simple logic.
                        # Duplicate logic for safety/speed:
                        markdown_output = ""
                        for item in json_data:
                            if isinstance(item, dict):
                                title = item.get('title', '').strip()
                                content = item.get('content', '').strip()
                                if title and title.lower() != "none":
                                    markdown_output += f"\n* **{title}**: {content}\n"
                                else:
                                    markdown_output += f"\n* {content}\n"
                        final_response_text = markdown_output
                        success = True
                    except:
                        final_response_text = response.text # Giving up
                        success = True
                else:
                    final_response_text = response.text
                    success = True

        except Exception as e:
            # If error (limit hit or model not found), continue to next model
            # logger.warning(f"Model {model_name} failed: {e}")
            continue
            
    if not success:
        final_response_text = "I apologize, but all AI models are currently unavailable or busy. Please try again later."
    
    return final_response_text
