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

import collections

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Memory Bank (Sliding Window)
# Stores last 5 turns: [(user, bot), (user, bot), ...]
CONVERSATION_HISTORY = collections.deque(maxlen=5)

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')

# Initialize Chroma Client
chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
collection = chroma_client.get_or_create_collection(name="legal_docs")

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

def query_rag(query_text: str):
    if not settings.GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not found in .env settings."

    # 1. Retrieve Context
    query_emb = get_query_embedding(query_text)
    
    context_text = ""
    if query_emb:
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=3,
            include=['documents', 'metadatas']
        )
        
        # Determine if we found valid results
        if results['documents'] and results['documents'][0]:
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            
            # Format context with source citations
            for i, doc in enumerate(docs):
                source = metas[i].get('source', 'Unknown')
                page = metas[i].get('page', '?')
                context_text += f"\n[Source: {source}, Page: {page}]\n{doc}\n---\n"
        else:
            context_text = "No specific relevant legal documents found in database."
    else:
        context_text = "Could not retrieve documents due to embedding error."

    # 2. Augment Prompt with History
    history_text = ""
    if CONVERSATION_HISTORY:
        history_text = "\nRECENT CONVERSATION HISTORY:\n"
        for q, a in CONVERSATION_HISTORY:
            history_text += f"User: {q}\nNyayaSetu: {a}\n"
    
    full_prompt = f"""{SYSTEM_PROMPT}

CONTEXT FROM LEGAL DOCUMENTS:
{context_text}

{history_text}
USER QUERY:
{query_text}

ANSWER:
"""

    # 3. Generate Response
    # Inject strong formatting instruction
    formatting_instruction = "\nIMPORTANT: Format your answer with clear bullet points. Ensure each bullet point is on a NEW LINE."
    final_prompt = full_prompt + formatting_instruction

    retries = 3
    final_response_text = ""
    for attempt in range(retries):
        try:
            response = model.generate_content(final_prompt)
            final_response_text = response.text
            break # Success
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait_time = 2 * (2 ** attempt)
                logger.warning(f"Rate limit hit during generation. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            elif attempt == retries - 1:
                 final_response_text = f"I encountered an error while processing your request: {str(e)}"
    
    # Post-processing: Ensure newlines before bullet points
    import re
    # Look for bullet points (*, -, or 1.) that are not preceded by a newline (ignoring start of string)
    # This regex finds a non-newline character followed immediately by a bullet marker
    final_response_text = re.sub(r'(?<!\n)([*-]|\d+\.) ', r'\n\1 ', final_response_text)

    # 4. Update Memory
    CONVERSATION_HISTORY.append((query_text, final_response_text))
    
    return final_response_text
