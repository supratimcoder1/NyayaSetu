import os
# Fix for "Could not find a suitable TLS CA certificate bundle" error
# attempting to use a non-existent PostgreSQL certificate.
os.environ.pop('CURL_CA_BUNDLE', None)

import google.generativeai as genai
import chromadb
from .config import settings
from .prompt_templates import SYSTEM_PROMPT
from . import models, judicial_engine
import time
import logging

# ... (Logging setup remains same) ...
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ... (Gemini/Chroma setup remains same) ...
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
# ...

# Initialize Chroma Client
chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
collection = chroma_client.get_or_create_collection(name="legal_docs")


def transcribe_audio(audio_bytes, mime_type="audio/webm"):
    # ... (remains same) ...
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
   # ... (remains same) ...
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

def query_rag(query_text: str, history: list = None, language: str = "en", user=None, db=None):
    if not settings.GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not found in .env settings."



    # 1. Embed the query (Standard RAG)
    # Even for judicial queries, we might need legal context (e.g. "What implies Section 420 for my case?")
    try:
        query_embedding = get_query_embedding(query_text) 
    except Exception as e:
        return f"Error generating embedding: {str(e)}"

    # 2. Retrieve from ChromaDB
    context_text = ""
    if query_embedding:
        try:
            results = collection.query(
                query_embeddings=[query_embedding], 
                n_results=3, 
                include=['documents', 'metadatas']
            )
            
            if results['documents'] and results['documents'][0]:
                docs = results['documents'][0]
                metas = results['metadatas'][0]
                
                formatted_snippets = []
                for i, doc in enumerate(docs):
                    source = metas[i].get('source', 'Unknown')
                    page = metas[i].get('page', '?')
                    # Strict Citation (Phase 6)
                    formatted_snippets.append(f"SOURCE: {source} (Page {page})\nCONTENT: {doc}")
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

CONTEXT FROM LEGAL DOCUMENTS (Primary Source):
{context_text}

{history_text}
USER QUERY:
{query_text}

IMPORTANT INSTRUCTION:
Answer the above query in **{target_lang}** language.
Only answer questions related to Indian law, constitution, and legal procedures.
Always cite your sources (e.g., "According to BNS Section X...").

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
                    except Exception:
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


def query_judicial_rag(query_text: str, history: list = None, language: str = "en", user=None, db=None, focused_case_id: int = None):
    """
    RAG Logic specifically for Judicial Procedural Guidance.
    Prioritizes User's Case Data over general legal documents.
    If focused_case_id is provided, gives deep context for that specific case.
    """
    if not settings.GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not found in .env settings."

    # 1. Fetch User's Cases (Primary Data Source)
    judicial_context = ""
    user_cases = []
    focused_case = None
    if user and db:
        user_cases = db.query(models.Case).filter(models.Case.user_id == user.id).all()
        
        # If a specific case is focused, find it
        if focused_case_id:
            focused_case = next((c for c in user_cases if c.id == focused_case_id), None)
        
        if focused_case:
            # DEEP context for the focused case
            c = focused_case
            judicial_context = f"\n=== FOCUSED CASE (User is asking about this case) ===\n"
            judicial_context += f"Case #{c.id}: {c.title}\n"
            judicial_context += f"CNR: {c.cnr_number or 'Not yet registered'}\n"
            judicial_context += f"Type: {c.case_type} | Status: {c.status} | Current Stage: {c.current_stage}\n"
            judicial_context += f"Description: {c.description}\n"
            judicial_context += f"Plaintiff: {c.plaintiff_name} (Lawyer: {c.plaintiff_lawyer})\n"
            judicial_context += f"Defendant: {c.defendant_name} (Lawyer: {c.defendant_lawyer})\n"
            judicial_context += f"User's Role: {c.user_role}\n"
            judicial_context += f"Registered: {c.created_at.strftime('%d %b %Y')}\n"
            
            # All hearing details
            if c.hearings:
                judicial_context += f"\nHEARINGS ({len(c.hearings)} total):\n"
                for i, h in enumerate(c.hearings, 1):
                    judicial_context += f"  {i}. {h.date.strftime('%d %b %Y')}"
                    if h.court_name:
                        judicial_context += f" at {h.court_name}"
                    if h.judge_name:
                        judicial_context += f" (Judge: {h.judge_name})"
                    if h.observation:
                        judicial_context += f" — {h.observation}"
                    if h.next_hearing_date:
                        judicial_context += f" | Next: {h.next_hearing_date.strftime('%d %b %Y')}"
                    judicial_context += "\n"
            else:
                judicial_context += "\nHEARINGS: None recorded yet.\n"
            
            # All evidence details
            if c.documents:
                judicial_context += f"\nEVIDENCE ({len(c.documents)} documents):\n"
                for d in c.documents:
                    judicial_context += f"  - [{d.party}] {d.title} ({d.doc_type or 'General'})"
                    if d.content:
                        judicial_context += f": {d.content[:150]}"
                    judicial_context += "\n"
            else:
                judicial_context += "\nEVIDENCE: No documents submitted yet.\n"
            
            # Judgment
            if c.judgment:
                judicial_context += f"\nJUDGMENT: {c.judgment.verdict} on {c.judgment.date.strftime('%d %b %Y')}\n"
                if c.judgment.summary:
                    judicial_context += f"Summary: {c.judgment.summary}\n"
                if c.judgment.pronounced_by:
                    judicial_context += f"Pronounced by: {c.judgment.pronounced_by}\n"
            
            # Timeline and next steps
            timeline = judicial_engine.generate_timeline(c.events, c.current_stage)
            next_step = judicial_engine.recommend_next_step(c.current_stage, c.case_type)
            judicial_context += f"\nRecommended Next Step: {next_step}\n"
            
            # Other cases (brief summary)
            other_cases = [oc for oc in user_cases if oc.id != focused_case_id]
            if other_cases:
                judicial_context += f"\nUser also has {len(other_cases)} other case(s): "
                judicial_context += ", ".join([f"{oc.title} ({oc.current_stage})" for oc in other_cases])
                judicial_context += "\n"
        
        elif user_cases:
            judicial_context = "\nUSER'S LEGAL CASES:\n"
            for case in user_cases:
                judicial_context += f"\n--- CASE #{case.id}: {case.title} ---\n"
                judicial_context += f"  CNR: {case.cnr_number or 'Not registered'}\n"
                judicial_context += f"  Type: {case.case_type} | Status: {case.status} | Stage: {case.current_stage}\n"
                judicial_context += f"  Description: {case.description or 'N/A'}\n"
                judicial_context += f"  Plaintiff: {case.plaintiff_name} (Lawyer: {case.plaintiff_lawyer})\n"
                judicial_context += f"  Defendant: {case.defendant_name} (Lawyer: {case.defendant_lawyer})\n"
                judicial_context += f"  User's Role: {case.user_role}\n"
                judicial_context += f"  Registered: {case.created_at.strftime('%d %b %Y')}\n"
                
                # Hearing info
                if case.hearings:
                    judicial_context += f"  Total Hearings: {len(case.hearings)}\n"
                    last_hearing = case.hearings[-1]
                    judicial_context += f"  Last Hearing: {last_hearing.date.strftime('%d %b %Y')}"
                    if last_hearing.observation:
                        judicial_context += f" — {last_hearing.observation[:100]}"
                    judicial_context += "\n"
                    if last_hearing.next_hearing_date:
                        judicial_context += f"  Next Hearing: {last_hearing.next_hearing_date.strftime('%d %b %Y')}\n"
                
                # Evidence info  
                plaintiff_docs = [d for d in case.documents if d.party == 'Plaintiff']
                defendant_docs = [d for d in case.documents if d.party == 'Defendant']
                judicial_context += f"  Evidence: {len(plaintiff_docs)} from Plaintiff, {len(defendant_docs)} from Defendant\n"
                
                # Judgment info
                if case.judgment:
                    judicial_context += f"  JUDGMENT: {case.judgment.verdict} on {case.judgment.date.strftime('%d %b %Y')}\n"
                    if case.judgment.summary:
                        judicial_context += f"  Judgment Summary: {case.judgment.summary[:200]}\n"
                
                # Add timeline/next steps if relevant to query
                if str(case.id) in query_text or case.title.lower() in query_text.lower() or "my case" in query_text.lower():
                     timeline = judicial_engine.generate_timeline(case.events, case.current_stage)
                     next_step = judicial_engine.recommend_next_step(case.current_stage, case.case_type)
                     judicial_context += f"  Recommended Next Step: {next_step}\n"
        else:
            judicial_context = "\nUSER'S CASES: No active cases registered in the system.\n"

    # 2. General Legal Context (Secondary Data Source - Only if needed)
    # We still fetch this because the user might ask "How do I file a divorce case?" (General procedure)
    context_text = ""
    try:
        query_embedding = get_query_embedding(query_text)
        if query_embedding:
            results = collection.query(
                query_embeddings=[query_embedding], 
                n_results=2, # Less context needed than main bot
                include=['documents', 'metadatas']
            )
            if results['documents'] and results['documents'][0]:
                 formatted_snippets = []
                 for i, doc in enumerate(results['documents'][0]):
                    source = results['metadatas'][0][i].get('source', 'Unknown')
                    formatted_snippets.append(f"SOURCE: {source}\nCONTENT: {doc}")
                 context_text = "\n---\n".join(formatted_snippets)
    except Exception as e:
        logger.warning(f"Judicial embedding failed: {e}")
        context_text = "General legal database unavailable."

    # 3. History
    history_text = ""
    if history:
        history_text = "\nRECENT CONVERSATION HISTORY:\n"
        for msg in history:
            role = "User" if msg.get("role") == "user" else "Judicial Assistant"
            history_text += f"{role}: {msg.get('content')}\n"

    # 4. Prompt Construction
    lang_map = {
        "en": "English", "hi": "Hindi", "bn": "Bengali", "te": "Telugu", 
        "ta": "Tamil", "mr": "Marathi", "kn": "Kannada", "ml": "Malayalam"
    }
    target_lang = lang_map.get(language, "English")

    # Build focused case prompt enhancement
    focused_prompt_addition = ""
    if focused_case:
        focused_prompt_addition = f"""

CRITICAL: The user has selected Case #{focused_case.id} ("{focused_case.title}") for this consultation.
All your responses MUST be about THIS specific case unless the user explicitly asks about something else.
Refer to the case by name and provide ACTIONABLE, SPECIFIC advice based on the case data above.
If the user's lawyer is 'Public Prosecutor', note that the user is representing themselves (pro se / in-person) and needs extra procedural guidance.
"""

    system_prompt = f"""You are the Judicial Procedural Guide of NyayaSetu.
Your role is to assist users specifically with their court cases and procedural queries.
You have access to their registered cases in the system, including party details, hearings, evidence, and judgments.
{focused_prompt_addition}
IMPORTANT: You MUST answer in **{target_lang}** language.

GUIDELINES:
1. IF the user asks about "my case" and cases exist in context, REFER specifically to those cases by ID/Title.
2. The user's role (Plaintiff or Defendant) is specified in the case data. TAILOR your advice to their role:
   - If user is PLAINTIFF: Focus on burden of proof, filing strategies, evidence presentation.
   - If user is DEFENDANT: Focus on defense strategies, counter-arguments, rights of the accused.
3. IF the user asks about "my case" but has NO cases, guide them on how to file a new case using the "Case Intake" module.
4. IF the user asks general procedural questions, provide standard legal procedure steps using the General Legal Context.
5. BE CONCISE and ACTION-ORIENTED. Focus on the "Next Step".
6. Do not prioritize general legal theory over specific case status.
7. Speak in a professional, empathetic, and authoritative judicial tone.
8. Reference hearing history and evidence when relevant to the user's query.
9. If the user has a Public Prosecutor as their lawyer, provide more detailed procedural guidance since they may be self-representing.
"""

    full_prompt = f"""{system_prompt}

USER'S CASE DATA:
{judicial_context}

GENERAL LEGAL CONTEXT:
{context_text}

{history_text}
USER QUERY:
{query_text}

IMPORTANT: Provide the response strictly in **{target_lang}**.
Formatted as Markdown.
"""

    # 5. Generate
    # Using the same model list and fallback logic as query_rag
    models_to_try = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-1.5-flash']
    generation_config = genai.types.GenerationConfig(
        candidate_count=1,
        max_output_tokens=1024,
        temperature=0.5, # Lower temperature for more deterministic procedural advice
    )

    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(full_prompt, generation_config=generation_config)
            return response.text
        except Exception:
            continue

    return "I apologize, but I cannot access the judicial network at the moment. Please consult the Case Tracker directly."
